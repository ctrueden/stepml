"""
Example script demonstrating multi-format support in Phase 3.

Shows how to use the universal parser to process .sm, .ssc, and .dwi files
with automatic format detection.
"""

from pathlib import Path

from stepml.config import get_songs_dir
from stepml.features.feature_extractor import FeatureExtractor
from stepml.parsers.universal_parser import (
    detect_format,
    is_supported_format,
    parse_chart_file,
)


def example_1_basic_parsing():
    """Example 1: Basic parsing with auto-detection."""
    print("=" * 80)
    print("EXAMPLE 1: Basic Multi-Format Parsing")
    print("=" * 80)
    print()

    songs_dir = get_songs_dir()
    files = [
        songs_dir / "StepMania 5/Goin' Under/Goin' Under.sm",
        songs_dir / "StepMania 5/Goin' Under/Goin' Under.ssc",
        songs_dir / "DDR GB 2/PARANOiA Rebirth/PARANOiA Rebirth.dwi",
    ]

    for filepath in files:
        if not filepath.exists():
            print(f"⚠ File not found: {filepath}")
            continue

        # Detect format
        format_name = detect_format(str(filepath))
        print(f"File: {filepath.name}")
        print(f"Format: {format_name}")

        # Parse with universal parser
        chart = parse_chart_file(str(filepath))
        print(f"Title: {chart.title}")
        print(f"Artist: {chart.artist}")
        print(f"Charts: {len(chart.charts)}")
        print()


def example_2_format_checking():
    """Example 2: Checking if a format is supported."""
    print("=" * 80)
    print("EXAMPLE 2: Format Support Checking")
    print("=" * 80)
    print()

    test_files = [
        "chart.sm",
        "chart.ssc",
        "chart.dwi",
        "song.mp3",
        "image.png",
        "data.json",
    ]

    for filename in test_files:
        supported = is_supported_format(filename)
        status = "✓ Supported" if supported else "✗ Not supported"
        print(f"{filename:15} - {status}")
    print()


def example_3_batch_processing():
    """Example 3: Batch processing multiple formats."""
    print("=" * 80)
    print("EXAMPLE 3: Batch Processing Multiple Formats")
    print("=" * 80)
    print()

    songs_dir = get_songs_dir()

    # Find all supported chart files
    chart_files = []
    for ext in [".sm", ".ssc", ".dwi"]:
        chart_files.extend(songs_dir.rglob(f"*{ext}"))

    print(f"Found {len(chart_files)} chart files:")
    print(f"  .sm files:  {len([f for f in chart_files if f.suffix == '.sm'])}")
    print(f"  .ssc files: {len([f for f in chart_files if f.suffix == '.ssc'])}")
    print(f"  .dwi files: {len([f for f in chart_files if f.suffix == '.dwi'])}")
    print()

    # Process a sample
    print("Processing sample of 3 charts:")
    print("-" * 80)

    sample_files = [
        songs_dir / "StepMania 5/Goin' Under/Goin' Under.sm",
        songs_dir / "StepMania 5/Goin' Under/Goin' Under.ssc",
        songs_dir / "DDR GB 2/PARANOiA Rebirth/PARANOiA Rebirth.dwi",
    ]

    for filepath in sample_files:
        if not filepath.exists():
            continue

        chart = parse_chart_file(str(filepath))
        print(f"{chart.title} ({chart.format})")
        print(f"  Songpack: {chart.songpack}")
        print(
            f"  Scale: {chart.detected_scale.value} ({chart.scale_confidence:.0%} confidence)"
        )
        print(f"  Charts: {len(chart.charts)}")
        print()


def example_4_feature_extraction():
    """Example 4: Feature extraction across formats."""
    print("=" * 80)
    print("EXAMPLE 4: Feature Extraction Across All Formats")
    print("=" * 80)
    print()

    extractor = FeatureExtractor()
    songs_dir = get_songs_dir()

    files = [
        (songs_dir / "StepMania 5/Goin' Under/Goin' Under.sm", "StepMania"),
        (songs_dir / "StepMania 5/Goin' Under/Goin' Under.ssc", "StepMania 5"),
        (songs_dir / "DDR GB 2/PARANOiA Rebirth/PARANOiA Rebirth.dwi", "DWI"),
    ]

    for filepath, format_name in files:
        if not filepath.exists():
            continue

        print(f"Format: {format_name}")
        print("-" * 40)

        chart_data = parse_chart_file(str(filepath))

        # Extract features for hardest chart
        hardest_chart = max(chart_data.charts, key=lambda c: c.rating)
        features = extractor.extract_features(chart_data, hardest_chart)

        print(
            f"Chart: {hardest_chart.difficulty.value} (Rating {hardest_chart.rating})"
        )
        print(f"  NPS: {features.notes_per_second:.2f}")
        print(f"  Peak Density: {features.peak_density:.2f}")
        print(f"  Total Notes: {features.total_notes}")
        print(f"  Jump Ratio: {features.jump_ratio:.2%}")
        print(f"  Hold Ratio: {features.hold_ratio:.2%}")
        print()


