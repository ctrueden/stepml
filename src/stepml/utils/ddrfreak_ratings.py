"""
Apply authoritative classic-DDR ratings (scraped from DDRFreak) to the dataset.

Many classic DDR / Dancing Stage packs have been partially "modernized": some
charts re-rated on the modern 1-20 scale, others left on the original 1-10
scale. That makes the in-file rating an unreliable training label. For packs
listed in ddrfreak_mixes.yaml we instead trust the original arcade foot rating
published by DDRFreak (ddrfreak_ratings.csv), re-normalizing it as a genuine
classic-DDR rating regardless of what the in-file number happens to be.

A correction is applied only when a chart matches DDRFreak on
(mix, normalized title, chart type, difficulty); unmatched charts keep their
existing normalized rating, so this is strictly additive and safe.
"""

import logging
from pathlib import Path
from typing import Dict, Tuple

import pandas as pd
import yaml

from stepml.scrape_ddrfreak import title_key
from stepml.utils.data_structures import ScaleType
from stepml.utils.rating_normalizer import RatingNormalizer

logger = logging.getLogger(__name__)


class DDRFreakRatings:
    """Overrides normalized_rating with DDRFreak classic ratings where known."""

    def __init__(self, mixes_path: Path, ratings_path: Path):
        self.mixes_path = Path(mixes_path)
        self.ratings_path = Path(ratings_path)
        # pack name (lower) -> mix id
        self.pack_to_mix: Dict[str, int] = {}
        # (mix_id, title_key, chart_type, difficulty) -> classic rating
        self.ratings: Dict[Tuple[int, str, str, str], int] = {}
        self._load()

    def _load(self):
        if self.mixes_path.exists():
            with open(self.mixes_path) as f:
                mapping = (yaml.safe_load(f) or {}).get("mixes", {})
            self.pack_to_mix = {str(k).lower(): int(v) for k, v in mapping.items()}
        else:
            logger.debug(f"No DDRFreak mix mapping at {self.mixes_path}")

        if self.ratings_path.exists():
            df = pd.read_csv(self.ratings_path)
            for r in df.itertuples(index=False):
                self.ratings[
                    (int(r.mix_id), r.title_key, r.chart_type, r.difficulty)
                ] = int(r.rating)
        else:
            logger.debug(f"No DDRFreak ratings at {self.ratings_path}")

        if self.pack_to_mix and self.ratings:
            logger.info(
                "Loaded DDRFreak ratings: %d mix(es) mapped, %d rating(s)",
                len(set(self.pack_to_mix.values())),
                len(self.ratings),
            )

    @property
    def available(self) -> bool:
        return bool(self.pack_to_mix and self.ratings)

    def apply(self, df: pd.DataFrame, target_scale: ScaleType) -> pd.DataFrame:
        """
        Return df with normalized_rating corrected from DDRFreak where matched.

        Adds ddrfreak_rating (the classic foot rating used, NaN if unmatched)
        and has_ddrfreak_rating (bool). original_rating is left untouched for
        provenance; only normalized_rating is recomputed.
        """
        df = df.copy()
        df["ddrfreak_rating"] = pd.NA
        df["has_ddrfreak_rating"] = False

        if not self.available:
            return df

        normalizer = RatingNormalizer(target_scale)
        per_pack: Dict[str, int] = {}

        for idx, row in df.iterrows():
            mix_id = self.pack_to_mix.get(str(row["pack_name"]).lower())
            if mix_id is None:
                continue
            key = (
                mix_id,
                title_key(str(row["title"])),
                row["chart_type"],
                row["difficulty"],
            )
            classic_rating = self.ratings.get(key)
            if classic_rating is None:
                continue

            normalized = normalizer.normalize(
                classic_rating,
                ScaleType.CLASSIC_DDR,
                notes_per_second=row.get("notes_per_second"),
                total_notes=row.get("total_notes"),
            )
            df.at[idx, "normalized_rating"] = normalized
            df.at[idx, "ddrfreak_rating"] = classic_rating
            df.at[idx, "has_ddrfreak_rating"] = True
            per_pack[row["pack_name"]] = per_pack.get(row["pack_name"], 0) + 1

        n = int(df["has_ddrfreak_rating"].sum())
        if n:
            logger.info("DDRFreak corrections applied to %d chart(s):", n)
            for pack, count in sorted(per_pack.items()):
                logger.info("  %-32s %d chart(s)", pack, count)
        return df
