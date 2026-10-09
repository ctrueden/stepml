"""
Diagnostics for trained baseline models.

Runs the slower checks that train-models skips: k-fold cross-validation of
each model's configuration, and permutation importance of each trained model
on the held-out split. Run it after train-models, against the same dataset,
when debugging features or model settings.

Usage:
    diagnose-models [--dataset PATH] [--model-dir PATH] [--cv-folds N]
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
        description="Cross-validate trained models and report permutation importance"
    )
    data_dir = get_data_dir()
    parser.add_argument(
        "--dataset",
        type=Path,
        default=data_dir / "processed" / "dataset.parquet",
        help="Dataset the models were trained on (default: data/processed/dataset.parquet)",
    )
    parser.add_argument(
        "--model-dir",
        type=Path,
        default=data_dir / "models",
        help="Directory of models saved by train-models (default: data/models)",
    )
    parser.add_argument(
        "--test-size",
        type=float,
        default=0.2,
        help="Fraction of data held out, as passed to train-models (default: 0.2)",
    )
    parser.add_argument(
        "--cv-folds",
        type=int,
        default=5,
        help="Number of cross-validation folds (default: 5)",
    )
    args = parser.parse_args()

    summary_rows = []
    for model in (LinearRegressionModel(), RandomForestModel()):
        logger.info("\n" + "=" * 60)
        logger.info(f"Diagnosing {model.model_name}")
        logger.info("=" * 60)

        model.load(args.model_dir)
        # The split is seeded, so this reproduces the train/test split (and
        # scaler) that train-models used for the saved model.
        X, y = model.load_dataset(args.dataset, feature_columns=model.feature_names)
        X_train, X_test, y_train, y_test = model.prepare_data(
            X, y, test_size=args.test_size
        )

        metrics = model.evaluate(X_test, y_test)
        cv_scores = model.cross_validate(X_train, y_train, cv_folds=args.cv_folds)

        # Permutation importance: the honest, collinearity-robust measure of
        # each feature's contribution to held-out accuracy.
        perm_importance = model.get_permutation_importance(X_test, y_test)
        logger.info("\nTop 10 Features by Permutation Importance:")
        for rank, (_, row) in enumerate(perm_importance.head(10).iterrows(), 1):
            logger.info(
                f"  {rank}. {row['feature']}: "
                f"{row['importance']:.4f} ± {row['importance_std']:.4f}"
            )
        perm_path = args.model_dir / f"{model.model_name}_permutation_importance.csv"
        perm_importance.to_csv(perm_path, index=False)
        logger.info(f"Saved permutation importance to {perm_path}")

        summary_rows.append(
            {
                "model": model.model_name,
                "test_mae": metrics["mae"],
                "test_r2": metrics["r2"],
                "cv_r2_mean": cv_scores.mean(),
                "cv_r2_std": cv_scores.std(),
            }
        )

    summary = pd.DataFrame(summary_rows)
    summary_path = args.model_dir / "diagnostics_summary.csv"
    summary.to_csv(summary_path, index=False)
    logger.info("\n" + summary.to_string(index=False))
    logger.info(f"\nSaved diagnostics summary to {summary_path}")


if __name__ == "__main__":
    main()
