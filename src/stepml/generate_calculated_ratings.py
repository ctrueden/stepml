"""
Generate calculated difficulty ratings for all charts in the collection.

Creates a mapping file that can be used to override StepMania's ratings.
"""
import argparse
import json
import pandas as pd
from pathlib import Path
from stepml.models.baseline_models import RandomForestModel
from stepml.utils import get_stepml_root, get_data_dir


def convert_chart_type_to_stepmania_format(chart_type: str) -> str:
    """
    Convert chart type from raw format to StepMania's internal format.

    Examples:
        dance-single -> Dance_Single
        dance-double -> Dance_Double
        pump-single -> Pump_Single

    This matches the logic in StepMania's StepsTypeToString function:
    - Replace hyphens with underscores
    - Capitalize first letter and any letter after underscore
    """
    # Replace hyphens with underscores
    result = chart_type.replace('-', '_')

    # Capitalize first letter and any letter after underscore
    chars = list(result)
    capitalize_next = True

    for i in range(len(chars)):
        if capitalize_next:
            chars[i] = chars[i].upper()
            capitalize_next = False

        if chars[i] == '_':
            capitalize_next = True

    return ''.join(chars)


def generate_ratings(dataset_path: Path, model_dir: Path, output_path: Path):
    """Generate calculated ratings for all charts."""
    print("=" * 80)
    print("GENERATING CALCULATED RATINGS")
    print("=" * 80)

    # Load model
    print(f"\nLoading model from {model_dir}...")
    model = RandomForestModel()
    model.load(model_dir)
    print(f"✓ Model loaded (trained on {model.target_column})")

    # Load dataset
    print(f"\nLoading dataset from {dataset_path}...")
    df = pd.read_parquet(dataset_path)
    print(f"✓ Loaded {len(df)} charts")

    # Prepare features
    X = df[model.feature_names]
    X_scaled = model.scaler.transform(X)

    # Generate predictions
    print("\nGenerating predictions...")
    predictions = model.model.predict(X_scaled)
    df['calculated_rating'] = predictions

    # Round to nearest 0.5 for readability
    df['calculated_rating_rounded'] = (df['calculated_rating'] * 2).round() / 2

    print(f"✓ Generated ratings for {len(df)} charts")

    # Statistics
    print("\n" + "=" * 80)
    print("RATING STATISTICS")
    print("=" * 80)

    print(f"\nCalculated ratings:")
    print(f"  Range: {df['calculated_rating'].min():.2f} - {df['calculated_rating'].max():.2f}")
    print(f"  Mean: {df['calculated_rating'].mean():.2f} ± {df['calculated_rating'].std():.2f}")
    print(f"  Median: {df['calculated_rating'].median():.2f}")

    print(f"\nRating changes from normalized:")
    df['rating_delta'] = df['calculated_rating'] - df['normalized_rating']
    print(f"  Mean change: {df['rating_delta'].mean():+.2f}")
    print(f"  Largest increase: {df['rating_delta'].max():+.2f}")
    print(f"  Largest decrease: {df['rating_delta'].min():+.2f}")

    # Show charts with biggest changes
    print("\n" + "=" * 80)
    print("LARGEST RATING ADJUSTMENTS (vs normalized rating)")
    print("=" * 80)

    hdr = f"{'Title':<34} {'Steps':<17} {'Scale':<12} {'Raw':>4} {'Norm':>5} {'Calc':>5} {'Δ':>7}"
    sep = "-" * 88

    def fmt_row(row):
        # Abbreviate "dance-single" → "single", "dance-double" → "double", etc.
        ctype = row['chart_type'].removeprefix('dance-')
        steps = f"{ctype}:{row['difficulty']}"
        return (f"{row['title'][:32]:<34} {steps[:16]:<17} "
                f"{row['detected_scale'][:11]:<12} "
                f"{row['original_rating']:4.0f} {row['normalized_rating']:5.1f} "
                f"{row['calculated_rating_rounded']:5.1f} {row['rating_delta']:+7.2f}")

    print("\nTop 10 rating increases:")
    print(hdr)
    print(sep)
    for _, row in df.nlargest(10, 'rating_delta').iterrows():
        print(fmt_row(row))

    print("\nTop 10 rating decreases:")
    print(hdr)
    print(sep)
    for _, row in df.nsmallest(10, 'rating_delta').iterrows():
        print(fmt_row(row))

    # Data quality warnings from dataset generation
    stats_path = dataset_path.parent / 'generation_stats.json'
    if stats_path.exists():
        with open(stats_path) as f:
            gen_stats = json.load(f)
        warnings = gen_stats.get('data_warnings', [])
        print("\n" + "=" * 80)
        print(f"DATA QUALITY WARNINGS ({len(warnings)} total)")
        print("=" * 80)
        if warnings:
            whdr = f"{'File':<50} {'Type':<14} {'Diff':<10} {'Rtg':>4}  Issue"
            print(whdr)
            print("-" * 84)
            for w in warnings:
                short_file = '/'.join(w['file'].replace('\\', '/').split('/')[-3:])
                print(f"{short_file:<50} {w['chart_type']:<14} {w['difficulty']:<10}"
                      f" {w['original_rating']:>4}  {w['issue']}")
        else:
            print("  None — all charts passed quality checks.")

    # Save full dataset with ratings
    print("\n" + "=" * 80)
    print("SAVING OUTPUT")
    print("=" * 80)

    output_dir = output_path.parent
    output_dir.mkdir(parents=True, exist_ok=True)

    # Save full dataset
    full_output = output_dir / 'dataset_with_calculated_ratings.parquet'
    df.to_parquet(full_output, index=False)
    print(f"\n✓ Saved full dataset to {full_output}")

    # Create compact mapping file
    mapping = []
    for _, row in df.iterrows():
        mapping.append({
            'file_path': row['file_path'],
            'pack_name': row['pack_name'],
            'title': row['title'],
            'chart_type': convert_chart_type_to_stepmania_format(row['chart_type']),
            'difficulty': row['difficulty'],
            'original_rating': float(row['original_rating']),
            'calculated_rating': float(row['calculated_rating_rounded']),
            'detected_scale': row['detected_scale']
        })

    # Save as JSON
    json_output = output_dir / 'calculated_ratings.json'
    with open(json_output, 'w') as f:
        json.dump(mapping, f, indent=2)
    print(f"✓ Saved rating mapping to {json_output}")

    # Save as CSV for easy viewing
    csv_output = output_dir / 'calculated_ratings.csv'
    pd.DataFrame(mapping).to_csv(csv_output, index=False)
    print(f"✓ Saved rating CSV to {csv_output}")

    # Create summary by scale
    print("\n" + "=" * 80)
    print("RATING CHANGES BY SCALE")
    print("=" * 80)

    for scale in df['detected_scale'].unique():
        scale_df = df[df['detected_scale'] == scale]
        avg_delta = scale_df['rating_delta'].mean()
        print(f"\n{scale}:")
        print(f"  Charts: {len(scale_df)}")
        print(f"  Avg original rating: {scale_df['original_rating'].mean():.2f}")
        print(f"  Avg calculated rating: {scale_df['calculated_rating'].mean():.2f}")
        print(f"  Avg change: {avg_delta:+.2f}")

    print("\n" + "=" * 80)
    print("✓ COMPLETE")
    print("=" * 80)

    return df


def main():
    parser = argparse.ArgumentParser(
        description='Generate calculated difficulty ratings for all charts'
    )
    data_dir = get_data_dir()
    parser.add_argument(
        '--dataset',
        type=Path,
        default=data_dir / 'processed' / 'dataset.parquet',
        help='Path to dataset file'
    )
    parser.add_argument(
        '--model-dir',
        type=Path,
        default=data_dir / 'models',
        help='Directory containing trained model'
    )
    parser.add_argument(
        '--output',
        type=Path,
        default=data_dir / 'calculated_ratings' / 'calculated_ratings.json',
        help='Output path for rating mappings'
    )

    args = parser.parse_args()

    df = generate_ratings(args.dataset, args.model_dir, args.output)

    print(f"\nOutput files:")
    print(f"  JSON mapping: {args.output.parent / 'calculated_ratings.json'}")
    print(f"  CSV mapping: {args.output.parent / 'calculated_ratings.csv'}")
    print(f"  Full dataset: {args.output.parent / 'dataset_with_calculated_ratings.parquet'}")


if __name__ == '__main__':
    main()
