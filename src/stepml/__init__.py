"""
StepMania Chart Analysis Package

This package provides tools for parsing StepMania chart files (.sm, .ssc, .dwi)
and extracting features for machine learning-based difficulty analysis.
"""

from .features.feature_extractor import AdvancedFeatureExtractor, FeatureExtractor
from .parsers.sm_parser import SMParser, parse_sm_file
from .utils.data_structures import (
    ChartData,
    ChartType,
    DifficultyType,
    FeatureSet,
    NoteData,
    ScaleType,
    TimingEvent,
)

__version__ = "0.1.0"

__all__ = [
    # Parsers
    "SMParser",
    "parse_sm_file",
    # Feature extractors
    "FeatureExtractor",
    "AdvancedFeatureExtractor",
    # Data structures
    "ChartData",
    "NoteData",
    "FeatureSet",
    "ScaleType",
    "DifficultyType",
    "ChartType",
    "TimingEvent",
]
