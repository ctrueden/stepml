"""
Test dance-solo (6-column) chart parsing.
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from parsers.sm_parser import parse_sm_file


def test_dance_solo_parsing():
    """Test that dance-solo charts are parsed correctly."""
    print("\nTest: dance-solo Chart Parsing")
    print("=" * 70)

    # Parse a file with dance-solo charts
    sm = parse_sm_file("../Songs/DDR 4th Mix PLUS/NA-NA/NA-NA.sm")

    solo_charts = [c for c in sm.charts if c.chart_type.value == 'dance-solo']

    print(f"Found {len(solo_charts)} dance-solo charts")
    assert len(solo_charts) == 3, f"Expected 3 dance-solo charts, found {len(solo_charts)}"

    # Check each chart has notes
    for chart in solo_charts:
        print(f"  {chart.difficulty.value} (rating {chart.rating}): {chart.total_notes} notes")
        assert chart.total_notes > 0, f"{chart.difficulty.value} chart has 0 notes (parsing failed)"

        # Verify 6-column format
        if chart.note_positions:
            first_note = chart.note_positions[0][1]
            assert len(first_note) == 6, f"Expected 6 columns for solo chart, got {len(first_note)}"

    # Verify specific note counts (approximate ranges)
    easy_chart = [c for c in solo_charts if c.difficulty.value == 'Easy'][0]
    assert 140 <= easy_chart.total_notes <= 160, f"Easy chart notes out of range: {easy_chart.total_notes}"

    medium_chart = [c for c in solo_charts if c.difficulty.value == 'Medium'][0]
    assert 210 <= medium_chart.total_notes <= 230, f"Medium chart notes out of range: {medium_chart.total_notes}"

    hard_chart = [c for c in solo_charts if c.difficulty.value == 'Hard'][0]
    assert 310 <= hard_chart.total_notes <= 340, f"Hard chart notes out of range: {hard_chart.total_notes}"

    print("✓ dance-solo parsing tests passed")


if __name__ == '__main__':
    print("\n" + "=" * 70)
    print("DANCE-SOLO PARSING TESTS")
    print("=" * 70)

    try:
        test_dance_solo_parsing()

        print("\n" + "=" * 70)
        print("ALL TESTS PASSED ✓")
        print("=" * 70)

    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
