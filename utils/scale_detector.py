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
        # Custom packs with classic scale
        r"^Jun's\s+DDR",
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

    def detect_scale(self, songpack_path: str, chart_data: Optional['ChartData'] = None) -> Tuple[ScaleType, float]:
        """
        Detect the rating scale type for a songpack.

        Args:
            songpack_path: Path to the songpack directory or chart file
            chart_data: Optional ChartData object for statistical analysis

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
        if chart_data:
            stats_detection = self._detect_from_statistics(chart_data)

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

    def _detect_from_statistics(self, chart_data: 'ChartData') -> Tuple[Optional[ScaleType], float]:
        """
        Detect scale type from statistical analysis of chart ratings and density.

        Strategy: Use NPS (notes per second) density to distinguish scales.
        Modern DDR uses inflated ratings with lower density, while classic DDR
        and ITG use higher density at the same rating level.

        Returns:
            Tuple of (ScaleType or None, confidence)
            - Returns (MODERN_DDR, high_confidence) if ratings suggest modern scale
            - Returns (None, 0.0) if ambiguous (need path-based detection)
        """
        if not chart_data or not chart_data.charts:
            return (None, 0.0)

        charts = chart_data.charts
        ratings = [chart.rating for chart in charts if chart.rating > 0]
        if not ratings:
            return (None, 0.0)

        max_rating = max(ratings)

        # Calculate NPS for high-rated charts
        # NPS = total_notes / song_length_seconds
        # song_length_seconds = chart_length_beats / (bpm / 60)
        def calc_nps(chart: 'NoteData') -> float:
            if chart.total_notes == 0 or not chart_data.bpms:
                return 0.0
            # Use the first BPM as baseline (simplified)
            base_bpm = chart_data.bpms[0].value if chart_data.bpms else 120.0
            # Estimate song length from note positions
            if chart.note_positions:
                last_beat = max(pos[0] for pos in chart.note_positions)
                song_length_seconds = (last_beat / base_bpm) * 60.0
                return chart.total_notes / song_length_seconds if song_length_seconds > 0 else 0.0
            return 0.0

        # Very high ratings are definitive modern DDR signal
        if max_rating > 15:
            return (ScaleType.MODERN_DDR, 0.98)
        elif max_rating > 12:
            return (ScaleType.MODERN_DDR, 0.95)
        
        # For ratings 11-12: check NPS density to distinguish extended classic from modern
        # Modern 11-12: typically ~3-4 NPS
        # Classic extended 11-12: typically ~7-10+ NPS  
        # ITG 11-12: also high density, ~6-12+ NPS
        if max_rating in (11, 12):
            high_rated = [c for c in charts if c.rating in (11, 12)]
            if high_rated:
                nps_values = [calc_nps(c) for c in high_rated]
                nps_values = [n for n in nps_values if n > 0]  # Filter out invalid
                if nps_values:
                    avg_nps = sum(nps_values) / len(nps_values)
                    # Modern 11-12s average ~3.5 NPS, classic/ITG average ~7+ NPS
                    if avg_nps >= 6.0:
                        # High NPS → likely classic DDR or ITG with extended ratings
                        return (None, 0.0)  # Fall back to path hints
                    elif avg_nps <= 4.5:
                        # Low NPS → modern DDR inflation
                        return (ScaleType.MODERN_DDR, 0.85)
                    # In between: ambiguous, fall back to path

        # For ratings 9-10: also check NPS to distinguish scales
        # Classic 9: median ~5.5 NPS, Classic 10: median ~9 NPS
        # Modern 9: lower density, Modern 10: much lower (~3-4 NPS)
        if max_rating <= 10 and max_rating >= 9:
            high_rated = [c for c in charts if c.rating in (9, 10)]
            if high_rated:
                nps_values = [calc_nps(c) for c in high_rated]
                nps_values = [n for n in nps_values if n > 0]
                if nps_values:
                    max_nps = max(nps_values)
                    # If highest rated chart has classic-level density
                    if max_nps >= 7.0:  # Classic 9-10 territory
                        return (None, 0.0)  # Ambiguous, use path
                    elif max_nps <= 4.5:  # Modern 9-10 territory
                        return (ScaleType.MODERN_DDR, 0.75)

        # No strong statistical signal - fall back to path-based detection
        return (None, 0.0)

    def _combine_detections(
        self,
        name_detection: Tuple[Optional[ScaleType], float],
        stats_detection: Optional[Tuple[Optional[ScaleType], float]]
    ) -> Tuple[ScaleType, float]:
        """
        Combine name-based and statistics-based detections.

        Priority logic:
        1. ITG/Modern DDR packs (high path confidence) → Always trust path
           - ITG packs never had rating updates
           - Modern DDR packs never had classic ratings
        2. Classic DDR packs → Use statistics to detect updated songs
           - Songs may have been updated from classic to modern scale
        3. Unknown packs → Use statistics (only way to classify)

        Returns:
            Tuple of (ScaleType, confidence)
        """
        name_scale, name_conf = name_detection
        stats_scale, stats_conf = None, 0.0

        if stats_detection and stats_detection[0] is not None:
            stats_scale, stats_conf = stats_detection

        # Priority 1: Trust ITG and Modern DDR path detection
        # These packs are consistent - never override with statistics
        if name_scale in (ScaleType.ITG, ScaleType.MODERN_DDR) and name_conf >= 0.8:
            # High confidence path detection for ITG or modern DDR
            # Don't override - these packs are internally consistent
            if stats_scale == name_scale:
                # Statistics agree - boost confidence slightly
                return (name_scale, min(1.0, name_conf + 0.05))
            else:
                # Trust path even if statistics disagree
                return (name_scale, name_conf)

        # Priority 2: Classic DDR packs - allow statistical override
        # These packs may contain songs updated to modern scale
        if name_scale == ScaleType.CLASSIC_DDR:
            if stats_scale == ScaleType.MODERN_DDR and stats_conf >= 0.85:
                # Strong statistical evidence of modern ratings
                # Override classic path detection
                return (stats_scale, stats_conf)
            elif stats_scale == ScaleType.CLASSIC_DDR or stats_scale is None:
                # Statistics agree with classic, or are ambiguous
                # Trust path detection
                return (name_scale, name_conf)
            else:
                # Weak statistical signal - trust path
                return (name_scale, name_conf)

        # Priority 3: Unknown packs - rely on statistics
        # No path information, must use statistical detection
        if name_scale is None or name_conf < 0.5:
            if stats_scale is not None and stats_conf >= 0.65:
                # Reasonable statistical confidence
                return (stats_scale, stats_conf)
            elif name_scale is not None:
                # Low confidence path detection, no better alternative
                return (name_scale, name_conf)
            else:
                # Complete unknown
                return (ScaleType.UNKNOWN, 0.0)

        # Default: use path detection
        return (name_scale, name_conf)

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
