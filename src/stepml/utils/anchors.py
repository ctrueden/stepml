"""
Anchor charts: felt difficulty from actual play (see anchor_charts.yaml).
"""

from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd
import yaml


def load_anchors(path: Path) -> List[Dict]:
    """Return the anchor entries from an anchor_charts.yaml file."""
    with open(path) as f:
        return (yaml.safe_load(f) or {}).get("anchors", [])


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
