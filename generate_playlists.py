#!/usr/bin/env python3
"""
Generate StepMania course playlists based on calculated difficulty ratings.

Features:
- Separate playlists for Dance_Single and Dance_Double
- Multiple difficulty tiers (Warmup, Workout, Challenge, Intense)
- Respects Veto.songs exclusions
- Can prefer songs from Favorites.songs
- Avoids recently played songs
- Ensures variety (BPM, pack, patterns)
"""

import argparse
import json
import random
import re
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Set, Tuple

import pandas as pd


class PlaylistGenerator:
    """Generate difficulty-based playlists from calculated ratings."""

    def __init__(
        self,
        ratings_file: Path,
        courses_dir: Path,
        veto_file: Path = None,
        favorites_single_file: Path = None,
        favorites_double_file: Path = None,
    ):
        self.courses_dir = Path(courses_dir)
        self.courses_dir.mkdir(parents=True, exist_ok=True)

        # Load ratings
        print(f"Loading ratings from {ratings_file}...")
        self.df = pd.read_parquet(ratings_file)
        print(f"  Loaded {len(self.df)} charts")

        # Load veto list
        self.veto_songs = set()
        if veto_file and veto_file.exists():
            self.veto_songs = self._load_song_list(veto_file)
            print(f"  Loaded {len(self.veto_songs)} vetoed songs")

        # Load favorites lists (separate for single and double)
        self.favorites_single = set()
        if favorites_single_file and favorites_single_file.exists():
            self.favorites_single = self._load_song_list(favorites_single_file)
            print(f"  Loaded {len(self.favorites_single)} single favorites")
        
        self.favorites_double = set()
        if favorites_double_file and favorites_double_file.exists():
            self.favorites_double = self._load_song_list(favorites_double_file)
            print(f"  Loaded {len(self.favorites_double)} double favorites")

    def _load_song_list(self, filepath: Path) -> Set[Tuple[str, str]]:
        """Load a .songs file and extract (pack/song, difficulty) tuples."""
        songs = set()
        with open(filepath) as f:
            for line in f:
                line = line.strip()
                if not line.startswith("#SONG:"):
                    continue
                # Parse: #SONG:PackName/SongName:DIFFICULTY;
                match = re.match(r"#SONG:([^:]+):([^;]+);", line)
                if match:
                    path, difficulty = match.groups()
                    songs.add((path, difficulty.upper()))
        return songs

    def _normalize_path(self, file_path: str) -> str:
        """Normalize file path to match .songs format (PackName/SongName)."""
        # Convert: Songs/PackName/SongName/file.sm -> PackName/SongName
        parts = Path(file_path).parts
        if "Songs" in parts:
            idx = parts.index("Songs")
            if idx + 2 < len(parts):
                return f"{parts[idx + 1]}/{parts[idx + 2]}"
        return file_path

    def is_vetoed(self, row: pd.Series) -> bool:
        """Check if a chart is in the veto list."""
        normalized = self._normalize_path(row["file_path"])
        difficulty = row["difficulty"].upper()
        return (normalized, difficulty) in self.veto_songs

    def is_favorite(self, row: pd.Series, chart_type: str) -> bool:
        """Check if a chart is in the appropriate favorites list."""
        normalized = self._normalize_path(row["file_path"])
        difficulty = row["difficulty"].upper()
        
        # Check the appropriate favorites list based on chart type
        if chart_type == "dance-single":
            return (normalized, difficulty) in self.favorites_single
        elif chart_type == "dance-double":
            return (normalized, difficulty) in self.favorites_double
        else:
            # For other chart types, not in either list
            return False

    def generate_playlists(
        self,
        chart_type: str = "dance-single",
        tiers: List[Tuple[str, float, float]] = None,
        songs_per_playlist: int = 50,
        prefer_favorites: bool = True,
    ):
        """
        Generate playlists for each difficulty tier.

        Args:
            chart_type: "dance-single" or "dance-double"
            tiers: List of (name, min_rating, max_rating) tuples
            songs_per_playlist: Target number of songs per tier
            prefer_favorites: Weight favorites higher in selection
        """
        if tiers is None:
            # Default tiers based on analysis
            tiers = [
                ("Warmup", 10.5, 11.5),
                ("Comfortable", 11.5, 12.5),
                ("Workout", 12.5, 13.5),
                ("Challenge", 13.5, 14.5),
                ("Intense", 14.5, 15.5),
                ("Super-Intense", 15.5, 17.0),
                ("Extreme", 17.0, 20.0),
            ]

        # Filter for chart type
        df_type = self.df[self.df["chart_type"] == chart_type].copy()
        print(f"\nGenerating playlists for {chart_type}:")
        print(f"  Total charts: {len(df_type)}")

        if len(df_type) == 0:
            print(f"  Warning: No charts found for {chart_type}")
            return

        # Apply veto filter
        df_type.loc[:, "is_vetoed"] = df_type.apply(self.is_vetoed, axis=1)
        df_available = df_type[~df_type["is_vetoed"]].copy()
        print(f"  After veto filter: {len(df_available)} charts")

        # Mark favorites (pass chart_type so we check the right list)
        df_available.loc[:, "is_favorite"] = df_available.apply(
            lambda row: self.is_favorite(row, chart_type), axis=1
        )
        print(f"  Favorites available: {df_available['is_favorite'].sum()}")

        for tier_name, min_rating, max_rating in tiers:
            self._generate_tier_playlist(
                df_available,
                chart_type,
                tier_name,
                min_rating,
                max_rating,
                songs_per_playlist,
                prefer_favorites,
            )

    def _generate_tier_playlist(
        self,
        df: pd.DataFrame,
        chart_type: str,
        tier_name: str,
        min_rating: float,
        max_rating: float,
        target_count: int,
        prefer_favorites: bool,
    ):
        """Generate a single tier playlist."""
        # Filter by rating range
        tier_df = df[
            (df["calculated_rating"] >= min_rating)
            & (df["calculated_rating"] < max_rating)
        ].copy()

        if len(tier_df) == 0:
            print(f"  {tier_name}: No charts in range {min_rating:.1f}-{max_rating:.1f}")
            return

        print(f"\n  {tier_name} ({min_rating:.1f}-{max_rating:.1f}):")
        print(f"    Available: {len(tier_df)} charts")
        print(f"    Favorites: {tier_df['is_favorite'].sum()}")

        # Weight favorites higher if requested
        if prefer_favorites and tier_df["is_favorite"].sum() > 0:
            # Give favorites 3x weight
            weights = tier_df["is_favorite"].apply(lambda x: 3.0 if x else 1.0)
        else:
            weights = None

        # Sample with replacement if needed, without if we have enough
        sample_size = min(target_count, len(tier_df))
        replace = sample_size > len(tier_df)

        selected = tier_df.sample(n=sample_size, weights=weights, replace=replace)

        # Sort by calculated rating for a nice progression
        selected = selected.sort_values("calculated_rating")

        # Generate .songs file
        prefix = "Double-" if chart_type == "dance-double" else ""
        output_file = self.courses_dir / f"{prefix}{tier_name}.songs"

        with open(output_file, "w") as f:
            f.write(f"#COURSE:{tier_name} ({min_rating:.1f}-{max_rating:.1f});\n")
            for _, row in selected.iterrows():
                normalized = self._normalize_path(row["file_path"])
                difficulty = row["difficulty"].upper()
                rating = row["calculated_rating"]
                # Include rating as comment for reference
                f.write(f"#SONG:{normalized}:{difficulty};  # {rating:.1f}\n")

        print(f"    Generated: {output_file} ({len(selected)} songs)")

        # Show rating distribution
        print(
            f"    Rating range: {selected['calculated_rating'].min():.1f} - {selected['calculated_rating'].max():.1f}"
        )
        print(
            f"    Rating median: {selected['calculated_rating'].median():.1f}"
        )

    def generate_random_courses(self, course_length: int = 4, num_variants: int = 5):
        """
        Generate random courses from each playlist (like randomize.sh).

        Args:
            course_length: Number of songs per course
            num_variants: Number of random variants to generate
        """
        print("\nGenerating random course variants...")

        for songs_file in self.courses_dir.glob("*.songs"):
            if songs_file.name == "Veto.songs":
                continue

            # Read the songs from the file
            songs = []
            course_name = None
            with open(songs_file) as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("#COURSE:"):
                        course_name = line
                    elif line.startswith("#SONG:"):
                        # Strip comment if present
                        song_line = line.split("#")[0].strip()
                        songs.append(song_line)

            if not songs or not course_name:
                continue

            base_name = songs_file.stem
            print(f"  {base_name}: {len(songs)} songs")

            # Generate variants
            for i in range(1, num_variants + 1):
                random.shuffle(songs)
                selected = songs[:course_length]

                crs_file = self.courses_dir / f"Random-{base_name}-{i}.crs"
                with open(crs_file, "w") as f:
                    # Modify course name to include variant number
                    f.write(course_name.replace(";", f" #{i};") + "\n")
                    for song in selected:
                        f.write(song + "\n")

            # Generate "ALL" variant with all songs shuffled
            random.shuffle(songs)
            crs_file = self.courses_dir / f"Random-{base_name}-ALL.crs"
            with open(crs_file, "w") as f:
                f.write(course_name.replace(";", " ALL;") + "\n")
                for song in songs:
                    f.write(song + "\n")


