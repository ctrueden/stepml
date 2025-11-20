"""
Parser for StepMania .sm files.
"""
import re
from pathlib import Path
from typing import List, Dict, Tuple, Optional
import sys
sys.path.append(str(Path(__file__).parent.parent))

from utils.data_structures import (
    ChartData, NoteData, TimingEvent, ChartType,
    DifficultyType, ScaleType
)
from utils.scale_detector import ScaleDetector
from utils.rating_normalizer import RatingNormalizer


class SMParser:
    """Parser for StepMania .sm format files."""

    # Map SM difficulty names to our enum
    DIFFICULTY_MAP = {
        "beginner": DifficultyType.BEGINNER,
        "easy": DifficultyType.EASY,
        "medium": DifficultyType.MEDIUM,
        "hard": DifficultyType.HARD,
        "challenge": DifficultyType.CHALLENGE,
        "edit": DifficultyType.EDIT,
    }

    # Map SM chart type names to our enum
    CHART_TYPE_MAP = {
        "dance-single": ChartType.SINGLE,
        "dance-double": ChartType.DOUBLE,
        "dance-couple": ChartType.COUPLE,
        "dance-solo": ChartType.SOLO,
    }

    def __init__(self):
        """Initialize the SM parser."""
        self.scale_detector = ScaleDetector()
        self.rating_normalizer = RatingNormalizer()

    def parse_file(self, filepath: str) -> ChartData:
        """
        Parse a .sm file and return ChartData.

        Args:
            filepath: Path to the .sm file

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
            songpack=filepath.parent.parent.name  # Assuming Songs/PackName/Song/file.sm
        )

        # Parse all tags
        self._parse_metadata(content, chart_data)
        self._parse_timing(content, chart_data)
        self._parse_charts(content, chart_data)

        # Detect scale and normalize ratings
        self._detect_and_normalize_scale(chart_data)

        return chart_data

    def _parse_metadata(self, content: str, chart_data: ChartData):
        """Extract metadata tags from .sm file."""
        # Simple tag parser - handles #TAG:value;
        def get_tag_value(tag_name: str) -> str:
            pattern = rf'#\s*{tag_name}\s*:\s*([^;]*);'
            match = re.search(pattern, content, re.IGNORECASE | re.MULTILINE)
            if match:
                return match.group(1).strip()
            return ""

        chart_data.title = get_tag_value("TITLE")
        chart_data.subtitle = get_tag_value("SUBTITLE")
        chart_data.artist = get_tag_value("ARTIST")
        chart_data.title_translit = get_tag_value("TITLETRANSLIT")
        chart_data.subtitle_translit = get_tag_value("SUBTITLETRANSLIT")
        chart_data.artist_translit = get_tag_value("ARTISTTRANSLIT")
        chart_data.genre = get_tag_value("GENRE")
        chart_data.credit = get_tag_value("CREDIT")
        chart_data.music = get_tag_value("MUSIC")

        # Parse numeric values
        offset_str = get_tag_value("OFFSET")
        if offset_str:
            try:
                chart_data.offset = float(offset_str)
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
        """Parse timing information (BPMs, stops, etc.)."""
        # Parse BPMs
        bpm_pattern = r'#\s*BPMS\s*:\s*([^;]+);'
        bpm_match = re.search(bpm_pattern, content, re.IGNORECASE | re.MULTILINE | re.DOTALL)
        if bpm_match:
            bpm_data = bpm_match.group(1)
            chart_data.bpms = self._parse_timing_list(bpm_data)

        # Parse stops
        stops_pattern = r'#\s*STOPS\s*:\s*([^;]+);'
        stops_match = re.search(stops_pattern, content, re.IGNORECASE | re.MULTILINE | re.DOTALL)
        if stops_match:
            stops_data = stops_match.group(1)
            chart_data.stops = self._parse_timing_list(stops_data)

        # Parse delays (if present)
        delays_pattern = r'#\s*DELAYS\s*:\s*([^;]+);'
        delays_match = re.search(delays_pattern, content, re.IGNORECASE | re.MULTILINE | re.DOTALL)
        if delays_match:
            delays_data = delays_match.group(1)
            chart_data.delays = self._parse_timing_list(delays_data)

        # Parse warps (if present)
        warps_pattern = r'#\s*WARPS\s*:\s*([^;]+);'
        warps_match = re.search(warps_pattern, content, re.IGNORECASE | re.MULTILINE | re.DOTALL)
        if warps_match:
            warps_data = warps_match.group(1)
            chart_data.warps = self._parse_timing_list(warps_data)

    def _parse_timing_list(self, timing_str: str) -> List[TimingEvent]:
        """
        Parse timing list format: beat=value,beat=value,...

        Args:
            timing_str: String like "0.000=120.000,4.000=140.000"

        Returns:
            List of TimingEvent objects
        """
        events = []
        # Split by comma and parse each pair
        pairs = timing_str.split(',')
        for pair in pairs:
            pair = pair.strip()
            if '=' not in pair:
                continue
            try:
                beat_str, value_str = pair.split('=', 1)
                beat = float(beat_str.strip())
                value = float(value_str.strip())
                events.append(TimingEvent(beat=beat, value=value))
            except (ValueError, IndexError):
                # Skip malformed entries
                continue
        return events

    def _parse_charts(self, content: str, chart_data: ChartData):
        """Parse all chart (NOTES) sections from .sm file."""
        # Pattern to match NOTES sections
        # Format: #NOTES:type:author:difficulty:rating:radar:notes;
        notes_pattern = r'#NOTES\s*:\s*([^:]+)\s*:\s*([^:]*)\s*:\s*([^:]+)\s*:\s*(\d+)\s*:\s*([^:]*)\s*:\s*([^;]+);'

        matches = re.finditer(notes_pattern, content, re.IGNORECASE | re.MULTILINE | re.DOTALL)

        for match in matches:
            chart_type_str = match.group(1).strip().lower()
            # author = match.group(2).strip()  # Not used currently
            difficulty_str = match.group(3).strip().lower()
            rating_str = match.group(4).strip()
            # radar = match.group(5).strip()  # Not used currently
            notes_data = match.group(6).strip()

            # Map to our enums
            chart_type = self.CHART_TYPE_MAP.get(chart_type_str)
            difficulty = self.DIFFICULTY_MAP.get(difficulty_str)

            if chart_type is None or difficulty is None:
                # Skip unknown chart types/difficulties
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

            # Parse the note data
            self._parse_note_data(notes_data, note_data)

            chart_data.charts.append(note_data)

    def _parse_note_data(self, notes_str: str, note_data: NoteData):
        """
        Parse the actual note data from a chart.

        Note format:
        - Each measure is separated by a comma
        - Each line represents a subdivision of a beat
        - For dance-single: 4 columns (LDUR - Left, Down, Up, Right)
        - For dance-double: 8 columns

        Note types:
        - 0: no note
        - 1: tap note
        - 2: hold head
        - 3: hold/roll tail
        - 4: roll head
        - M: mine

        Args:
            notes_str: Raw note string from .sm file
            note_data: NoteData object to populate
        """
        # Split by comma to get measures
        measures = notes_str.split(',')

        current_beat = 0.0
        columns = 4 if note_data.chart_type == ChartType.SINGLE else 8

        for measure_idx, measure in enumerate(measures):
            # Remove whitespace and get note lines
            lines = [line.strip() for line in measure.strip().split('\n') if line.strip()]

            if not lines:
                current_beat += 4.0  # Empty measure
                continue

            # Calculate beat increment per line
            subdivisions = len(lines)
            beat_increment = 4.0 / subdivisions  # 4 beats per measure

            for line_idx, line in enumerate(lines):
                # Remove any non-note characters
                line = re.sub(r'[^0-9M]', '', line.upper())

                if len(line) < columns:
                    continue  # Skip malformed lines

                beat = current_beat + (line_idx * beat_increment)

                # Count note types
                tap_count = 0
                hold_count = 0
                roll_count = 0
                mine_count = 0

                for char in line[:columns]:
                    if char == '1':
                        tap_count += 1
                        note_data.tap_notes += 1
                    elif char == '2':
                        hold_count += 1
                        note_data.hold_notes += 1
                    elif char == '4':
                        roll_count += 1
                        note_data.roll_notes += 1
                    elif char == 'M':
                        mine_count += 1
                        note_data.mine_notes += 1

                # Check for jumps (2+ simultaneous notes)
                simultaneous_notes = tap_count + hold_count + roll_count
                if simultaneous_notes >= 2:
                    note_data.jump_count += 1

                # Store note position if there are any notes
                if simultaneous_notes > 0 or mine_count > 0:
                    note_data.note_positions.append((beat, line[:columns]))

            current_beat += 4.0  # Move to next measure

        # Calculate total notes (excluding mines and hold/roll tails)
        note_data.total_notes = note_data.tap_notes + note_data.hold_notes + note_data.roll_notes

    def _detect_and_normalize_scale(self, chart_data: ChartData):
        """
        Detect the rating scale and normalize all chart ratings.

        Args:
            chart_data: ChartData object to update with scale detection
        """
        # Detect scale type
        detected_scale, confidence = self.scale_detector.detect_scale(
            chart_data.filepath,
            chart_data.charts
        )

        # Update chart data
        chart_data.detected_scale = detected_scale
        chart_data.scale_confidence = confidence

        # Normalize ratings for all charts
        for chart in chart_data.charts:
            difficulty_key = f"{chart.chart_type.value}_{chart.difficulty.value}"
            normalized_rating = self.rating_normalizer.normalize(
                chart.rating,
                detected_scale
            )
            chart_data.normalized_ratings[difficulty_key] = normalized_rating


def parse_sm_file(filepath: str) -> ChartData:
    """
    Convenience function to parse a .sm file.

    Args:
        filepath: Path to the .sm file

    Returns:
        ChartData object
    """
    parser = SMParser()
    return parser.parse_file(filepath)
