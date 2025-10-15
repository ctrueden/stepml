#!/usr/bin/env python3
"""
Test script for SM parser and feature extraction.
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent))

from parsers.sm_parser import parse_sm_file
from features.feature_extractor import FeatureExtractor, AdvancedFeatureExtractor


def test_single_file(filepath: str):
    """Test parsing and feature extraction on a single file."""
    print(f"\n{'='*80}")
    print(f"Testing: {filepath}")
    print(f"{'='*80}\n")

    try:
        # Parse the file
        print("Parsing file...")
        chart_data = parse_sm_file(filepath)

        # Display metadata
        print(f"Title: {chart_data.title}")
        print(f"Artist: {chart_data.artist}")
        print(f"Song Pack: {chart_data.songpack}")
        print(f"Format: {chart_data.format}")
        print(f"\nBPMs: {len(chart_data.bpms)} change(s)")
        if chart_data.bpms:
            for bpm in chart_data.bpms[:3]:  # Show first 3
                print(f"  Beat {bpm.beat}: {bpm.value} BPM")
            if len(chart_data.bpms) > 3:
                print(f"  ... and {len(chart_data.bpms) - 3} more")

        print(f"\nStops: {len(chart_data.stops)}")
        if chart_data.stops:
            for stop in chart_data.stops[:3]:
                print(f"  Beat {stop.beat}: {stop.value}s")
            if len(chart_data.stops) > 3:
                print(f"  ... and {len(chart_data.stops) - 3} more")

        # Display chart information
        print(f"\nCharts found: {len(chart_data.charts)}")
        for chart in chart_data.charts:
            print(f"\n  {chart.chart_type.value} - {chart.difficulty.value} (Rating: {chart.rating})")
            print(f"    Total notes: {chart.total_notes}")
            print(f"    Taps: {chart.tap_notes}, Holds: {chart.hold_notes}, Rolls: {chart.roll_notes}")
            print(f"    Jumps: {chart.jump_count}, Mines: {chart.mine_notes}")

        # Extract features for each chart
        print(f"\n{'-'*80}")
        print("Feature Extraction:")
        print(f"{'-'*80}\n")

        extractor = FeatureExtractor()
        advanced_extractor = AdvancedFeatureExtractor()

        for chart in chart_data.charts:
            chart_id = f"{chart.chart_type.value} - {chart.difficulty.value}"
            print(f"\n{chart_id}:")

            # Extract basic features
            features = extractor.extract_features(chart_data, chart)

            print(f"  Density Metrics:")
            print(f"    Notes per second: {features.notes_per_second:.2f}")
            print(f"    Average density: {features.average_density:.2f} notes/beat")
            print(f"    Peak density: {features.peak_density:.2f} notes/beat")
            print(f"    Density variance: {features.density_variance:.4f}")

            print(f"  Pattern Metrics:")
            print(f"    Jump ratio: {features.jump_ratio:.2%}")
            print(f"    Hold ratio: {features.hold_ratio:.2%}")
            print(f"    Roll ratio: {features.roll_ratio:.2%}")
            print(f"    Mine ratio: {features.mine_ratio:.2%}")

            print(f"  Timing Metrics:")
            print(f"    Chart length: {features.chart_length_seconds:.1f}s ({features.chart_length_beats:.1f} beats)")
            print(f"    BPM changes: {features.bpm_changes}")
            print(f"    BPM variance: {features.bpm_variance:.2f}")
            print(f"    Stop count: {features.stop_count}")
            print(f"    Total stop duration: {features.total_stop_duration:.2f}s")

            print(f"  Technical:")
            print(f"    Advanced timing: {features.has_advanced_timing}")

            # Extract advanced features
            advanced_features = advanced_extractor.extract_advanced_features(chart)
            print(f"  Advanced Features:")
            print(f"    Stream sections: {advanced_features['stream_sections']}")
            print(f"    Direction changes: {advanced_features['direction_changes']}")
            print(f"    Crossover potential: {advanced_features['crossover_potential']:.4f}")

        print(f"\n{'='*80}")
        print("Test completed successfully!")
        print(f"{'='*80}\n")

    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()


def main():
    """Main test function."""
    if len(sys.argv) > 1:
        # Test specific file from command line
        test_single_file(sys.argv[1])
    else:
        # Test some default files
        base_dir = Path(__file__).parent.parent
        songs_dir = base_dir / "Songs"

        # Try to find some test files
        test_files = []

        # Look for .sm files
        for sm_file in songs_dir.rglob("*.sm"):
            test_files.append(sm_file)
            if len(test_files) >= 3:  # Test first 3 files found
                break

        if not test_files:
            print("No .sm files found in Songs directory!")
            print(f"Searched in: {songs_dir}")
            return

        for filepath in test_files:
            test_single_file(str(filepath))


if __name__ == "__main__":
    main()
