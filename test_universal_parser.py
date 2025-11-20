"""
Test script for Universal parser.
"""
from pathlib import Path
import sys
sys.path.append(str(Path(__file__).parent))

from parsers.universal_parser import parse_chart_file, detect_format, is_supported_format

def test_universal_parser():
    """Test universal parser on all three formats."""
    test_files = [
        "/home/curtis/Games/StepMania/Songs/StepMania 5/Goin' Under/Goin' Under.sm",
        "/home/curtis/Games/StepMania/Songs/StepMania 5/Goin' Under/Goin' Under.ssc",
        "/home/curtis/Games/StepMania/Songs/DDR GB 2/PARANOiA Rebirth/PARANOiA Rebirth.dwi",
    ]

    print("=" * 80)
    print("UNIVERSAL PARSER TEST")
    print("=" * 80)
    print()

    for filepath in test_files:
        print(f"Testing: {filepath}")
        print("-" * 80)

        # Test format detection
        format_name = detect_format(filepath)
        is_supported = is_supported_format(filepath)
        print(f"Format Detection: {format_name}")
        print(f"Supported: {is_supported}")

        if not is_supported:
            print("⚠ Format not supported, skipping...")
            print()
            continue

        try:
            # Parse the file
            chart_data = parse_chart_file(filepath)

            print(f"Title: {chart_data.title}")
            print(f"Artist: {chart_data.artist}")
            print(f"Detected Scale: {chart_data.detected_scale.value}")
            print(f"Charts Found: {len(chart_data.charts)}")

            # List all charts
            for chart in chart_data.charts:
                key = f"{chart.chart_type.value}_{chart.difficulty.value}"
                normalized = chart_data.normalized_ratings.get(key, 0.0)
                print(f"  - {chart.chart_type.value} {chart.difficulty.value}: "
                      f"Rating {chart.rating} → {normalized:.1f} "
                      f"({chart.total_notes} notes)")

            print("✓ Parse successful!")

        except Exception as e:
            print(f"✗ Parse failed: {e}")

        print()

    # Test unsupported format
    print("Testing unsupported format:")
    print("-" * 80)
    fake_file = "test.mp3"
    print(f"File: {fake_file}")
    print(f"Format: {detect_format(fake_file)}")
    print(f"Supported: {is_supported_format(fake_file)}")
    print()

    print("=" * 80)
    print("UNIVERSAL PARSER TEST COMPLETE!")
    print("=" * 80)

if __name__ == "__main__":
    test_universal_parser()
