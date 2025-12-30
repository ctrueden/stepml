"""
Tests for scale detection and rating normalization.
"""
import pytest

from stepml.utils.scale_detector import ScaleDetector
from stepml.utils.rating_normalizer import RatingNormalizer
from stepml.utils.data_structures import ScaleType, NoteData, DifficultyType, ChartType, ChartData
from stepml.config import get_songs_dir


class TestScaleDetector:
    """Tests for ScaleDetector class."""

    @pytest.fixture
    def detector(self):
        """Create a scale detector instance."""
        return ScaleDetector()

    def test_classic_ddr_detection(self, detector):
        """Test detection of Classic DDR packs."""
        test_cases = [
            "DDR 1st Mix",
            "DDR 2nd Mix",
            "DDR 3rd Mix PLUS",
            "DDR 4th Mix",
            "DDR 5th Mix",
            "DDR EXTREME",
            "DDR SuperNOVA",
            "DS EuroMIX",
            "Dancing Stage",
        ]

        for pack_name in test_cases:
            scale, confidence = detector.detect_scale(f"/Songs/{pack_name}/Song/file.sm")
            assert scale == ScaleType.CLASSIC_DDR, f"Failed for {pack_name}"
            assert confidence > 0.8, f"Low confidence for {pack_name}: {confidence}"

    def test_modern_ddr_detection(self, detector):
        """Test detection of Modern DDR packs."""
        test_cases = [
            "DDR X",
            "DDR X2",
            "DDR A",
            "DDR A20",
            "DDR A3",
            "DDR 2013",
            "DDR 2014",
            "DDR SuperNOVA 2",
            "DDR Extreme 2",
        ]

        for pack_name in test_cases:
            scale, confidence = detector.detect_scale(f"/Songs/{pack_name}/Song/file.sm")
            assert scale == ScaleType.MODERN_DDR, f"Failed for {pack_name}"
            assert confidence > 0.8, f"Low confidence for {pack_name}: {confidence}"

    def test_itg_detection(self, detector):
        """Test detection of ITG packs."""
        test_cases = [
            "ITG",
            "ITG 2",
            "ITG 3",
            "ITG Rebirth",
            "ITG Rebirth 2 (Beta)",
            "[fraxtil] Beast Beats",
            "[SA] Video Game Step Pack",
            "Valex's Magical 4-Arrow Adventure",
            "Sudziosis",
        ]

        for pack_name in test_cases:
            scale, confidence = detector.detect_scale(f"/Songs/{pack_name}/Song/file.sm")
            assert scale == ScaleType.ITG, f"Failed for {pack_name}"
            assert confidence > 0.7, f"Low confidence for {pack_name}: {confidence}"

    def test_unknown_pack_detection(self, detector):
        """Test detection of unknown packs."""
        test_cases = [
            "Random Custom Pack",
            "My Songs",
            "Unknown Pack 123",
        ]

        for pack_name in test_cases:
            scale, confidence = detector.detect_scale(f"/Songs/{pack_name}/Song/file.sm")
            assert scale == ScaleType.UNKNOWN or confidence < 0.5, f"Unexpected detection for {pack_name}"

    def test_detection_with_statistics(self, detector):
        """Test statistical detection from chart ratings."""
        # Create mock charts with Classic DDR rating range
        classic_charts = [
            NoteData(ChartType.SINGLE, DifficultyType.EASY, 3, ""),
            NoteData(ChartType.SINGLE, DifficultyType.MEDIUM, 6, ""),
            NoteData(ChartType.SINGLE, DifficultyType.HARD, 8, ""),
            NoteData(ChartType.SINGLE, DifficultyType.CHALLENGE, 10, ""),
        ]

        chart_data = ChartData(
            filepath="/Songs/Unknown/Song/file.sm",
            format=".sm",
            songpack="Unknown",
            charts=classic_charts
        )
        scale, confidence = detector.detect_scale("/Songs/Unknown/Song/file.sm", chart_data)
        # Without name match, should rely on statistics
        assert scale == ScaleType.CLASSIC_DDR or scale == ScaleType.UNKNOWN

        # Modern DDR rating range
        modern_charts = [
            NoteData(ChartType.SINGLE, DifficultyType.EASY, 5, ""),
            NoteData(ChartType.SINGLE, DifficultyType.MEDIUM, 10, ""),
            NoteData(ChartType.SINGLE, DifficultyType.HARD, 15, ""),
            NoteData(ChartType.SINGLE, DifficultyType.CHALLENGE, 19, ""),
        ]

        chart_data = ChartData(
            filepath="/Songs/Unknown/Song/file.sm",
            format=".sm",
            songpack="Unknown",
            charts=modern_charts
        )
        scale, confidence = detector.detect_scale("/Songs/Unknown/Song/file.sm", chart_data)
        assert scale == ScaleType.MODERN_DDR

    def test_get_scale_info(self, detector):
        """Test scale information retrieval."""
        for scale_type in [ScaleType.CLASSIC_DDR, ScaleType.MODERN_DDR, ScaleType.ITG]:
            info = detector.get_scale_info(scale_type)
            assert "name" in info
            assert "range" in info
            assert "description" in info
            assert "era" in info


