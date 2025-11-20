"""
Rating normalization across different StepMania scale types.

Converts ratings between Classic DDR, Modern DDR, and ITG scales
to a unified rating system for consistent ML training and comparison.
"""
from typing import Dict, Optional
from utils.data_structures import ScaleType


class RatingNormalizer:
    """
    Normalizes ratings across different scale types.

    The unified scale uses Modern DDR (1-20) as the reference, since it provides
    the finest granularity and covers the full difficulty spectrum.
    """

    # Conversion tables: source_scale -> {source_rating: unified_rating}
    # Based on observed difficulty equivalencies and rating creep adjustments

    CLASSIC_DDR_TO_UNIFIED = {
        1: 1.0,    # Beginner levels map 1:1 at low end
        2: 3.0,
        3: 5.0,
        4: 7.0,
        5: 9.0,
        6: 10.0,
        7: 11.0,   # Classic 7 ≈ Modern 11
        8: 13.0,   # Classic 8 ≈ Modern 13
        9: 14.0,   # Classic 9 ≈ Modern 14
        10: 16.0,  # Classic 10 (flashing 10) ≈ Modern 16
    }

    ITG_TO_UNIFIED = {
        1: 1.0,
        2: 3.0,
        3: 5.0,
        4: 7.0,
        5: 9.0,
        6: 11.0,
        7: 12.0,   # ITG has rating creep starting here
        8: 14.0,   # ITG 8 ≈ Classic DDR 9 ≈ Modern 14
        9: 15.0,   # ITG 9 ≈ Classic DDR hard-9/10 ≈ Modern 15
        10: 16.5,  # ITG 10 ≈ Modern 16-17
        11: 18.0,  # ITG 11 ≈ Modern 18
        12: 19.0,  # ITG 12 ≈ Modern 19
    }

    # Modern DDR maps directly (it's our reference scale)
    MODERN_DDR_TO_UNIFIED = {
        i: float(i) for i in range(1, 21)
    }

    # Reverse mappings for denormalization (if needed)
    UNIFIED_TO_CLASSIC_DDR = {
        v: k for k, v in CLASSIC_DDR_TO_UNIFIED.items()
    }

    UNIFIED_TO_ITG = {
        v: k for k, v in ITG_TO_UNIFIED.items()
    }

    UNIFIED_TO_MODERN_DDR = {
        v: k for k, v in MODERN_DDR_TO_UNIFIED.items()
    }

    def __init__(self):
        """Initialize the rating normalizer."""
        self.conversion_tables = {
            ScaleType.CLASSIC_DDR: self.CLASSIC_DDR_TO_UNIFIED,
            ScaleType.ITG: self.ITG_TO_UNIFIED,
            ScaleType.MODERN_DDR: self.MODERN_DDR_TO_UNIFIED,
        }

    def normalize(
        self,
        rating: int,
        source_scale: ScaleType,
        interpolate: bool = True
    ) -> float:
        """
        Normalize a rating from a source scale to the unified scale.

        Args:
            rating: Original rating value
            source_scale: The scale type of the original rating
            interpolate: If True, interpolate between known values

        Returns:
            Normalized rating on unified scale (1-20)
        """
        if source_scale == ScaleType.UNKNOWN:
            # No conversion possible, return as-is
            return float(rating)

        if source_scale not in self.conversion_tables:
            return float(rating)

        conversion_table = self.conversion_tables[source_scale]

        # Direct lookup if rating exists in table
        if rating in conversion_table:
            return conversion_table[rating]

        # Interpolate if requested
        if interpolate:
            return self._interpolate_rating(rating, conversion_table)

        # Fall back to identity mapping
        return float(rating)

    def _interpolate_rating(
        self,
        rating: int,
        conversion_table: Dict[int, float]
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
                slope = (conversion_table[keys[1]] - conversion_table[keys[0]]) / (keys[1] - keys[0])
                return conversion_table[keys[0]] - slope * (keys[0] - rating)
            else:
                return float(rating)

        if upper_bound is None:
            # Rating above maximum, extrapolate from last two points
            keys = sorted(conversion_table.keys())[-2:]
            if len(keys) >= 2:
                slope = (conversion_table[keys[1]] - conversion_table[keys[0]]) / (keys[1] - keys[0])
                return conversion_table[keys[1]] + slope * (rating - keys[1])
            else:
                return float(rating)

        # Linear interpolation
        lower_unified = conversion_table[lower_bound]
        upper_unified = conversion_table[upper_bound]

        progress = (rating - lower_bound) / (upper_bound - lower_bound)
        return lower_unified + progress * (upper_unified - lower_unified)

    def denormalize(
        self,
        unified_rating: float,
        target_scale: ScaleType
    ) -> int:
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
        closest_unified = min(reverse_table.keys(), key=lambda x: abs(x - unified_rating))

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
        denormalized = reverse_table[lower] + progress * (reverse_table[upper] - reverse_table[lower])

        return round(denormalized)

    def batch_normalize(
        self,
        ratings: Dict[str, int],
        source_scale: ScaleType
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
            "classic_ddr_equivalent": self.denormalize(normalized, ScaleType.CLASSIC_DDR),
            "modern_ddr_equivalent": self.denormalize(normalized, ScaleType.MODERN_DDR),
            "itg_equivalent": self.denormalize(normalized, ScaleType.ITG),
        }
