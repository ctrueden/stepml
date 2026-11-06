"""
Tests for the anchor-fitted crossover correction.
"""

import numpy as np
import pandas as pd
import pytest

from stepml.models import crossover_correction as cc
from stepml.utils.data_structures import ScaleType


def _dataset(ratios, chart_type="dance-double"):
    return pd.DataFrame(
        {
            "file_path": [f"Songs/Pack/Song{i}/x.sm" for i in range(len(ratios))],
            "chart_type": chart_type,
            "difficulty": "Hard",
            "crossover_ratio": ratios,
        }
    )


def _anchors(felt, width=0.5):
    return [
        {
            "song": f"Pack/Song{i}",
            "chart_type": "dance-double",
            "difficulty": "Hard",
            "min": f - width / 2,
            "max": f + width / 2,
        }
        for i, f in enumerate(felt)
    ]


class TestCrossoverCorrection:
    def test_recovers_beta(self):
        # Felt difficulty rises 4 per crossover per step above the model.
        ratios = np.array([0.0, 0.02, 0.05, 0.08, 0.1])
        df = _dataset(ratios)
        ratings = pd.Series(12.0, index=df.index)
        felt = 12.0 + 4.0 * (ratios - np.median(ratios))
        correction = cc.fit(df, _anchors(felt), ratings)
        assert correction.reference == pytest.approx(0.05)
        assert correction.beta == pytest.approx(4.0, abs=1e-3)

    def test_beta_is_never_negative(self):
        ratios = np.array([0.0, 0.05, 0.1])
        df = _dataset(ratios)
        felt = 12.0 - 4.0 * ratios  # crossovers "easier": not allowed
        correction = cc.fit(df, _anchors(felt), pd.Series(12.0, index=df.index))
        assert correction.beta == pytest.approx(0.0, abs=1e-3)

    def test_one_sided_range_only_pulls_when_missed(self):
        df = _dataset([0.0, 0.1])
        ratings = pd.Series(12.0, index=df.index)
        anchors = [
            {"song": "Pack/Song0", "chart_type": "dance-double",
             "difficulty": "Hard", "max": 12.5},
            {"song": "Pack/Song1", "chart_type": "dance-double",
             "difficulty": "Hard", "min": 12.0},
        ]  # fmt: skip
        # Both already satisfied at beta = 0, so nothing to correct.
        assert cc.fit_beta(cc.anchor_points(df, anchors, ratings), 0.05) == (
            pytest.approx(0.0, abs=1e-3)
        )

    def test_singles_untouched(self):
        df = pd.concat([_dataset([0.2]), _dataset([0.2], "dance-single")])
        df = df.reset_index(drop=True)
        correction = cc.CrossoverCorrection(beta=5.0, reference=0.0)
        out = correction.apply(df, np.array([7.0, 7.0]), ScaleType.ITG)
        assert out[0] > 7.0
        assert out[1] == 7.0

    def test_scale_round_trip(self):
        ratings = np.array([3.0, 6.5, 9.0])
        modern = cc.to_modern(ratings, ScaleType.ITG)
        assert cc.from_modern(modern, ScaleType.ITG) == pytest.approx(ratings)

    def test_leave_one_out_excludes_own_anchor(self):
        ratios = np.array([0.0, 0.05, 0.1])
        df = _dataset(ratios)
        ratings = pd.Series(12.0, index=df.index)
        # Only the last anchor wants a correction; without it, none is fitted.
        felt = [12.0, 12.0, 13.0]
        loo = cc.leave_one_out(df, _anchors(felt, width=0.0), ratings)
        assert loo[2] == pytest.approx(12.0, abs=1e-3)
        assert loo[0] < 12.0  # the others see the third anchor's pull
