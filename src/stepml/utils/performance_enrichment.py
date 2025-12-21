"""
Utility for enriching chart data with player performance metrics.
"""
from pathlib import Path
from typing import Optional, Dict, Any
import logging

from stepml.parsers.stats_parser import StatsParser, ChartPerformance

logger = logging.getLogger(__name__)


class PerformanceEnricher:
    """Enriches chart data with player performance metrics from Stats.xml."""

    def __init__(self, stats_file_path: str):
        """
        Initialize enricher with Stats.xml data.

        Args:
            stats_file_path: Path to Stats.xml file
        """
        self.stats_parser = StatsParser(stats_file_path)
        self.total_charts = 0
        self.matched_charts = 0

    def extract_song_dir(self, file_path: str) -> str:
        """
        Extract song directory from file path.

        Args:
            file_path: Full file path (e.g., 'Songs/DDR 1st Mix/Butterfly/Butterfly.sm')

        Returns:
            Song directory (e.g., 'Songs/DDR 1st Mix/Butterfly')
        """
        path = Path(file_path)
        return str(path.parent).replace('\\', '/')

    def normalize_chart_type(self, chart_type: str) -> str:
        """
        Normalize chart type to match Stats.xml format.

        Args:
            chart_type: Chart type from dataset (e.g., 'dance-single')

        Returns:
            Normalized chart type
        """
        return chart_type.lower()

    def normalize_difficulty(self, difficulty: str) -> str:
        """
        Normalize difficulty to match Stats.xml format.

        Args:
            difficulty: Difficulty from dataset (e.g., 'Hard')

        Returns:
            Normalized difficulty (capitalized)
        """
        return difficulty.capitalize()

    def get_performance_features(
        self,
        file_path: str,
        difficulty: str,
        chart_type: str
    ) -> Dict[str, Any]:
        """
        Get performance features for a chart.

        Args:
            file_path: File path from dataset
            difficulty: Difficulty level
            chart_type: Chart type (e.g., 'dance-single')

        Returns:
            Dictionary of performance features
        """
        self.total_charts += 1

        # Extract song directory
        song_dir = self.extract_song_dir(file_path)

        # Normalize parameters
        norm_difficulty = self.normalize_difficulty(difficulty)
        norm_chart_type = self.normalize_chart_type(chart_type)

        # Look up performance data
        perf = self.stats_parser.get_performance(song_dir, norm_difficulty, norm_chart_type)

        if perf is None:
            return self._empty_features()

        self.matched_charts += 1

        # Extract features
        features = {
            'times_played': perf.num_times_played,
            'has_performance_data': True,
        }

        # Add detailed metrics if available
        if perf.best_accuracy is not None:
            features['best_accuracy'] = perf.best_accuracy
        else:
            features['best_accuracy'] = None

        if perf.average_accuracy is not None:
            features['average_accuracy'] = perf.average_accuracy
        else:
            features['average_accuracy'] = None

        if perf.consistency_score is not None:
            features['consistency_score'] = perf.consistency_score
        else:
            features['consistency_score'] = None

        if perf.best_percent_dp is not None:
            features['best_percent_dp'] = perf.best_percent_dp
        else:
            features['best_percent_dp'] = None

        if perf.best_max_combo is not None:
            features['best_max_combo'] = perf.best_max_combo
        else:
            features['best_max_combo'] = None

        # Calculate perceived difficulty (if we have accuracy data)
        if perf.best_accuracy is not None:
            # Lower accuracy = higher perceived difficulty
            # Scale: 100% accuracy = perceived_difficulty_factor of 0.5
            #        90% accuracy = perceived_difficulty_factor of 1.0
            #        80% accuracy = perceived_difficulty_factor of 1.5
            #        50% accuracy = perceived_difficulty_factor of 3.0
            if perf.best_accuracy > 0.01:  # Avoid division by zero
                # Inverse relationship: lower accuracy = higher difficulty
                perceived_factor = 2.0 - perf.best_accuracy
                features['perceived_difficulty_factor'] = max(0.5, min(3.0, perceived_factor))
            else:
                features['perceived_difficulty_factor'] = 3.0
        else:
            features['perceived_difficulty_factor'] = None

        # Add fail indicator (extremely low accuracy or grade)
        features['has_failed'] = False
        if perf.best_accuracy is not None and perf.best_accuracy < 0.3:
            features['has_failed'] = True
        if perf.high_grade and 'Failed' in perf.high_grade:
            features['has_failed'] = True

        # Add timing breakdown if available
        if perf.best_tap_scores:
            ts = perf.best_tap_scores
            total_notes = ts.total_notes
            if total_notes > 0:
                features['perfect_rate'] = ts.perfect_rate  # W1+W2 rate
                features['great_or_worse_rate'] = (ts.w3 + ts.w4 + ts.w5 + ts.miss) / total_notes
                features['miss_rate'] = ts.miss / total_notes
            else:
                features['perfect_rate'] = None
                features['great_or_worse_rate'] = None
                features['miss_rate'] = None
        else:
            features['perfect_rate'] = None
            features['great_or_worse_rate'] = None
            features['miss_rate'] = None

        # Hold note success rate
        if perf.best_hold_scores and perf.best_hold_scores.total_holds > 0:
            features['hold_success_rate'] = perf.best_hold_scores.hold_success_rate
        else:
            features['hold_success_rate'] = None

        # High grade
        features['high_grade'] = perf.high_grade

        return features

    def _empty_features(self) -> Dict[str, Any]:
        """Return empty feature dict for charts without performance data."""
        return {
            'times_played': 0,
            'has_performance_data': False,
            'best_accuracy': None,
            'average_accuracy': None,
            'consistency_score': None,
            'best_percent_dp': None,
            'best_max_combo': None,
            'perceived_difficulty_factor': None,
            'has_failed': False,
            'perfect_rate': None,
            'great_or_worse_rate': None,
            'miss_rate': None,
            'hold_success_rate': None,
            'high_grade': None,
        }

    def get_match_rate(self) -> float:
        """Get percentage of charts matched with performance data."""
        if self.total_charts == 0:
            return 0.0
        return (self.matched_charts / self.total_charts) * 100

    def get_stats(self) -> Dict[str, Any]:
        """Get enrichment statistics."""
        return {
            'total_charts_processed': self.total_charts,
            'charts_with_performance_data': self.matched_charts,
            'match_rate_percent': self.get_match_rate(),
            'total_songs_in_stats': len(self.stats_parser.performances),
            'total_performances_in_stats': len(self.stats_parser.get_all_performances()),
        }
