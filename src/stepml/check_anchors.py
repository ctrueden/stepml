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
from typing import Optional

import pandas as pd
import yaml

from stepml.utils import get_data_dir, get_stepml_root


def _song_mask(df: pd.DataFrame, song: str) -> pd.Series:
    # file_path looks like "Songs/<Pack>/<Folder>/<file>.sm".
    return df["file_path"].str.contains(f"/{song}/", regex=False)


def find_chart(
    df: pd.DataFrame, song: str, chart_type: str, difficulty: str
) -> Optional[pd.Series]:
    """Return the dataset row for the given chart, or None if absent."""
    mask = (
        _song_mask(df, song)
        & (df["chart_type"].str.lower() == chart_type.lower())
        & (df["difficulty"].str.lower() == difficulty.lower())
    )
    matches = df[mask]
    return matches.iloc[0] if len(matches) else None


def miss(value: float, lo: Optional[float], hi: Optional[float]) -> float:
    """Signed distance outside [lo, hi]: negative = too low, positive = too high."""
    if lo is not None and value < lo:
        return value - lo
    if hi is not None and value > hi:
        return value - hi
    return 0.0


def check_anchors(ratings_path: Path, anchors_path: Path) -> pd.DataFrame:
    df = pd.read_parquet(ratings_path)
    with open(anchors_path) as f:
        anchors = (yaml.safe_load(f) or {}).get("anchors", [])

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
    with pd.option_context("display.width", 200, "display.precision", 2):
        print(result.to_string(index=False))

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
