"""
Pytest configuration and shared fixtures for StepMania parser tests.
"""
import json
import sys
from pathlib import Path
from typing import Dict, List, Any

import pytest

# Add src directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from stepml.parsers.sm_parser import parse_sm_file
from stepml.features.feature_extractor import FeatureExtractor, AdvancedFeatureExtractor
from stepml.utils.data_structures import ChartData, NoteData
from stepml.utils import get_fixtures_dir
from stepml.config import get_songs_dir


@pytest.fixture(scope="session")
def songs_dir() -> Path:
    """Path to the Songs directory."""
    return get_songs_dir()


@pytest.fixture(scope="session")
def test_charts_config() -> Dict[str, Any]:
    """Load the test charts configuration."""
    config_path = get_fixtures_dir() / "test_charts.json"
    with open(config_path, 'r') as f:
        return json.load(f)


@pytest.fixture(scope="session")
def baseline_features() -> Dict[str, Any]:
    """Load the baseline feature extractions."""
    baseline_path = get_fixtures_dir() / "baseline_features.json"
    with open(baseline_path, 'r') as f:
        return json.load(f)


@pytest.fixture(scope="session")
def test_chart_paths(songs_dir: Path, test_charts_config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Get absolute paths to test charts.

    Returns list of dicts with:
    - name: Test name
    - path: Absolute path to chart file
    - description: Chart description
    - edge_cases: List of edge case tags
    """
    charts = []
    for chart_info in test_charts_config.get("charts", []):
        chart_path = songs_dir / chart_info["path"]
        if chart_path.exists():
            charts.append({
                "name": chart_info["name"],
                "path": chart_path,
                "description": chart_info["description"],
                "edge_cases": chart_info["edge_cases"],
            })
        else:
            # Chart not found - this is OK, just skip it
            pass
    return charts


@pytest.fixture
def feature_extractor() -> FeatureExtractor:
    """Create a FeatureExtractor instance."""
    return FeatureExtractor()


@pytest.fixture
def advanced_feature_extractor() -> AdvancedFeatureExtractor:
    """Create an AdvancedFeatureExtractor instance."""
    return AdvancedFeatureExtractor()


def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "parser: Tests for SM file parsing"
    )
    config.addinivalue_line(
        "markers", "features: Tests for feature extraction"
    )
    config.addinivalue_line(
        "markers", "regression: Regression tests against baseline"
    )
    config.addinivalue_line(
        "markers", "edge_case: Tests for specific edge cases"
    )
