"""
Path resolution utilities for the stepml project.

Provides centralized functions for resolving common paths relative to
the project root, improving maintainability and reducing code duplication.
"""

from pathlib import Path


def get_stepml_root() -> Path:
    """
    Get the root directory of the stepml project.

    Returns the parent directory of the src/ directory.
    """
    return Path(__file__).parent.parent.parent.parent


def get_src_dir() -> Path:
    """Get the src/ directory."""
    return Path(__file__).parent.parent.parent


def get_package_dir() -> Path:
    """Get the stepml package directory (src/stepml)."""
    return Path(__file__).parent.parent


def get_data_dir() -> Path:
    """Get the data/ directory at project root."""
    return get_stepml_root() / "data"


def get_models_dir() -> Path:
    """Get the models/ directory."""
    return get_data_dir() / "models"


def get_tests_dir() -> Path:
    """Get the tests/ directory at project root."""
    return get_stepml_root() / "tests"


def get_fixtures_dir() -> Path:
    """Get the test fixtures directory."""
    return get_tests_dir() / "fixtures"
