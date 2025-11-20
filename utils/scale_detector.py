"""
Scale detection for StepMania song packs.

Automatically detects which rating scale a song pack uses based on
pack name, path patterns, and statistical analysis of ratings.
"""
import re
from pathlib import Path
from typing import Tuple, List, Optional
from utils.data_structures import ScaleType, ChartData, NoteData


class ScaleDetector:
    """Detects rating scale type from songpack information."""

    # Pattern matching rules for pack name/path detection
    CLASSIC_DDR_PATTERNS = [
        # Original DDR series (1st - Extreme)
        r"^DDR\s+(1st|2nd|3rd|4th|5th|6th|7th)\s+Mix",
        r"^DDR\s+EXTREME($|\s+[^2])",  # EXTREME but not EXTREME 2
        r"^DDR\s+MAX($|\s*[^2])",      # MAX but not MAX2
        r"^DDR\s+SuperNOVA\s*1?$",     # SuperNOVA 1
        r"^DDR\s+Disney",
        r"^DDR\s+Solo",
        r"^DDRei\s+Tournamix",
        r"^DDR\s+from\s+",
        r"^DDR\s+Anime",
        # Dancing Stage series (European DDR)
        r"^DS\s+",
        r"Dancing\s+Stage",
        # Spin-offs
        r"DDRMAX",
        r"MAX2",
        r"CLUB\s+Version",
        r"LINK\s+Version",
        r"KOREA",
    ]

    MODERN_DDR_PATTERNS = [
        # Modern DDR with 1-20 scale
        r"^DDR\s+X($|\d+|\s)",         # DDR X, X2, X3 series
        r"^DDR\s+A($|\d+)?$",          # DDR A, A20, A3
        r"^DDR\s+20\d{2}",             # DDR 2013, 2014, etc.
        r"^DDR\s+SuperNOVA\s*2",       # SuperNOVA 2
        r"^DDR\s+Extreme\s+2",         # Extreme 2 (transition era)
    ]

    ITG_PATTERNS = [
        # In The Groove series
        r"^ITG($|\s+\d+)",             # ITG, ITG 2, ITG 3, etc.
        r"In\s+the\s+Groove",
        r"ITG\s+Rebirth",
        # Community packs often follow ITG scale
        r"^\[fraxtil\]",
        r"^\[SA\]",
        r"Valex.*Adventure",
        r"Sudziosis",
        r"Notice\s+Me\s+Benpai",
        r"Really\s+Long\s+Stuff",
    ]

    def __init__(self):
        """Initialize the scale detector."""
        # Compile regex patterns for performance
        self.classic_ddr_regex = [re.compile(p, re.IGNORECASE) for p in self.CLASSIC_DDR_PATTERNS]
        self.modern_ddr_regex = [re.compile(p, re.IGNORECASE) for p in self.MODERN_DDR_PATTERNS]
        self.itg_regex = [re.compile(p, re.IGNORECASE) for p in self.ITG_PATTERNS]

    def detect_scale(self, songpack_path: str, charts: Optional[List[NoteData]] = None) -> Tuple[ScaleType, float]:
        """
        Detect the rating scale type for a songpack.

        Args:
            songpack_path: Path to the songpack directory or chart file
            charts: Optional list of chart data for statistical analysis

        Returns:
            Tuple of (ScaleType, confidence_score)
            Confidence score ranges from 0.0 (uncertain) to 1.0 (certain)
        """
        # Extract songpack name from path
        path = Path(songpack_path)

        # Handle different path structures
        if path.is_file():
            # For actual files: /path/to/Songs/PackName/SongFolder/file.sm
            # Go up two levels to get PackName
            songpack_name = path.parent.parent.name
        elif path.is_dir():
            # For directories, use the directory name
            songpack_name = path.name
        else:
            # For non-existent paths (e.g., in tests), try to extract pack name
            # Assume structure like: /Songs/PackName/... or PackName/...
            parts = path.parts
            if len(parts) >= 2 and 'Songs' in parts:
                # Find 'Songs' in path and take the next part
                songs_idx = parts.index('Songs')
                if songs_idx + 1 < len(parts):
                    songpack_name = parts[songs_idx + 1]
                else:
                    songpack_name = parts[-1]
            elif len(parts) >= 2:
                # Take the first meaningful part after root
                songpack_name = parts[1] if len(parts) > 1 else parts[0]
            else:
                songpack_name = path.name

        # Pattern matching on songpack name
        name_detection = self._detect_from_name(songpack_name)

        # Statistical analysis on ratings (if available)
        stats_detection = None
        if charts:
            stats_detection = self._detect_from_statistics(charts)

        # Combine detections
        return self._combine_detections(name_detection, stats_detection)

    def _detect_from_name(self, songpack_name: str) -> Tuple[Optional[ScaleType], float]:
        """
        Detect scale type from songpack name pattern matching.

        Returns:
            Tuple of (ScaleType or None, confidence)
        """
        # Check Classic DDR patterns
        for pattern in self.classic_ddr_regex:
            if pattern.search(songpack_name):
                return (ScaleType.CLASSIC_DDR, 0.9)

        # Check Modern DDR patterns
        for pattern in self.modern_ddr_regex:
            if pattern.search(songpack_name):
                return (ScaleType.MODERN_DDR, 0.9)

        # Check ITG patterns
        for pattern in self.itg_regex:
            if pattern.search(songpack_name):
                return (ScaleType.ITG, 0.85)

        # Unknown pack name
        return (None, 0.0)

    def _detect_from_statistics(self, charts: List[NoteData]) -> Tuple[Optional[ScaleType], float]:
        """
        Detect scale type from statistical analysis of chart ratings.

        Strategy: Use rating ranges to definitively identify modern DDR scales.
        Classic DDR and ITG both used 1-10 range (ITG extended to 12), so ratings
        above 10 are a clear signal of modern DDR (1-20 scale).

        Returns:
            Tuple of (ScaleType or None, confidence)
            - Returns (MODERN_DDR, high_confidence) if max_rating > 10
            - Returns (None, 0.0) if ambiguous (all ratings <= 10)
              This signals fallback to path-based detection
        """
        if not charts:
            return (None, 0.0)

        # Extract all ratings
        ratings = [chart.rating for chart in charts if chart.rating > 0]
        if not ratings:
            return (None, 0.0)

        max_rating = max(ratings)
        min_rating = min(ratings)
        avg_rating = sum(ratings) / len(ratings)
        rating_spread = max_rating - min_rating

        # Clear modern DDR signal: classic DDR never went above 10
        if max_rating > 10:
            # The higher the max rating, the more confident we are
            if max_rating > 15:
                return (ScaleType.MODERN_DDR, 0.98)  # Very high confidence
            elif max_rating > 12:
                return (ScaleType.MODERN_DDR, 0.95)  # High confidence
            else:  # 11-12 range
                return (ScaleType.MODERN_DDR, 0.90)  # Still quite confident

        # All ratings <= 10: Check for modern scale inflation
        # In classic DDR, getting a 10 rating was very rare (only the hardest songs)
        # In modern DDR, 10 is mid-range difficulty

        # Count high ratings (9s and 10s)
        high_rating_count = sum(1 for r in ratings if r >= 9)

        # Heuristic 1: Multiple 9s or 10s strongly suggests modern
        # Classic DDR had very few 9s/10s total, so multiple for one song = modern
        if high_rating_count >= 2:
            return (ScaleType.MODERN_DDR, 0.88)  # High confidence - very strong signal

        # Heuristic 2: Single 10 with reasonable chart set
        if max_rating == 10 and len(ratings) >= 4:
            # A 10 rating with high average suggests modern scale
            if avg_rating > 5.5:
                return (ScaleType.MODERN_DDR, 0.75)
            # Even with lower average, a 10 is suspicious if there are
            # beginner/easy charts (classic 10s were standalone hard songs)
            elif min_rating <= 3 and len(ratings) >= 5:
                return (ScaleType.MODERN_DDR, 0.70)

        # Heuristic 3: Single 9 with full difficulty spread
        elif max_rating == 9 and len(ratings) >= 5 and avg_rating > 5.0:
            return (ScaleType.MODERN_DDR, 0.65)

        # Ambiguous: could be Classic DDR, ITG, or moderate modern charts
        # Return None to signal fallback to path-based detection
        return (None, 0.0)

    def _combine_detections(
        self,
        name_detection: Tuple[Optional[ScaleType], float],
        stats_detection: Optional[Tuple[Optional[ScaleType], float]]
    ) -> Tuple[ScaleType, float]:
        """
        Combine name-based and statistics-based detections.

        Strategy (statistics-first with path fallback):
        1. If statistics gives high confidence (e.g., max_rating > 10), trust it
        2. If statistics is ambiguous (None), fall back to path-based detection
        3. If both agree, boost confidence slightly

        Returns:
            Tuple of (ScaleType, confidence)
        """
        name_scale, name_conf = name_detection

        # Priority 1: High-confidence statistical detection
        # If max_rating > 10, this is definitely modern DDR regardless of path
        if stats_detection and stats_detection[0] is not None:
            stats_scale, stats_conf = stats_detection

            # High confidence from statistics (e.g., max_rating > 10)
            if stats_conf >= 0.85:
                # If path agrees, boost confidence slightly
                if name_scale == stats_scale and name_conf > 0.5:
                    combined_conf = min(1.0, stats_conf + 0.02)
                    return (stats_scale, combined_conf)
                else:
                    # Trust statistics even if path disagrees
                    return (stats_scale, stats_conf)

        # Priority 2: Path-based detection (fallback)
        # Used when statistics are ambiguous (all ratings <= 10)
        # This distinguishes between Classic DDR and ITG
        if name_scale is not None:
            # If statistics and path agree, boost confidence
            if stats_detection and stats_detection[0] == name_scale:
                combined_conf = min(1.0, name_conf + 0.05)
                return (name_scale, combined_conf)
            else:
                # Use path detection alone
                return (name_scale, name_conf)

        # No reliable detection from either source
        if stats_detection and stats_detection[0] is not None:
            # Fall back to low-confidence stats
            return stats_detection
        else:
            # Complete unknown
            return (ScaleType.UNKNOWN, 0.0)

    def detect_scale_from_chart(self, chart_data: ChartData) -> Tuple[ScaleType, float]:
        """
        Convenience method to detect scale from a ChartData object.

        Args:
            chart_data: Parsed chart data

        Returns:
            Tuple of (ScaleType, confidence)
        """
        return self.detect_scale(chart_data.filepath, chart_data.charts)

    def get_scale_info(self, scale_type: ScaleType) -> dict:
        """
        Get information about a rating scale.

        Args:
            scale_type: The scale type to get info for

        Returns:
            Dictionary with scale information
        """
        scale_info = {
            ScaleType.CLASSIC_DDR: {
                "name": "Classic DDR",
                "range": "1-10",
                "description": "Original DDR scale (1st Mix through Extreme)",
                "era": "1998-2006",
            },
            ScaleType.MODERN_DDR: {
                "name": "Modern DDR",
                "range": "1-20",
                "description": "Modern DDR scale (X onwards)",
                "era": "2008-present",
            },
            ScaleType.ITG: {
                "name": "In The Groove",
                "range": "1-12",
                "description": "ITG scale (affected by rating creep)",
                "era": "2004-present",
            },
            ScaleType.UNKNOWN: {
                "name": "Unknown",
                "range": "varies",
                "description": "Unable to determine scale",
                "era": "N/A",
            },
        }
        return scale_info.get(scale_type, scale_info[ScaleType.UNKNOWN])
