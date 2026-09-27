"""
Ground truth rating overrides for known-incorrect normalized ratings.

Loads a YAML file of manual corrections and applies them to the dataset
before training.  The overrides replace normalized_rating with a
human-verified ground_truth_rating for specific charts.
"""

import logging
from pathlib import Path
from typing import Dict, List

import numpy as np
import pandas as pd
import yaml

from stepml.utils.data_structures import ScaleType
from stepml.utils.rating_normalizer import RatingNormalizer

logger = logging.getLogger(__name__)


class GroundTruthOverrides:
    """Applies manual rating corrections to a dataset DataFrame."""

    def __init__(self, overrides_path: Path):
        self.path = Path(overrides_path)
        self.overrides: List[Dict] = []
        self._load()

    def _load(self):
        if not self.path.exists():
            logger.debug(f"No ground truth file at {self.path}")
            return
        with open(self.path) as f:
            data = yaml.safe_load(f)
        self.overrides = (data or {}).get("overrides", [])
        self.pack_weights = (data or {}).get("pack_weights", [])
        logger.info(
            f"Loaded {len(self.overrides)} ground truth override(s) from {self.path}"
        )

    @staticmethod
    def _from_modern(rating: float, target_scale: ScaleType) -> float:
        """Convert a modern_ddr rating to the target scale, interpolating."""
        tables = {
            ScaleType.CLASSIC_DDR: RatingNormalizer.UNIFIED_TO_CLASSIC_DDR,
            ScaleType.ITG: RatingNormalizer.UNIFIED_TO_ITG,
        }
        if target_scale not in tables:
            return rating
        table = sorted(tables[target_scale].items())
        return float(np.interp(rating, [u for u, _ in table], [t for _, t in table]))

    def apply(
        self, df: pd.DataFrame, target_scale: ScaleType = ScaleType.MODERN_DDR
    ) -> pd.DataFrame:
        """
        Return a copy of df with ground_truth_rating and has_ground_truth columns.

        ground_truth_rating defaults to normalized_rating; overridden rows get
        the value from the YAML file (given on the modern_ddr scale, converted
        to target_scale).  has_ground_truth is True only for those rows so the
        training pipeline can report or weight them differently.
        """
        df = df.copy()
        df["ground_truth_rating"] = df["normalized_rating"]
        df["has_ground_truth"] = False
        df["label_weight"] = 1.0

        for entry in self.pack_weights:
            mask = df["pack_name"].str.lower() == entry["pack"].lower()
            df.loc[mask, "label_weight"] = float(entry["weight"])
            logger.info(
                "  Pack weight: %-40s ×%.1f  (%d rows)",
                repr(entry["pack"]),
                float(entry["weight"]),
                int(mask.sum()),
            )

        for override in self.overrides:
            song = override.get("song")
            title = override.get("title") or song
            chart_type = override.get("chart_type", "all")
            difficulty = override.get("difficulty", "all")
            pack = override.get("pack")
            rating = self._from_modern(float(override["rating"]), target_scale)

            if song:
                # file_path looks like "Songs/<Pack>/<Folder>/<file>.sm".
                mask = df["file_path"].str.contains(f"/{song}/", regex=False)
            else:
                mask = df["title"].str.lower() == title.lower()

            if pack:
                mask &= df["pack_name"].str.lower().str.contains(pack.lower(), na=False)

            if chart_type != "all":
                mask &= df["chart_type"].str.lower() == chart_type.lower()

            if difficulty != "all":
                mask &= df["difficulty"].str.lower() == difficulty.lower()

            n = mask.sum()
            if n == 0:
                logger.warning(
                    "Ground truth override matched 0 rows: %r %s %s%s",
                    title,
                    chart_type,
                    difficulty,
                    f" (pack={pack!r})" if pack else "",
                )
            else:
                df.loc[mask, "ground_truth_rating"] = rating
                df.loc[mask, "has_ground_truth"] = True
                logger.info(
                    "  GT override: %-40s %-14s %-10s → %.1f  (%d row%s)",
                    repr(title),
                    chart_type,
                    difficulty,
                    rating,
                    n,
                    "s" if n != 1 else "",
                )

        n_overridden = int(df["has_ground_truth"].sum())
        if n_overridden:
            logger.info(
                "Ground truth applied: %d row%s overridden, %d using normalized_rating",
                n_overridden,
                "s" if n_overridden != 1 else "",
                len(df) - n_overridden,
            )
        return df
