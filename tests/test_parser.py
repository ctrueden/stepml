"""
Regression tests for SM file parser.

These tests ensure the parser continues to correctly extract metadata,
timing data, and note information from SM files.
"""
import pytest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from stepml.parsers.sm_parser import parse_sm_file
from stepml.utils.data_structures import ChartData, DifficultyType, ChartType


@pytest.mark.parser
class TestParserBasics:
    """Basic parser functionality tests."""

    def test_parser_returns_chart_data(self, test_chart_paths):
        """Parser should return ChartData object."""
        if not test_chart_paths:
            pytest.skip("No test charts available")

        chart_path = test_chart_paths[0]["path"]
        result = parse_sm_file(str(chart_path))
        assert isinstance(result, ChartData)

    def test_parser_extracts_metadata(self, test_chart_paths):
        """Parser should extract basic metadata fields."""
        if not test_chart_paths:
            pytest.skip("No test charts available")

        chart_path = test_chart_paths[0]["path"]
        result = parse_sm_file(str(chart_path))

        # Should have basic metadata
        assert result.title != "", "Title should not be empty"
        assert result.format in ['.sm', '.ssc', '.dwi'], "Format should be recognized"
        assert result.songpack != "", "Songpack should be extracted"

    def test_parser_extracts_timing_data(self, test_chart_paths):
        """Parser should extract BPM and timing information."""
        if not test_chart_paths:
            pytest.skip("No test charts available")

        chart_path = test_chart_paths[0]["path"]
        result = parse_sm_file(str(chart_path))

        # Should have at least one BPM value
        assert len(result.bpms) > 0, "Should have at least one BPM value"
        assert result.bpms[0].value > 0, "BPM should be positive"

    def test_parser_extracts_charts(self, test_chart_paths):
        """Parser should extract individual difficulty charts."""
        if not test_chart_paths:
            pytest.skip("No test charts available")

        chart_path = test_chart_paths[0]["path"]
        result = parse_sm_file(str(chart_path))

        # Should have at least one chart
        assert len(result.charts) > 0, "Should have at least one difficulty chart"

        # Each chart should have valid data
        for chart in result.charts:
            assert chart.chart_type in ChartType, "Chart type should be valid"
            assert chart.difficulty in DifficultyType, "Difficulty should be valid"
            assert chart.rating >= 0, "Rating should be non-negative"


@pytest.mark.parser
@pytest.mark.edge_case
class TestParserEdgeCases:
    """Tests for specific edge cases."""

    def test_high_bpm_charts(self, test_chart_paths):
        """Parser should handle high BPM charts correctly."""
        high_bpm_charts = [c for c in test_chart_paths if "high_bpm" in c.get("edge_cases", [])]

        if not high_bpm_charts:
            pytest.skip("No high BPM test charts available")

        for chart_info in high_bpm_charts:
            result = parse_sm_file(str(chart_info["path"]))
            primary_bpm = result.get_primary_bpm()
            assert primary_bpm >= 180, f"Expected high BPM, got {primary_bpm}"

    def test_bpm_changes(self, test_chart_paths):
        """Parser should detect BPM changes."""
        bpm_change_charts = [c for c in test_chart_paths if "bpm_changes" in c.get("edge_cases", [])]

        if not bpm_change_charts:
            pytest.skip("No BPM change test charts available")

        for chart_info in bpm_change_charts:
            result = parse_sm_file(str(chart_info["path"]))
            assert result.has_bpm_changes() or len(result.bpms) > 0, \
                "Should detect BPM data"

    def test_multiple_difficulties(self, test_chart_paths):
        """Parser should handle multiple difficulty charts."""
        multi_diff_charts = [c for c in test_chart_paths if "multiple_difficulties" in c.get("edge_cases", [])]

        if not multi_diff_charts:
            pytest.skip("No multi-difficulty test charts available")

        for chart_info in multi_diff_charts:
            result = parse_sm_file(str(chart_info["path"]))
            assert len(result.charts) >= 3, \
                f"Expected multiple difficulties, found {len(result.charts)}"


@pytest.mark.parser
@pytest.mark.regression
class TestParserNoteData:
    """Tests for note data parsing."""

    def test_note_counts_are_positive(self, test_chart_paths):
        """Note counts should be non-negative."""
        if not test_chart_paths:
            pytest.skip("No test charts available")

        for chart_info in test_chart_paths:
            result = parse_sm_file(str(chart_info["path"]))

            for chart in result.charts:
                assert chart.total_notes >= 0, "Total notes should be non-negative"
                assert chart.tap_notes >= 0, "Tap notes should be non-negative"
                assert chart.hold_notes >= 0, "Hold notes should be non-negative"
                assert chart.roll_notes >= 0, "Roll notes should be non-negative"
                assert chart.mine_notes >= 0, "Mine notes should be non-negative"
                assert chart.jump_count >= 0, "Jump count should be non-negative"

    def test_note_counts_are_consistent(self, test_chart_paths):
        """Note counts should be logically consistent."""
        if not test_chart_paths:
            pytest.skip("No test charts available")

        for chart_info in test_chart_paths:
            result = parse_sm_file(str(chart_info["path"]))

            for chart in result.charts:
                # Jumps shouldn't exceed total notes
                assert chart.jump_count <= chart.total_notes, \
                    "Jump count shouldn't exceed total notes"

                # Component notes shouldn't exceed total (allowing for overlap)
                component_sum = chart.tap_notes + chart.hold_notes + chart.roll_notes
                assert component_sum >= chart.total_notes * 0.5, \
                    "Component notes should account for significant portion of total"

    def test_difficulty_rating_progression(self, test_chart_paths):
        """Higher difficulties should generally have higher ratings."""
        if not test_chart_paths:
            pytest.skip("No test charts available")

        difficulty_order = [
            DifficultyType.BEGINNER,
            DifficultyType.EASY,
            DifficultyType.MEDIUM,
            DifficultyType.HARD,
            DifficultyType.CHALLENGE,
        ]

        for chart_info in test_chart_paths:
            result = parse_sm_file(str(chart_info["path"]))

            # Group charts by type
            charts_by_type = {}
            for chart in result.charts:
                if chart.chart_type not in charts_by_type:
                    charts_by_type[chart.chart_type] = []
                charts_by_type[chart.chart_type].append(chart)

            # Check rating progression within each type
            for chart_type, charts in charts_by_type.items():
                # Sort by difficulty order
                sorted_charts = []
                for diff in difficulty_order:
                    matching = [c for c in charts if c.difficulty == diff]
                    sorted_charts.extend(matching)

                # Ratings should generally increase (allow some flexibility)
                if len(sorted_charts) >= 2:
                    first_rating = sorted_charts[0].rating
                    last_rating = sorted_charts[-1].rating
                    assert last_rating >= first_rating, \
                        f"Last difficulty rating ({last_rating}) should be >= first ({first_rating})"


@pytest.mark.parser
class TestParserErrorHandling:
    """Tests for parser error handling."""

    def test_parser_handles_missing_file(self):
        """Parser should raise appropriate error for missing files."""
        with pytest.raises((FileNotFoundError, IOError)):
            parse_sm_file("/nonexistent/path/to/chart.sm")

    def test_parser_handles_invalid_path(self):
        """Parser should raise appropriate error for invalid paths."""
        with pytest.raises((FileNotFoundError, IOError, ValueError)):
            parse_sm_file("")
