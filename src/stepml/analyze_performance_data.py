"""
Analysis of performance-enriched dataset.

Explores the relationship between player performance data and chart difficulty ratings.
"""

import pandas as pd


def load_dataset(path="data/processed/dataset.parquet"):
    """Load the enriched dataset."""
    return pd.read_parquet(path)


def analyze_performance_correlation(df):
    """Analyze correlation between performance metrics and difficulty."""
    print("=" * 80)
    print("PERFORMANCE METRICS vs. DIFFICULTY CORRELATION")
    print("=" * 80)

    # Filter to charts with performance data
    perf_data = df[df["has_performance_data"]].copy()
    print(f"\nCharts with performance data: {len(perf_data)}")
    print(f"Charts with detailed scores: {perf_data['best_accuracy'].notna().sum()}")

    # Correlation with original rating
    print("\nCorrelation with original_rating:")
    perf_cols = [
        "times_played",
        "best_accuracy",
        "average_accuracy",
        "perceived_difficulty_factor",
        "perfect_rate",
        "miss_rate",
    ]

    for col in perf_cols:
        if col in perf_data.columns:
            valid_data = perf_data[[col, "original_rating"]].dropna()
            if len(valid_data) > 10:
                corr = valid_data[col].corr(valid_data["original_rating"])
                print(f"  {col:30s}: {corr:7.3f} (n={len(valid_data)})")

    # Scatter some examples
    print("\n" + "=" * 80)
    print("DIFFICULTY vs. PERFORMANCE EXAMPLES")
    print("=" * 80)

    # Group by original rating and show average accuracy
    rating_groups = perf_data[perf_data["best_accuracy"].notna()].groupby(
        "original_rating"
    )

    print("\nAverage accuracy by rating level:")
    print("Rating | Avg Accuracy | Std Dev | Charts")
    print("-" * 45)
    for rating, group in sorted(rating_groups):
        avg_acc = group["best_accuracy"].mean()
        std_acc = group["best_accuracy"].std()
        count = len(group)
        print(f"{rating:6.0f} | {avg_acc:11.2%} | {std_acc:7.2%} | {count:6d}")


def find_rating_anomalies(df):
    """Find charts where performance suggests different difficulty than stated."""
    print("\n" + "=" * 80)
    print("POTENTIAL RATING ANOMALIES")
    print("=" * 80)

    # Filter to charts with detailed performance data
    perf_data = df[df["best_accuracy"].notna()].copy()

    # Calculate expected difficulty from performance
    # Lower accuracy typically means higher difficulty
    # But also consider play count (more plays = more familiar)

    # Group by rating and calculate average accuracy
    rating_avg_accuracy = perf_data.groupby("original_rating")["best_accuracy"].mean()

    # For each chart, compare its accuracy to the average for its rating
    print("\nCharts significantly easier than their rating suggests:")
    print("(High accuracy compared to average for that rating level)")
    print()
    print(
        f"{'Title':<40} {'Diff':<10} {'Rating':>6} {'Accuracy':>9} {'Avg@Rating':>11} {'Delta':>7} {'Plays':>6}"
    )
    print("-" * 110)

    easier_charts = []
    for _, row in perf_data.iterrows():
        rating = row["original_rating"]
        accuracy = row["best_accuracy"]
        avg_acc = rating_avg_accuracy.get(rating, 0.9)

        # Significantly higher accuracy than average for this rating = easier
        if accuracy > avg_acc + 0.10 and row["times_played"] >= 2:  # At least 2 plays
            delta = accuracy - avg_acc
            easier_charts.append(
                {
                    "title": row["title"][:38],
                    "difficulty": row["difficulty"][:9],
                    "rating": rating,
                    "accuracy": accuracy,
                    "avg_accuracy": avg_acc,
                    "delta": delta,
                    "plays": row["times_played"],
                }
            )

    # Sort by delta and show top 15
    easier_charts.sort(key=lambda x: x["delta"], reverse=True)
    for chart in easier_charts[:15]:
        print(
            f"{chart['title']:<40} {chart['difficulty']:<10} {chart['rating']:6.0f} "
            f"{chart['accuracy']:9.2%} {chart['avg_accuracy']:11.2%} "
            f"{chart['delta']:+7.2%} {chart['plays']:6.0f}"
        )

    print("\n\nCharts significantly harder than their rating suggests:")
    print("(Low accuracy compared to average for that rating level)")
    print()
    print(
        f"{'Title':<40} {'Diff':<10} {'Rating':>6} {'Accuracy':>9} {'Avg@Rating':>11} {'Delta':>7} {'Plays':>6}"
    )
    print("-" * 110)

    harder_charts = []
    for _, row in perf_data.iterrows():
        rating = row["original_rating"]
        accuracy = row["best_accuracy"]
        avg_acc = rating_avg_accuracy.get(rating, 0.9)

        # Significantly lower accuracy than average for this rating = harder
        if accuracy < avg_acc - 0.10 and row["times_played"] >= 2:
            delta = accuracy - avg_acc
            harder_charts.append(
                {
                    "title": row["title"][:38],
                    "difficulty": row["difficulty"][:9],
                    "rating": rating,
                    "accuracy": accuracy,
                    "avg_accuracy": avg_acc,
                    "delta": delta,
                    "plays": row["times_played"],
                }
            )

    # Sort by delta and show top 15
    harder_charts.sort(key=lambda x: x["delta"])
    for chart in harder_charts[:15]:
        print(
            f"{chart['title']:<40} {chart['difficulty']:<10} {chart['rating']:6.0f} "
            f"{chart['accuracy']:9.2%} {chart['avg_accuracy']:11.2%} "
            f"{chart['delta']:+7.2%} {chart['plays']:6.0f}"
        )


