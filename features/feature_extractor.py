"""
Feature extraction for StepMania charts.
"""
import numpy as np
from typing import List, Dict, Tuple
from pathlib import Path
import sys
sys.path.append(str(Path(__file__).parent.parent))

from utils.data_structures import ChartData, NoteData, FeatureSet, TimingEvent


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
