"""
Compare calculated ratings against felt difficulty of anchor charts.

Anchors (anchor_charts.yaml) record how specific charts actually played. This
script reports, for each one, the training label, the calculated rating, and
how far the calculated rating falls outside the felt range, plus any violated
"harder than" orderings.

Usage:
    check-anchors [--ratings PATH] [--anchors PATH]
"""

import argparse
from pathlib import Path

import pandas as pd

from stepml.models import crossover_correction
from stepml.utils import get_data_dir, get_stepml_root
from stepml.utils.anchors import find_chart, load_anchors, miss


def check_anchors(ratings_path: Path, anchors_path: Path) -> pd.DataFrame:
    df = pd.read_parquet(ratings_path)
    anchors = load_anchors(anchors_path)
    # The crossover correction is fitted to these very anchors, so also
    # judge each one by a correction fitted without it.
    loo = {}
    if "uncorrected_rating" in df.columns:
        loo = crossover_correction.leave_one_out(df, anchors, df["uncorrected_rating"])

    rows = []
    order_violations = []
    for a in anchors:
        chart_type = a["chart_type"]
        row = find_chart(df, a["song"], chart_type, a["difficulty"])
        if row is None:
            print(f"  NOT FOUND: {a['song']} {chart_type} {a['difficulty']}")
            continue
        calc = float(row["calculated_rating"])
        lo, hi = a.get("min"), a.get("max")
        rows.append(
            {
                "song": a["song"].split("/", 1)[1][:36],
                "type": chart_type.removeprefix("dance-"),
                "diff": a["difficulty"],
                "label": float(row["ground_truth_rating"]),
                "gt": bool(row.get("has_ground_truth", False)),
                "calc": calc,
                "felt": f"{lo if lo is not None else '':>5}–{hi if hi is not None else '':<5}",
                "miss": miss(calc, lo, hi),
                "loo": miss(loo[row.name], lo, hi) if row.name in loo else None,
                "raw": miss(row["uncorrected_rating"], lo, hi) if loo else None,
            }
        )
        for other in a.get("harder_than", []):
            song, difficulty = other.rsplit(":", 1)
            other_row = find_chart(df, song, chart_type, difficulty)
            if other_row is None:
                print(f"  NOT FOUND: {song} {chart_type} {difficulty}")
                continue
            other_calc = float(other_row["calculated_rating"])
            if calc <= other_calc:
                order_violations.append(
                    f"{a['song']} ({calc:.2f}) should out-rate "
                    f"{song}:{difficulty} ({other_calc:.2f})"
                )

    result = pd.DataFrame(rows)
    with pd.option_context("display.width", 200):
        print(
            result.drop(columns="raw").to_string(
                index=False, float_format=lambda v: f"{v:.2f}", na_rep=""
            )
        )

    within = int((result["miss"] == 0).sum())
    print(f"\nWithin felt range: {within}/{len(result)}")
    print(f"Mean |miss|: {result['miss'].abs().mean():.3f}")
    # Anchors without a ground-truth override are the honest test: the model
    # was not told their answer.
    free = result[~result["gt"]]
    if len(free):
        print(
            f"Mean |miss| (no override, {len(free)} charts): "
            f"{free['miss'].abs().mean():.3f}"
        )
    held_out = result.dropna(subset=["loo"])
    if len(held_out):
        print(
            f"\nLeave-one-out crossover correction ({len(held_out)} doubles):"
            f" within {int((held_out['loo'] == 0).sum())},"
            f" mean |miss| {held_out['loo'].abs().mean():.3f}"
            f" (uncorrected: within {int((held_out['raw'] == 0).sum())},"
            f" mean |miss| {held_out['raw'].abs().mean():.3f})"
        )
    if order_violations:
        print("\nOrdering violations:")
        for v in order_violations:
            print(f"  {v}")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    parser.add_argument(
        "--ratings",
        type=Path,
        default=get_data_dir()
        / "modern_ddr"
        / "output"
        / "dataset_with_calculated_ratings.parquet",
        help="Dataset with calculated_rating column (default: modern_ddr output)",
    )
    parser.add_argument(
        "--anchors",
        type=Path,
        default=get_stepml_root() / "anchor_charts.yaml",
        help="Anchor charts YAML (default: anchor_charts.yaml)",
    )
    args = parser.parse_args()
    check_anchors(args.ratings, args.anchors)


if __name__ == "__main__":
    main()
