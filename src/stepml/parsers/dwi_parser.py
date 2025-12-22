"""
Parser for legacy DanceWith Intensity .dwi files.
"""
import re
from pathlib import Path
from typing import List, Dict, Tuple, Optional

from stepml.utils.data_structures import (
    ChartData, NoteData, TimingEvent, ChartType,
    DifficultyType, ScaleType
)
from stepml.utils.scale_detector import ScaleDetector
from stepml.utils.rating_normalizer import RatingNormalizer


class DWIParser:
    """Parser for DanceWith Intensity .dwi format files."""

    # Map DWI difficulty names to our enum
    # Based on ITGMania's NotesLoaderDWI.cpp DwiCompatibleStringToDifficulty
    DIFFICULTY_MAP = {
        "beginner": DifficultyType.EASY,
        "basic": DifficultyType.EASY,
        "easy": DifficultyType.EASY,
        "light": DifficultyType.EASY,
        "medium": DifficultyType.MEDIUM,
        "another": DifficultyType.MEDIUM,
        "trick": DifficultyType.MEDIUM,
        "standard": DifficultyType.MEDIUM,
        "difficult": DifficultyType.MEDIUM,
        "hard": DifficultyType.HARD,
        "ssr": DifficultyType.HARD,
        "maniac": DifficultyType.HARD,  # MANIAC = HARD, not CHALLENGE
        "heavy": DifficultyType.HARD,
        "smaniac": DifficultyType.CHALLENGE,  # S-MANIAC = CHALLENGE
        "challenge": DifficultyType.CHALLENGE,
        "expert": DifficultyType.CHALLENGE,
        "oni": DifficultyType.CHALLENGE,
    }

    def __init__(self):
        """Initialize the DWI parser."""
        self.scale_detector = ScaleDetector()
        self.rating_normalizer = RatingNormalizer()

    def parse_file(self, filepath: str) -> ChartData:
        """
        Parse a .dwi file and return ChartData.

        Args:
            filepath: Path to the .dwi file

        Returns:
            ChartData object with parsed information
        """
        filepath = Path(filepath)
        if not filepath.exists():
            raise FileNotFoundError(f"File not found: {filepath}")

        # Read file content
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()

        # Create ChartData object
        chart_data = ChartData(
            filepath=str(filepath),
            format=filepath.suffix,
            songpack=filepath.parent.parent.name  # Assuming Songs/PackName/Song/file.dwi
        )

        # Parse all tags
        self._parse_metadata(content, chart_data)
        self._parse_timing(content, chart_data)
        self._parse_charts(content, chart_data)

        # Detect scale and normalize ratings
        self._detect_and_normalize_scale(chart_data)

        return chart_data

    def _parse_metadata(self, content: str, chart_data: ChartData):
        """Extract metadata tags from .dwi file."""
        # Simple tag parser - handles #TAG:value;
        def get_tag_value(tag_name: str) -> str:
            pattern = rf'#\s*{tag_name}\s*:\s*([^;]*);'
            match = re.search(pattern, content, re.IGNORECASE | re.MULTILINE)
            if match:
                return match.group(1).strip()
            return ""

        chart_data.title = get_tag_value("TITLE")
        chart_data.artist = get_tag_value("ARTIST")
        chart_data.genre = get_tag_value("GENRE")
        chart_data.credit = get_tag_value("CREDIT")

        # DWI uses #GAP instead of #OFFSET (in milliseconds)
        gap_str = get_tag_value("GAP")
        if gap_str:
            try:
                # Convert milliseconds to seconds
                chart_data.offset = float(gap_str) / 1000.0
            except ValueError:
                pass

        sample_start_str = get_tag_value("SAMPLESTART")
        if sample_start_str:
            try:
                chart_data.sample_start = float(sample_start_str)
            except ValueError:
                pass

        sample_length_str = get_tag_value("SAMPLELENGTH")
        if sample_length_str:
            try:
                chart_data.sample_length = float(sample_length_str)
            except ValueError:
                pass

    def _parse_timing(self, content: str, chart_data: ChartData):
        """
        Parse timing information from .dwi file.

        DWI files typically have a single BPM value (no BPM changes).
        """
        # Parse BPM (single value)
        bpm_pattern = r'#\s*BPM\s*:\s*([^;]+);'
        bpm_match = re.search(bpm_pattern, content, re.IGNORECASE)
        if bpm_match:
            try:
                bpm_value = float(bpm_match.group(1).strip())
                # Create a single BPM event at beat 0
                chart_data.bpms = [TimingEvent(beat=0.0, value=bpm_value)]
            except ValueError:
                pass

    def _parse_charts(self, content: str, chart_data: ChartData):
        """
        Parse all chart sections from .dwi file.

        DWI format: #SINGLE:DIFFICULTY:RATING:NOTEDATA;
                    #DOUBLE:DIFFICULTY:RATING:LEFT_NOTES:RIGHT_NOTES;
        """
        # Pattern to match SINGLE/DOUBLE chart definitions
        chart_pattern = r'#(SINGLE|DOUBLE)\s*:\s*([^:]+)\s*:\s*(\d+)\s*:\s*([^;]+);'

        matches = re.finditer(chart_pattern, content, re.IGNORECASE | re.MULTILINE | re.DOTALL)

        for match in matches:
            chart_type_str = match.group(1).strip().lower()
            difficulty_str = match.group(2).strip().lower()
            rating_str = match.group(3).strip()
            notes_data = match.group(4).strip()

            # Map to our enums
            chart_type = ChartType.SINGLE if chart_type_str == "single" else ChartType.DOUBLE
            difficulty = self.DIFFICULTY_MAP.get(difficulty_str)

            if difficulty is None:
                # Try to infer difficulty from rating if mapping fails
                try:
                    rating_val = int(rating_str)
                    if rating_val <= 3:
                        difficulty = DifficultyType.EASY
                    elif rating_val <= 6:
                        difficulty = DifficultyType.MEDIUM
                    elif rating_val <= 8:
                        difficulty = DifficultyType.HARD
                    else:
                        difficulty = DifficultyType.CHALLENGE
                except ValueError:
                    continue

            try:
                rating = int(rating_str)
            except ValueError:
                rating = 0

            # Create NoteData object
            note_data = NoteData(
                chart_type=chart_type,
                difficulty=difficulty,
                rating=rating,
                raw_notes=notes_data
            )

            # Parse the note data (DWI compressed format)
            if chart_data.bpms:
                bpm = chart_data.bpms[0].value
                self._parse_dwi_note_data(notes_data, note_data, bpm, chart_type)

            chart_data.charts.append(note_data)

    def _parse_dwi_note_data(self, notes_str: str, note_data: NoteData, bpm: float, chart_type: ChartType):
        """
        Parse DWI compressed note data format.

        DWI uses hexadecimal encoding where each character represents a note:
        - 0 = no notes
        - 1 = Left
        - 2 = Down
        - 4 = Up
        - 8 = Right
        - 3 = Left+Down (1+2)
        - 5 = Left+Up (1+4)
        - 6 = Down+Up (2+4)
        - 9 = Left+Right (1+8)
        - A = Down+Right (2+8)
        - C = Up+Right (4+8)
        - 7 = Left+Down+Up (1+2+4)
        - B = Left+Down+Right (1+2+8)
        - D = Left+Up+Right (1+4+8)
        - E = Down+Up+Right (2+4+8)
        - F = All four (1+2+4+8)

        For DOUBLE charts, the note string contains two sections separated by ':':
        - First section: left 4 panels
        - Second section: right 4 panels

        Args:
            notes_str: Compressed note string
            note_data: NoteData object to populate
            bpm: BPM for timing calculations
            chart_type: SINGLE or DOUBLE chart type
        """
        # DWI typically uses 1/8th note resolution (8 subdivisions per beat)
        # Each character represents 1/8th of a beat
        beat_increment = 0.125  # 1/8th beat

        # For DOUBLE charts, split into left and right panel sections
        if chart_type == ChartType.DOUBLE and ':' in notes_str:
            left_notes, right_notes = notes_str.split(':', 1)
            # Parse both sections and merge
            self._parse_double_panels(left_notes, right_notes, note_data, beat_increment)
        else:
            # SINGLE chart or DOUBLE chart without separator (old format)
            self._parse_single_panel(notes_str, note_data, beat_increment, chart_type)

        # Calculate total notes
        note_data.total_notes = note_data.tap_notes + note_data.hold_notes + note_data.roll_notes

    def _parse_single_panel(self, notes_str: str, note_data: NoteData, beat_increment: float, chart_type: ChartType):
        """Parse a single panel section (for SINGLE charts)."""
        current_beat = 0.0

        for char in notes_str.upper():
            if char == '0':
                current_beat += beat_increment
                continue

            try:
                # Convert hex char to decimal value
                if char.isdigit():
                    value = int(char)
                else:
                    value = ord(char) - ord('A') + 10  # A=10, B=11, etc.

                if value < 0 or value > 15:
                    current_beat += beat_increment
                    continue

                # Convert bitwise encoding to 4-column format
                left = '1' if (value & 1) else '0'    # Bit 0
                down = '1' if (value & 2) else '0'    # Bit 1
                up = '1' if (value & 4) else '0'      # Bit 2
                right = '1' if (value & 8) else '0'   # Bit 3
                note_line = left + down + up + right

                # Count note types
                tap_count = note_line.count('1')

                if tap_count > 0:
                    note_data.tap_notes += tap_count

                    # Check for jumps (2+ simultaneous notes)
                    if tap_count >= 2:
                        note_data.jump_count += 1

                    # Store note position
                    note_data.note_positions.append((current_beat, note_line))

                current_beat += beat_increment

            except (ValueError, IndexError):
                current_beat += beat_increment
                continue

    def _parse_double_panels(self, left_str: str, right_str: str, note_data: NoteData, beat_increment: float):
        """Parse DOUBLE chart with separate left and right panel sections."""
        # Parse left panel (columns 0-3)
        left_notes = []
        current_beat = 0.0

        for char in left_str.upper():
            if char == '0':
                left_notes.append((current_beat, '0000'))
                current_beat += beat_increment
                continue

            try:
                if char.isdigit():
                    value = int(char)
                else:
                    value = ord(char) - ord('A') + 10

                if value < 0 or value > 15:
                    left_notes.append((current_beat, '0000'))
                    current_beat += beat_increment
                    continue

                left = '1' if (value & 1) else '0'
                down = '1' if (value & 2) else '0'
                up = '1' if (value & 4) else '0'
                right = '1' if (value & 8) else '0'
                left_notes.append((current_beat, left + down + up + right))
                current_beat += beat_increment

            except (ValueError, IndexError):
                left_notes.append((current_beat, '0000'))
                current_beat += beat_increment
                continue

        # Parse right panel (columns 4-7)
        right_notes = []
        current_beat = 0.0

        for char in right_str.upper():
            if char == '0':
                right_notes.append((current_beat, '0000'))
                current_beat += beat_increment
                continue

            try:
                if char.isdigit():
                    value = int(char)
                else:
                    value = ord(char) - ord('A') + 10

                if value < 0 or value > 15:
                    right_notes.append((current_beat, '0000'))
                    current_beat += beat_increment
                    continue

                left = '1' if (value & 1) else '0'
                down = '1' if (value & 2) else '0'
                up = '1' if (value & 4) else '0'
                right = '1' if (value & 8) else '0'
                right_notes.append((current_beat, left + down + up + right))
                current_beat += beat_increment

            except (ValueError, IndexError):
                right_notes.append((current_beat, '0000'))
                current_beat += beat_increment
                continue

        # Merge left and right panels into 8-column format
        # Create a dictionary to merge notes at the same beat
        merged_notes = {}

        for beat, notes in left_notes:
            if notes != '0000':
                merged_notes[beat] = notes + '0000'

        for beat, notes in right_notes:
            if notes != '0000':
                if beat in merged_notes:
                    # Combine with existing left notes
                    left_part = merged_notes[beat][:4]
                    merged_notes[beat] = left_part + notes
                else:
                    # Only right notes at this beat
                    merged_notes[beat] = '0000' + notes

        # Count notes and populate note_data
        for beat in sorted(merged_notes.keys()):
            note_line = merged_notes[beat]
            tap_count = note_line.count('1')

            if tap_count > 0:
                note_data.tap_notes += tap_count

                # Check for jumps (2+ simultaneous notes)
                if tap_count >= 2:
                    note_data.jump_count += 1

                # Store note position
                note_data.note_positions.append((beat, note_line))

    def _detect_and_normalize_scale(self, chart_data: ChartData):
        """
        Detect the rating scale and normalize all chart ratings.

        Args:
            chart_data: ChartData object to update with scale detection
        """
        # Detect scale type
        detected_scale, confidence = self.scale_detector.detect_scale(
            chart_data.filepath,
            chart_data
        )

        # Update chart data
        chart_data.detected_scale = detected_scale
        chart_data.scale_confidence = confidence

        # Normalize ratings for all charts
        for chart in chart_data.charts:
            difficulty_key = f"{chart.chart_type.value}_{chart.difficulty.value}"

            # Calculate notes_per_second for metric-based refinement
            notes_per_second = self._calculate_nps(chart, chart_data.bpms)

            normalized_rating = self.rating_normalizer.normalize(
                chart.rating,
                detected_scale,
                notes_per_second=notes_per_second,
                total_notes=chart.total_notes
            )
            chart_data.normalized_ratings[difficulty_key] = normalized_rating

    def _calculate_nps(self, chart: NoteData, bpms: List[TimingEvent]) -> float:
        """
        Calculate notes per second for a chart.

        Args:
            chart: Chart data with note positions
            bpms: BPM timing events

        Returns:
            Notes per second, or 0 if cannot calculate
        """
        if not chart.note_positions or not bpms or chart.total_notes == 0:
            return 0.0

        # Get last note beat
        last_beat = chart.note_positions[-1][0]

        # Calculate duration in seconds using primary BPM
        # (Simplified: assumes constant BPM for most charts)
        bpm = bpms[0].value
        if bpm <= 0:
            return 0.0

        duration_seconds = (last_beat / bpm) * 60.0

        if duration_seconds <= 0:
            return 0.0

        return chart.total_notes / duration_seconds


def parse_dwi_file(filepath: str) -> ChartData:
    """
    Convenience function to parse a .dwi file.

    Args:
        filepath: Path to the .dwi file

    Returns:
        ChartData object
    """
    parser = DWIParser()
    return parser.parse_file(filepath)
