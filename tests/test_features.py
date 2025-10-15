"""
Regression tests for feature extraction.

These tests ensure feature extraction continues to produce consistent,
accurate results across parser updates.
"""
import json
import pytest
from pathlib import Path

from parsers.sm_parser import parse_sm_file
from features.feature_extractor import FeatureExtractor, AdvancedFeatureExtractor
from utils.data_structures import FeatureSet


@pytest.mark.features
class TestFeatureExtraction:
    """Basic feature extraction tests."""

    def test_feature_extractor_returns_featureset(self, test_chart_paths, feature_extractor):
        """Feature extractor should return FeatureSet object."""
        if not test_chart_paths:
            pytest.skip("No test charts available")

        chart_path = test_chart_paths[0]["path"]
        chart_data = parse_sm_file(str(chart_path))

        if not chart_data.charts:
            pytest.skip("No charts found in test file")

        features = feature_extractor.extract_features(chart_data, chart_data.charts[0])
        assert isinstance(features, FeatureSet)

    def test_feature_values_are_valid(self, test_chart_paths, feature_extractor):
        """All extracted features should have valid values."""
        if not test_chart_paths:
            pytest.skip("No test charts available")

        for chart_info in test_chart_paths:
            chart_data = parse_sm_file(str(chart_info["path"]))

            for chart in chart_data.charts:
                features = feature_extractor.extract_features(chart_data, chart)

                # Density metrics should be non-negative
                assert features.notes_per_second >= 0, "NPS should be non-negative"
                assert features.average_density >= 0, "Average density should be non-negative"
                assert features.peak_density >= 0, "Peak density should be non-negative"
                assert features.density_variance >= 0, "Density variance should be non-negative"

                # Peak should be >= average
                assert features.peak_density >= features.average_density, \
                    "Peak density should be >= average density"

                # Ratios should be between 0 and 1
                assert 0 <= features.jump_ratio <= 1, "Jump ratio should be in [0,1]"
                assert 0 <= features.hold_ratio <= 1, "Hold ratio should be in [0,1]"
                assert 0 <= features.roll_ratio <= 1, "Roll ratio should be in [0,1]"
                assert 0 <= features.mine_ratio <= 1, "Mine ratio should be in [0,1]"

                # Timing metrics
                assert features.bpm_changes >= 0, "BPM changes should be non-negative"
                assert features.bpm_variance >= 0, "BPM variance should be non-negative"
                assert features.stop_count >= 0, "Stop count should be non-negative"
                assert features.total_stop_duration >= 0, "Stop duration should be non-negative"

                # Length metrics
                assert features.chart_length_seconds > 0, "Chart length should be positive"
                assert features.chart_length_beats > 0, "Chart length in beats should be positive"
                assert features.total_notes >= 0, "Total notes should be non-negative"

    def test_features_to_dict(self, test_chart_paths, feature_extractor):
        """FeatureSet.to_dict() should produce valid numerical dictionary."""
        if not test_chart_paths:
            pytest.skip("No test charts available")

        chart_path = test_chart_paths[0]["path"]
        chart_data = parse_sm_file(str(chart_path))

        if not chart_data.charts:
            pytest.skip("No charts found in test file")

        features = feature_extractor.extract_features(chart_data, chart_data.charts[0])
        feature_dict = features.to_dict()

        # Should be a dict
        assert isinstance(feature_dict, dict)

        # Should have numerical values
        for key, value in feature_dict.items():
            assert isinstance(value, (int, float)), \
                f"Feature {key} should be numerical, got {type(value)}"

        # Should have expected keys
        expected_keys = [
            'notes_per_second', 'peak_density', 'density_variance', 'average_density',
            'jump_ratio', 'hold_ratio', 'roll_ratio', 'mine_ratio',
            'bpm_changes', 'bpm_variance', 'stop_count', 'total_stop_duration',
            'total_notes', 'chart_length_seconds', 'chart_length_beats',
            'original_rating', 'scale_confidence', 'normalized_rating'
        ]

        for key in expected_keys:
            assert key in feature_dict, f"Expected feature key '{key}' not found"


