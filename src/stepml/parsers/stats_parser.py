"""
Parser for StepMania Stats.xml files to extract player performance data.
"""

import logging
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class TapNoteScores:
    """Detailed timing breakdown for a chart."""

    w1: int = 0  # Marvelous/Fantastic
    w2: int = 0  # Perfect
    w3: int = 0  # Great
    w4: int = 0  # Good
    w5: int = 0  # Boo/OK
    miss: int = 0
    hit_mine: int = 0

    @property
    def total_notes(self) -> int:
        """Total notes in the chart (excluding mines)."""
        return self.w1 + self.w2 + self.w3 + self.w4 + self.w5 + self.miss

    @property
    def accuracy(self) -> float:
        """Calculate accuracy percentage (0.0-1.0)."""
        if self.total_notes == 0:
            return 0.0
        # Weight: W1=1.0, W2=0.9, W3=0.7, W4=0.4, W5=0.2, Miss=0
        weighted_score = (
            self.w1 * 1.0
            + self.w2 * 0.9
            + self.w3 * 0.7
            + self.w4 * 0.4
            + self.w5 * 0.2
        )
        return weighted_score / self.total_notes

    @property
    def perfect_rate(self) -> float:
        """Percentage of W1+W2 notes (high accuracy)."""
        if self.total_notes == 0:
            return 0.0
        return (self.w1 + self.w2) / self.total_notes


@dataclass
class HoldNoteScores:
    """Hold note performance."""

    held: int = 0
    let_go: int = 0
    missed_hold: int = 0

    @property
    def total_holds(self) -> int:
        return self.held + self.let_go + self.missed_hold

    @property
    def hold_success_rate(self) -> float:
        if self.total_holds == 0:
            return 0.0
        return self.held / self.total_holds


@dataclass
class HighScoreData:
    """Individual high score record."""

    percent_dp: float
    max_combo: int
    grade: Optional[str]
    tap_scores: TapNoteScores
    hold_scores: HoldNoteScores


@dataclass
class ChartPerformance:
    """Performance data for a specific chart."""

    song_dir: str
    difficulty: str
    steps_type: str
    description: Optional[str]  # For Edit charts

    # Aggregated stats
    num_times_played: int
    high_grade: Optional[str]

    # Best score details (if available)
    best_percent_dp: Optional[float] = None
    best_max_combo: Optional[int] = None
    best_tap_scores: Optional[TapNoteScores] = None
    best_hold_scores: Optional[HoldNoteScores] = None

    # All scores for analysis
    all_scores: List[HighScoreData] = None

    def __post_init__(self):
        if self.all_scores is None:
            self.all_scores = []

    @property
    def average_accuracy(self) -> Optional[float]:
        """Average accuracy across all plays."""
        if not self.all_scores:
            return None
        accuracies = [score.tap_scores.accuracy for score in self.all_scores]
        return sum(accuracies) / len(accuracies) if accuracies else None

    @property
    def best_accuracy(self) -> Optional[float]:
        """Best accuracy achieved."""
        if self.best_tap_scores:
            return self.best_tap_scores.accuracy
        return None

    @property
    def consistency_score(self) -> Optional[float]:
        """Measure of performance consistency (0.0-1.0, higher is more consistent)."""
        if len(self.all_scores) < 2:
            return None
        accuracies = [score.tap_scores.accuracy for score in self.all_scores]
        avg = sum(accuracies) / len(accuracies)
        variance = sum((acc - avg) ** 2 for acc in accuracies) / len(accuracies)
        std_dev = variance**0.5
        # Normalize: higher consistency = lower std dev
        return max(0.0, 1.0 - std_dev * 2)  # Scale std_dev (typically 0-0.5)


