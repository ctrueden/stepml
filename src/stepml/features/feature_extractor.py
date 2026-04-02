"""
Feature extraction for StepMania charts.
"""
import numpy as np
from typing import List, Dict, Tuple
from pathlib import Path

from stepml.utils.data_structures import ChartData, ChartType, NoteData, FeatureSet, TimingEvent


class FeatureExtractor:
    """Extract features from parsed chart data."""

    def __init__(self):
        """Initialize the feature extractor."""
        pass

    def extract_features(self, chart_data: ChartData, note_data: NoteData) -> FeatureSet:
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
            len(chart_data.stops) > 0 or
            len(chart_data.delays) > 0 or
            len(chart_data.warps) > 0
        )

        # Extract timing-based features
        self._extract_timing_features(chart_data, note_data, features)

        # Extract pattern-based features
        self._extract_pattern_features(note_data, features)

        # Extract density features
        self._extract_density_features(chart_data, note_data, features)

        # Extract technical features
        self._extract_technical_features(chart_data, note_data, features)

        # Extract spatial / COM features
        self._extract_spatial_features(chart_data, note_data, features)

        # Extract facing / footwork features
        self._extract_facing_features(note_data, features)

        # Extract rhythm variability features
        self._extract_rhythm_features(note_data, features)

        return features

    def _extract_timing_features(self, chart_data: ChartData, note_data: NoteData,
                                 features: FeatureSet):
        """Extract timing-related features."""
        # BPM analysis
        features.bpm_changes = len(chart_data.bpms)

        if chart_data.bpms:
            bpm_values = [bpm.value for bpm in chart_data.bpms]
            features.bpm_variance = float(np.var(bpm_values)) if len(bpm_values) > 1 else 0.0

        # Stop analysis
        features.stop_count = len(chart_data.stops)
        if chart_data.stops:
            features.total_stop_duration = sum(stop.value for stop in chart_data.stops)

        # Calculate chart length in beats and seconds
        if note_data.note_positions:
            features.chart_length_beats = note_data.note_positions[-1][0]

            # Calculate time in seconds using BPM
            features.chart_length_seconds = self._calculate_chart_duration(
                chart_data, features.chart_length_beats
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

    def _extract_density_features(self, chart_data: ChartData, note_data: NoteData,
                                  features: FeatureSet):
        """Extract note density features."""
        if features.chart_length_seconds <= 0 or not note_data.note_positions:
            return

        # Overall density
        features.notes_per_second = note_data.total_notes / features.chart_length_seconds
        features.average_density = note_data.total_notes / features.chart_length_beats

        # Calculate peak density using sliding window
        window_size = 8.0  # 8 beats (2 measures)
        peak_density = self._calculate_peak_density(note_data.note_positions, window_size)
        features.peak_density = peak_density

        # Calculate density variance
        density_variance = self._calculate_density_variance(note_data.note_positions, window_size)
        features.density_variance = density_variance

    def _extract_technical_features(self, chart_data: ChartData, note_data: NoteData,
                                    features: FeatureSet):
        """Extract technical difficulty features."""
        # These are handled in the basic extraction above
        # Can be extended with more complex analysis like:
        # - Crossover detection
        # - Stream detection
        # - Footwork complexity
        # - Direction change analysis
        pass

    def _calculate_chart_duration(self, chart_data: ChartData, total_beats: float) -> float:
        """
        Calculate chart duration in seconds accounting for BPM changes.

        Args:
            chart_data: Chart with BPM information
            total_beats: Total number of beats in the chart

        Returns:
            Duration in seconds
        """
        if not chart_data.bpms:
            return 0.0

        total_seconds = 0.0
        current_beat = 0.0

        # Sort BPM changes by beat
        bpm_changes = sorted(chart_data.bpms, key=lambda x: x.beat)

        for i, bpm_change in enumerate(bpm_changes):
            # Get the beat range for this BPM
            start_beat = bpm_change.beat
            if i + 1 < len(bpm_changes):
                end_beat = min(bpm_changes[i + 1].beat, total_beats)
            else:
                end_beat = total_beats

            # Calculate duration for this BPM section
            beats_in_section = end_beat - start_beat
            if beats_in_section > 0 and bpm_change.value > 0:
                # Time = beats / (BPM / 60)
                seconds_in_section = (beats_in_section * 60.0) / bpm_change.value
                total_seconds += seconds_in_section

            if end_beat >= total_beats:
                break

        return total_seconds

    def _calculate_peak_density(self, note_positions: List[Tuple[float, str]],
                               window_size: float) -> float:
        """
        Calculate peak note density using a sliding window.

        Args:
            note_positions: List of (beat, note_pattern) tuples
            window_size: Size of the sliding window in beats

        Returns:
            Maximum notes per beat in any window
        """
        if not note_positions:
            return 0.0

        max_density = 0.0

        # Sort by beat position
        sorted_positions = sorted(note_positions, key=lambda x: x[0])

        # Sliding window
        for i, (beat, _) in enumerate(sorted_positions):
            window_end = beat + window_size
            notes_in_window = 0

            # Count notes in window
            for j in range(i, len(sorted_positions)):
                if sorted_positions[j][0] < window_end:
                    notes_in_window += 1
                else:
                    break

            # Calculate density for this window
            density = notes_in_window / window_size
            max_density = max(max_density, density)

        return max_density

    def _calculate_density_variance(self, note_positions: List[Tuple[float, str]],
                                   window_size: float) -> float:
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

        densities = []
        sorted_positions = sorted(note_positions, key=lambda x: x[0])

        # Calculate density for multiple windows
        total_beats = sorted_positions[-1][0]
        num_windows = max(int(total_beats / window_size), 1)

        for window_idx in range(num_windows):
            window_start = window_idx * window_size
            window_end = window_start + window_size

            notes_in_window = sum(
                1 for beat, _ in sorted_positions
                if window_start <= beat < window_end
            )

            density = notes_in_window / window_size
            densities.append(density)

        return float(np.var(densities)) if densities else 0.0

    # ------------------------------------------------------------------ #
    # x-position lookup tables (lateral only; Up/Down share centre x)    #
    # ------------------------------------------------------------------ #
    _SINGLE_X = [-1.0,  0.0, 0.0, 1.0]   # L  D  U  R
    # Double: left pad centred at -2, right pad at +2, 2-unit gap between them
    _DOUBLE_X = [-3.0, -2.0, -2.0, -1.0,  # Left pad:  L  D  U  R
                  1.0,  2.0,  2.0,  3.0]  # Right pad: L  D  U  R

    def _col_x(self, note_data: NoteData) -> List[float]:
        return self._DOUBLE_X if note_data.chart_type == ChartType.DOUBLE else self._SINGLE_X

    def _windowed_peak(self, values: np.ndarray, beats: np.ndarray,
                       window_beats: float) -> float:
        """Mean of values in the busiest window of width window_beats."""
        if len(values) == 0:
            return 0.0
        peak = 0.0
        for i in range(len(beats)):
            mask = (beats >= beats[i]) & (beats < beats[i] + window_beats)
            if mask.any():
                peak = max(peak, float(np.mean(values[mask])))
        return peak

    def _extract_spatial_features(self, chart_data: ChartData, note_data: NoteData,
                                  features: FeatureSet):
        """Center-of-mass position, velocity, and cross-pad statistics."""
        x_pos = self._col_x(note_data)
        coms: List[float] = []
        beats: List[float] = []

        for beat, pattern in note_data.note_positions:
            active = [i for i, c in enumerate(pattern)
                      if c in '124' and i < len(x_pos)]
            if active:
                coms.append(float(np.mean([x_pos[i] for i in active])))
                beats.append(beat)

        if len(coms) < 2:
            return

        coms_arr = np.array(coms)
        beats_arr = np.array(beats)
        dbeats = np.diff(beats_arr)
        dbeats = np.where(dbeats > 0, dbeats, 1e-6)
        delta = np.diff(coms_arr)
        # velocity in beats domain; convert to units/second via BPM
        velocity_per_beat = np.abs(delta) / dbeats
        bpm = chart_data.get_primary_bpm()
        bps = bpm / 60.0 if bpm > 0 else 1.0
        velocity = velocity_per_beat * bps

        features.com_lateral_range = float(coms_arr.max() - coms_arr.min())
        features.com_velocity_mean = float(velocity.mean())
        features.com_velocity_peak = self._windowed_peak(velocity, beats_arr[1:], 8.0)
        features.com_velocity_std = float(velocity.std())

        # Direction changes normalized to per-beat rate
        raw_direction_changes = int(np.sum(np.diff(np.sign(delta)) != 0))
        features.com_direction_changes = (raw_direction_changes / features.chart_length_beats
                                          if features.chart_length_beats > 0 else 0.0)

        # Cross-pad rate: times COM crosses x=0 (pad boundary) per beat
        sign_changes = int(np.sum(np.diff(np.sign(coms_arr)) != 0))
        features.cross_pad_rate = (sign_changes / features.chart_length_beats
                                   if features.chart_length_beats > 0 else 0.0)

    def _count_crossovers_with_start(self, xs: List[float],
                                     start_foot: int) -> Tuple[int, int]:
        """
        Simulate alternating footwork starting with the given foot (0=LF, 1=RF).

        Returns (crossover_count, facing_change_count).  A crossover is any
        step where the moving foot lands on the wrong side of the standing foot.
        """
        foot_x = [-1.0, 1.0]   # [LF_x, RF_x] — reasonable starting positions
        facing = 1              # +1 forward (RF >= LF), -1 crossed
        foot_idx = start_foot
        crossovers = 0
        facing_changes = 0

        for x in xs:
            other = 1 - foot_idx
            other_x = foot_x[other]
            # Crossover: LF stepping right of RF, or RF stepping left of LF
            if (foot_idx == 0 and x > other_x) or (foot_idx == 1 and x < other_x):
                crossovers += 1
            foot_x[foot_idx] = x
            new_facing = 1 if foot_x[1] >= foot_x[0] else -1
            if new_facing != facing:
                facing_changes += 1
                facing = new_facing
            foot_idx = 1 - foot_idx

        return crossovers, facing_changes

    def _extract_facing_features(self, note_data: NoteData, features: FeatureSet):
        """Crossover rate and facing-change frequency via foot simulation."""
        x_pos = self._col_x(note_data)

        # Only track single-column steps; jumps reset foot independence
        single_xs: List[float] = []
        for _, pattern in note_data.note_positions:
            active = [i for i, c in enumerate(pattern)
                      if c in '124' and i < len(x_pos)]
            if len(active) == 1:
                single_xs.append(x_pos[active[0]])

        if len(single_xs) < 4:
            return

        # Try both starting feet; keep the result with fewer crossovers
        c0, f0 = self._count_crossovers_with_start(single_xs, 0)
        c1, f1 = self._count_crossovers_with_start(single_xs, 1)
        crossovers, facing_changes = (c0, f0) if c0 <= c1 else (c1, f1)

        features.crossover_rate = crossovers / len(single_xs)
        features.facing_changes_per_beat = (facing_changes / features.chart_length_beats
                                            if features.chart_length_beats > 0 else 0.0)

    # Threshold for "short" interval: 16th note = 1/4 beat.
    _GALLOP_SHORT = 0.25   # beats (≤ 16th note)
    # A same-column re-tap counts as a "free" repeat gallop if the note
    # sharing that column occurred within this many beats (catches both
    # AB bC and A bB gallop orientations).
    _SAME_COL_WINDOW = 1.0  # beats

    def _extract_rhythm_features(self, note_data: NoteData, features: FeatureSet):
        """Note interval std, same-column repeat ratio, and stream ratio."""
        positions = sorted(note_data.note_positions, key=lambda x: x[0])
        n = len(positions)
        if n < 2:
            return

        beats = np.array([p[0] for p in positions])
        intervals = np.diff(beats)
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
        #   following intervals are ≤ _GALLOP_SHORT (16th note) AND the note  #
        #   does NOT share a column with either neighbor.                     #
        # ------------------------------------------------------------------ #
        same_col_repeat = 0
        stream_interior = 0

        for i in range(1, n):
            gap_before = intervals[i - 1]
            pat_prev = positions[i - 1][1]
            pat_curr = positions[i][1]

            col_overlap = any(
                a == '1' and b == '1'
                for a, b in zip(pat_prev, pat_curr)
            )

            if gap_before <= self._SAME_COL_WINDOW and col_overlap:
                same_col_repeat += 1
                continue  # don't double-count as stream

            if gap_before <= self._GALLOP_SHORT and i < n - 1:
                gap_after = intervals[i]
                if gap_after <= self._GALLOP_SHORT:
                    pat_next = positions[i + 1][1]
                    col_overlap_next = any(
                        a == '1' and b == '1'
                        for a, b in zip(pat_curr, pat_next)
                    )
                    if not col_overlap_next:
                        stream_interior += 1

        features.same_col_repeat_ratio = same_col_repeat / n
        features.stream_ratio = stream_interior / n

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
        features['stream_sections'] = self._detect_streams(note_data)

        # Direction changes
        features['direction_changes'] = self._count_direction_changes(note_data)

        # Crossover potential
        features['crossover_potential'] = self._estimate_crossovers(note_data)

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
            beat_diff = sorted_positions[i][0] - sorted_positions[i-1][0]

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
            active_cols = [i for i, char in enumerate(pattern) if char in '124']

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
            active_cols = [i for i, char in enumerate(pattern) if char in '124']

            if len(active_cols) == 2:
                # Check distance between arrows
                distance = abs(active_cols[1] - active_cols[0])
                if distance > 1:  # Non-adjacent = potential crossover
                    crossover_score += 1.0

        return crossover_score / len(note_data.note_positions) if note_data.note_positions else 0.0
