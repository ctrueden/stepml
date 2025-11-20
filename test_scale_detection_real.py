#!/usr/bin/env python3
"""
Test scale detection on real song collection.

Validates scale detection accuracy across different pack types.
"""
from pathlib import Path
from parsers.sm_parser import parse_sm_file
from utils.data_structures import ScaleType
import sys


def test_scale_detection():
    """Test scale detection on various packs from the collection."""

    songs_dir = Path("/home/curtis/Games/StepMania/Songs")

    # Test cases: (pack_name, expected_scale, sample_song)
    test_cases = [
        # Classic DDR
        ("DDR 1st Mix", ScaleType.CLASSIC_DDR, None),
        ("DDR 3rd Mix", ScaleType.CLASSIC_DDR, None),
        ("DDR 5th Mix", ScaleType.CLASSIC_DDR, None),
        ("DDR EXTREME", ScaleType.CLASSIC_DDR, None),

        # Modern DDR
        ("DDR A", ScaleType.MODERN_DDR, None),
        ("DDR A20", ScaleType.MODERN_DDR, None),
        ("DDR 2013", ScaleType.MODERN_DDR, None),
        ("DDR 2014", ScaleType.MODERN_DDR, None),

        # ITG
        ("ITG", ScaleType.ITG, None),
        ("ITG 2", ScaleType.ITG, None),
        ("ITG Rebirth", ScaleType.ITG, None),

        # StepMania 5 default pack
        ("StepMania 5", ScaleType.UNKNOWN, None),
    ]

    results = []

    print("=" * 80)
    print("SCALE DETECTION TEST ON REAL SONG COLLECTION")
    print("=" * 80)
    print()

    for pack_name, expected_scale, _ in test_cases:
        pack_path = songs_dir / pack_name

        if not pack_path.exists():
            print(f"⊘ SKIP: {pack_name:30s} - Pack not found")
            continue

        # Find the first .sm file in the pack
        sm_files = list(pack_path.rglob("*.sm"))
        if not sm_files:
            print(f"⊘ SKIP: {pack_name:30s} - No .sm files found")
            continue

        # Parse the first chart
        try:
            chart_data = parse_sm_file(str(sm_files[0]))
            detected_scale = chart_data.detected_scale
            confidence = chart_data.scale_confidence

            # Check if detection matches expectation
            is_correct = detected_scale == expected_scale
            symbol = "✓" if is_correct else "✗"

            # Prepare normalized ratings summary
            norm_ratings = []
            for chart in chart_data.charts[:3]:  # Show first 3 charts
                difficulty_key = f"{chart.chart_type.value}_{chart.difficulty.value}"
                if difficulty_key in chart_data.normalized_ratings:
                    norm_rating = chart_data.normalized_ratings[difficulty_key]
                    norm_ratings.append(f"{chart.difficulty.value[:3]}:{chart.rating}→{norm_rating:.1f}")

            ratings_str = ", ".join(norm_ratings[:3])

            print(f"{symbol} {pack_name:30s} | Detected: {detected_scale.value:12s} | "
                  f"Confidence: {confidence:.2f} | {ratings_str}")

            results.append({
                "pack": pack_name,
                "expected": expected_scale,
                "detected": detected_scale,
                "confidence": confidence,
                "correct": is_correct,
            })

        except Exception as e:
            print(f"✗ ERROR: {pack_name:30s} - {str(e)}")

    # Summary
    print()
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)

    total = len(results)
    correct = sum(1 for r in results if r["correct"])
    accuracy = (correct / total * 100) if total > 0 else 0

    print(f"Total packs tested: {total}")
    print(f"Correctly detected: {correct}")
    print(f"Accuracy: {accuracy:.1f}%")
    print()

    # Show misdetections
    misdetections = [r for r in results if not r["correct"]]
    if misdetections:
        print("Misdetections:")
        for r in misdetections:
            print(f"  - {r['pack']}: Expected {r['expected'].value}, got {r['detected'].value}")
    else:
        print("No misdetections! 🎉")

    print("=" * 80)

    return accuracy >= 90.0  # Success if 90%+ accuracy


if __name__ == "__main__":
    success = test_scale_detection()
    sys.exit(0 if success else 1)
