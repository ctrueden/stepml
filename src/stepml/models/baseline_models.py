"""
Baseline ML models for difficulty rating prediction.

Implements simple but effective models:
- Linear Regression
- Random Forest

These serve as performance baselines for more complex models.
"""

import logging
import pickle
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import cross_val_score, train_test_split
from sklearn.preprocessing import StandardScaler

logger = logging.getLogger(__name__)


class BaselineModel:
    """
    Base class for baseline difficulty prediction models.

    Handles common functionality like data loading, preprocessing,
    training, evaluation, and persistence.
    """

    def __init__(self, model_name: str):
        """
        Initialize baseline model.

        Args:
            model_name: Name of the model (for logging/saving)
        """
        self.model_name = model_name
        self.model = None
        self.scaler = StandardScaler()
        self.feature_names = None
        # ground_truth_rating is normalized_rating for most rows, with manual
        # overrides applied for songs where normalized_rating is known to be wrong.
        self.target_column = "ground_truth_rating"

        # Training metadata
        self.trained = False
        self.train_score = None
        self.test_score = None
        self.cv_scores = None

    def load_dataset(
        self, dataset_path: Path, feature_columns: Optional[List[str]] = None
    ) -> Tuple[pd.DataFrame, pd.Series]:
        """
        Load and prepare dataset for training.

        Args:
            dataset_path: Path to dataset CSV or Parquet file
            feature_columns: Optional list of feature columns to use
                           (if None, auto-detect numeric columns)

        Returns:
            (X, y) tuple of features and target
        """
        logger.info(f"Loading dataset from {dataset_path}...")

        # Load dataset
        if dataset_path.suffix == ".parquet":
            df = pd.read_parquet(dataset_path)
        else:
            df = pd.read_csv(dataset_path)

        logger.info(f"  Loaded {len(df)} rows, {len(df.columns)} columns")

        # Fall back to normalized_rating if ground_truth_rating not present
        # (e.g. dataset generated before this feature was added)
        if self.target_column not in df.columns:
            logger.warning(
                "Column %r not found; falling back to 'normalized_rating'",
                self.target_column,
            )
            self.target_column = "normalized_rating"

        # Report how many rows use manual ground truth labels
        if "has_ground_truth" in df.columns:
            n_gt = int(df["has_ground_truth"].sum())
            if n_gt:
                logger.info(f"  Training with {n_gt} ground-truth-overridden label(s)")

        # Remove rows with missing target
        df = df.dropna(subset=[self.target_column])
        logger.info(f"  After removing missing targets: {len(df)} rows")

        # Select features
        if feature_columns is None:
            # Auto-detect numeric feature columns
            # Exclude metadata, target, and performance columns
            exclude_cols = {
                # Metadata
                "file_path",
                "pack_name",
                "file_format",
                "title",
                "artist",
                "genre",
                "credit",
                "chart_type",
                "difficulty",
                "original_rating",
                "normalized_rating",
                "ground_truth_rating",
                "has_ground_truth",
                "detected_scale",
                "scale_confidence",
                # Raw counts that conflate difficulty with song length;
                # their rate-based equivalents (notes_per_second,
                # chart_length_*) are kept instead.
                "total_notes",
                # Tempo-blind notes/beat density features. They are highly
                # collinear with notes_per_second / peak_density (the tempo-aware
                # versions) and, via Random Forest impurity bias, soaked up
                # importance that belongs to the other features. Dropping them
                # breaks that collinearity at negligible accuracy cost.
                "average_density",
                "density_variance",
                # Performance features (sparse data, not intrinsic to chart)
                "times_played",
                "has_performance_data",
                "best_accuracy",
                "average_accuracy",
                "consistency_score",
                "best_percent_dp",
                "best_max_combo",
                "perceived_difficulty_factor",
                "has_failed",
                "perfect_rate",
                "great_or_worse_rate",
                "miss_rate",
                "hold_success_rate",
                "high_grade",
            }
            feature_columns = [
                col
                for col in df.columns
                if col not in exclude_cols and pd.api.types.is_numeric_dtype(df[col])
            ]

        self.feature_names = feature_columns
        logger.info(f"  Using {len(feature_columns)} features")

        # Extract features and target
        X = df[feature_columns]
        y = df[self.target_column]

        # Remove rows with any NaN features
        mask = X.notna().all(axis=1)
        X = X[mask]
        y = y[mask]

        logger.info(f"  Final dataset: {len(X)} rows, {len(X.columns)} features")
        logger.info(f"  Target range: {y.min():.1f} - {y.max():.1f}")
        logger.info(f"  Target mean: {y.mean():.2f} ± {y.std():.2f}")

        return X, y

    def prepare_data(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        test_size: float = 0.2,
        random_state: int = 42,
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """
        Split and scale data for training.

        Args:
            X: Feature matrix
            y: Target vector
            test_size: Fraction of data for testing
            random_state: Random seed for reproducibility

        Returns:
            (X_train, X_test, y_train, y_test) tuple
        """
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=random_state
        )

        logger.info("Data split:")
        logger.info(f"  Training: {len(X_train)} samples")
        logger.info(f"  Testing: {len(X_test)} samples")

        # Scale features
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)

        return X_train_scaled, X_test_scaled, y_train.values, y_test.values

    def train(self, X_train: np.ndarray, y_train: np.ndarray, cv_folds: int = 5):
        """
        Train the model.

        Args:
            X_train: Training features
            y_train: Training targets
            cv_folds: Number of cross-validation folds
        """
        if self.model is None:
            raise ValueError("Model not initialized!")

        logger.info(f"\nTraining {self.model_name}...")

        # Train model
        self.model.fit(X_train, y_train)

        # Training score
        self.train_score = self.model.score(X_train, y_train)
        logger.info(f"  Training R² score: {self.train_score:.4f}")

        # Cross-validation
        logger.info(f"  Running {cv_folds}-fold cross-validation...")
        self.cv_scores = cross_val_score(
            self.model, X_train, y_train, cv=cv_folds, scoring="r2"
        )
        logger.info(f"  CV R² scores: {self.cv_scores}")
        logger.info(
            f"  Mean CV R² score: {self.cv_scores.mean():.4f} ± {self.cv_scores.std():.4f}"
        )

        self.trained = True

    def evaluate(self, X_test: np.ndarray, y_test: np.ndarray) -> Dict:
        """
        Evaluate model on test set.

        Args:
            X_test: Test features
            y_test: Test targets

        Returns:
            Dictionary of evaluation metrics
        """
        if not self.trained:
            raise ValueError("Model not trained!")

        logger.info(f"\nEvaluating {self.model_name}...")

        # Make predictions
        y_pred = self.model.predict(X_test)

        # Calculate metrics
        from scipy.stats import spearmanr
        from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

        mae = mean_absolute_error(y_test, y_pred)
        rmse = np.sqrt(mean_squared_error(y_test, y_pred))
        r2 = r2_score(y_test, y_pred)
        spearman_corr, spearman_p = spearmanr(y_test, y_pred)

        metrics = {
            "mae": mae,
            "rmse": rmse,
            "r2": r2,
            "spearman_correlation": spearman_corr,
            "spearman_p_value": spearman_p,
        }

        self.test_score = r2

        logger.info("  Test Metrics:")
        logger.info(f"    MAE: {mae:.4f}")
        logger.info(f"    RMSE: {rmse:.4f}")
        logger.info(f"    R² score: {r2:.4f}")
        logger.info(
            f"    Spearman correlation: {spearman_corr:.4f} (p={spearman_p:.2e})"
        )

        return metrics

    def get_feature_importance(self) -> Optional[pd.DataFrame]:
        """
        Get feature importance scores (if supported by model).

        Returns:
            DataFrame with features and importance scores, or None
        """
        if not self.trained:
            raise ValueError("Model not trained!")

        if not hasattr(self.model, "feature_importances_"):
            logger.warning(f"{self.model_name} does not support feature importance")
            return None

        importances = self.model.feature_importances_
        feature_importance = pd.DataFrame(
            {"feature": self.feature_names, "importance": importances}
        ).sort_values("importance", ascending=False)

        return feature_importance

    def get_permutation_importance(
        self,
        X_test: np.ndarray,
        y_test: np.ndarray,
        n_repeats: int = 10,
        random_state: int = 42,
    ) -> pd.DataFrame:
        """
        Get permutation feature importance on held-out data.

        Unlike tree impurity importance, permutation importance measures each
        feature's true contribution to test accuracy and is not biased toward
        high-cardinality or one-of-several-collinear features. It works for any
        estimator, so it is the honest measure to compare features by.

        Args:
            X_test: Test features (already scaled)
            y_test: Test targets
            n_repeats: Number of shuffles per feature
            random_state: Random seed for reproducibility

        Returns:
            DataFrame with features, mean importance, and std, sorted descending.
        """
        if not self.trained:
            raise ValueError("Model not trained!")

        from sklearn.inspection import permutation_importance

        result = permutation_importance(
            self.model,
            X_test,
            y_test,
            n_repeats=n_repeats,
            random_state=random_state,
            n_jobs=-1,
        )
        return pd.DataFrame(
            {
                "feature": self.feature_names,
                "importance": result.importances_mean,
                "importance_std": result.importances_std,
            }
        ).sort_values("importance", ascending=False)

    def save(self, save_dir: Path):
        """
        Save model to disk.

        Args:
            save_dir: Directory to save model files
        """
        if not self.trained:
            raise ValueError("Cannot save untrained model!")

        save_dir = Path(save_dir)
        save_dir.mkdir(parents=True, exist_ok=True)

        # Save model
        model_path = save_dir / f"{self.model_name}.pkl"
        with open(model_path, "wb") as f:
            pickle.dump(self.model, f)
        logger.info(f"Saved model to {model_path}")

        # Save scaler
        scaler_path = save_dir / f"{self.model_name}_scaler.pkl"
        with open(scaler_path, "wb") as f:
            pickle.dump(self.scaler, f)
        logger.info(f"Saved scaler to {scaler_path}")

        # Save metadata
        import json

        metadata = {
            "model_name": self.model_name,
            "feature_names": self.feature_names,
            "target_column": self.target_column,
            "train_score": float(self.train_score) if self.train_score else None,
            "test_score": float(self.test_score) if self.test_score else None,
            "cv_scores": [float(s) for s in self.cv_scores]
            if self.cv_scores is not None
            else None,
        }
        metadata_path = save_dir / f"{self.model_name}_metadata.json"
        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=2)
        logger.info(f"Saved metadata to {metadata_path}")

    def load(self, save_dir: Path):
        """
        Load model from disk.

        Args:
            save_dir: Directory containing saved model files
        """
        save_dir = Path(save_dir)

        # Load model
        model_path = save_dir / f"{self.model_name}.pkl"
        with open(model_path, "rb") as f:
            self.model = pickle.load(f)

        # Load scaler
        scaler_path = save_dir / f"{self.model_name}_scaler.pkl"
        with open(scaler_path, "rb") as f:
            self.scaler = pickle.load(f)

        # Load metadata
        import json

        metadata_path = save_dir / f"{self.model_name}_metadata.json"
        with open(metadata_path, "r") as f:
            metadata = json.load(f)

        self.feature_names = metadata["feature_names"]
        self.target_column = metadata["target_column"]
        self.train_score = metadata.get("train_score")
        self.test_score = metadata.get("test_score")
        self.cv_scores = (
            np.array(metadata["cv_scores"]) if metadata.get("cv_scores") else None
        )
        self.trained = True

        logger.info(f"Loaded {self.model_name} from {save_dir}")


