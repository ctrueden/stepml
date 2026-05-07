"""
Data structures for StepMania chart analysis.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple


class ScaleType(Enum):
    """Rating scale types across different game series."""

    CLASSIC_DDR = "classic_ddr"  # DDR 1st-Extreme (1-10 scale)
    MODERN_DDR = "modern_ddr"  # DDR X onwards (1-20 scale)
    ITG = "itg"  # In The Groove (1-12 scale)
    UNKNOWN = "unknown"  # Unable to determine


class DifficultyType(Enum):
    """Standard difficulty types."""

    BEGINNER = "Beginner"
    EASY = "Easy"
    MEDIUM = "Medium"
    HARD = "Hard"
    CHALLENGE = "Challenge"
    EDIT = "Edit"


class ChartType(Enum):
    """Chart play styles."""

    SINGLE = "dance-single"
    DOUBLE = "dance-double"
    COUPLE = "dance-couple"
    SOLO = "dance-solo"


@dataclass
class TimingEvent:
    """Represents a timing change in the chart."""

    beat: float
    value: float  # BPM for BPM changes, duration for stops


@dataclass
class NoteData:
    """Parsed note data for a single chart."""

    chart_type: ChartType
    difficulty: DifficultyType
    rating: int
    raw_notes: str  # Raw note string from file

    # Parsed note metrics
    total_notes: int = 0
    tap_notes: int = 0
    hold_notes: int = 0
    roll_notes: int = 0
    mine_notes: int = 0
    jump_count: int = 0

    # Timing information
    note_positions: List[Tuple[float, str]] = field(
        default_factory=list
    )  # (beat, note_pattern)


@dataclass
class ChartData:
    """Complete chart data with metadata and features."""

    # File metadata
    filepath: str
    format: str  # '.sm', '.ssc', '.dwi'
    songpack: str  # Parent directory name

    # Song metadata
    title: str = ""
    subtitle: str = ""
    artist: str = ""
    title_translit: str = ""
    subtitle_translit: str = ""
    artist_translit: str = ""
    genre: str = ""
    credit: str = ""

    # Audio/timing metadata
    music: str = ""
    offset: float = 0.0
    sample_start: float = 0.0
    sample_length: float = 0.0

    # Timing data
    bpms: List[TimingEvent] = field(default_factory=list)
    stops: List[TimingEvent] = field(default_factory=list)
    delays: List[TimingEvent] = field(default_factory=list)
    warps: List[TimingEvent] = field(default_factory=list)

    # Chart data
    charts: List[NoteData] = field(default_factory=list)

    # Scale detection
    detected_scale: ScaleType = ScaleType.UNKNOWN
    scale_confidence: float = 0.0
    normalized_ratings: Dict[str, float] = field(
        default_factory=dict
    )  # difficulty -> normalized rating

    # Extracted features (populated during feature extraction)
    features: Dict[str, float] = field(default_factory=dict)

    def get_chart(
        self, chart_type: ChartType, difficulty: DifficultyType
    ) -> Optional[NoteData]:
        """Get a specific chart by type and difficulty."""
        for chart in self.charts:
            if chart.chart_type == chart_type and chart.difficulty == difficulty:
                return chart
        return None

    def get_primary_bpm(self) -> float:
        """Get the primary (most common or starting) BPM."""
        if not self.bpms:
            return 0.0
        return self.bpms[0].value

    def has_bpm_changes(self) -> bool:
        """Check if the chart has BPM changes."""
        return len(self.bpms) > 1

    def has_stops(self) -> bool:
        """Check if the chart has stops/freezes."""
        return len(self.stops) > 0


@dataclass
class FeatureSet:
    """Organized feature set for ML models."""

    # Density metrics
    notes_per_second: float = 0.0
    peak_density: float = 0.0
    density_variance: float = 0.0
    average_density: float = 0.0

    # Pattern complexity
    jump_ratio: float = 0.0
    hold_ratio: float = 0.0
    roll_ratio: float = 0.0
    mine_ratio: float = 0.0

    # Technical elements
    bpm_changes: int = 0
    bpm_variance: float = 0.0
    stop_count: int = 0
    total_stop_duration: float = 0.0

    # Statistical
    total_notes: int = 0
    chart_length_seconds: float = 0.0
    chart_length_beats: float = 0.0

    # Scale-aware features
    original_rating: int = 0
    detected_scale: str = ""
    scale_confidence: float = 0.0
    normalized_rating: float = 0.0

    # Format metadata
    file_format: str = ""
    has_advanced_timing: bool = False

    # Spatial / center-of-mass features
    com_lateral_range: float = 0.0
    com_velocity_mean: float = 0.0
    com_velocity_peak: float = 0.0
    com_velocity_std: float = 0.0
    com_direction_changes: float = 0.0
    cross_pad_rate: float = 0.0

    # Facing / footwork features
    crossover_rate: float = 0.0
    facing_changes_per_beat: float = 0.0

    # Rhythm variability
    note_interval_std: float = 0.0

    # Gallop / stream rhythm features
    # same_col_repeat_ratio: fraction of notes that re-tap the same column as
    #   the immediately preceding note within ≤ 1 beat (quarter note).
    #   Catches both gallop orientations:
    #     "AB bC" — short b immediately after B (gap ≤ 0.25 beats)
    #     "A bB"  — free re-tap B after short transition b (gap 0.5–0.75)
    #   High values reduce effective difficulty relative to raw NPS because
    #   the foot is already in position for these taps.
    same_col_repeat_ratio: float = 0.0
    # stream_ratio: fraction of notes that are interior to a sustained fast run
    #   (both the preceding AND following interval are ≤ 16th note, ≤ 0.25 beats,
    #   and the note does NOT share a column with its neighbours).
    #   Genuinely hard — no free taps, foot must travel each step.
    stream_ratio: float = 0.0

    # Stamina features (12th-note / triplet threshold: gap ≤ 1/3 beat)
    # max_run_seconds: duration of the longest single continuous dense run.
    #   Captures the peak sustained effort required without recovery.
    max_run_seconds: float = 0.0
    # stream_fraction: fraction of chart time spent inside dense runs.
    #   Distinguishes long charts that are mostly rest from those that
    #   sustain high-speed stepping throughout (e.g. triplet marathons).
    stream_fraction: float = 0.0
    # stream_nps: notes per second *during* dense run sections only.
    #   Overall NPS averages in rests and can severely understate how fast
    #   the streaming passages actually are.  A chart with NPS=6 but
    #   stream_nps=9.5 (triplets at 170 BPM) is much harder than one with
    #   NPS=6 and stream_nps=6.5 (widely-spaced 8th notes with brief bursts).
    stream_nps: float = 0.0

    def to_dict(self) -> Dict[str, float]:
        """Convert to dictionary for ML models."""
        result = {}
        for key, value in self.__dict__.items():
            if isinstance(value, (int, float)):
                result[key] = float(value)
            elif isinstance(value, bool):
                result[key] = float(value)
            elif isinstance(value, str):
                # Skip string fields for numerical features
                continue
        return result
