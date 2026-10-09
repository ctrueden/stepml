"""
Dataset Generation Script for StepMania Chart Analysis

Labels the feature cache written by extract-features for one rating scale:
converts each chart's unified rating to the target scale, corrects classic-DDR
labels from DDRFreak, and applies ground-truth overrides. This takes seconds,
so label changes (ground truth, DDRFreak, scale tables) never require
re-extracting features.

Usage:
    generate-dataset [--features PATH] [--output-dir PATH]
                     [--normalization-scale {classic_ddr,modern_ddr,itg}]
"""

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Optional

import pandas as pd

from stepml.utils import get_data_dir, get_stepml_root
from stepml.utils.data_structures import ScaleType
from stepml.utils.ddrfreak_ratings import DDRFreakRatings
from stepml.utils.ground_truth import GroundTruthOverrides
from stepml.utils.rating_normalizer import RatingNormalizer

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def label_dataset(
    features: pd.DataFrame,
    target_scale: ScaleType,
    ground_truth: Optional[GroundTruthOverrides] = None,
    ddrfreak: Optional[DDRFreakRatings] = None,
) -> pd.DataFrame:
    """
    Produce a training dataset for one rating scale from the feature cache.

    Args:
        features: Feature cache, with unified_rating and detected_scale columns
        target_scale: Scale to normalize ratings to
        ground_truth: Manual rating overrides (optional)
        ddrfreak: Authoritative classic-DDR ratings (optional)

    Returns:
        Dataset with normalized_rating, ground_truth_rating, has_ground_truth
        (and DDRFreak provenance columns when ddrfreak is given)
    """
    normalizer = RatingNormalizer(target_scale)
    df = features.rename(columns={"unified_rating": "normalized_rating"})
    df["normalized_rating"] = [
        normalizer.from_unified(rating, ScaleType(scale))
        for rating, scale in zip(df["normalized_rating"], df["detected_scale"])
    ]

    # Correct classic-DDR labels using authoritative DDRFreak ratings before
    # ground-truth overrides, so manual overrides still take precedence.
    if ddrfreak:
        df = ddrfreak.apply(df, target_scale)

    # Apply ground truth overrides (adds ground_truth_rating column)
    if ground_truth:
        df = ground_truth.apply(df, target_scale)
    else:
        df["ground_truth_rating"] = df["normalized_rating"]
        df["has_ground_truth"] = False

    return df


def save_dataset(df: pd.DataFrame, output_dir: Path):
    """Save dataset to CSV and Parquet formats."""
    output_dir.mkdir(parents=True, exist_ok=True)

    csv_path = output_dir / "dataset.csv"
    logger.info(f"Saving CSV to {csv_path}...")
    df.to_csv(csv_path, index=False)

    # Parquet is what training reads (more efficient for large datasets).
    parquet_path = output_dir / "dataset.parquet"
    logger.info(f"Saving Parquet to {parquet_path}...")
    df.to_parquet(parquet_path, index=False, compression="snappy")
    logger.info(f"  Saved {len(df)} rows, {len(df.columns)} columns")

    column_info = {
        "columns": list(df.columns),
        "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()},
        "shape": df.shape,
    }
    with open(output_dir / "dataset_info.json", "w") as f:
        json.dump(column_info, f, indent=2)


def print_summary(df: pd.DataFrame):
    """Print rating statistics and ground-truth overrides."""
    logger.info("\nRating Statistics:")
    logger.info(
        f"  Normalized rating range: {df['normalized_rating'].min():.1f} - {df['normalized_rating'].max():.1f}"
    )
    logger.info(
        f"  Mean normalized rating: {df['normalized_rating'].mean():.2f} ± {df['normalized_rating'].std():.2f}"
    )

    n_gt = int(df["has_ground_truth"].sum())
    logger.info(f"\nGround Truth Overrides: {n_gt} row(s)")
    gt_rows = df[df["has_ground_truth"]]
    for _, r in gt_rows.iterrows():
        logger.info(
            f"  {r['title'][:40]:<42} {r['chart_type']:<14} {r['difficulty']:<10}"
            f" norm={r['normalized_rating']:.1f} → gt={r['ground_truth_rating']:.1f}"
        )


def main():
    parser = argparse.ArgumentParser(
        description="Label the feature cache to produce an ML dataset for one rating scale"
    )
    stepml_root = get_stepml_root()
    data_dir = get_data_dir()

    parser.add_argument(
        "--features",
        type=Path,
        default=data_dir / "features" / "features.parquet",
        help="Feature cache written by extract-features (default: ./data/features/features.parquet)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=data_dir / "processed",
        help="Output directory for dataset files (default: ./data/processed)",
    )
    parser.add_argument(
        "--ground-truth",
        type=Path,
        default=stepml_root / "ground_truth_ratings.yaml",
        help="Path to ground truth rating overrides YAML (default: ground_truth_ratings.yaml)",
    )
    parser.add_argument(
        "--no-ground-truth",
        action="store_true",
        help="Disable ground truth rating overrides",
    )
    parser.add_argument(
        "--ddrfreak-mixes",
        type=Path,
        default=stepml_root / "ddrfreak_mixes.yaml",
        help="Path to DDRFreak pack->mix mapping YAML (default: ddrfreak_mixes.yaml)",
    )
    parser.add_argument(
        "--ddrfreak-ratings",
        type=Path,
        default=stepml_root / "ddrfreak_ratings.csv",
        help="Path to scraped DDRFreak ratings CSV (default: ddrfreak_ratings.csv)",
    )
    parser.add_argument(
        "--no-ddrfreak",
        action="store_true",
        help="Disable DDRFreak classic-rating corrections",
    )
    parser.add_argument(
        "--normalization-scale",
        type=str,
        choices=["classic_ddr", "modern_ddr", "itg"],
        default="modern_ddr",
        help="Target scale for rating normalization (default: modern_ddr). Options: classic_ddr (1-10), modern_ddr (1-20), itg (1-12)",
    )

    args = parser.parse_args()

    if not args.features.exists():
        logger.error(f"Feature cache not found: {args.features}")
        logger.error("Run `uv run extract-features` first.")
        sys.exit(1)

    target_scale = ScaleType(args.normalization_scale)
    logger.info(
        f"Using normalization scale: {args.normalization_scale} ({target_scale.value})"
    )

    ground_truth = None
    if not args.no_ground_truth:
        if args.ground_truth.exists():
            ground_truth = GroundTruthOverrides(args.ground_truth)
        else:
            logger.warning(
                f"Ground truth file not found at {args.ground_truth} — continuing without overrides"
            )

    ddrfreak = None
    if not args.no_ddrfreak:
        if args.ddrfreak_mixes.exists() and args.ddrfreak_ratings.exists():
            ddrfreak = DDRFreakRatings(args.ddrfreak_mixes, args.ddrfreak_ratings)
        else:
            logger.warning(
                "DDRFreak files not found (%s / %s) — continuing without corrections",
                args.ddrfreak_mixes,
                args.ddrfreak_ratings,
            )

    logger.info(f"Loading feature cache from {args.features}...")
    features = pd.read_parquet(args.features)
    df = label_dataset(features, target_scale, ground_truth, ddrfreak)
    save_dataset(df, args.output_dir)
    print_summary(df)
    logger.info("\n✓ Dataset generation complete!")


if __name__ == "__main__":
    main()