@pytest.mark.features
class TestAdvancedFeatures:
    """Tests for advanced feature extraction."""

    def test_advanced_features_structure(self, test_chart_paths, advanced_feature_extractor):
        """Advanced features should return dict with expected keys."""
        if not test_chart_paths:
            pytest.skip("No test charts available")

        chart_path = test_chart_paths[0]["path"]
        chart_data = parse_sm_file(str(chart_path))

        if not chart_data.charts:
            pytest.skip("No charts found in test file")

        features = advanced_feature_extractor.extract_advanced_features(chart_data.charts[0])

        # Should be a dict
        assert isinstance(features, dict)

        # Should have expected keys
        expected_keys = ['stream_sections', 'direction_changes', 'crossover_potential']
        for key in expected_keys:
            assert key in features, f"Expected key '{key}' not found"

    def test_advanced_features_are_valid(self, test_chart_paths, advanced_feature_extractor):
        """Advanced feature values should be valid."""
        if not test_chart_paths:
            pytest.skip("No test charts available")

        for chart_info in test_chart_paths:
            chart_data = parse_sm_file(str(chart_info["path"]))

            for chart in chart_data.charts:
                features = advanced_feature_extractor.extract_advanced_features(chart)

                assert features['stream_sections'] >= 0, "Stream sections should be non-negative"
                assert features['direction_changes'] >= 0, "Direction changes should be non-negative"
                assert 0 <= features['crossover_potential'] <= 1, \
                    "Crossover potential should be in [0,1]"


@pytest.mark.features
@pytest.mark.regression
class TestFeatureRegression:
    """
    Regression tests against baseline feature extractions.

    These tests compare current feature extraction against saved baseline data
    to detect unintended changes in feature computation.
    """

    def test_features_match_baseline(self, test_chart_paths, baseline_features, feature_extractor):
        """Current features should match baseline within tolerance."""
        baseline_data = baseline_features.get("baseline_data", {})

        if not baseline_data:
            pytest.skip("No baseline data available - run generate_baseline.py first")

        # Tolerance for floating point comparisons
        RELATIVE_TOLERANCE = 0.01  # 1% relative difference
        ABSOLUTE_TOLERANCE = 0.001  # Small absolute tolerance for near-zero values

        mismatches = []

        for chart_info in test_chart_paths:
            chart_name = chart_info["name"]
            if chart_name not in baseline_data:
                continue

            chart_path = chart_info["path"]
            chart_data = parse_sm_file(str(chart_path))

            # Compare each difficulty chart
            for chart in chart_data.charts:
                chart_key = f"{chart.chart_type.value}_{chart.difficulty.value}"
                baseline_charts = baseline_data[chart_name].get("charts", {})

                if chart_key not in baseline_charts:
                    continue

                baseline_chart = baseline_charts[chart_key]

                # Extract current features
                current_features = feature_extractor.extract_features(chart_data, chart)
                current_dict = current_features.to_dict()

                # Compare each feature (skip advanced_features as it's tested separately)
                for feature_name, baseline_value in baseline_chart.items():
                    # Skip nested advanced_features dict (tested in separate test)
                    if feature_name == "advanced_features":
                        continue

                    if feature_name not in current_dict:
                        mismatches.append(
                            f"{chart_name}/{chart_key}: Feature '{feature_name}' missing in current extraction"
                        )
                        continue

                    current_value = current_dict[feature_name]

                    # Check if values match within tolerance
                    if baseline_value == 0:
                        # For zero baseline, use absolute tolerance
                        if abs(current_value) > ABSOLUTE_TOLERANCE:
                            mismatches.append(
                                f"{chart_name}/{chart_key}/{feature_name}: "
                                f"Expected ~0, got {current_value:.6f}"
                            )
                    else:
                        # For non-zero baseline, use relative tolerance
                        relative_diff = abs(current_value - baseline_value) / abs(baseline_value)
                        if relative_diff > RELATIVE_TOLERANCE:
                            mismatches.append(
                                f"{chart_name}/{chart_key}/{feature_name}: "
                                f"Expected {baseline_value:.6f}, got {current_value:.6f} "
                                f"(diff: {relative_diff*100:.2f}%)"
                            )

        # Report all mismatches
        if mismatches:
            mismatch_report = "\n".join(mismatches)
            pytest.fail(f"Feature regression detected:\n{mismatch_report}")

    def test_advanced_features_match_baseline(
        self, test_chart_paths, baseline_features, advanced_feature_extractor
    ):
        """Current advanced features should match baseline."""
        baseline_data = baseline_features.get("baseline_data", {})

        if not baseline_data:
            pytest.skip("No baseline data available - run generate_baseline.py first")

        mismatches = []

        for chart_info in test_chart_paths:
            chart_name = chart_info["name"]
            if chart_name not in baseline_data:
                continue

            chart_path = chart_info["path"]
            chart_data = parse_sm_file(str(chart_path))

            # Compare each difficulty chart
            for chart in chart_data.charts:
                chart_key = f"{chart.chart_type.value}_{chart.difficulty.value}"
                baseline_charts = baseline_data[chart_name].get("charts", {})

                if chart_key not in baseline_charts:
                    continue

                baseline_advanced = baseline_charts[chart_key].get("advanced_features", {})
                if not baseline_advanced:
                    continue

                # Extract current advanced features
                current_advanced = advanced_feature_extractor.extract_advanced_features(chart)

                # Compare each advanced feature
                for feature_name, baseline_value in baseline_advanced.items():
                    if feature_name not in current_advanced:
                        mismatches.append(
                            f"{chart_name}/{chart_key}: Advanced feature '{feature_name}' missing"
                        )
                        continue

                    current_value = current_advanced[feature_name]

                    # For integer features (counts), require exact match
                    if isinstance(baseline_value, int):
                        if current_value != baseline_value:
                            mismatches.append(
                                f"{chart_name}/{chart_key}/advanced/{feature_name}: "
                                f"Expected {baseline_value}, got {current_value}"
                            )
                    else:
                        # For float features, use tolerance
                        if abs(current_value - baseline_value) > 0.01:
                            mismatches.append(
                                f"{chart_name}/{chart_key}/advanced/{feature_name}: "
                                f"Expected {baseline_value:.4f}, got {current_value:.4f}"
                            )

        if mismatches:
            mismatch_report = "\n".join(mismatches)
            pytest.fail(f"Advanced feature regression detected:\n{mismatch_report}")


