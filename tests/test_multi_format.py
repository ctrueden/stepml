"""
Comprehensive tests for multi-format parser support (Phase 3).

Tests .sm, .ssc, and .dwi parsers along with universal parser.
"""
import pytest
from pathlib import Path
import sys
sys.path.append(str(Path(__file__).parent.parent))

from parsers.sm_parser import parse_sm_file
from parsers.ssc_parser import parse_ssc_file
from parsers.dwi_parser import parse_dwi_file
from parsers.universal_parser import (
    parse_chart_file,
    detect_format,
    is_supported_format,
    UniversalParser
)
from utils.data_structures import ChartType, DifficultyType


# Test file paths
SONGS_DIR = Path("/home/curtis/Games/StepMania/Songs")
SM_FILE = SONGS_DIR / "StepMania 5/Goin' Under/Goin' Under.sm"
SSC_FILE = SONGS_DIR / "StepMania 5/Goin' Under/Goin' Under.ssc"
DWI_FILE = SONGS_DIR / "DDR GB 2/PARANOiA Rebirth/PARANOiA Rebirth.dwi"


class TestSSCParser:
    """Tests for StepMania 5 .ssc parser."""

    def test_parse_ssc_basic(self):
        """Test basic SSC parsing."""
        chart_data = parse_ssc_file(str(SSC_FILE))

        assert chart_data.title == "Goin' Under"
        assert chart_data.artist == "NegaRen"
        assert chart_data.genre == "Raggacore"
        assert chart_data.format == ".ssc"

    def test_ssc_version_tag(self):
        """Test SSC-specific version tag."""
        chart_data = parse_ssc_file(str(SSC_FILE))
        assert chart_data.version == "0.83"

    def test_ssc_timing_data(self):
        """Test timing data parsing."""
        chart_data = parse_ssc_file(str(SSC_FILE))

        assert len(chart_data.bpms) > 0
        assert chart_data.bpms[0].beat == 0.0
        assert chart_data.bpms[0].value == 210.0

    def test_ssc_multiple_charts(self):
        """Test parsing multiple charts from NOTEDATA sections."""
        chart_data = parse_ssc_file(str(SSC_FILE))

        # Should find multiple charts
        assert len(chart_data.charts) >= 5

        # Check we have different difficulties
        difficulties = {chart.difficulty for chart in chart_data.charts}
        assert DifficultyType.BEGINNER in difficulties
        assert DifficultyType.CHALLENGE in difficulties

    def test_ssc_chart_types(self):
        """Test parsing both single and double charts."""
        chart_data = parse_ssc_file(str(SSC_FILE))

        chart_types = {chart.chart_type for chart in chart_data.charts}
        assert ChartType.SINGLE in chart_types

    def test_ssc_note_data(self):
        """Test note data parsing (same format as .sm)."""
        chart_data = parse_ssc_file(str(SSC_FILE))

        # Find a chart with notes
        chart = next(c for c in chart_data.charts
                    if c.difficulty == DifficultyType.CHALLENGE)

        assert chart.total_notes > 0
        assert chart.tap_notes > 0
        assert len(chart.note_positions) > 0

    def test_ssc_scale_detection(self):
        """Test scale detection works for SSC files."""
        chart_data = parse_ssc_file(str(SSC_FILE))

        assert chart_data.detected_scale is not None
        assert 0.0 <= chart_data.scale_confidence <= 1.0
        assert len(chart_data.normalized_ratings) > 0


class TestDWIParser:
    """Tests for legacy .dwi parser."""

    def test_parse_dwi_basic(self):
        """Test basic DWI parsing."""
        chart_data = parse_dwi_file(str(DWI_FILE))

        assert chart_data.title == "PARANOiA Rebirth"
        assert chart_data.artist == "190'"
        assert chart_data.format == ".dwi"

    def test_dwi_gap_to_offset(self):
        """Test GAP (ms) conversion to OFFSET (seconds)."""
        chart_data = parse_dwi_file(str(DWI_FILE))

        # GAP is 116ms, should convert to 0.116s
        assert abs(chart_data.offset - 0.116) < 0.001

    def test_dwi_bpm_parsing(self):
        """Test BPM parsing (single value in DWI)."""
        chart_data = parse_dwi_file(str(DWI_FILE))

        assert len(chart_data.bpms) == 1
        assert chart_data.bpms[0].beat == 0.0
        assert abs(chart_data.bpms[0].value - 198.4) < 0.1

    def test_dwi_chart_parsing(self):
        """Test parsing charts from SINGLE/DOUBLE lines."""
        chart_data = parse_dwi_file(str(DWI_FILE))

        assert len(chart_data.charts) >= 3
        assert all(c.chart_type == ChartType.SINGLE for c in chart_data.charts)

    def test_dwi_difficulty_mapping(self):
        """Test DWI difficulty name mapping."""
        chart_data = parse_dwi_file(str(DWI_FILE))

        # DWI uses BASIC, ANOTHER, MANIAC
        difficulties = {chart.difficulty for chart in chart_data.charts}
        assert len(difficulties) >= 2  # At least 2 different difficulties

    def test_dwi_note_decoding(self):
        """Test DWI compressed note format decoding."""
        chart_data = parse_dwi_file(str(DWI_FILE))

        # Find a chart with notes
        chart = chart_data.charts[0]

        assert chart.total_notes > 0
        assert chart.tap_notes > 0
        assert len(chart.note_positions) > 0

        # Check note format is 4-column (LDUR)
        for beat, notes in chart.note_positions[:5]:
            assert len(notes) == 4
            assert all(c in '01' for c in notes)

    def test_dwi_jump_detection(self):
        """Test jump detection in decoded notes."""
        chart_data = parse_dwi_file(str(DWI_FILE))

        chart = chart_data.charts[0]
        # Should have some jumps
        assert chart.jump_count > 0

    def test_dwi_scale_detection(self):
        """Test scale detection for DWI files."""
        chart_data = parse_dwi_file(str(DWI_FILE))

        assert chart_data.detected_scale is not None
        assert len(chart_data.normalized_ratings) > 0