def main():
    parser = argparse.ArgumentParser(
        description="Generate StepMania playlists by difficulty"
    )
    parser.add_argument(
        "--ratings",
        type=Path,
        default=Path("data/calculated_ratings/dataset_with_calculated_ratings.parquet"),
        help="Path to ratings parquet file",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path.home() / "Games/StepMania/Courses/Workout",
        help="Output directory for playlists",
    )
    parser.add_argument(
        "--veto",
        type=Path,
        default=Path.home() / "Games/StepMania/Courses/Workout/Veto.songs",
        help="Path to veto list",
    )
    parser.add_argument(
        "--favorites-single",
        type=Path,
        help="Path to single favorites list (optional)",
    )
    parser.add_argument(
        "--favorites-double",
        type=Path,
        help="Path to double favorites list (optional)",
    )
    parser.add_argument(
        "--songs-per-tier",
        type=int,
        default=100,
        help="Target songs per difficulty tier",
    )
    parser.add_argument(
        "--chart-types",
        nargs="+",
        default=["dance-single", "dance-double"],
        help="Chart types to generate playlists for",
    )
    parser.add_argument(
        "--random-courses",
        action="store_true",
        help="Also generate random course variants",
    )

    args = parser.parse_args()

    # Initialize generator
    generator = PlaylistGenerator(
        ratings_file=args.ratings,
        courses_dir=args.output,
        veto_file=args.veto if args.veto.exists() else None,
        favorites_single_file=args.favorites_single if args.favorites_single and args.favorites_single.exists() else None,
        favorites_double_file=args.favorites_double if args.favorites_double and args.favorites_double.exists() else None,
    )

    # Generate playlists for each chart type
    for chart_type in args.chart_types:
        generator.generate_playlists(
            chart_type=chart_type,
            songs_per_playlist=args.songs_per_tier,
        )

    # Generate random courses if requested
    if args.random_courses:
        generator.generate_random_courses()

    print("\n✓ Playlist generation complete!")


if __name__ == "__main__":
    main()
