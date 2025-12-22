"""
Example usage of Phase 2: Scale Detection and Rating Normalization

Demonstrates automatic scale detection and rating normalization across
different StepMania song packs (Classic DDR, Modern DDR, ITG).
"""
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from stepml.parsers.sm_parser import parse_sm_file
from stepml.utils.scale_detector import ScaleDetector
from stepml.utils.rating_normalizer import RatingNormalizer
from stepml.utils.data_structures import ScaleType
from stepml.config import get_songs_dir


def example_basic_usage():
    """Basic example: Parse a chart with automatic scale detection."""
    print("=" * 80)
    print("EXAMPLE 1: Basic Usage - Automatic Scale Detection")
    print("=" * 80)
    print()

    songs_dir = get_songs_dir()
    chart_path = songs_dir / "DDR EXTREME/PARANOiA survivor/PARANOiA survivor.sm"

    if chart_path.exists():
        chart_data = parse_sm_file(str(chart_path))

        print(f"Song: {chart_data.title}")
        print(f"Pack: {chart_data.songpack}")
        print(f"Detected Scale: {chart_data.detected_scale.value}")
        print(f"Confidence: {chart_data.scale_confidence:.2f}")
        print()

        print("Difficulty Ratings (Original → Normalized):")
        for chart in chart_data.charts[:5]:
            difficulty_key = f"{chart.chart_type.value}_{chart.difficulty.value}"
            normalized = chart_data.normalized_ratings.get(difficulty_key, 0)
            print(f"  {chart.difficulty.value:10s}: {chart.rating:2d} → {normalized:.1f}")
    else:
        print(f"⚠ Chart file not found: {chart_path}")
    print()


def example_manual_detection():
    """Example: Manually detect scale and normalize ratings."""
    print("=" * 80)
    print("EXAMPLE 2: Manual Scale Detection")
    print("=" * 80)
    print()

    detector = ScaleDetector()
    normalizer = RatingNormalizer()

    # Test different pack names
    test_packs = [
        "DDR 1st Mix",
        "DDR A20",
        "ITG 2",
        "Custom Pack XYZ",
    ]

    for pack_name in test_packs:
        scale, confidence = detector.detect_scale(f"/Songs/{pack_name}/Song/file.sm")
        info = detector.get_scale_info(scale)

        print(f"Pack: {pack_name}")
        print(f"  Scale: {info['name']} ({info['range']})")
        print(f"  Confidence: {confidence:.2f}")
        print(f"  Era: {info['era']}")
        print()


def example_rating_conversion():
    """Example: Convert ratings between different scales."""
    print("=" * 80)
    print("EXAMPLE 3: Rating Conversion Between Scales")
    print("=" * 80)
    print()

    normalizer = RatingNormalizer()

    # Show how a rating of 8 converts from different scales
    original_rating = 8
    print(f"Converting rating '{original_rating}' from different scales:\n")

    for scale in [ScaleType.CLASSIC_DDR, ScaleType.ITG, ScaleType.MODERN_DDR]:
        normalized = normalizer.normalize(original_rating, scale)
        info = normalizer.get_conversion_info(scale, original_rating)

        print(f"{scale.value.upper().replace('_', ' ')}:")
        print(f"  Original: {original_rating}")
        print(f"  Normalized (Unified): {normalized:.1f}")
        print(f"  Classic DDR Equivalent: {info['classic_ddr_equivalent']}")
        print(f"  Modern DDR Equivalent: {info['modern_ddr_equivalent']}")
        print(f"  ITG Equivalent: {info['itg_equivalent']}")
        print()


def example_comparing_charts():
    """Example: Compare difficulty across different scales."""
    print("=" * 80)
    print("EXAMPLE 4: Cross-Scale Difficulty Comparison")
    print("=" * 80)
    print()

    # Compare three charts from different eras
    test_charts = [
        ("DDR 5th Mix", "MATSURI JAPAN", 9),  # Classic DDR 9
        ("DDR A", "Lachryma《Re:Queen'M》", 14),  # Modern DDR 14
        ("ITG 2", "Disconnected Hardkore", 9),  # ITG 9
    ]

    normalizer = RatingNormalizer()

    print("Which chart is hardest?")
    print()

    results = []
    for pack, song, rating in test_charts:
        # Detect scale from pack name
        if "ITG" in pack:
            scale = ScaleType.ITG
        elif any(x in pack for x in ["A", "2013", "2014"]):
            scale = ScaleType.MODERN_DDR
        else:
            scale = ScaleType.CLASSIC_DDR

        normalized = normalizer.normalize(rating, scale)
        results.append((song, scale.value, rating, normalized))

        print(f"{song:30s} - {scale.value:12s} {rating:2d} → Unified {normalized:.1f}")

    # Sort by normalized difficulty
    results.sort(key=lambda x: x[3])
    print()
    print("Difficulty ranking (easiest to hardest):")
    for i, (song, scale, rating, normalized) in enumerate(results, 1):
        print(f"{i}. {song} ({normalized:.1f})")
    print()


def example_batch_processing():
    """Example: Process multiple charts and compare."""
    print("=" * 80)
    print("EXAMPLE 5: Batch Processing and Analysis")
    print("=" * 80)
    print()

    songs_dir = get_songs_dir()

    # Process a few packs
    packs = ["DDR 1st Mix", "DDR A20", "ITG"]
    all_charts = []

    for pack in packs:
        pack_path = songs_dir / pack
        if not pack_path.exists():
            continue

        # Get first song
        sm_files = list(pack_path.rglob("*.sm"))[:1]
        if not sm_files:
            continue

        chart_data = parse_sm_file(str(sm_files[0]))

        for chart in chart_data.charts:
            difficulty_key = f"{chart.chart_type.value}_{chart.difficulty.value}"
            normalized = chart_data.normalized_ratings.get(difficulty_key, 0)

            all_charts.append({
                "pack": pack,
                "song": chart_data.title,
                "difficulty": chart.difficulty.value,
                "original_rating": chart.rating,
                "scale": chart_data.detected_scale.value,
                "normalized_rating": normalized,
            })

    # Show distribution
    if all_charts:
        print("Sample of normalized ratings:")
        print()
        for c in all_charts[:10]:
            print(f"{c['pack']:15s} | {c['song']:20s} | "
                  f"{c['difficulty']:10s} | {c['original_rating']:2d} → {c['normalized_rating']:5.1f}")


if __name__ == "__main__":
    example_basic_usage()
    example_manual_detection()
    example_rating_conversion()
    example_comparing_charts()
    example_batch_processing()

    print("=" * 80)
    print("All examples complete!")
    print("=" * 80)
