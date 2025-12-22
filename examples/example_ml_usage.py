"""
Example usage of trained ML models for difficulty prediction.

Demonstrates:
1. Loading a trained model
2. Predicting difficulty for a new chart
3. Comparing predictions across models
4. Analyzing feature contributions
"""

from pathlib import Path

from stepml.models.baseline_models import LinearRegressionModel, RandomForestModel
from stepml.parsers.universal_parser import parse_chart_file
from stepml.features.feature_extractor import FeatureExtractor
from stepml.utils import get_models_dir


def predict_chart_difficulty(chart_path: str, models_dir: Path):
    """
    Predict difficulty for a chart using trained models.

    Args:
        chart_path: Path to chart file (.sm, .ssc, or .dwi)
        models_dir: Directory containing trained models
    """
    print("=" * 60)
    print("CHART DIFFICULTY PREDICTION")
    print("=" * 60)

    # Parse chart
    print(f"\n1. Parsing chart: {Path(chart_path).name}")
    chart_data = parse_chart_file(chart_path)
    print(f"   Title: {chart_data.title}")
    print(f"   Artist: {chart_data.artist}")
    print(f"   Detected scale: {chart_data.detected_scale.value}")
    print(f"   Charts found: {len(chart_data.charts)}")

    # Extract features for each difficulty
    extractor = FeatureExtractor()

    # Load models
    print(f"\n2. Loading trained models from {models_dir}")
    lr_model = LinearRegressionModel()
    rf_model = RandomForestModel()

    try:
        lr_model.load(models_dir)
        print("   ✓ Loaded Linear Regression model")
    except:
        print("   ✗ Linear Regression model not found")
        lr_model = None

    try:
        rf_model.load(models_dir)
        print("   ✓ Loaded Random Forest model")
    except:
        print("   ✗ Random Forest model not found")
        rf_model = None

    # Predict for each chart
    print(f"\n3. Predicting difficulty ratings:")
    print(f"   {'Difficulty':<12} {'Original':<10} {'Linear Reg':<12} {'Random Forest':<14}")
    print(f"   {'-' * 12} {'-' * 10} {'-' * 12} {'-' * 14}")

    for chart in chart_data.charts:
        # Extract features
        features = extractor.extract_features(chart_data, chart)
        feature_dict = features.to_dict()

        # Prepare feature vector (must match training order)
        if lr_model:
            import pandas as pd
            X = pd.DataFrame([feature_dict])[lr_model.feature_names]
            X_scaled = lr_model.scaler.transform(X)

            # Predict with each model
            lr_pred = lr_model.model.predict(X_scaled)[0] if lr_model else None
            rf_pred = rf_model.model.predict(X_scaled)[0] if rf_model else None

            print(f"   {chart.difficulty.value:<12} "
                  f"{chart.rating:<10.1f} "
                  f"{lr_pred if lr_pred else 'N/A':<12.2f} "
                  f"{rf_pred if rf_pred else 'N/A':<14.2f}")
        else:
            print(f"   {chart.difficulty.value:<12} "
                  f"{chart.rating:<10.1f} "
                  f"{'N/A':<12} "
                  f"{'N/A':<14}")

    # Show key features for one chart
    if chart_data.charts and rf_model:
        print(f"\n4. Key features for {chart_data.charts[0].difficulty.value} chart:")
        features = extractor.extract_features(chart_data, chart_data.charts[0])

        # Get top features by importance
        feature_importance = rf_model.get_feature_importance()
        if feature_importance is not None:
            top_features = feature_importance.head(5)
            for i, row in top_features.iterrows():
                feat_name = row['feature']
                feat_value = getattr(features, feat_name, None)
                if feat_value is not None:
                    print(f"   {feat_name}: {feat_value:.3f} (importance: {row['importance']:.3f})")

    print("\n" + "=" * 60)


def main():
    if len(sys.argv) < 2:
        print("Usage: python example_ml_usage.py <chart_file>")
        print("\nExample:")
        print('  python example_ml_usage.py "../Songs/StepMania 5/Goin\' Under/Goin\' Under.sm"')
        sys.exit(1)

    chart_path = sys.argv[1]
    models_dir = get_models_dir()

    if not Path(chart_path).exists():
        print(f"Error: Chart file not found: {chart_path}")
        sys.exit(1)

    if not models_dir.exists():
        print(f"Error: Models directory not found: {models_dir}")
        print("Please run train_baseline_models.py first to train the models.")
        sys.exit(1)

    predict_chart_difficulty(chart_path, models_dir)


if __name__ == '__main__':
    main()
