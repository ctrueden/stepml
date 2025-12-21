"""
Training script for baseline ML models.

Trains Linear Regression and Random Forest models on the generated dataset
and evaluates their performance.

Usage:
    python train_baseline_models.py [--dataset PATH] [--output-dir PATH]
"""

import argparse
import logging
from pathlib import Path

import pandas as pd

from models.baseline_models import LinearRegressionModel, RandomForestModel


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(
        description='Train baseline models for difficulty prediction'
    )
    parser.add_argument(
        '--dataset',
        type=Path,
        default=Path(__file__).parent / 'data' / 'processed' / 'dataset.parquet',
        help='Path to dataset file (default: data/processed/dataset.parquet)'
    )
    parser.add_argument(
        '--output-dir',
        type=Path,
        default=Path(__file__).parent / 'data' / 'models',
        help='Output directory for trained models (default: data/models)'
    )
    parser.add_argument(
        '--test-size',
        type=float,
        default=0.2,
        help='Fraction of data for testing (default: 0.2)'
    )
    parser.add_argument(
        '--cv-folds',
        type=int,
        default=5,
        help='Number of cross-validation folds (default: 5)'
    )

    args = parser.parse_args()

    logger.info("=" * 60)
    logger.info("BASELINE MODEL TRAINING")
    logger.info("=" * 60)
    logger.info(f"Dataset: {args.dataset}")
    logger.info(f"Output directory: {args.output_dir}")

    # Initialize models
    models = {
        'Linear Regression': LinearRegressionModel(),
        'Random Forest': RandomForestModel(n_estimators=100, max_depth=20)
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
            model.train(X_train, y_train, cv_folds=args.cv_folds)

            # Evaluate
            metrics = model.evaluate(X_test, y_test)
            results[model_name] = metrics

            # Feature importance (if available)
            feature_importance = model.get_feature_importance()
            if feature_importance is not None:
                logger.info(f"\nTop 10 Most Important Features:")
                for i, row in feature_importance.head(10).iterrows():
                    logger.info(f"  {i+1}. {row['feature']}: {row['importance']:.4f}")

                # Save feature importance
                importance_path = args.output_dir / f'{model.model_name}_feature_importance.csv'
                feature_importance.to_csv(importance_path, index=False)
                logger.info(f"\nSaved feature importance to {importance_path}")

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

        summary_rows.append({
            'model': model_name,
            **metrics
        })

    # Save summary
    summary_df = pd.DataFrame(summary_rows)
    summary_path = args.output_dir / 'training_summary.csv'
    summary_df.to_csv(summary_path, index=False)
    logger.info(f"\nSaved training summary to {summary_path}")

    logger.info("\n" + "=" * 60)
    logger.info("✓ Training complete!")
    logger.info("=" * 60)


if __name__ == '__main__':
    main()