def example_5_cross_format_comparison():
    """Example 5: Comparing same song across formats."""
    print("=" * 80)
    print("EXAMPLE 5: Cross-Format Comparison (Same Song)")
    print("=" * 80)
    print()

    songs_dir = get_songs_dir()

    # Parse same song in both .sm and .ssc formats
    sm_path = songs_dir / "StepMania 5/Goin' Under/Goin' Under.sm"
    ssc_path = songs_dir / "StepMania 5/Goin' Under/Goin' Under.ssc"

    if not sm_path.exists() or not ssc_path.exists():
        print("⚠ Required files not found")
        return

    sm_chart = parse_chart_file(str(sm_path))
    ssc_chart = parse_chart_file(str(ssc_path))

    print(f"Song: {sm_chart.title}")
    print()

    print("Format Comparison:")
    print("-" * 40)
    print(f"{'Attribute':<20} {'SM':<15} {'SSC':<15}")
    print("-" * 40)
    print(f"{'Format':<20} {sm_chart.format:<15} {ssc_chart.format:<15}")
    print(f"{'Charts':<20} {len(sm_chart.charts):<15} {len(ssc_chart.charts):<15}")
    print(
        f"{'BPM':<20} {sm_chart.bpms[0].value:<15.1f} {ssc_chart.bpms[0].value:<15.1f}"
    )
    print(
        f"{'Detected Scale':<20} {sm_chart.detected_scale.value:<15} {ssc_chart.detected_scale.value:<15}"
    )
    print()

    print("Chart Comparison:")
    print("-" * 40)
    sm_challenge = next(
        (
            c
            for c in sm_chart.charts
            if c.chart_type.value == "dance-single" and c.rating == 10
        ),
        None,
    )
    ssc_challenge = next(
        (
            c
            for c in ssc_chart.charts
            if c.chart_type.value == "dance-single" and c.rating == 10
        ),
        None,
    )

    if not sm_challenge or not ssc_challenge:
        print("Challenge charts not found, skipping comparison.")
        print()
        return

    print(
        f"Challenge Chart (SM):  {sm_challenge.total_notes} notes, Rating {sm_challenge.rating}"
    )
    print(
        f"Challenge Chart (SSC): {ssc_challenge.total_notes} notes, Rating {ssc_challenge.rating}"
    )
    print(
        f"Match: {'✓' if sm_challenge.total_notes == ssc_challenge.total_notes else '✗'}"
    )
    print()


def example_6_unified_workflow():
    """Example 6: Unified workflow for any chart file."""
    print("=" * 80)
    print("EXAMPLE 6: Unified Processing Workflow")
    print("=" * 80)
    print()

    def process_any_chart(filepath: Path):
        """Process any supported chart file with a unified workflow."""
        # Check if supported
        if not is_supported_format(str(filepath)):
            print(f"⚠ Unsupported format: {filepath}")
            return

        # Parse (auto-detects format)
        chart_data = parse_chart_file(str(filepath))

        # Process
        print(f"✓ {chart_data.title} by {chart_data.artist}")
        print(f"  Format: {detect_format(str(filepath))}")
        print(f"  Songpack: {chart_data.songpack}")
        print(f"  Scale: {chart_data.detected_scale.value}")

        # Extract features for all charts
        extractor = FeatureExtractor()
        for chart in chart_data.charts:
            features = extractor.extract_features(chart_data, chart)
            key = f"{chart.chart_type.value}_{chart.difficulty.value}"
            normalized = chart_data.normalized_ratings.get(key, 0.0)

            print(
                f"  - {chart.difficulty.value}: "
                f"Rating {chart.rating} → {normalized:.1f}, "
                f"NPS {features.notes_per_second:.2f}"
            )
        print()

    # Process files of different formats with same workflow
    songs_dir = get_songs_dir()
    files = [
        songs_dir / "StepMania 5/Goin' Under/Goin' Under.sm",
        songs_dir / "DDR GB 2/PARANOiA Rebirth/PARANOiA Rebirth.dwi",
    ]

    for filepath in files:
        if filepath.exists():
            process_any_chart(filepath)


def main():
    """Run all examples."""
    print()
    print("╔" + "═" * 78 + "╗")
    print("║" + " MULTI-FORMAT SUPPORT EXAMPLES (Phase 3)".center(78) + "║")
    print("╚" + "═" * 78 + "╝")
    print()

    examples = [
        example_1_basic_parsing,
        example_2_format_checking,
        example_3_batch_processing,
        example_4_feature_extraction,
        example_5_cross_format_comparison,
        example_6_unified_workflow,
    ]

    for example in examples:
        example()

    print("=" * 80)
    print("ALL EXAMPLES COMPLETE!")
    print("=" * 80)


if __name__ == "__main__":
    main()
