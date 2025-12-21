"""
Test script for SSC parser.
"""
from pathlib import Path
import sys
sys.path.append(str(Path(__file__).parent))

from parsers.ssc_parser import parse_ssc_file

def test_ssc_parser():
    """Test SSC parser on a real file."""
    # Test file path
    ssc_file = "/home/curtis/Games/StepMania/Songs/StepMania 5/Goin' Under/Goin' Under.ssc"

    print(f"Testing SSC parser on: {ssc_file}\n")
    print("=" * 80)

    # Parse the file
    chart_data = parse_ssc_file(ssc_file)

    # Display metadata
    print("METADATA")
    print("-" * 80)
    print(f"Title: {chart_data.title}")
    print(f"Artist: {chart_data.artist}")
    print(f"Genre: {chart_data.genre}")
    print(f"Version: {chart_data.version}")
    print(f"Songpack: {chart_data.songpack}")
    print(f"Format: {chart_data.format}")
    print()

    # Display timing info
    print("TIMING")
    print("-" * 80)
    print(f"Offset: {chart_data.offset:.3f}s")
    print(f"BPMs: {len(chart_data.bpms)} changes")
    if chart_data.bpms:
        for bpm in chart_data.bpms[:3]:
            print(f"  Beat {bpm.beat:.3f}: {bpm.value:.2f} BPM")
    print(f"Stops: {len(chart_data.stops)}")
    print(f"Delays: {len(chart_data.delays)}")
    print(f"Warps: {len(chart_data.warps)}")
    print()

    # Display scale detection
    print("SCALE DETECTION")
    print("-" * 80)
    print(f"Detected Scale: {chart_data.detected_scale.value}")
    print(f"Confidence: {chart_data.scale_confidence:.2%}")
    print()

    # Display charts
    print("CHARTS")
    print("-" * 80)
    print(f"Total charts found: {len(chart_data.charts)}")
    print()

    for chart in chart_data.charts:
        print(f"{chart.chart_type.value.upper()} - {chart.difficulty.value.title()}")
        print(f"  Rating: {chart.rating}")

        # Get normalized rating
        key = f"{chart.chart_type.value}_{chart.difficulty.value}"
        normalized = chart_data.normalized_ratings.get(key, 0.0)
        print(f"  Normalized Rating: {normalized:.1f}")

        print(f"  Total Notes: {chart.total_notes}")
        print(f"    Taps: {chart.tap_notes}")
        print(f"    Holds: {chart.hold_notes}")
        print(f"    Rolls: {chart.roll_notes}")
        print(f"    Jumps: {chart.jump_count}")
        print(f"    Mines: {chart.mine_notes}")
        print()

    print("=" * 80)
    print("SSC PARSER TEST COMPLETE!")
    print("=" * 80)

if __name__ == "__main__":
    test_ssc_parser()
