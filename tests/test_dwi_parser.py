"""
Comprehensive tests for DWI parser.

Tests the fix for DOUBLE chart parsing and validates note counting.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from stepml.parsers.dwi_parser import parse_dwi_file


def test_zip_a_dee_doo_dah():
    """Test Zip-A-Dee-Doo-Dah parsing (includes DOUBLE charts)."""
    print("\nTest: Zip-A-Dee-Doo-Dah")
    print("=" * 70)

    dwi = parse_dwi_file("../Songs/DS feat. Disney's Rave/Zip-A-Dee-Doo-Dah/Zip-A-Dee-Doo-Dah.dwi")

    assert dwi.title == "Zip-A-Dee-Doo-Dah"
    assert len(dwi.charts) == 5  # 3 SINGLE + 2 DOUBLE

    # Test SINGLE:BASIC
    single_basic = [c for c in dwi.charts if c.chart_type.value == 'dance-single' and c.difficulty.value == 'Easy'][0]
    print(f"SINGLE Easy: {single_basic.total_notes} notes")
    assert 85 <= single_basic.total_notes <= 95, f"Expected ~89 notes, got {single_basic.total_notes}"

    # Test DOUBLE:BASIC - should have more notes than SINGLE (uses 8 panels)
    double_basic = [c for c in dwi.charts if c.chart_type.value == 'dance-double' and c.difficulty.value == 'Easy'][0]
    print(f"DOUBLE Easy: {double_basic.total_notes} notes")
    assert 110 <= double_basic.total_notes <= 130, f"Expected ~120 notes, got {double_basic.total_notes}"

    # Verify left and right notes are distributed
    left_notes = sum(1 for _, notes in double_basic.note_positions if notes[:4].count('1') > 0)
    right_notes = sum(1 for _, notes in double_basic.note_positions if notes[4:].count('1') > 0)
    print(f"  - Left side beats: {left_notes}")
    print(f"  - Right side beats: {right_notes}")
    assert left_notes > 0, "DOUBLE chart should have left-side notes"
    assert right_notes > 0, "DOUBLE chart should have right-side notes"

    print("✓ Zip-A-Dee-Doo-Dah tests passed")


def test_castlevania():
    """Test Castlevania parsing (SINGLE charts only)."""
    print("\nTest: Castlevania")
    print("=" * 70)

    dwi = parse_dwi_file("../Songs/DDR Anime Mix/Castlevania/Castlevania.dwi")

    assert dwi.title == "Castlevania - Bloody Tears Remix"
    assert len(dwi.charts) == 3  # 3 SINGLE charts

    # Test BASIC
    basic = [c for c in dwi.charts if c.difficulty.value == 'Easy'][0]
    print(f"SINGLE Easy (BASIC): {basic.total_notes} notes")
    assert 290 <= basic.total_notes <= 320, f"Expected ~306 notes, got {basic.total_notes}"

    # Test ANOTHER
    another = [c for c in dwi.charts if c.difficulty.value == 'Medium'][0]
    print(f"SINGLE Medium (ANOTHER): {another.total_notes} notes")
    assert 380 <= another.total_notes <= 410, f"Expected ~397 notes, got {another.total_notes}"

    # Test MANIAC
    maniac = [c for c in dwi.charts if c.difficulty.value == 'Challenge'][0]
    print(f"SINGLE Challenge (MANIAC): {maniac.total_notes} notes (rating {maniac.rating})")
    assert 490 <= maniac.total_notes <= 520, f"Expected ~509 notes, got {maniac.total_notes}"

    # Verify it's properly encoded with jumps
    assert maniac.jump_count > 0, "MANIAC chart should have jumps"
    print(f"  - Jump count: {maniac.jump_count}")
    print(f"  - Unique beats: {len(maniac.note_positions)}")

    print("✓ Castlevania tests passed")


def test_double_format():
    """Test that DOUBLE charts use 8-column format."""
    print("\nTest: DOUBLE Chart Format")
    print("=" * 70)

    dwi = parse_dwi_file("../Songs/DS feat. Disney's Rave/Zip-A-Dee-Doo-Dah/Zip-A-Dee-Doo-Dah.dwi")

    for chart in dwi.charts:
        if chart.chart_type.value == 'dance-double':
            # Check that note positions use 8 columns
            for beat, notes in chart.note_positions:
                assert len(notes) == 8, f"DOUBLE chart should have 8-column notes, got {len(notes)}"

            print(f"✓ DOUBLE {chart.difficulty.value} uses proper 8-column format")


def test_single_format():
    """Test that SINGLE charts use 4-column format."""
    print("\nTest: SINGLE Chart Format")
    print("=" * 70)

    dwi = parse_dwi_file("../Songs/DDR Anime Mix/Castlevania/Castlevania.dwi")

    for chart in dwi.charts:
        # Check that note positions use 4 columns
        for beat, notes in chart.note_positions[:5]:  # Check first 5
            assert len(notes) == 4, f"SINGLE chart should have 4-column notes, got {len(notes)}"

    print(f"✓ SINGLE charts use proper 4-column format")


if __name__ == '__main__':
    print("\n" + "=" * 70)
    print("DWI PARSER COMPREHENSIVE TESTS")
    print("=" * 70)

    try:
        test_zip_a_dee_doo_dah()
        test_castlevania()
        test_double_format()
        test_single_format()

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
