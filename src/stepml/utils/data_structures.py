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
    # Holds and rolls as (column, head beat, tail beat). Not tracked for DWI.
    hold_spans: List[Tuple[int, float, float]] = field(default_factory=list)


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
    # peak_density: notes/second in the busiest 8-beat (2-measure) window.
    #   Tempo-aware (converted from notes/beat via the chart's average BPS) so a
    #   dense burst at high BPM rates harder than the same notes/beat at low BPM.
    peak_density: float = 0.0
    density_variance: float = 0.0  # variance of notes/beat across 8-beat windows
    average_density: float = 0.0  # notes/beat averaged over the whole chart

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

    # Footwork / weight-shift features, from a simulated foot path (see
    # features/footwork.py). Lateral positions are in panel widths.
    # body_speed_*: lateral travel of the body's weight centre (the feet's
    #   midpoint, low-pass filtered since weight lags footwork) per second —
    #   over the whole chart, the busiest 4 s, and the busiest 30 s. Small on
    #   single, large on double pad-to-pad play.
    body_speed_mean: float = 0.0
    body_speed_peak: float = 0.0
    body_speed_sustained: float = 0.0
    # weight_shifts_per_second: back-and-forth swings of ≥ 1 panel.
    weight_shifts_per_second: float = 0.0
    # pad_shifts_per_second: swings of ≥ 2 panels (across onto the other pad).
    pad_shifts_per_second: float = 0.0
    # pad_switches_*: like pad_shifts, but swings of the feet's raw midpoint,
    #   so fast back-and-forth between pads that the lagged weight centre
    #   smooths away still counts — over the whole chart and the busiest 10 s.
    pad_switches_per_second: float = 0.0
    pad_switches_peak: float = 0.0
    # body_lateral_range: 5th–95th percentile span of the weight centre.
    body_lateral_range: float = 0.0
    # foot_speed_*: distance travelled by both feet per second — over the
    #   whole chart and the busiest 4 s. Fast pad-to-pad footwork scores high.
    foot_speed_mean: float = 0.0
    foot_speed_peak: float = 0.0
    # crossovers_per_second: times the simulated feet enter a crossed stance.
    crossovers_per_second: float = 0.0

    # Stepping while holding: steps with the other foot while a hold or roll
    #   is held, which on double can pin one foot while the other reaches
    #   across pads.
    # hold_step_ratio: fraction of step rows taken during a hold.
    hold_step_ratio: float = 0.0
    # hold_step_reach: mean distance (panels) from the held panel to the
    #   farthest panel stepped on, over those rows.
    hold_step_reach: float = 0.0

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
    #   (both the preceding AND following gaps are ≤ 0.18 s,
    #   and the note does NOT share a column with its neighbours).
    #   Genuinely hard — no free taps, foot must travel each step.
    stream_ratio: float = 0.0

    # Stamina features ("dense" = steps ≤ 0.18 s apart, ~5.5+ steps/second)
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
    # sustained_nps: step rows per second over the busiest 30 seconds.
    sustained_nps: float = 0.0

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
