"""
Feature extraction for StepMania charts.
"""

from typing import Dict, List, Tuple

import numpy as np

from stepml.features import footwork
from stepml.features.timing import TimingMap
from stepml.utils.data_structures import (
    ChartData,
    FeatureSet,
    NoteData,
)


class FeatureExtractor:
    """Extract features from parsed chart data."""

    def __init__(self):
        """Initialize the feature extractor."""
        pass

    def extract_features(
        self, chart_data: ChartData, note_data: NoteData
    ) -> FeatureSet:
        """
        Extract all features from a chart.

        Args:
            chart_data: Parsed chart metadata and timing
            note_data: Parsed note data for a specific difficulty

        Returns:
            FeatureSet with all extracted features
        """
        features = FeatureSet()

        # Basic metadata
        features.original_rating = note_data.rating
        features.file_format = chart_data.format
        features.detected_scale = chart_data.detected_scale.value
        features.scale_confidence = chart_data.scale_confidence
        features.total_notes = note_data.total_notes

        # Check for advanced timing features
        features.has_advanced_timing = (
            len(chart_data.stops) > 0
            or len(chart_data.delays) > 0
            or len(chart_data.warps) > 0
        )

        # Real elapsed time of every step row (mine-only rows excluded), so
        # that speed features follow the chart's local tempo through BPM
        # changes and stops rather than a single chart-wide average.
        timing = TimingMap(chart_data)
        steps = [
            (beat, pattern)
            for beat, pattern in sorted(note_data.note_positions, key=lambda x: x[0])
            if any(c in "124" for c in pattern)
        ]
        step_times = timing.seconds([beat for beat, _ in steps])

        # Extract timing-based features
        self._extract_timing_features(chart_data, note_data, features, timing)

        # Extract pattern-based features
        self._extract_pattern_features(note_data, features)

        # Extract density features
        self._extract_density_features(note_data, features, timing, steps)

        # Extract footwork / weight-shift features
        self._extract_footwork_features(note_data, features, steps, step_times)

        # Extract rhythm variability features
        self._extract_rhythm_features(note_data, features, steps, step_times)

        # Extract stamina features
        self._extract_stamina_features(features, step_times)

        return features

    def _extract_timing_features(
        self,
        chart_data: ChartData,
        note_data: NoteData,
        features: FeatureSet,
        timing: TimingMap,
    ):
        """Extract timing-related features."""
        # BPM analysis
        features.bpm_changes = len(chart_data.bpms)

        if chart_data.bpms:
            bpm_values = [bpm.value for bpm in chart_data.bpms]
            features.bpm_variance = (
                float(np.var(bpm_values)) if len(bpm_values) > 1 else 0.0
            )

        # Stop analysis
        features.stop_count = len(chart_data.stops)
        if chart_data.stops:
            features.total_stop_duration = sum(stop.value for stop in chart_data.stops)

        # Calculate chart length in beats and seconds
        if note_data.note_positions:
            features.chart_length_beats = note_data.note_positions[-1][0]

            # Calculate time in seconds using BPM changes and stops
            if timing.valid:
                features.chart_length_seconds = float(
                    timing.seconds(features.chart_length_beats)
                )

    def _extract_pattern_features(self, note_data: NoteData, features: FeatureSet):
        """Extract pattern complexity features."""
        if note_data.total_notes == 0:
            return

        # Calculate ratios
        features.jump_ratio = note_data.jump_count / note_data.total_notes
        features.hold_ratio = note_data.hold_notes / note_data.total_notes
        features.roll_ratio = note_data.roll_notes / note_data.total_notes
        features.mine_ratio = note_data.mine_notes / note_data.total_notes

    # Width of the sliding windows used for sustained-effort features.
    _SUSTAINED_WINDOW = 30.0  # seconds

    def _extract_density_features(
        self,
        note_data: NoteData,
        features: FeatureSet,
        timing: TimingMap,
        steps: List[Tuple[float, str]],
    ):
        """Extract note density features."""
        if features.chart_length_seconds <= 0 or not steps:
            return

        # Overall density
        features.notes_per_second = (
            note_data.total_notes / features.chart_length_seconds
        )
        features.average_density = note_data.total_notes / features.chart_length_beats

        # Peak density: step rows per second in the busiest 8-beat (2-measure)
        # window. Each window is timed at the tempo in effect there, so a dense
        # burst in a fast section of a chart with BPM changes counts at full
        # speed rather than being diluted by the chart's average tempo.
        window_size = 8.0  # 8 beats (2 measures)
        beats = np.array([beat for beat, _ in steps])
        ends = np.searchsorted(beats, beats + window_size, side="left")
        spans = timing.seconds(beats + window_size) - timing.seconds(beats)
        spans = np.maximum(spans, 1e-3)
        features.peak_density = float(np.max((ends - np.arange(len(beats))) / spans))

        # Calculate density variance
        density_variance = self._calculate_density_variance(
            note_data.note_positions, window_size
        )
        features.density_variance = density_variance

    def _calculate_density_variance(
        self, note_positions: List[Tuple[float, str]], window_size: float
    ) -> float:
        """
        Calculate variance in note density across the chart.

        Args:
            note_positions: List of (beat, note_pattern) tuples
            window_size: Size of the sliding window in beats

        Returns:
            Variance in density across windows
        """
        if len(note_positions) < 2:
            return 0.0

        # Count notes in consecutive non-overlapping windows from beat 0
        # (notes past the last whole window are not counted).
        beats = np.array([beat for beat, _ in note_positions])
        num_windows = max(int(beats.max() / window_size), 1)
        window_idx = np.floor(beats / window_size).astype(int)
        window_idx = window_idx[(window_idx >= 0) & (window_idx < num_windows)]
        counts = np.bincount(window_idx, minlength=num_windows)
        return float(np.var(counts / window_size))

    # Weight shifts must move the body at least this far (panels) before
    # reversing to count; smaller wobbles are ordinary stepping in place.
    _SHIFT_MIN = 1.0
    # A shift this large means hauling the body across onto the other pad.
    _PAD_SHIFT_MIN = 2.0
    # Short window for peak lateral effort.
    _BURST_WINDOW = 4.0  # seconds
    # Window for peak pad-switching rate; longer than _BURST_WINDOW because a
    # few seconds hold only a handful of switches, too coarse to compare.
    _SWITCH_WINDOW = 10.0  # seconds

    def _extract_footwork_features(
        self,
        note_data: NoteData,
        features: FeatureSet,
        steps: List[Tuple[float, str]],
        step_times: np.ndarray,
    ):
        """Weight-shift and crossover features from a simulated foot path."""
        duration = features.chart_length_seconds
        if duration <= 0 or len(steps) < 2:
            return
        path = footwork.simulate(note_data.chart_type, steps, step_times)
        if path is None:
            return

        body = path.body_x
        travel = np.concatenate([[0.0], np.cumsum(np.abs(np.diff(body)))])
        features.body_speed_mean = float(travel[-1] / duration)
        features.body_speed_peak = self._windowed_rate(
            travel, path.times, self._BURST_WINDOW
        )
        features.body_speed_sustained = self._windowed_rate(
            travel, path.times, self._SUSTAINED_WINDOW
        )
        features.weight_shifts_per_second = (
            self._count_swings(body, self._SHIFT_MIN) / duration
        )
        features.pad_shifts_per_second = (
            self._count_swings(body, self._PAD_SHIFT_MIN) / duration
        )
        # The weight centre's lag hides switches made faster than it settles
        # (e.g. PARANOiA (X-Special) double loses 42% of them), so also count
        # switches of the feet themselves.
        switches = np.zeros(len(path.times))
        switches[self._swing_indices(path.mid_x, self._PAD_SHIFT_MIN)] = 1
        switches = np.cumsum(switches)
        features.pad_switches_per_second = float(switches[-1] / duration)
        features.pad_switches_peak = self._windowed_rate(
            switches, path.times, self._SWITCH_WINDOW
        )
        lo, hi = np.percentile(body, [5, 95])
        features.body_lateral_range = float(hi - lo)

        foot = np.cumsum(path.foot_travel)
        features.foot_speed_mean = float(foot[-1] / duration)
        features.foot_speed_peak = self._windowed_rate(
            foot, path.times, self._BURST_WINDOW
        )

        crossed = path.crossed
        entered = int(crossed[0]) + int(np.sum(crossed[1:] & ~crossed[:-1]))
        features.crossovers_per_second = entered / duration

    @staticmethod
    def _windowed_rate(cumulative: np.ndarray, times: np.ndarray, window: float):
        """Peak increase of a cumulative quantity per second over a window."""
        ends = np.searchsorted(times, times + window, side="right") - 1
        return float(np.max(cumulative[ends] - cumulative) / window)

    @classmethod
    def _count_swings(cls, x: np.ndarray, amplitude: float) -> int:
        """Count monotone legs of at least `amplitude` (zigzag with hysteresis)."""
        return len(cls._swing_indices(x, amplitude))

    @staticmethod
    def _swing_indices(x: np.ndarray, amplitude: float) -> List[int]:
        """Indices at which each monotone leg of at least `amplitude` registers."""
        swings = []
        direction = 0
        lo = hi = extreme = x[0]
        for i in range(1, len(x)):
            v = x[i]
            if direction == 0:
                lo, hi = min(lo, v), max(hi, v)
                if v - lo >= amplitude:
                    direction, extreme = 1, v
                    swings.append(i)
                elif hi - v >= amplitude:
                    direction, extreme = -1, v
                    swings.append(i)
            elif direction * (v - extreme) > 0:
                extreme = v
            elif abs(v - extreme) >= amplitude:
                direction, extreme = -direction, v
                swings.append(i)
        return swings

    # A same-column re-tap counts as a "free" repeat gallop if the note
    # sharing that column occurred within this many beats (catches both
    # AB bC and A bB gallop orientations).
    _SAME_COL_WINDOW = 1.0  # beats

    # Threshold for "dense" stepping, in real time: ~5.5 steps/second or
    # faster. Measured in seconds rather than beats so tempo counts: 8th notes
    # at 220 BPM (0.136 s apart) are a stream, 16ths at 80 BPM (0.19 s) are not.
    _DENSE_SECONDS = 0.18

    def _extract_rhythm_features(
        self,
        note_data: NoteData,
        features: FeatureSet,
        steps: List[Tuple[float, str]],
        step_times: np.ndarray,
    ):
        """Note interval std, same-column repeat ratio, and stream ratio."""
        n = len(steps)
        if n < 2:
            return

        beats = np.array([p[0] for p in steps])
        intervals = np.diff(beats)
        gaps = np.diff(step_times)
        features.note_interval_std = float(intervals.std())

        # ------------------------------------------------------------------ #
        # same_col_repeat_ratio                                                #
        #   Note i is a "free" tap if it shares at least one active column    #
        #   with its immediately preceding note AND the gap between them is   #
        #   ≤ _SAME_COL_WINDOW beats.  Catches both gallop orientations:     #
        #     "AB bC" — b follows B with a short gap, same column            #
        #     "A bB"  — B follows b with a longer gap but same column as A   #
        # stream_ratio                                                         #
        #   Note i is a stream interior note if both the preceding AND        #
        #   following gaps are ≤ _DENSE_SECONDS AND the note does NOT share   #
        #   a column with either neighbor.                                    #
        # ------------------------------------------------------------------ #
        same_col_repeat = 0
        stream_interior = 0

        for i in range(1, n):
            pat_prev = steps[i - 1][1]
            pat_curr = steps[i][1]

            col_overlap = any(a == "1" and b == "1" for a, b in zip(pat_prev, pat_curr))

            if intervals[i - 1] <= self._SAME_COL_WINDOW and col_overlap:
                same_col_repeat += 1
                continue  # don't double-count as stream

            if gaps[i - 1] <= self._DENSE_SECONDS and i < n - 1:
                if gaps[i] <= self._DENSE_SECONDS:
                    pat_next = steps[i + 1][1]
                    col_overlap_next = any(
                        a == "1" and b == "1" for a, b in zip(pat_curr, pat_next)
                    )
                    if not col_overlap_next:
                        stream_interior += 1

        features.same_col_repeat_ratio = same_col_repeat / n
        features.stream_ratio = stream_interior / n

    def _extract_stamina_features(self, features: FeatureSet, step_times: np.ndarray):
        """Dense-run lengths and sustained step rate."""
        if features.chart_length_seconds <= 0 or len(step_times) < 4:
            return

        # Busiest stretch of continuous stepping: step rows per second over
        # the densest _SUSTAINED_WINDOW, which is what leaves a player winded.
        counts = np.arange(len(step_times), dtype=float)
        features.sustained_nps = self._windowed_rate(
            counts, step_times, self._SUSTAINED_WINDOW
        )

        # Walk gaps and collect contiguous dense runs as (start, end, rows).
        gaps = np.diff(step_times)
        runs = []
        start = None
        for i, gap in enumerate(gaps):
            if gap <= self._DENSE_SECONDS:
                if start is None:
                    start = i
            elif start is not None:
                runs.append((start, i))
                start = None
        if start is not None:
            runs.append((start, len(gaps)))

        if not runs:
            return

        run_seconds = [step_times[end] - step_times[begin] for begin, end in runs]
        run_rows = [end - begin + 1 for begin, end in runs]

        features.max_run_seconds = float(max(run_seconds))
        total_stream_seconds = float(sum(run_seconds))
        features.stream_fraction = total_stream_seconds / features.chart_length_seconds

        # Notes per second specifically during dense-run sections.
        if total_stream_seconds > 0:
            features.stream_nps = sum(run_rows) / total_stream_seconds

    def extract_all_charts(self, chart_data: ChartData) -> Dict[str, FeatureSet]:
        """
        Extract features for all charts in a ChartData object.

        Args:
            chart_data: Parsed chart data

        Returns:
            Dictionary mapping chart identifier to FeatureSet
        """
        features_dict = {}

        for note_data in chart_data.charts:
            # Create identifier
            chart_id = f"{note_data.chart_type.value}_{note_data.difficulty.value}"

            # Extract features
            features = self.extract_features(chart_data, note_data)
            features_dict[chart_id] = features

        return features_dict