class TestRatingNormalizer:
    """Tests for RatingNormalizer class."""

    @pytest.fixture
    def normalizer(self):
        """Create a rating normalizer instance."""
        return RatingNormalizer()

    def test_classic_ddr_normalization(self, normalizer):
        """Test normalization of Classic DDR ratings."""
        test_cases = {
            1: 1.0,
            5: 9.0,
            7: 10.5,
            8: 12.0,
            9: 13.0,
            10: 14.5,
        }

        for original, expected in test_cases.items():
            normalized = normalizer.normalize(original, ScaleType.CLASSIC_DDR)
            assert normalized == expected, f"Classic DDR {original} -> {normalized}, expected {expected}"

    def test_itg_normalization(self, normalizer):
        """Test normalization of ITG ratings (with rating creep)."""
        test_cases = {
            1: 1.0,
            5: 9.0,
            8: 12.5,  # ITG 8 ≈ Classic DDR 9
            9: 14.0,
            10: 15.5,
            12: 18.5,
        }

        for original, expected in test_cases.items():
            normalized = normalizer.normalize(original, ScaleType.ITG)
            assert normalized == expected, f"ITG {original} -> {normalized}, expected {expected}"

    def test_modern_ddr_normalization(self, normalizer):
        """Test normalization of Modern DDR ratings (identity mapping)."""
        for rating in range(1, 21):
            normalized = normalizer.normalize(rating, ScaleType.MODERN_DDR)
            assert normalized == float(rating), f"Modern DDR {rating} should map to itself"

    def test_interpolation(self, normalizer):
        """Test interpolation for unmapped ratings."""
        # Test rating between mapped values (Classic DDR 6.5)
        # Should interpolate between 6->10.0 and 7->11.0
        normalized = normalizer.normalize(6.5, ScaleType.CLASSIC_DDR, interpolate=True)
        assert 10.0 < normalized < 11.0, f"Interpolation failed: {normalized}"

    def test_denormalization(self, normalizer):
        """Test converting unified ratings back to original scales."""
        # Test Classic DDR denormalization
        assert normalizer.denormalize(11.0, ScaleType.CLASSIC_DDR) == 7
        assert normalizer.denormalize(13.0, ScaleType.CLASSIC_DDR) == 9

        # Test ITG denormalization
        assert normalizer.denormalize(14.0, ScaleType.ITG) == 9
        assert normalizer.denormalize(19.0, ScaleType.ITG) == 12

        # Test Modern DDR denormalization (identity)
        for rating in [10, 12, 15, 18]:
            assert normalizer.denormalize(float(rating), ScaleType.MODERN_DDR) == rating

    def test_batch_normalization(self, normalizer):
        """Test batch normalization of multiple ratings."""
        ratings = {
            "Easy": 3,
            "Medium": 6,
            "Hard": 8,
            "Challenge": 10,
        }

        normalized = normalizer.batch_normalize(ratings, ScaleType.CLASSIC_DDR)

        assert len(normalized) == len(ratings)
        assert normalized["Easy"] == 5.0
        assert normalized["Medium"] == 10.0
        assert normalized["Hard"] == 12.0
        assert normalized["Challenge"] == 14.5

    def test_get_scale_range(self, normalizer):
        """Test scale range retrieval."""
        assert normalizer.get_scale_range(ScaleType.CLASSIC_DDR) == (1, 10)
        assert normalizer.get_scale_range(ScaleType.MODERN_DDR) == (1, 20)
        assert normalizer.get_scale_range(ScaleType.ITG) == (1, 12)

    def test_get_conversion_info(self, normalizer):
        """Test detailed conversion information."""
        info = normalizer.get_conversion_info(ScaleType.ITG, 8)

        assert info["original_rating"] == 8
        assert info["source_scale"] == "itg"
        assert info["normalized_rating"] == 12.5
        assert "classic_ddr_equivalent" in info
        assert "modern_ddr_equivalent" in info
        assert "itg_equivalent" in info

    def test_unknown_scale_handling(self, normalizer):
        """Test handling of unknown scale type."""
        # Should return rating as-is
        normalized = normalizer.normalize(7, ScaleType.UNKNOWN)
        assert normalized == 7.0

    def test_configurable_target_scale_itg(self):
        """Test normalization to ITG target scale."""
        normalizer_itg = RatingNormalizer(target_scale=ScaleType.ITG)

        # Classic DDR to ITG conversions
        # Classic 10 → Modern 14.5 → ITG 9 (14.5 closer to 14.0 than 15.5)
        assert normalizer_itg.normalize(10, ScaleType.CLASSIC_DDR) == 9.0
        # Classic 8 → Modern 12.0 → ITG 8 (12.0 closer to 12.5 than 11.0)
        assert normalizer_itg.normalize(8, ScaleType.CLASSIC_DDR) == 8.0
        # Classic 9 → Modern 13.0 → ITG 8 (13.0 closer to 12.5 than 14.0)
        assert normalizer_itg.normalize(9, ScaleType.CLASSIC_DDR) == 8.0

        # Modern DDR to ITG conversions
        # Modern 14.0 → ITG 9
        assert normalizer_itg.normalize(14, ScaleType.MODERN_DDR) == 9.0
        # Modern 12.5 → ITG 8
        assert normalizer_itg.normalize(12, ScaleType.MODERN_DDR) == 8.0

        # ITG identity (should map to itself)
        for rating in [1, 5, 8, 9, 10, 12]:
            normalized = normalizer_itg.normalize(rating, ScaleType.ITG)
            assert normalized == float(rating), f"ITG {rating} → ITG should be identity"

    def test_configurable_target_scale_classic_ddr(self):
        """Test normalization to Classic DDR target scale."""
        normalizer_classic = RatingNormalizer(target_scale=ScaleType.CLASSIC_DDR)

        # ITG to Classic DDR conversions
        # ITG 9 → Modern 14.0 → Classic 10 (14.0 closest to 14.5)
        assert normalizer_classic.normalize(9, ScaleType.ITG) == 10.0
        # ITG 8 → Modern 12.5 → Classic 8 (12.5 equidistant from 12.0 and 13.0, picks 8)
        assert normalizer_classic.normalize(8, ScaleType.ITG) == 8.0
        # ITG 7 → Modern 11.0 → Classic 7 (11.0 closest to 10.5)
        assert normalizer_classic.normalize(7, ScaleType.ITG) == 7.0

        # Modern DDR to Classic DDR conversions
        # Modern 13.0 → Classic 9
        assert normalizer_classic.normalize(13, ScaleType.MODERN_DDR) == 9.0
        # Modern 10.5 → Classic 7
        assert normalizer_classic.normalize(10.5, ScaleType.MODERN_DDR) == 7.0

        # Classic DDR identity (should map to itself)
        for rating in [1, 5, 7, 8, 9, 10]:
            normalized = normalizer_classic.normalize(rating, ScaleType.CLASSIC_DDR)
            assert normalized == float(rating), f"Classic {rating} → Classic should be identity"

    def test_configurable_target_scale_modern_ddr(self):
        """Test that default Modern DDR target scale still works correctly."""
        normalizer_modern = RatingNormalizer(target_scale=ScaleType.MODERN_DDR)

        # Should behave identically to default normalizer
        # Classic to Modern
        assert normalizer_modern.normalize(10, ScaleType.CLASSIC_DDR) == 14.5
        assert normalizer_modern.normalize(8, ScaleType.CLASSIC_DDR) == 12.0

        # ITG to Modern
        assert normalizer_modern.normalize(9, ScaleType.ITG) == 14.0
        assert normalizer_modern.normalize(8, ScaleType.ITG) == 12.5

        # Modern identity
        for rating in range(1, 21):
            normalized = normalizer_modern.normalize(rating, ScaleType.MODERN_DDR)
            assert normalized == float(rating), f"Modern {rating} should map to itself"

    def test_cross_scale_conversion_symmetry(self):
        """Test that cross-scale conversions maintain reasonable symmetry."""
        normalizer_itg = RatingNormalizer(target_scale=ScaleType.ITG)
        normalizer_classic = RatingNormalizer(target_scale=ScaleType.CLASSIC_DDR)

        # Classic 10 → ITG and ITG 9 → Classic should be roughly equivalent difficulty
        classic_to_itg = normalizer_itg.normalize(10, ScaleType.CLASSIC_DDR)
        itg_to_classic = normalizer_classic.normalize(9, ScaleType.ITG)

        # Both represent approximately the same difficulty level
        assert classic_to_itg == 9.0  # Classic 10 → Modern 14.5 → ITG 9
        assert itg_to_classic == 10.0  # ITG 9 → Modern 14.0 → Classic 10

        # Verify round-trip consistency (Classic → Modern → ITG → Modern → Classic)
        normalizer_modern = RatingNormalizer(target_scale=ScaleType.MODERN_DDR)
        classic_8_to_modern = normalizer_modern.normalize(8, ScaleType.CLASSIC_DDR)  # 12.0
        modern_12_to_itg = normalizer_itg.normalize(12, ScaleType.MODERN_DDR)  # 8.0
        itg_8_to_modern = normalizer_modern.normalize(8, ScaleType.ITG)  # 12.5
        # Should be close (within rounding)
        assert abs(classic_8_to_modern - itg_8_to_modern) <= 1.0

    def test_configurable_target_scale_with_interpolation(self):
        """Test that interpolation works correctly with configurable target scales."""
        normalizer_itg = RatingNormalizer(target_scale=ScaleType.ITG)

        # Test Classic DDR interpolation to ITG
        # Classic 8.5 should interpolate between 8→12.0 and 9→13.0
        # Unified: 12.5, then to ITG should be ~8
        normalized = normalizer_itg.normalize(8.5, ScaleType.CLASSIC_DDR, interpolate=True)
        assert 8.0 <= normalized <= 9.0, f"Interpolated value {normalized} out of expected range"


