"""
Feature Extraction Script for StepMania Chart Analysis

Batch processes all chart files (.sm, .ssc, .dwi) in the Songs directory and
extracts features into a feature cache (features.parquet). This is by far the
slowest step of the pipeline, and its output does not depend on the rating
scale, so it runs once; generate-dataset then labels the cache for each scale.

Each chart's rating is stored as `unified_rating` (Modern DDR 1-20, as the
parsers normalize it) alongside its detected source scale, from which
generate-dataset derives the normalized rating for any target scale.

Usage:
    extract-features [--songs-dir PATH] [--output-dir PATH] [--verbose]
"""

import argparse
import json
import logging
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd
import yaml

from stepml.features.feature_extractor import FeatureExtractor
from stepml.parsers.universal_parser import parse_chart_file
from stepml.utils import get_data_dir, get_stepml_root
from stepml.utils.data_structures import ChartData, ScaleType
from stepml.utils.performance_enrichment import PerformanceEnricher
from stepml.utils.scale_detector import ScaleDetector

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class FeatureCacheBuilder:
    """Extracts scale-independent features from a StepMania chart collection."""

    def __init__(
        self,
        songs_dir: Path,
        output_dir: Path,
        stats_file: Optional[Path] = None,
        exclusions_file: Optional[Path] = None,
    ):
        self.songs_dir = Path(songs_dir)
        self.output_dir = Path(output_dir)
        self.feature_extractor = FeatureExtractor()
        self.scale_detector = ScaleDetector()

        # Pack directories to skip entirely (optional)
        self.excluded_packs = set()
        if exclusions_file and exclusions_file.exists():
            with open(exclusions_file) as f:
                entries = (yaml.safe_load(f) or {}).get("packs", [])
            self.excluded_packs = {e["pack"].lower() for e in entries}
            logger.info(
                f"Excluding {len(self.excluded_packs)} pack(s) from {exclusions_file}"
            )

        # Performance enrichment (optional)
        self.performance_enricher = None
        if stats_file and stats_file.exists():
            logger.info(f"Loading player performance data from {stats_file}")
            try:
                self.performance_enricher = PerformanceEnricher(str(stats_file))
                logger.info("✓ Performance enrichment enabled")
            except Exception as e:
                logger.warning(f"Failed to load Stats.xml: {e}")
                logger.warning("Continuing without performance enrichment")

        # Statistics tracking
        self.stats = {
            "total_files": 0,
            "successful_parses": 0,
            "failed_parses": 0,
            "total_charts": 0,
            "charts_by_format": defaultdict(int),
            "charts_by_scale": defaultdict(int),
            "charts_by_difficulty": defaultdict(int),
            "errors": [],
            "data_warnings": [],  # suspicious chart entries flagged during extraction
        }

        # Output data
        self.dataset_rows = []

    def _is_excluded(self, chart_file: Path) -> bool:
        """Whether a chart file lies in an excluded pack directory."""
        try:
            pack = chart_file.relative_to(self.songs_dir).parts[0]
        except (ValueError, IndexError):
            return False
        return pack.lower() in self.excluded_packs

    def find_chart_files(self) -> List[Path]:
        """
        Find all chart files in the songs directory.

        Follows StepMania's file priority when multiple formats exist in the same directory:
        1. SSC (highest priority)
        2. SMA
        3. SM
        4. DWI
        5. BMS
        6. KSF (lowest priority)

        Only one file per song directory is loaded (the highest priority one).
        """
        logger.info(f"Scanning {self.songs_dir} for chart files...")

        # Priority order matching StepMania's NotesLoader::LoadFromDir
        extensions = ["*.ssc", "*.sma", "*.sm", "*.dwi", "*.bms", "*.ksf"]

        # Get all song directories (directories containing at least one simfile)
        song_dirs = {}
        for ext in extensions:
            found = list(self.songs_dir.rglob(ext))
            for file_path in found:
                song_dir = file_path.parent
                song_dir_key = str(song_dir)

                # Only add if we haven't already found a higher-priority file for this directory
                if song_dir_key not in song_dirs:
                    song_dirs[song_dir_key] = file_path

        chart_files = [
            path for path in song_dirs.values() if not self._is_excluded(path)
        ]
        n_excluded = len(song_dirs) - len(chart_files)
        if n_excluded:
            logger.info(f"  Skipped {n_excluded} song(s) in excluded packs")

        # Log findings
        format_counts = {}
        for file_path in chart_files:
            ext = file_path.suffix.lower()
            format_counts[ext] = format_counts.get(ext, 0) + 1

        for ext in extensions:
            ext_key = ext.replace("*", "")  # Remove wildcard
            count = format_counts.get(ext_key, 0)
            if count > 0:
                logger.info(f"  Found {count} {ext} files")

        self.stats["total_files"] = len(chart_files)
        logger.info(
            f"Total chart files found: {len(chart_files)} (one per song directory)"
        )
        return sorted(chart_files)

    def extract_pack_name(self, file_path: Path) -> str:
        """Extract the song pack name from file path."""
        # Assuming structure: .../Songs/PackName/SongName/chart.sm
        try:
            parts = file_path.parts
            songs_idx = parts.index("Songs")
            if songs_idx + 1 < len(parts):
                return parts[songs_idx + 1]
        except (ValueError, IndexError):
            pass
        return "Unknown"

    def process_chart_file(self, file_path: Path) -> Optional[ChartData]:
        """Parse a single chart file."""
        try:
            # Note: MODERN_DDR is the unified scale, so normalized ratings come
            # out unified; generate-dataset converts them per target scale.
            chart_data = parse_chart_file(str(file_path), ScaleType.MODERN_DDR)
            self.stats["successful_parses"] += 1
            return chart_data
        except Exception as e:
            self.stats["failed_parses"] += 1
            error_msg = f"{file_path}: {str(e)}"
            self.stats["errors"].append(error_msg)
            logger.error(f"Failed to parse {file_path}: {e}")
            return None

    # Thresholds for data-quality checks
    _WARN_SPARSE_NOTES = 30  # fewer notes than this is suspicious for any rated chart
    _WARN_SPARSE_FOR_RATING = 6  # original_rating >= this with very few notes
    _WARN_HIGH_NPS = 30.0  # notes/sec above this suggests a BPM parse error
    _WARN_SHORT_SONG = 10.0  # chart length in seconds below this is suspicious

    def _check_chart_quality(self, row: Dict, file_path: Path):
        """Collect warnings for implausible chart entries."""
        title = row.get("title", "?")
        ctype = row.get("chart_type", "?")
        diff = row.get("difficulty", "?")
        rating = row.get("original_rating", 0) or 0
        nps = row.get("notes_per_second", 0) or 0
        total = row.get("total_notes", 0) or 0
        length = row.get("chart_length_seconds", 0) or 0
        path_str = str(file_path)

        issues = []
        if total < self._WARN_SPARSE_NOTES and rating >= self._WARN_SPARSE_FOR_RATING:
            issues.append(f"only {int(total)} notes but rated {rating}")
        if nps > self._WARN_HIGH_NPS:
            issues.append(f"implausibly high NPS {nps:.1f} (BPM error?)")
        if length < self._WARN_SHORT_SONG and total > 0:
            issues.append(f"chart length only {length:.1f}s")

        for issue in issues:
            self.stats["data_warnings"].append(
                {
                    "file": path_str,
                    "title": title,
                    "chart_type": ctype,
                    "difficulty": diff,
                    "original_rating": rating,
                    "issue": issue,
                }
            )

    def extract_chart_features(
        self, chart_data: ChartData, file_path: Path
    ) -> List[Dict]:
        """Extract features from all difficulty levels in a chart."""
        rows = []
        pack_name = self.extract_pack_name(file_path)
        file_format = file_path.suffix.lower()

        for chart in chart_data.charts:
            try:
                # Extract features
                features = self.feature_extractor.extract_features(chart_data, chart)
                feature_dict = features.to_dict()

                # Get normalized rating for this difficulty
                # The key format is "{chart_type}_{difficulty}"
                difficulty_key = f"{chart.chart_type.value}_{chart.difficulty.value}"
                normalized_rating = chart_data.normalized_ratings.get(
                    difficulty_key, chart.rating
                )

                # Build complete row with metadata
                # NOTE: feature_dict is unpacked first, then we override its normalized_rating
                # with the correct value from chart_data.normalized_ratings
                row = {
                    # All extracted features (includes a default normalized_rating: 0.0)
                    **feature_dict,
                    # File metadata (override/add)
                    "file_path": str(file_path.relative_to(self.songs_dir.parent)),
                    "pack_name": pack_name,
                    "file_format": file_format,
                    # Chart metadata
                    "title": chart_data.title,
                    "artist": chart_data.artist,
                    "genre": chart_data.genre or "",
                    "credit": chart_data.credit or "",
                    # Chart-specific info
                    "chart_type": chart.chart_type.value,
                    "difficulty": chart.difficulty.value,
                    "original_rating": chart.rating,
                    "normalized_rating": normalized_rating,  # Override the 0.0 from feature_dict
                    "detected_scale": chart_data.detected_scale.value
                    if chart_data.detected_scale
                    else "unknown",
                    "scale_confidence": chart_data.scale_confidence,
                }

                # Add performance features if enricher is available
                if self.performance_enricher:
                    perf_features = self.performance_enricher.get_performance_features(
                        str(file_path.relative_to(self.songs_dir.parent)),
                        chart.difficulty.value,
                        chart.chart_type.value,
                    )
                    row.update(perf_features)

                self._check_chart_quality(row, file_path)
                rows.append(row)

                # Update statistics
                self.stats["total_charts"] += 1
                self.stats["charts_by_format"][file_format] += 1
                self.stats["charts_by_difficulty"][chart.difficulty.value] += 1
                if chart_data.detected_scale:
                    self.stats["charts_by_scale"][chart_data.detected_scale.value] += 1

            except Exception as e:
                error_msg = f"{file_path} ({chart.difficulty.value}): {str(e)}"
                self.stats["errors"].append(error_msg)
                logger.error(
                    f"Failed to extract features from {file_path} ({chart.difficulty.value}): {e}"
                )

        return rows

    def extract(self, verbose: bool = False) -> pd.DataFrame:
        """Extract features from all chart files."""
        logger.info("=" * 60)
        logger.info("FEATURE EXTRACTION START")
        logger.info("=" * 60)

        start_time = time.time()

        # Find all chart files
        chart_files = self.find_chart_files()

        if not chart_files:
            logger.error("No chart files found!")
            return pd.DataFrame()

        # Process each file
        logger.info("\nProcessing chart files...")
        for i, file_path in enumerate(chart_files, 1):
            if verbose or i % 100 == 0:
                logger.info(f"  [{i}/{len(chart_files)}] {file_path.name}")

            # Parse chart file
            chart_data = self.process_chart_file(file_path)
            if chart_data is None:
                continue

            # Extract features for all difficulties
            rows = self.extract_chart_features(chart_data, file_path)
            self.dataset_rows.extend(rows)

        # Create DataFrame; normalized ratings are unified (see process_chart_file).
        df = pd.DataFrame(self.dataset_rows)
        df = df.rename(columns={"normalized_rating": "unified_rating"})

        elapsed_time = time.time() - start_time
        logger.info(f"\nFeature extraction complete in {elapsed_time:.2f}s")

        return df

    def save_features(self, df: pd.DataFrame):
        """Save the feature cache to Parquet."""
        if df.empty:
            logger.error("Cannot save empty feature cache!")
            return

        self.output_dir.mkdir(parents=True, exist_ok=True)
        parquet_path = self.output_dir / "features.parquet"
        logger.info(f"\nSaving Parquet to {parquet_path}...")
        df.to_parquet(parquet_path, index=False, compression="snappy")
        logger.info(f"  Saved {len(df)} rows, {len(df.columns)} columns")

    def save_statistics(self):
        """Save generation statistics to JSON."""
        stats_path = self.output_dir / "generation_stats.json"
        logger.info(f"\nSaving statistics to {stats_path}...")

        # Convert defaultdict to regular dict for JSON serialization
        stats = {
            "total_files": self.stats["total_files"],
            "successful_parses": self.stats["successful_parses"],
            "failed_parses": self.stats["failed_parses"],
            "parse_success_rate": (
                self.stats["successful_parses"] / self.stats["total_files"] * 100
                if self.stats["total_files"] > 0
                else 0
            ),
            "total_charts": self.stats["total_charts"],
            "charts_by_format": dict(self.stats["charts_by_format"]),
            "charts_by_scale": dict(self.stats["charts_by_scale"]),
            "charts_by_difficulty": dict(self.stats["charts_by_difficulty"]),
            "error_count": len(self.stats["errors"]),
            "errors": self.stats["errors"][:100],  # Limit to first 100 errors
            "data_warning_count": len(self.stats["data_warnings"]),
            "data_warnings": self.stats["data_warnings"],
        }

        with open(stats_path, "w") as f:
            json.dump(stats, f, indent=2)

    def print_summary(self, df: pd.DataFrame):
        """Print feature extraction summary."""
        logger.info("\n" + "=" * 60)
        logger.info("FEATURE EXTRACTION SUMMARY")
        logger.info("=" * 60)

        logger.info("\nFile Processing:")
        logger.info(f"  Total files found: {self.stats['total_files']}")
        logger.info(f"  Successfully parsed: {self.stats['successful_parses']}")
        logger.info(f"  Failed to parse: {self.stats['failed_parses']}")
        success_rate = (
            self.stats["successful_parses"] / self.stats["total_files"] * 100
            if self.stats["total_files"] > 0
            else 0
        )
        logger.info(f"  Success rate: {success_rate:.1f}%")

        logger.info("\nChart Statistics:")
        logger.info(f"  Total charts extracted: {self.stats['total_charts']}")

        logger.info("\n  By format:")
        for fmt, count in sorted(self.stats["charts_by_format"].items()):
            logger.info(f"    {fmt}: {count}")

        logger.info("\n  By scale:")
        for scale, count in sorted(self.stats["charts_by_scale"].items()):
            logger.info(f"    {scale}: {count}")

        logger.info("\n  By difficulty:")
        for diff, count in sorted(self.stats["charts_by_difficulty"].items()):
            logger.info(f"    {diff}: {count}")

        if not df.empty:
            logger.info("\nDataset Shape:")
            logger.info(f"  Rows: {len(df)}")
            logger.info(f"  Columns: {len(df.columns)}")
            logger.info(
                f"  Memory usage: {df.memory_usage(deep=True).sum() / 1024**2:.2f} MB"
            )

            logger.info("\nRating Statistics:")
            logger.info(
                f"  Original rating range: {df['original_rating'].min():.1f} - {df['original_rating'].max():.1f}"
            )
            logger.info(
                f"  Unified rating range: {df['unified_rating'].min():.1f} - {df['unified_rating'].max():.1f}"
            )
            logger.info(
                f"  Mean unified rating: {df['unified_rating'].mean():.2f} ± {df['unified_rating'].std():.2f}"
            )

        if self.stats["errors"]:
            logger.info("\nErrors:")
            logger.info(f"  Total errors: {len(self.stats['errors'])}")
            logger.info("  First 5 errors:")
            for error in self.stats["errors"][:5]:
                logger.info(f"    - {error}")

        warnings = self.stats["data_warnings"]
        logger.info(f"\nData Quality Warnings: {len(warnings)}")
        if warnings:
            logger.info(f"  {'File':<55} {'Type':<14} {'Diff':<10} {'Rtg':>4}  Issue")
            logger.info(f"  {'-' * 55} {'-' * 14} {'-' * 10} {'-' * 4}  {'-' * 40}")
            for w in warnings:
                short_file = "/".join(w["file"].replace("\\", "/").split("/")[-3:])
                logger.info(
                    f"  {short_file:<55} {w['chart_type']:<14} {w['difficulty']:<10}"
                    f" {w['original_rating']:>4}  {w['issue']}"
                )

        # Performance enrichment statistics
        if self.performance_enricher:
            enrichment_stats = self.performance_enricher.get_stats()
            logger.info("\nPerformance Enrichment:")
            logger.info(
                f"  Charts with performance data: {enrichment_stats['charts_with_performance_data']}"
            )
            logger.info(
                f"  Total charts processed: {enrichment_stats['total_charts_processed']}"
            )
            logger.info(f"  Match rate: {enrichment_stats['match_rate_percent']:.1f}%")
            logger.info(
                f"  Songs in Stats.xml: {enrichment_stats['total_songs_in_stats']}"
            )

            # Show performance data stats from DataFrame
            if not df.empty and "has_performance_data" in df.columns:
                charts_with_data = df["has_performance_data"].sum()
                logger.info(f"  Charts with performance data (df): {charts_with_data}")
                avg_plays = (
                    df[df["times_played"] > 0]["times_played"].mean()
                    if any(df["times_played"] > 0)
                    else 0
                )
                logger.info(f"  Average plays (played charts): {avg_plays:.1f}")

                if "best_accuracy" in df.columns:
                    accuracy_data = df[df["best_accuracy"].notna()]
                    if len(accuracy_data) > 0:
                        logger.info(
                            f"  Charts with accuracy data: {len(accuracy_data)}"
                        )
                        logger.info(
                            f"  Average best accuracy: {accuracy_data['best_accuracy'].mean():.2%}"
                        )

        logger.info("\n" + "=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description="Extract features from a StepMania chart collection"
    )
    stepml_root = get_stepml_root()
    data_dir = get_data_dir()

    parser.add_argument(
        "--songs-dir",
        type=Path,
        default=stepml_root.parent / "Songs",
        help="Path to Songs directory (default: ../Songs)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=data_dir / "features",
        help="Output directory for the feature cache (default: ./data/features)",
    )
    parser.add_argument(
        "--stats-file",
        type=Path,
        default=stepml_root.parent
        / "Save"
        / "LocalProfiles"
        / "00000000"
        / "Stats.xml",
        help="Path to Stats.xml for performance enrichment (default: ../Save/LocalProfiles/00000000/Stats.xml)",
    )
    parser.add_argument(
        "--exclusions",
        type=Path,
        default=stepml_root / "excluded_packs.yaml",
        help="Path to excluded packs YAML (default: excluded_packs.yaml)",
    )
    parser.add_argument(
        "--no-performance",
        action="store_true",
        help="Disable performance data enrichment",
    )
    parser.add_argument(
        "--verbose", action="store_true", help="Show progress for every file"
    )

    args = parser.parse_args()

    # Validate songs directory
    if not args.songs_dir.exists():
        logger.error(f"Songs directory not found: {args.songs_dir}")
        sys.exit(1)

    # Determine stats file (None if disabled or not found)
    stats_file = None
    if not args.no_performance:
        if args.stats_file.exists():
            stats_file = args.stats_file
        else:
            logger.warning(f"Stats.xml not found at {args.stats_file}")
            logger.warning("Continuing without performance enrichment")

    builder = FeatureCacheBuilder(
        args.songs_dir, args.output_dir, stats_file, args.exclusions
    )
    df = builder.extract(verbose=args.verbose)

    if not df.empty:
        builder.save_features(df)
        builder.save_statistics()
        builder.print_summary(df)

        logger.info("\n✓ Feature extraction complete!")
        logger.info(f"  Parquet: {args.output_dir / 'features.parquet'}")
        logger.info(f"  Stats: {args.output_dir / 'generation_stats.json'}")
    else:
        logger.error("Failed to extract features!")
        sys.exit(1)


if __name__ == "__main__":
    main()