class AdvancedFeatureExtractor(FeatureExtractor):
    """Extended feature extractor with advanced pattern analysis."""

    def extract_advanced_features(self, note_data: NoteData) -> Dict[str, float]:
        """
        Extract advanced features like streams, crossovers, etc.

        Args:
            note_data: Parsed note data

        Returns:
            Dictionary of advanced features
        """
        features = {}

        # Stream detection
        features["stream_sections"] = self._detect_streams(note_data)

        # Direction changes
        features["direction_changes"] = self._count_direction_changes(note_data)

        # Crossover potential
        features["crossover_potential"] = self._estimate_crossovers(note_data)

        return features

    def _detect_streams(self, note_data: NoteData) -> int:
        """
        Detect stream sections (continuous 1/8 or 1/16 note patterns).

        Args:
            note_data: Parsed note data

        Returns:
            Number of stream sections detected
        """
        if len(note_data.note_positions) < 8:
            return 0

        stream_count = 0
        in_stream = False
        consecutive_notes = 0

        sorted_positions = sorted(note_data.note_positions, key=lambda x: x[0])

        for i in range(1, len(sorted_positions)):
            beat_diff = sorted_positions[i][0] - sorted_positions[i - 1][0]

            # Check for stream tempo (1/8 or 1/16 notes = 0.125 or 0.0625 beats)
            if 0.06 <= beat_diff <= 0.13:  # Allow some tolerance
                consecutive_notes += 1
                if consecutive_notes >= 8 and not in_stream:
                    stream_count += 1
                    in_stream = True
            else:
                in_stream = False
                consecutive_notes = 0

        return stream_count

    def _count_direction_changes(self, note_data: NoteData) -> int:
        """
        Count directional changes in note patterns.

        Args:
            note_data: Parsed note data

        Returns:
            Number of direction changes
        """
        # Map columns to positions (for dance-single: L=0, D=1, U=2, R=3)
        direction_changes = 0

        prev_active_cols = None
        for _, pattern in note_data.note_positions:
            active_cols = [i for i, char in enumerate(pattern) if char in "124"]

            if prev_active_cols and active_cols:
                # Simple heuristic: check if direction switched
                if active_cols != prev_active_cols:
                    direction_changes += 1

            if active_cols:
                prev_active_cols = active_cols

        return direction_changes

    def _estimate_crossovers(self, note_data: NoteData) -> float:
        """
        Estimate crossover complexity.

        Args:
            note_data: Parsed note data

        Returns:
            Crossover complexity score
        """
        # Simple heuristic: jumps involving non-adjacent arrows suggest crossovers
        crossover_score = 0.0

        for _, pattern in note_data.note_positions:
            active_cols = [i for i, char in enumerate(pattern) if char in "124"]

            if len(active_cols) == 2:
                # Check distance between arrows
                distance = abs(active_cols[1] - active_cols[0])
                if distance > 1:  # Non-adjacent = potential crossover
                    crossover_score += 1.0

        return (
            crossover_score / len(note_data.note_positions)
            if note_data.note_positions
            else 0.0
        )