@pytest.mark.integration
class TestScaleDetectionIntegration:
    """Integration tests using real song collection."""

    @pytest.fixture
    def detector(self):
        return ScaleDetector()

    @pytest.fixture
    def songs_dir(self):
        return get_songs_dir()

    def test_real_classic_ddr_packs(self, detector, songs_dir):
        """Test detection on real Classic DDR packs."""
        if not songs_dir.exists():
            pytest.skip("Songs directory not available")

        classic_packs = [
            "DDR 1st Mix",
            "DDR 2nd Mix",
            "DDR 3rd Mix",
            "DDR EXTREME",
        ]

        for pack in classic_packs:
            pack_path = songs_dir / pack
            if pack_path.exists():
                scale, confidence = detector.detect_scale(str(pack_path))
                assert scale == ScaleType.CLASSIC_DDR, f"Misdetected {pack}"
                assert confidence > 0.8

    def test_real_modern_ddr_packs(self, detector, songs_dir):
        """Test detection on real Modern DDR packs."""
        if not songs_dir.exists():
            pytest.skip("Songs directory not available")

        modern_packs = [
            "DDR A",
            "DDR A20",
            "DDR 2013",
        ]

        for pack in modern_packs:
            pack_path = songs_dir / pack
            if pack_path.exists():
                scale, confidence = detector.detect_scale(str(pack_path))
                assert scale == ScaleType.MODERN_DDR, f"Misdetected {pack}"
                assert confidence > 0.8

    def test_real_itg_packs(self, detector, songs_dir):
        """Test detection on real ITG packs."""
        if not songs_dir.exists():
            pytest.skip("Songs directory not available")

        itg_packs = [
            "ITG",
            "ITG 2",
            "ITG Rebirth",
        ]

        for pack in itg_packs:
            pack_path = songs_dir / pack
            if pack_path.exists():
                scale, confidence = detector.detect_scale(str(pack_path))
                assert scale == ScaleType.ITG, f"Misdetected {pack}"
                assert confidence > 0.7
