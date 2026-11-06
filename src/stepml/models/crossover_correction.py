"""
Anchor-fitted crossover correction for double charts.

The ratings in chart files carry almost no crossover signal: once density is
accounted for, double labels do not rise with crossover rate, so the model
cannot learn it. Charts that have actually been played (anchor_charts.yaml)
say otherwise: how far a double chart's felt difficulty exceeds its
calculated rating grows with its crossovers per step. This adds that term
back as a single linear adjustment fitted to the anchors:

    rating += beta * (crossover_ratio - median crossover_ratio of doubles)

with beta >= 0. Each anchor contributes its squared distance from the middle
of its felt range, or for a one-sided range its squared miss outside it. The
fit is in modern_ddr units (as anchors are); ratings on other scales are
converted there and back.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional

import numpy as np
import pandas as pd
from scipy.optimize import minimize_scalar

from stepml.utils.anchors import find_chart
from stepml.utils.data_structures import ScaleType
from stepml.utils.rating_normalizer import RatingNormalizer

CHART_TYPE = "dance-double"
FEATURE = "crossover_ratio"
_MAX_BETA = 50.0
# Tie-breaker: among equally good fits, prefer the smallest correction.
_RIDGE = 1e-6

_TO_MODERN = {
    ScaleType.CLASSIC_DDR: RatingNormalizer.CLASSIC_DDR_TO_UNIFIED,
    ScaleType.ITG: RatingNormalizer.ITG_TO_UNIFIED,
}


def to_modern(ratings: np.ndarray, scale: ScaleType) -> np.ndarray:
    """Convert ratings on the given scale to modern_ddr, interpolating."""
    if scale not in _TO_MODERN:
        return np.asarray(ratings, dtype=float)
    table = sorted(_TO_MODERN[scale].items())
    return np.interp(ratings, [s for s, _ in table], [m for _, m in table])


def from_modern(ratings: np.ndarray, scale: ScaleType) -> np.ndarray:
    """Convert modern_ddr ratings to the given scale, interpolating."""
    if scale not in _TO_MODERN:
        return np.asarray(ratings, dtype=float)
    table = sorted(_TO_MODERN[scale].items())
    return np.interp(ratings, [m for _, m in table], [s for s, _ in table])


@dataclass
class AnchorPoint:
    """One anchor chart, as the fit sees it."""

    index: int  # dataset row label
    rating: float  # uncorrected, modern_ddr
    ratio: float  # crossover_ratio
    lo: Optional[float]
    hi: Optional[float]


@dataclass
class CrossoverCorrection:
    beta: float
    reference: float

    def adjustment(self, df: pd.DataFrame) -> np.ndarray:
        """Modern_ddr rating adjustment for every row (0 unless double)."""
        is_double = (df["chart_type"] == CHART_TYPE).to_numpy()
        delta = self.beta * (df[FEATURE].to_numpy() - self.reference)
        return np.where(is_double, delta, 0.0)

    def apply(
        self, df: pd.DataFrame, ratings: np.ndarray, scale: ScaleType
    ) -> np.ndarray:
        """Corrected ratings on the given scale."""
        modern = to_modern(ratings, scale)
        # Add only the converted change, so that unadjusted rows are left
        # exactly as they were even outside the conversion table's range.
        return ratings + (
            from_modern(modern + self.adjustment(df), scale)
            - from_modern(modern, scale)
        )


def reference_ratio(df: pd.DataFrame) -> float:
    """Median crossover_ratio of double charts: the zero point of the term."""
    return float(df.loc[df["chart_type"] == CHART_TYPE, FEATURE].median())


def anchor_points(
    df: pd.DataFrame, anchors: List[Dict], ratings: pd.Series
) -> List[AnchorPoint]:
    """Double anchors with a felt range that are present in the dataset."""
    points = []
    for a in anchors:
        lo, hi = a.get("min"), a.get("max")
        if a["chart_type"] != CHART_TYPE or (lo is None and hi is None):
            continue
        row = find_chart(df, a["song"], a["chart_type"], a["difficulty"])
        if row is None:
            continue
        points.append(
            AnchorPoint(row.name, float(ratings[row.name]), row[FEATURE], lo, hi)
        )
    return points


def fit_beta(points: List[AnchorPoint], reference: float) -> float:
    """The beta >= 0 that best fits the given anchors."""
    if not points:
        return 0.0
    rating = np.array([p.rating for p in points])
    x = np.array([p.ratio for p in points]) - reference
    lo = np.array([np.nan if p.lo is None else p.lo for p in points])
    hi = np.array([np.nan if p.hi is None else p.hi for p in points])
    two_sided = ~np.isnan(lo) & ~np.isnan(hi)
    middle = (lo + hi) / 2

    def loss(beta):
        r = rating + beta * x
        err = np.where(
            two_sided,
            r - middle,
            np.fmin(r - lo, 0) + np.fmax(r - hi, 0),
        )
        return float(np.sum(np.nan_to_num(err) ** 2) + _RIDGE * beta**2)

    return float(minimize_scalar(loss, bounds=(0.0, _MAX_BETA)).x)


def fit(
    df: pd.DataFrame, anchors: List[Dict], ratings: pd.Series
) -> CrossoverCorrection:
    """
    Fit the correction to the anchors.

    Args:
        df: Dataset (with chart_type, file_path, difficulty, crossover_ratio)
        anchors: Entries from anchor_charts.yaml
        ratings: Uncorrected modern_ddr ratings, indexed like df
    """
    reference = reference_ratio(df)
    return CrossoverCorrection(
        fit_beta(anchor_points(df, anchors, ratings), reference), reference
    )


def leave_one_out(
    df: pd.DataFrame, anchors: List[Dict], ratings: pd.Series
) -> Dict[int, float]:
    """
    Corrected modern_ddr rating of each double anchor, fitted without it.

    This is the honest test of the correction: an anchor's own felt range
    never helps fit the rating it is judged by.
    """
    reference = reference_ratio(df)
    points = anchor_points(df, anchors, ratings)
    result = {}
    for i, p in enumerate(points):
        beta = fit_beta(points[:i] + points[i + 1 :], reference)
        result[p.index] = p.rating + beta * (p.ratio - reference)
    return result