class TestUniversalParser:
    """Tests for universal parser with auto-detection."""

    def test_detect_sm_format(self):
        """Test .sm format detection."""
        assert detect_format(SM_FILE) == "StepMania"
        assert is_supported_format(SM_FILE) is True

    def test_detect_ssc_format(self):
        """Test .ssc format detection."""
        assert detect_format(SSC_FILE) == "StepMania 5"
        assert is_supported_format(SSC_FILE) is True

    def test_detect_dwi_format(self):
        """Test .dwi format detection."""
        assert detect_format(DWI_FILE) == "DanceWith Intensity"
        assert is_supported_format(DWI_FILE) is True

    def test_detect_unsupported_format(self):
        """Test unsupported format detection."""
        assert detect_format("test.mp3") == "Unknown"
        assert is_supported_format("test.mp3") is False

    def test_parse_sm_with_universal(self):
        """Test parsing .sm file with universal parser."""
        chart_data = parse_chart_file(SM_FILE)

        assert chart_data.title == "Goin' Under"
        assert chart_data.format == ".sm"
        assert len(chart_data.charts) > 0

    def test_parse_ssc_with_universal(self):
        """Test parsing .ssc file with universal parser."""
        chart_data = parse_chart_file(SSC_FILE)

        assert chart_data.title == "Goin' Under"
        assert chart_data.format == ".ssc"
        assert len(chart_data.charts) > 0

    def test_parse_dwi_with_universal(self):
        """Test parsing .dwi file with universal parser."""
        chart_data = parse_chart_file(DWI_FILE)

        assert chart_data.title == "PARANOiA Rebirth"
        assert chart_data.format == ".dwi"
        assert len(chart_data.charts) > 0

    def test_universal_parser_error_handling(self):
        """Test error handling for unsupported formats."""
        parser = UniversalParser()

        # Create a temp file with unsupported extension
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            temp_path = f.name

        try:
            with pytest.raises(ValueError, match="Unsupported file format"):
                parser.parse_file(temp_path)
        finally:
            Path(temp_path).unlink(missing_ok=True)

    def test_universal_parser_file_not_found(self):
        """Test error handling for missing files."""
        parser = UniversalParser()

        with pytest.raises(FileNotFoundError):
            parser.parse_file("nonexistent.sm")


class TestFormatEquivalence:
    """Tests to verify .sm and .ssc parse to equivalent data."""

    def test_sm_ssc_same_song(self):
        """Test that .sm and .ssc of same song produce equivalent data."""
        sm_data = parse_sm_file(str(SM_FILE))
        ssc_data = parse_ssc_file(str(SSC_FILE))

        # Same metadata
        assert sm_data.title == ssc_data.title
        assert sm_data.artist == ssc_data.artist

        # Same timing
        assert len(sm_data.bpms) == len(ssc_data.bpms)
        if sm_data.bpms and ssc_data.bpms:
            assert sm_data.bpms[0].value == ssc_data.bpms[0].value

        # Same number of charts
        assert len(sm_data.charts) == len(ssc_data.charts)

    def test_sm_ssc_same_charts(self):
        """Test that chart data is equivalent between .sm and .ssc."""
        sm_data = parse_sm_file(str(SM_FILE))
        ssc_data = parse_ssc_file(str(SSC_FILE))

        # Sort charts by type and difficulty for comparison
        sm_charts = sorted(sm_data.charts,
                          key=lambda c: (c.chart_type.value, c.difficulty.value))
        ssc_charts = sorted(ssc_data.charts,
                           key=lambda c: (c.chart_type.value, c.difficulty.value))

        for sm_chart, ssc_chart in zip(sm_charts, ssc_charts):
            assert sm_chart.chart_type == ssc_chart.chart_type
            assert sm_chart.difficulty == ssc_chart.difficulty
            assert sm_chart.rating == ssc_chart.rating
            assert sm_chart.total_notes == ssc_chart.total_notes


class TestFeatureExtractionCompatibility:
    """Tests to verify feature extraction works across all formats."""

    def test_feature_extraction_sm(self):
        """Test feature extraction on .sm files."""
        from features.feature_extractor import FeatureExtractor

        chart_data = parse_sm_file(str(SM_FILE))
        extractor = FeatureExtractor()

        chart = chart_data.charts[0]
        features = extractor.extract_features(chart_data, chart)

        assert features.notes_per_second > 0
        assert features.total_notes > 0

    def test_feature_extraction_ssc(self):
        """Test feature extraction on .ssc files."""
        from features.feature_extractor import FeatureExtractor

        chart_data = parse_ssc_file(str(SSC_FILE))
        extractor = FeatureExtractor()

        chart = chart_data.charts[0]
        features = extractor.extract_features(chart_data, chart)

        assert features.notes_per_second > 0
        assert features.total_notes > 0

    def test_feature_extraction_dwi(self):
        """Test feature extraction on .dwi files."""
        from features.feature_extractor import FeatureExtractor

        chart_data = parse_dwi_file(str(DWI_FILE))
        extractor = FeatureExtractor()

        chart = chart_data.charts[0]
        features = extractor.extract_features(chart_data, chart)

        assert features.notes_per_second > 0
        assert features.total_notes > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
