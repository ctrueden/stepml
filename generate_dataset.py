"""
Dataset Generation Script for StepMania Chart Analysis

Batch processes all chart files (.sm, .ssc, .dwi) in the Songs directory,
extracts features, and exports to CSV and Parquet formats for ML training.

Usage:
    python generate_dataset.py [--songs-dir PATH] [--output-dir PATH] [--verbose]
"""

import argparse
import json
import logging
import sys
import time
from collections import defaultdict
from dataclasses import asdict
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd

from parsers.universal_parser import parse_chart_file
from features.feature_extractor import FeatureExtractor
from utils.data_structures import ChartData
from utils.scale_detector import ScaleDetector
from utils.performance_enrichment import PerformanceEnricher


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DatasetGenerator:
    """Generates ML-ready dataset from StepMania chart collection."""

    def __init__(self, songs_dir: Path, output_dir: Path, stats_file: Optional[Path] = None):
        self.songs_dir = Path(songs_dir)
        self.output_dir = Path(output_dir)
        self.feature_extractor = FeatureExtractor()
        self.scale_detector = ScaleDetector()

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
            'total_files': 0,
            'successful_parses': 0,
            'failed_parses': 0,
            'total_charts': 0,
            'charts_by_format': defaultdict(int),
            'charts_by_scale': defaultdict(int),
            'charts_by_difficulty': defaultdict(int),
            'errors': []
        }

        # Output data
        self.dataset_rows = []

    def find_chart_files(self) -> List[Path]:
        """Find all chart files in the songs directory."""
        logger.info(f"Scanning {self.songs_dir} for chart files...")

        chart_files = []
        for ext in ['*.sm', '*.ssc', '*.dwi']:
            found = list(self.songs_dir.rglob(ext))
            chart_files.extend(found)
            logger.info(f"  Found {len(found)} {ext} files")

        self.stats['total_files'] = len(chart_files)
        logger.info(f"Total chart files found: {len(chart_files)}")
        return sorted(chart_files)

    def extract_pack_name(self, file_path: Path) -> str:
        """Extract the song pack name from file path."""
        # Assuming structure: .../Songs/PackName/SongName/chart.sm
        try:
            parts = file_path.parts
            songs_idx = parts.index('Songs')
            if songs_idx + 1 < len(parts):
                return parts[songs_idx + 1]
        except (ValueError, IndexError):
            pass
        return 'Unknown'

    def process_chart_file(self, file_path: Path) -> Optional[ChartData]:
        """Parse a single chart file."""
        try:
            chart_data = parse_chart_file(str(file_path))
            self.stats['successful_parses'] += 1
            return chart_data
        except Exception as e:
            self.stats['failed_parses'] += 1
            error_msg = f"{file_path}: {str(e)}"
            self.stats['errors'].append(error_msg)
            logger.error(f"Failed to parse {file_path}: {e}")
            return None

    def extract_chart_features(self, chart_data: ChartData, file_path: Path) -> List[Dict]:
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
                normalized_rating = chart_data.normalized_ratings.get(difficulty_key, chart.rating)

                # Build complete row with metadata
                # NOTE: feature_dict is unpacked first, then we override its normalized_rating
                # with the correct value from chart_data.normalized_ratings
                row = {
                    # All extracted features (includes a default normalized_rating: 0.0)
                    **feature_dict,

                    # File metadata (override/add)
                    'file_path': str(file_path.relative_to(self.songs_dir.parent)),
                    'pack_name': pack_name,
                    'file_format': file_format,

                    # Chart metadata
                    'title': chart_data.title,
                    'artist': chart_data.artist,
                    'genre': chart_data.genre or '',
                    'credit': chart_data.credit or '',

                    # Chart-specific info
                    'chart_type': chart.chart_type.value,
                    'difficulty': chart.difficulty.value,
                    'original_rating': chart.rating,
                    'normalized_rating': normalized_rating,  # Override the 0.0 from feature_dict
                    'detected_scale': chart_data.detected_scale.value if chart_data.detected_scale else 'unknown',
                    'scale_confidence': chart_data.scale_confidence,
                }

                # Add performance features if enricher is available
                if self.performance_enricher:
                    perf_features = self.performance_enricher.get_performance_features(
                        str(file_path.relative_to(self.songs_dir.parent)),
                        chart.difficulty.value,
                        chart.chart_type.value
                    )
                    row.update(perf_features)

                rows.append(row)

                # Update statistics
                self.stats['total_charts'] += 1
                self.stats['charts_by_format'][file_format] += 1
                self.stats['charts_by_difficulty'][chart.difficulty.value] += 1
                if chart_data.detected_scale:
                    self.stats['charts_by_scale'][chart_data.detected_scale.value] += 1

            except Exception as e:
                error_msg = f"{file_path} ({chart.difficulty.value}): {str(e)}"
                self.stats['errors'].append(error_msg)
                logger.error(f"Failed to extract features from {file_path} ({chart.difficulty.value}): {e}")

        return rows

    def generate_dataset(self, verbose: bool = False) -> pd.DataFrame:
        """Generate complete dataset from all chart files."""
        logger.info("=" * 60)
        logger.info("DATASET GENERATION START")
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

        # Create DataFrame
        df = pd.DataFrame(self.dataset_rows)

        elapsed_time = time.time() - start_time
        logger.info(f"\nDataset generation complete in {elapsed_time:.2f}s")

        return df

    def save_dataset(self, df: pd.DataFrame):
        """Save dataset to CSV and Parquet formats."""
        if df.empty:
            logger.error("Cannot save empty dataset!")
            return

        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Save as CSV
        csv_path = self.output_dir / 'dataset.csv'
        logger.info(f"\nSaving CSV to {csv_path}...")
        df.to_csv(csv_path, index=False)
        logger.info(f"  Saved {len(df)} rows, {len(df.columns)} columns")

        # Save as Parquet (more efficient for large datasets)
        parquet_path = self.output_dir / 'dataset.parquet'
        logger.info(f"Saving Parquet to {parquet_path}...")
        df.to_parquet(parquet_path, index=False, compression='snappy')
        logger.info(f"  Saved {len(df)} rows, {len(df.columns)} columns")

        # Save column info
        column_info = {
            'columns': list(df.columns),
            'dtypes': {col: str(dtype) for col, dtype in df.dtypes.items()},
            'shape': df.shape
        }
        column_info_path = self.output_dir / 'dataset_info.json'
        with open(column_info_path, 'w') as f:
            json.dump(column_info, f, indent=2)
        logger.info(f"Saved column info to {column_info_path}")

    def save_statistics(self):
        """Save generation statistics to JSON."""
        stats_path = self.output_dir / 'generation_stats.json'
        logger.info(f"\nSaving statistics to {stats_path}...")

        # Convert defaultdict to regular dict for JSON serialization
        stats = {
            'total_files': self.stats['total_files'],
            'successful_parses': self.stats['successful_parses'],
            'failed_parses': self.stats['failed_parses'],
            'parse_success_rate': (
                self.stats['successful_parses'] / self.stats['total_files'] * 100
                if self.stats['total_files'] > 0 else 0
            ),
            'total_charts': self.stats['total_charts'],
            'charts_by_format': dict(self.stats['charts_by_format']),
            'charts_by_scale': dict(self.stats['charts_by_scale']),
            'charts_by_difficulty': dict(self.stats['charts_by_difficulty']),
            'error_count': len(self.stats['errors']),
            'errors': self.stats['errors'][:100]  # Limit to first 100 errors
        }

        with open(stats_path, 'w') as f:
            json.dump(stats, f, indent=2)

    def print_summary(self, df: pd.DataFrame):
        """Print dataset generation summary."""
        logger.info("\n" + "=" * 60)
        logger.info("DATASET GENERATION SUMMARY")
        logger.info("=" * 60)

        logger.info(f"\nFile Processing:")
        logger.info(f"  Total files found: {self.stats['total_files']}")
        logger.info(f"  Successfully parsed: {self.stats['successful_parses']}")
        logger.info(f"  Failed to parse: {self.stats['failed_parses']}")
        success_rate = (
            self.stats['successful_parses'] / self.stats['total_files'] * 100
            if self.stats['total_files'] > 0 else 0
        )
        logger.info(f"  Success rate: {success_rate:.1f}%")

        logger.info(f"\nChart Statistics:")
        logger.info(f"  Total charts extracted: {self.stats['total_charts']}")

        logger.info(f"\n  By format:")
        for fmt, count in sorted(self.stats['charts_by_format'].items()):
            logger.info(f"    {fmt}: {count}")

        logger.info(f"\n  By scale:")
        for scale, count in sorted(self.stats['charts_by_scale'].items()):
            logger.info(f"    {scale}: {count}")

        logger.info(f"\n  By difficulty:")
        for diff, count in sorted(self.stats['charts_by_difficulty'].items()):
            logger.info(f"    {diff}: {count}")

        if not df.empty:
            logger.info(f"\nDataset Shape:")
            logger.info(f"  Rows: {len(df)}")
            logger.info(f"  Columns: {len(df.columns)}")
            logger.info(f"  Memory usage: {df.memory_usage(deep=True).sum() / 1024**2:.2f} MB")

            logger.info(f"\nRating Statistics:")
            logger.info(f"  Original rating range: {df['original_rating'].min():.1f} - {df['original_rating'].max():.1f}")
            logger.info(f"  Normalized rating range: {df['normalized_rating'].min():.1f} - {df['normalized_rating'].max():.1f}")
            logger.info(f"  Mean normalized rating: {df['normalized_rating'].mean():.2f} ± {df['normalized_rating'].std():.2f}")

        if self.stats['errors']:
            logger.info(f"\nErrors:")
            logger.info(f"  Total errors: {len(self.stats['errors'])}")
            logger.info(f"  First 5 errors:")
            for error in self.stats['errors'][:5]:
                logger.info(f"    - {error}")

        # Performance enrichment statistics
        if self.performance_enricher:
            enrichment_stats = self.performance_enricher.get_stats()
            logger.info(f"\nPerformance Enrichment:")
            logger.info(f"  Charts with performance data: {enrichment_stats['charts_with_performance_data']}")
            logger.info(f"  Total charts processed: {enrichment_stats['total_charts_processed']}")
            logger.info(f"  Match rate: {enrichment_stats['match_rate_percent']:.1f}%")
            logger.info(f"  Songs in Stats.xml: {enrichment_stats['total_songs_in_stats']}")

            # Show performance data stats from DataFrame
            if not df.empty and 'has_performance_data' in df.columns:
                charts_with_data = df['has_performance_data'].sum()
                avg_plays = df[df['times_played'] > 0]['times_played'].mean() if any(df['times_played'] > 0) else 0
                logger.info(f"  Average plays (played charts): {avg_plays:.1f}")

                if 'best_accuracy' in df.columns:
                    accuracy_data = df[df['best_accuracy'].notna()]
                    if len(accuracy_data) > 0:
                        logger.info(f"  Charts with accuracy data: {len(accuracy_data)}")
                        logger.info(f"  Average best accuracy: {accuracy_data['best_accuracy'].mean():.2%}")

        logger.info("\n" + "=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description='Generate ML dataset from StepMania chart collection'
    )
    parser.add_argument(
        '--songs-dir',
        type=Path,
        default=Path(__file__).parent.parent / 'Songs',
        help='Path to Songs directory (default: ../Songs)'
    )
    parser.add_argument(
        '--output-dir',
        type=Path,
        default=Path(__file__).parent / 'data' / 'processed',
        help='Output directory for dataset files (default: ./data/processed)'
    )
    parser.add_argument(
        '--stats-file',
        type=Path,
        default=Path(__file__).parent.parent / 'Save' / 'LocalProfiles' / '00000000' / 'Stats.xml',
        help='Path to Stats.xml for performance enrichment (default: ../Save/LocalProfiles/00000000/Stats.xml)'
    )
    parser.add_argument(
        '--no-performance',
        action='store_true',
        help='Disable performance data enrichment'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Show progress for every file'
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

    # Generate dataset
    generator = DatasetGenerator(args.songs_dir, args.output_dir, stats_file)
    df = generator.generate_dataset(verbose=args.verbose)

    if not df.empty:
        generator.save_dataset(df)
        generator.save_statistics()
        generator.print_summary(df)

        logger.info(f"\n✓ Dataset generation complete!")
        logger.info(f"  CSV: {args.output_dir / 'dataset.csv'}")
        logger.info(f"  Parquet: {args.output_dir / 'dataset.parquet'}")
        logger.info(f"  Stats: {args.output_dir / 'generation_stats.json'}")
    else:
        logger.error("Failed to generate dataset!")
        sys.exit(1)


if __name__ == '__main__':
    main()
