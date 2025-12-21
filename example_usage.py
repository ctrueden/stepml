"""
Example usage of the StepMania chart analysis package.
"""
from pathlib import Path
from parsers.sm_parser import parse_sm_file
from features.feature_extractor import FeatureExtractor, AdvancedFeatureExtractor


def analyze_chart(filepath: str):
    """
    Simple example: analyze a single chart file.

    Args:
        filepath: Path to .sm file
    """
    print(f"Analyzing: {filepath}\n")

    # Parse the chart
    chart_data = parse_sm_file(filepath)

    print(f"Song: {chart_data.title}")
    print(f"Artist: {chart_data.artist}")
    print(f"Pack: {chart_data.songpack}")
    print(f"Primary BPM: {chart_data.get_primary_bpm()}")
    print(f"BPM Changes: {len(chart_data.bpms) - 1}")
    print(f"Has Stops: {chart_data.has_stops()}")
    print(f"\nCharts: {len(chart_data.charts)}\n")

    # Extract features for each difficulty
    extractor = FeatureExtractor()

    for chart in chart_data.charts:
        if chart.chart_type.value == "dance-single":  # Focus on single charts
            features = extractor.extract_features(chart_data, chart)

            print(f"{chart.difficulty.value} (Rating {chart.rating}):")
            print(f"  NPS: {features.notes_per_second:.2f}")
            print(f"  Peak Density: {features.peak_density:.2f} notes/beat")
            print(f"  Jumps: {features.jump_ratio:.1%}")
            print(f"  Holds: {features.hold_ratio:.1%}")
            print()


def compare_difficulties(filepath: str):
    """
    Example: compare difficulty progression in a chart.

    Args:
        filepath: Path to .sm file
    """
    chart_data = parse_sm_file(filepath)
    extractor = FeatureExtractor()

    print(f"\nDifficulty Progression: {chart_data.title}")
    print("-" * 60)
    print(f"{'Difficulty':<12} {'Rating':<8} {'NPS':<8} {'Peak':<8} {'Jumps':<8}")
    print("-" * 60)

    for chart in sorted(chart_data.charts, key=lambda x: x.rating):
        if chart.chart_type.value == "dance-single":
            features = extractor.extract_features(chart_data, chart)
            print(f"{chart.difficulty.value:<12} "
                  f"{chart.rating:<8} "
                  f"{features.notes_per_second:<8.2f} "
                  f"{features.peak_density:<8.2f} "
                  f"{features.jump_ratio:<8.1%}")


def extract_all_features(filepath: str):
    """
    Example: extract all features including advanced ones.

    Args:
        filepath: Path to .sm file
    """
    chart_data = parse_sm_file(filepath)
    basic_extractor = FeatureExtractor()
    advanced_extractor = AdvancedFeatureExtractor()

    print(f"\nComplete Feature Set: {chart_data.title}")
    print("=" * 80)

    for chart in chart_data.charts:
        if chart.chart_type.value == "dance-single" and chart.difficulty.value == "Hard":
            # Basic features
            features = basic_extractor.extract_features(chart_data, chart)

            # Advanced features
            advanced = advanced_extractor.extract_advanced_features(chart)

            print(f"\n{chart.difficulty.value} (Rating {chart.rating}):")
            print(f"\nDensity:")
            print(f"  Average: {features.average_density:.2f} notes/beat")
            print(f"  Peak: {features.peak_density:.2f} notes/beat")
            print(f"  Variance: {features.density_variance:.4f}")

            print(f"\nPatterns:")
            print(f"  Jumps: {features.jump_ratio:.2%}")
            print(f"  Holds: {features.hold_ratio:.2%}")
            print(f"  Streams: {advanced['stream_sections']}")
            print(f"  Direction Changes: {advanced['direction_changes']}")
            print(f"  Crossover Potential: {advanced['crossover_potential']:.4f}")

            print(f"\nTiming:")
            print(f"  Length: {features.chart_length_seconds:.1f}s")
            print(f"  BPM Changes: {features.bpm_changes}")
            print(f"  Stops: {features.stop_count}")

            # Convert to dictionary for ML
            feature_dict = features.to_dict()
            print(f"\nTotal Features: {len(feature_dict)}")
            break


def batch_analyze_pack(pack_path: str):
    """
    Example: analyze all charts in a song pack.

    Args:
        pack_path: Path to song pack directory
    """
    pack_dir = Path(pack_path)
    sm_files = list(pack_dir.rglob("*.sm"))

    print(f"\nAnalyzing pack: {pack_dir.name}")
    print(f"Found {len(sm_files)} charts\n")

    extractor = FeatureExtractor()
    results = []

    for sm_file in sm_files[:5]:  # Limit to first 5 for example
        try:
            chart_data = parse_sm_file(str(sm_file))

            # Get hardest chart
            hardest = max(chart_data.charts, key=lambda x: x.rating)
            features = extractor.extract_features(chart_data, hardest)

            results.append({
                'title': chart_data.title,
                'difficulty': hardest.difficulty.value,
                'rating': hardest.rating,
                'nps': features.notes_per_second
            })
        except Exception as e:
            print(f"Error parsing {sm_file.name}: {e}")

    # Display results
    print(f"{'Title':<30} {'Difficulty':<12} {'Rating':<8} {'NPS':<8}")
    print("-" * 70)
    for result in sorted(results, key=lambda x: x['rating'], reverse=True):
        print(f"{result['title'][:29]:<30} "
              f"{result['difficulty']:<12} "
              f"{result['rating']:<8} "
              f"{result['nps']:<8.2f}")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        filepath = sys.argv[1]

        # Run all examples
        print("=" * 80)
        print("EXAMPLE 1: Basic Analysis")
        print("=" * 80)
        analyze_chart(filepath)

        print("\n" + "=" * 80)
        print("EXAMPLE 2: Difficulty Progression")
        print("=" * 80)
        compare_difficulties(filepath)

        print("\n" + "=" * 80)
        print("EXAMPLE 3: Complete Feature Extraction")
        print("=" * 80)
        extract_all_features(filepath)
    else:
        print("Usage:")
        print(f"  python {sys.argv[0]} <path-to-sm-file>")
        print(f"\nExample:")
        print(f"  python {sys.argv[0]} Songs/StepMania\\ 5/Goin\\'\\ Under/Goin\\'\\ Under.sm")
