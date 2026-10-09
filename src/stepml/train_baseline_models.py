"""
Training script for baseline ML models.

Trains Linear Regression and Random Forest models on the generated dataset
and evaluates them on a held-out split. Cross-validation and permutation
importance are slower diagnostics; run diagnose-models for those.

Usage:
    train-models [--dataset PATH] [--output-dir PATH]
"""

import argparse
import logging
from pathlib import Path

import pandas as pd

from stepml.models.baseline_models import LinearRegressionModel, RandomForestModel
from stepml.utils import get_data_dir

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(
        description="Train baseline models for difficulty prediction"
    )
    data_dir = get_data_dir()
    parser.add_argument(
        "--dataset",
        type=Path,
        default=data_dir / "processed" / "dataset.parquet",
        help="Path to dataset file (default: data/processed/dataset.parquet)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=data_dir / "models",
        help="Output directory for trained models (default: data/models)",
    )
    parser.add_argument(
        "--test-size",
        type=float,
        default=0.2,
        help="Fraction of data for testing (default: 0.2)",
    )

    args = parser.parse_args()

    logger.info("=" * 60)
    logger.info("BASELINE MODEL TRAINING")
    logger.info("=" * 60)
    logger.info(f"Dataset: {args.dataset}")
    logger.info(f"Output directory: {args.output_dir}")

    # Initialize models
    models = {
        "Linear Regression": LinearRegressionModel(),
        # Regularized RF (see RandomForestModel defaults): more trees, capped
        # depth, and min_samples_leaf to keep per-feature response smooth.
        "Random Forest": RandomForestModel(),
    }

    # Store results
    results = {}

    for model_name, model in models.items():
        logger.info("\n" + "=" * 60)
        logger.info(f"Training {model_name}")
        logger.info("=" * 60)

        try:
            # Load and prepare data
            X, y = model.load_dataset(args.dataset)
            X_train, X_test, y_train, y_test = model.prepare_data(
                X, y, test_size=args.test_size
            )

            # Train model
            model.train(X_train, y_train)

            # Evaluate
            metrics = model.evaluate(X_test, y_test)
            results[model_name] = metrics

            # Impurity-based feature importance (if available)
            feature_importance = model.get_feature_importance()
            if feature_importance is not None:
                # Save impurity importance (kept for reference / comparison)
                importance_path = (
                    args.output_dir / f"{model.model_name}_feature_importance.csv"
                )
                feature_importance.to_csv(importance_path, index=False)
                logger.info(f"\nSaved impurity importance to {importance_path}")

            # Permutation importance from an earlier diagnose-models run
            # describes the previous model; remove it rather than mislead.
            stale = args.output_dir / f"{model.model_name}_permutation_importance.csv"
            stale.unlink(missing_ok=True)

            # Save model
            model.save(args.output_dir)

        except Exception as e:
            logger.error(f"Failed to train {model_name}: {e}", exc_info=True)
            continue

    # Print summary
    logger.info("\n" + "=" * 60)
    logger.info("TRAINING SUMMARY")
    logger.info("=" * 60)

    summary_rows = []
    for model_name, metrics in results.items():
        logger.info(f"\n{model_name}:")
        logger.info(f"  MAE: {metrics['mae']:.4f}")
        logger.info(f"  RMSE: {metrics['rmse']:.4f}")
        logger.info(f"  R² score: {metrics['r2']:.4f}")
        logger.info(f"  Spearman correlation: {metrics['spearman_correlation']:.4f}")

        summary_rows.append({"model": model_name, **metrics})

    # Save summary
    summary_df = pd.DataFrame(summary_rows)
    summary_path = args.output_dir / "training_summary.csv"
    summary_df.to_csv(summary_path, index=False)
    logger.info(f"\nSaved training summary to {summary_path}")

    logger.info("\n" + "=" * 60)
    logger.info("✓ Training complete!")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