class LinearRegressionModel(BaselineModel):
    """Simple linear regression model."""

    def __init__(self):
        super().__init__("linear_regression")
        self.model = LinearRegression()


class RandomForestModel(BaselineModel):
    """Random forest regression model."""

    # Features for which difficulty must be monotonically non-decreasing:
    # all else equal, more notes, faster tempo, and more lateral/footwork
    # movement never make a chart easier. Enforcing this stops the forest from
    # learning physically nonsensical dips (e.g. higher peak_density predicting a
    # lower rating) from label noise, and guarantees two charts that differ only
    # by being denser/faster are ordered correctly.
    MONOTONIC_INCREASING = frozenset(
        {
            "notes_per_second",
            "peak_density",
            "com_velocity_mean",
            "com_velocity_peak",
            "com_direction_changes",
            "cross_pad_rate",
            "crossover_rate",
            "facing_changes_per_beat",
            "stream_nps",
            "stream_fraction",
            "max_run_seconds",
        }
    )

    def __init__(
        self,
        n_estimators: int = 300,
        max_depth: Optional[int] = 18,
        min_samples_leaf: int = 5,
        random_state: int = 42,
    ):
        super().__init__("random_forest")
        # min_samples_leaf is the key regularizer: with the default of 1, leaves
        # can memorize single charts, which made the model's response to any one
        # feature jumpy and non-monotonic (e.g. peak_density 1.75 -> 11.5 but
        # 2.0 -> 10.1). Averaging over >=5 charts per leaf smooths that out.
        self.model = RandomForestRegressor(
            n_estimators=n_estimators,
            max_depth=max_depth,
            min_samples_leaf=min_samples_leaf,
            random_state=random_state,
            n_jobs=-1,  # Use all CPU cores
        )

    def train(self, X_train: np.ndarray, y_train: np.ndarray, cv_folds: int = 5):
        """Apply monotonic constraints (in feature order) then train."""
        # monotonic_cst must align with the feature column order, which is only
        # known after load_dataset has populated feature_names. StandardScaler
        # scales each feature by a positive std and centers it, both of which
        # preserve per-feature ordering, so a +1 constraint stays +1 after
        # scaling.
        if self.feature_names is not None:
            constraints = [
                1 if name in self.MONOTONIC_INCREASING else 0
                for name in self.feature_names
            ]
            if any(constraints):
                self.model.set_params(monotonic_cst=constraints)
                n = sum(constraints)
                logger.info(
                    f"  Applied monotonic-increasing constraint to {n} feature(s)"
                )
        super().train(X_train, y_train, cv_folds=cv_folds)
