"""
Rating normalization across different StepMania scale types.

Converts ratings between Classic DDR, Modern DDR, and ITG scales
to a unified rating system for consistent ML training and comparison.
"""

from typing import Dict, Optional

from stepml.utils.data_structures import ScaleType


class RatingNormalizer:
    """
    Normalizes ratings across different scale types.

    The unified scale uses Modern DDR (1-20) as the reference, since it provides
    the finest granularity and covers the full difficulty spectrum.

    Supports configurable target normalization scales (Classic DDR, Modern DDR, or ITG).
    """

    # Conversion tables: source_scale -> {source_rating: unified_rating}
    # Based on observed difficulty equivalencies and rating creep adjustments

    CLASSIC_DDR_TO_UNIFIED = {
        1: 1.0,  # Beginner levels map 1:1 at low end
        2: 3.0,
        3: 5.0,
        4: 7.0,
        5: 9.0,
        6: 10.0,
        7: 10.5,  # Classic 7 ≈ Modern 10-11
        8: 12.0,  # Classic 8 ≈ Modern 12
        9: 13.0,  # Classic 9 ≈ Modern 13
        10: 14.5,  # Classic 10 baseline (refined using metrics)
        # Easy 10s (SAKURA): ~13, Hard 10s (PSMO): ~16
        11: 16.0,  # Extended classic scale - extremely difficult
        12: 17.5,  # Extended classic scale - beyond classic 10 flashing territory
    }

    ITG_TO_UNIFIED = {
        1: 1.0,
        2: 3.0,
        3: 5.0,
        4: 7.0,
        5: 9.0,
        6: 10.0,  # ITG 6 ≈ Modern 10
        7: 11.0,  # ITG 7 ≈ Modern 11
        8: 12.5,  # ITG 8 ≈ Modern 12-13 (reduced from 14.0)
        9: 14.0,  # ITG 9 ≈ Modern 14 (reduced from 15.0)
        10: 15.5,  # ITG 10 ≈ Modern 15-16 (reduced from 16.5)
        11: 17.0,  # ITG 11 ≈ Modern 17 (reduced from 18.0)
        12: 18.5,  # ITG 12 ≈ Modern 18-19 (reduced from 19.0)
    }

    # Modern DDR maps directly (it's our reference scale)
    MODERN_DDR_TO_UNIFIED = {i: float(i) for i in range(1, 21)}

    # Reverse mappings for denormalization (if needed)
    UNIFIED_TO_CLASSIC_DDR = {v: k for k, v in CLASSIC_DDR_TO_UNIFIED.items()}

    UNIFIED_TO_ITG = {v: k for k, v in ITG_TO_UNIFIED.items()}

    UNIFIED_TO_MODERN_DDR = {v: k for k, v in MODERN_DDR_TO_UNIFIED.items()}

    def __init__(self, target_scale: ScaleType = ScaleType.MODERN_DDR):
        """
        Initialize the rating normalizer.

        Args:
            target_scale: The scale to normalize ratings to (default: Modern DDR 1-20).
                         Options: ScaleType.CLASSIC_DDR (1-10), ScaleType.MODERN_DDR (1-20),
                         or ScaleType.ITG (1-12).
        """
        self.target_scale = target_scale
        self.conversion_tables = {
            ScaleType.CLASSIC_DDR: self.CLASSIC_DDR_TO_UNIFIED,
            ScaleType.ITG: self.ITG_TO_UNIFIED,
            ScaleType.MODERN_DDR: self.MODERN_DDR_TO_UNIFIED,
        }

    def normalize(
        self,
        rating: int,
        source_scale: ScaleType,
        interpolate: bool = True,
        notes_per_second: Optional[float] = None,
        total_notes: Optional[int] = None,
    ) -> float:
        """
        Normalize a rating from a source scale to the target scale.

        Args:
            rating: Original rating value
            source_scale: The scale type of the original rating
            interpolate: If True, interpolate between known values
            notes_per_second: Optional NPS for metric-based refinement
            total_notes: Optional step count for metric-based refinement

        Returns:
            Normalized rating on target scale (configured in __init__, default 1-20 Modern DDR)
        """
        if source_scale == ScaleType.UNKNOWN:
            # No conversion possible, return as-is
            return float(rating)

        if source_scale not in self.conversion_tables:
            return float(rating)

        conversion_table = self.conversion_tables[source_scale]

        # Step 1: Convert to unified scale (Modern DDR 1-20)
        unified_rating = None

        # Special refinement for Classic DDR 10s using metrics
        if (
            source_scale == ScaleType.CLASSIC_DDR
            and rating == 10
            and notes_per_second is not None
        ):
            unified_rating = self._refine_classic_10(notes_per_second, total_notes)
        # Direct lookup if rating exists in table
        elif rating in conversion_table:
            unified_rating = conversion_table[rating]
        # Interpolate if requested
        elif interpolate:
            unified_rating = self._interpolate_rating(rating, conversion_table)
        else:
            # Fall back to identity mapping
            unified_rating = float(rating)

        # Step 2: Convert from unified scale to target scale (if different)
        if self.target_scale == ScaleType.MODERN_DDR:
            # Already in target scale
            return unified_rating
        else:
            # Convert unified → target scale
            return float(self.denormalize(unified_rating, self.target_scale))

    def _refine_classic_10(
        self, notes_per_second: float, total_notes: Optional[int] = None
    ) -> float:
        """
        Refine Classic DDR 10 ratings using chart metrics.

        Classic 10s vary widely in modern scale (13-16):
        - Easy 10s (SAKURA, ~3-8 NPS): Modern 13
        - Medium 10s (~8-14 NPS): Modern 14
        - Hard 10s (~14-20 NPS): Modern 15
        - Flashing 10s (PSMO, 20+ NPS): Modern 16

        Based on dataset analysis:
        - Rating 9 median: 9.4 NPS
        - Rating 10 median: 15.7 NPS
        - Rating 10 range: 2.7-37.5 NPS

        Args:
            notes_per_second: Notes per second for the chart
            total_notes: Optional total step count (fallback if NPS unreliable)

        Returns:
            Refined rating (13.0 - 16.5)
        """
        # Primary: use notes_per_second (normalizes for song length)
        if notes_per_second >= 20.0:
            # Flashing 10 territory (PSMO level)
            return 16.0
        elif notes_per_second >= 14.0:
            # Hard 10s
            return 15.0
        elif notes_per_second >= 8.0:
            # Medium 10s
            return 14.0
        elif notes_per_second >= 4.0:
            # Easy 10s (SAKURA level)
            return 13.0
        else:
            # Very easy or possibly misclassified
            # But if it's rated 10, trust the rating with caution
            return 13.0

    def _interpolate_rating(
        self, rating: int, conversion_table: Dict[int, float]
    ) -> float:
        """
        Interpolate a rating between known conversion points.

        Args:
            rating: Rating to interpolate
            conversion_table: Conversion table to use

        Returns:
            Interpolated normalized rating
        """
        # Find bounding values
        lower_bound = None
        upper_bound = None

        for key in sorted(conversion_table.keys()):
            if key < rating:
                lower_bound = key
            elif key > rating:
                upper_bound = key
                break

        # Handle edge cases
        if lower_bound is None:
            # Rating below minimum, extrapolate from first two points
            keys = sorted(conversion_table.keys())[:2]
            if len(keys) >= 2:
                slope = (conversion_table[keys[1]] - conversion_table[keys[0]]) / (
                    keys[1] - keys[0]
                )
                return conversion_table[keys[0]] - slope * (keys[0] - rating)
            else:
                return float(rating)

        if upper_bound is None:
            # Rating above maximum, extrapolate from last two points
            keys = sorted(conversion_table.keys())[-2:]
            if len(keys) >= 2:
                slope = (conversion_table[keys[1]] - conversion_table[keys[0]]) / (
                    keys[1] - keys[0]
                )
                return conversion_table[keys[1]] + slope * (rating - keys[1])
            else:
                return float(rating)

        # Linear interpolation
        lower_unified = conversion_table[lower_bound]
        upper_unified = conversion_table[upper_bound]

        progress = (rating - lower_bound) / (upper_bound - lower_bound)
        return lower_unified + progress * (upper_unified - lower_unified)

    def denormalize(self, unified_rating: float, target_scale: ScaleType) -> int:
        """
        Convert a unified rating back to a target scale (for display purposes).

        Args:
            unified_rating: Rating on unified scale
            target_scale: Target scale type

        Returns:
            Rating in target scale (rounded to nearest integer)
        """
        if target_scale == ScaleType.UNKNOWN:
            return round(unified_rating)

        # Get reverse mapping
        reverse_tables = {
            ScaleType.CLASSIC_DDR: self.UNIFIED_TO_CLASSIC_DDR,
            ScaleType.ITG: self.UNIFIED_TO_ITG,
            ScaleType.MODERN_DDR: self.UNIFIED_TO_MODERN_DDR,
        }

        if target_scale not in reverse_tables:
            return round(unified_rating)

        reverse_table = reverse_tables[target_scale]

        # Find closest match
        closest_unified = min(
            reverse_table.keys(), key=lambda x: abs(x - unified_rating)
        )

        # If very close, use exact mapping
        if abs(closest_unified - unified_rating) < 0.5:
            return reverse_table[closest_unified]

        # Otherwise, find bounding values and interpolate
        sorted_unified = sorted(reverse_table.keys())
        lower = None
        upper = None

        for val in sorted_unified:
            if val <= unified_rating:
                lower = val
            elif val > unified_rating:
                upper = val
                break

        if lower is None:
            return reverse_table[sorted_unified[0]]
        if upper is None:
            return reverse_table[sorted_unified[-1]]

        # Linear interpolation
        progress = (unified_rating - lower) / (upper - lower)
        denormalized = reverse_table[lower] + progress * (
            reverse_table[upper] - reverse_table[lower]
        )

        return round(denormalized)

    def batch_normalize(
        self, ratings: Dict[str, int], source_scale: ScaleType
    ) -> Dict[str, float]:
        """
        Normalize a batch of ratings (e.g., all difficulties in a song).

        Args:
            ratings: Dictionary mapping difficulty names to ratings
            source_scale: Source scale type

        Returns:
            Dictionary mapping difficulty names to normalized ratings
        """
        return {
            difficulty: self.normalize(rating, source_scale)
            for difficulty, rating in ratings.items()
        }

    def get_scale_range(self, scale_type: ScaleType) -> tuple:
        """
        Get the typical rating range for a scale type.

        Args:
            scale_type: Scale type to query

        Returns:
            Tuple of (min_rating, max_rating)
        """
        ranges = {
            ScaleType.CLASSIC_DDR: (1, 10),
            ScaleType.MODERN_DDR: (1, 20),
            ScaleType.ITG: (1, 12),
            ScaleType.UNKNOWN: (1, 20),  # Assume widest range
        }
        return ranges.get(scale_type, (1, 20))

    def get_conversion_info(self, source_scale: ScaleType, rating: int) -> dict:
        """
        Get detailed conversion information for a rating.

        Args:
            source_scale: Source scale type
            rating: Rating to convert

        Returns:
            Dictionary with conversion details
        """
        normalized = self.normalize(rating, source_scale)

        return {
            "original_rating": rating,
            "source_scale": source_scale.value,
            "normalized_rating": normalized,
            "classic_ddr_equivalent": self.denormalize(
                normalized, ScaleType.CLASSIC_DDR
            ),
            "modern_ddr_equivalent": self.denormalize(normalized, ScaleType.MODERN_DDR),
            "itg_equivalent": self.denormalize(normalized, ScaleType.ITG),
        }
