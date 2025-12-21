"""
Generate baseline feature extractions for regression testing.

This script:
1. Reads test_charts.json to find representative charts
2. Extracts all features from each chart
3. Saves the feature values as baseline_features.json

Run this script when you intentionally change feature extraction algorithms
and want to update the regression baseline.
"""
import json
import sys
from datetime import datetime
from pathlib import Path

from ..parsers.sm_parser import parse_sm_file
from ..features.feature_extractor import FeatureExtractor, AdvancedFeatureExtractor


def generate_baseline():
    """Generate baseline feature extractions for all test charts."""
    # Setup paths - script is at src/stepml/scripts/generate_baseline.py
    # Need to go up 3 levels to reach project root (stepml/)
    script_dir = Path(__file__).parent  # scripts/
    scripts_parent = script_dir.parent  # stepml/ (package)
    src_parent = scripts_parent.parent  # src/
    stepml_root = src_parent.parent  # stepml/ (project root)
    
    songs_dir = stepml_root.parent / "Songs"  # ../Songs
    test_charts_path = stepml_root / "tests" / "fixtures" / "test_charts.json"
    baseline_path = stepml_root / "tests" / "fixtures" / "baseline_features.json"

    # Load test charts config
    print(f"Loading test charts from: {test_charts_path}")
    with open(test_charts_path, 'r') as f:
        test_config = json.load(f)

    # Initialize extractors
    extractor = FeatureExtractor()
    advanced_extractor = AdvancedFeatureExtractor()

    # Baseline data structure
    baseline_data = {
        "_comment": "Baseline feature extractions for regression testing",
        "_generated": datetime.now().isoformat(),
        "_version": "1.0.0",
        "_instructions": "Do not edit manually. Regenerate with: uv run python scripts/generate_baseline.py",
        "baseline_data": {}
    }

    # Process each test chart
    print("\n" + "="*80)
    print("GENERATING BASELINE FEATURE EXTRACTIONS")
    print("="*80 + "\n")

    charts_processed = 0
    charts_skipped = 0

    for chart_info in test_config.get("charts", []):
        chart_name = chart_info["name"]
        chart_path = songs_dir / chart_info["path"]

        print(f"Processing: {chart_name}")
        print(f"  Path: {chart_path}")

        if not chart_path.exists():
            print(f"  ⚠️  SKIPPED - File not found")
            charts_skipped += 1
            continue

        try:
            # Parse the chart
            chart_data = parse_sm_file(str(chart_path))

            # Store baseline for this chart
            chart_baseline = {
                "path": chart_info["path"],
                "description": chart_info["description"],
                "edge_cases": chart_info["edge_cases"],
                "metadata": {
                    "title": chart_data.title,
                    "artist": chart_data.artist,
                    "format": chart_data.format,
                },
                "charts": {}
            }

            # Extract features for each difficulty
            for chart in chart_data.charts:
                chart_key = f"{chart.chart_type.value}_{chart.difficulty.value}"

                print(f"  - {chart.chart_type.value} {chart.difficulty.value} (Rating: {chart.rating})")

                # Extract basic features
                features = extractor.extract_features(chart_data, chart)
                feature_dict = features.to_dict()

                # Extract advanced features
                advanced_features = advanced_extractor.extract_advanced_features(chart)

                # Store in baseline
                chart_baseline["charts"][chart_key] = {
                    **feature_dict,
                    "advanced_features": advanced_features
                }

            baseline_data["baseline_data"][chart_name] = chart_baseline
            charts_processed += 1
            print(f"  ✓ Processed {len(chart_data.charts)} difficulty chart(s)")

        except Exception as e:
            print(f"  ✗ ERROR: {e}")
            charts_skipped += 1
            continue

        print()

    # Save baseline
    print("="*80)
    print(f"Saving baseline to: {baseline_path}")

    with open(baseline_path, 'w') as f:
        json.dump(baseline_data, f, indent=2)

    print(f"\n✓ Baseline generation complete!")
    print(f"  Charts processed: {charts_processed}")
    print(f"  Charts skipped: {charts_skipped}")
    print(f"  Total charts in baseline: {charts_processed}")
    print("\nTo run regression tests:")
    print("  cd tests")
    print("  uv run pytest -v")
    print("\nOr run specific test:")
    print("  uv run pytest -v -m regression")
    print("="*80 + "\n")


if __name__ == "__main__":
    generate_baseline()