@pytest.mark.features
@pytest.mark.edge_case
class TestFeatureEdgeCases:
    """Tests for feature extraction edge cases."""

    def test_zero_note_chart_features(self):
        """Feature extraction should handle charts with no notes gracefully."""
        # This is a hypothetical edge case - parser might reject such charts
        # But feature extractor should handle it if it occurs
        pass  # Implementation depends on whether this edge case is possible

    def test_features_scale_with_difficulty(self, test_chart_paths, feature_extractor):
        """Features should generally scale with difficulty rating."""
        if not test_chart_paths:
            pytest.skip("No test charts available")

        for chart_info in test_chart_paths:
            chart_data = parse_sm_file(str(chart_info["path"]))

            if len(chart_data.charts) < 2:
                continue  # Need multiple difficulties to compare

            # Group by chart type
            charts_by_type = {}
            for chart in chart_data.charts:
                if chart.chart_type not in charts_by_type:
                    charts_by_type[chart.chart_type] = []
                charts_by_type[chart.chart_type].append(chart)

            # Check that features increase with rating
            for chart_type, charts in charts_by_type.items():
                if len(charts) < 2:
                    continue

                # Sort by rating
                sorted_charts = sorted(charts, key=lambda c: c.rating)
                lowest_chart = sorted_charts[0]
                highest_chart = sorted_charts[-1]

                # Skip if both have same rating (edge case)
                if lowest_chart.rating == highest_chart.rating:
                    continue

                lowest_features = feature_extractor.extract_features(chart_data, lowest_chart)
                highest_features = feature_extractor.extract_features(chart_data, highest_chart)

                # Higher difficulty should have higher density
                assert highest_features.notes_per_second >= lowest_features.notes_per_second, \
                    f"Higher difficulty should have higher NPS"

                # Higher difficulty should have more total notes (generally)
                # Note: Some charts may have fewer notes at higher difficulty if they're shorter
                # but they should have higher density
                assert highest_features.average_density >= lowest_features.average_density * 0.8, \
                    f"Higher difficulty should have comparable or higher density"