def performance_feature_summary(df):
    """Summary statistics for performance features."""
    print("\n" + "=" * 80)
    print("PERFORMANCE FEATURE SUMMARY")
    print("=" * 80)

    perf_data = df[df["has_performance_data"]]

    print(f"\nTotal charts in dataset: {len(df)}")
    print(
        f"Charts with performance data: {len(perf_data)} ({len(perf_data) / len(df) * 100:.1f}%)"
    )

    # Play count distribution
    print("\nPlay count distribution:")
    play_counts = perf_data["times_played"].value_counts().sort_index()
    for plays, count in list(play_counts.items())[:10]:
        print(f"  {plays:2d} plays: {count:4d} charts")
    if len(play_counts) > 10:
        print(f"  ... ({len(play_counts) - 10} more distinct play counts)")

    # Grade distribution
    if "high_grade" in perf_data.columns:
        print("\nHigh grade distribution (top 10):")
        grade_dist = perf_data["high_grade"].value_counts().head(10)
        for grade, count in grade_dist.items():
            print(f"  {grade}: {count} charts")

    # Accuracy statistics
    accuracy_data = perf_data[perf_data["best_accuracy"].notna()]
    if len(accuracy_data) > 0:
        print(f"\nAccuracy statistics ({len(accuracy_data)} charts):")
        print(f"  Mean: {accuracy_data['best_accuracy'].mean():.2%}")
        print(f"  Median: {accuracy_data['best_accuracy'].median():.2%}")
        print(f"  Std Dev: {accuracy_data['best_accuracy'].std():.2%}")
        print(f"  Min: {accuracy_data['best_accuracy'].min():.2%}")
        print(f"  Max: {accuracy_data['best_accuracy'].max():.2%}")

        # Percentiles
        print("\n  Percentiles:")
        for pct in [10, 25, 50, 75, 90, 95, 99]:
            val = accuracy_data["best_accuracy"].quantile(pct / 100)
            print(f"    {pct:2d}th: {val:.2%}")


def main():
    print("\n" + "=" * 80)
    print("PERFORMANCE-ENRICHED DATASET ANALYSIS")
    print("=" * 80)

    # Load dataset
    df = load_dataset()
    print(f"\nDataset loaded: {len(df)} charts, {len(df.columns)} features")

    # Run analyses
    analyze_performance_correlation(df)
    find_rating_anomalies(df)
    performance_feature_summary(df)

    print("\n" + "=" * 80)
    print("ANALYSIS COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    main()