class StatsParser:
    """Parser for StepMania Stats.xml files."""

    def __init__(self, stats_file_path: str):
        """
        Initialize parser with path to Stats.xml.

        Args:
            stats_file_path: Path to Stats.xml file
        """
        self.stats_file_path = Path(stats_file_path)
        if not self.stats_file_path.exists():
            raise FileNotFoundError(f"Stats.xml not found: {stats_file_path}")

        self.performances: Dict[str, List[ChartPerformance]] = {}
        self._parse()

    def _parse(self):
        """Parse the Stats.xml file."""
        try:
            tree = ET.parse(self.stats_file_path)
            root = tree.getroot()

            # Find SongScores section
            song_scores = root.find("SongScores")
            if song_scores is None:
                logger.warning("No SongScores section found in Stats.xml")
                return

            # Parse each song
            for song in song_scores.findall("Song"):
                song_dir = song.get("Dir", "")
                if not song_dir:
                    continue

                # Normalize song directory path
                song_dir = song_dir.replace("\\", "/")
                if song_dir.endswith("/"):
                    song_dir = song_dir[:-1]

                # Parse each chart (Steps) in this song
                for steps in song.findall("Steps"):
                    perf = self._parse_chart_performance(song_dir, steps)
                    if perf:
                        if song_dir not in self.performances:
                            self.performances[song_dir] = []
                        self.performances[song_dir].append(perf)

            logger.info(f"Parsed performance data for {len(self.performances)} songs")

        except ET.ParseError as e:
            logger.error(f"Failed to parse Stats.xml: {e}")
            raise

    def _parse_chart_performance(
        self, song_dir: str, steps_elem: ET.Element
    ) -> Optional[ChartPerformance]:
        """Parse performance data for a single chart."""
        difficulty = steps_elem.get("Difficulty", "")
        steps_type = steps_elem.get("StepsType", "")
        description = steps_elem.get("Description", None)

        if not difficulty or not steps_type:
            return None

        high_score_list = steps_elem.find("HighScoreList")
        if high_score_list is None:
            return None

        # Get aggregated stats
        num_times_played_elem = high_score_list.find("NumTimesPlayed")
        num_times_played = (
            int(num_times_played_elem.text) if num_times_played_elem is not None else 0
        )

        high_grade_elem = high_score_list.find("HighGrade")
        high_grade = high_grade_elem.text if high_grade_elem is not None else None

        # Parse all high scores
        all_scores = []
        for high_score in high_score_list.findall("HighScore"):
            score_data = self._parse_high_score(high_score)
            if score_data:
                all_scores.append(score_data)

        # Get best score data
        best_percent_dp = None
        best_max_combo = None
        best_tap_scores = None
        best_hold_scores = None

        if all_scores:
            # Find best score by percent_dp
            best_score = max(all_scores, key=lambda s: s.percent_dp)
            best_percent_dp = best_score.percent_dp
            best_max_combo = best_score.max_combo
            best_tap_scores = best_score.tap_scores
            best_hold_scores = best_score.hold_scores

        return ChartPerformance(
            song_dir=song_dir,
            difficulty=difficulty,
            steps_type=steps_type,
            description=description,
            num_times_played=num_times_played,
            high_grade=high_grade,
            best_percent_dp=best_percent_dp,
            best_max_combo=best_max_combo,
            best_tap_scores=best_tap_scores,
            best_hold_scores=best_hold_scores,
            all_scores=all_scores,
        )

    def _parse_high_score(self, high_score_elem: ET.Element) -> Optional[HighScoreData]:
        """Parse a single high score record."""
        try:
            # Get basic score info
            percent_dp_elem = high_score_elem.find("PercentDP")
            max_combo_elem = high_score_elem.find("MaxCombo")
            grade_elem = high_score_elem.find("Grade")

            if percent_dp_elem is None or max_combo_elem is None:
                return None

            percent_dp = float(percent_dp_elem.text)
            max_combo = int(max_combo_elem.text)
            grade = grade_elem.text if grade_elem is not None else None

            # Parse tap note scores
            tap_scores = TapNoteScores()
            tap_note_scores_elem = high_score_elem.find("TapNoteScores")
            if tap_note_scores_elem is not None:
                for elem_name in ["W1", "W2", "W3", "W4", "W5", "Miss", "HitMine"]:
                    elem = tap_note_scores_elem.find(elem_name)
                    if elem is not None and elem.text:
                        value = int(elem.text)
                        setattr(
                            tap_scores,
                            elem_name.lower().replace("hitmine", "hit_mine"),
                            value,
                        )

            # Parse hold note scores
            hold_scores = HoldNoteScores()
            hold_note_scores_elem = high_score_elem.find("HoldNoteScores")
            if hold_note_scores_elem is not None:
                for elem_name in ["Held", "LetGo", "MissedHold"]:
                    elem = hold_note_scores_elem.find(elem_name)
                    if elem is not None and elem.text:
                        value = int(elem.text)
                        setattr(
                            hold_scores,
                            elem_name.lower()
                            .replace("letgo", "let_go")
                            .replace("missedhold", "missed_hold"),
                            value,
                        )

            return HighScoreData(
                percent_dp=percent_dp,
                max_combo=max_combo,
                grade=grade,
                tap_scores=tap_scores,
                hold_scores=hold_scores,
            )

        except (ValueError, AttributeError) as e:
            logger.debug(f"Failed to parse high score: {e}")
            return None

    def get_performance(
        self, song_dir: str, difficulty: str, steps_type: str
    ) -> Optional[ChartPerformance]:
        """
        Get performance data for a specific chart.

        Args:
            song_dir: Song directory path (e.g., 'Songs/DDR 1st Mix/Butterfly')
            difficulty: Difficulty level (e.g., 'Hard', 'Challenge')
            steps_type: Chart type (e.g., 'dance-single', 'dance-double')

        Returns:
            ChartPerformance object or None if not found
        """
        # Normalize song_dir
        song_dir = song_dir.replace("\\", "/")
        if song_dir.endswith("/"):
            song_dir = song_dir[:-1]

        performances = self.performances.get(song_dir, [])
        for perf in performances:
            if perf.difficulty == difficulty and perf.steps_type == steps_type:
                return perf

        return None

    def get_all_performances(self) -> List[ChartPerformance]:
        """Get all chart performances."""
        all_perfs = []
        for perfs in self.performances.values():
            all_perfs.extend(perfs)
        return all_perfs

    def get_songs_with_performance_data(self) -> List[str]:
        """Get list of song directories that have performance data."""
        return list(self.performances.keys())


def parse_stats_file(stats_file_path: str) -> StatsParser:
    """
    Parse a Stats.xml file.

    Args:
        stats_file_path: Path to Stats.xml file

    Returns:
        StatsParser object with parsed performance data
    """
    return StatsParser(stats_file_path)
