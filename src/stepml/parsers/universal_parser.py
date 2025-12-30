"""
Universal parser that auto-detects file format and uses appropriate parser.
"""
from pathlib import Path
from typing import Union

from stepml.utils.data_structures import ChartData
from stepml.parsers.sm_parser import parse_sm_file
from stepml.parsers.ssc_parser import parse_ssc_file
from stepml.parsers.dwi_parser import parse_dwi_file


class UniversalParser:
    """
    Universal chart file parser with automatic format detection.

    Supports:
    - .sm (StepMania)
    - .ssc (StepMania 5)
    - .dwi (DanceWith Intensity / legacy)
    """

    SUPPORTED_FORMATS = {
        '.sm': 'StepMania',
        '.ssc': 'StepMania 5',
        '.dwi': 'DanceWith Intensity',
    }

    def __init__(self):
        """Initialize the universal parser."""
        pass

    def parse_file(self, filepath: Union[str, Path], target_scale: 'ScaleType' = None) -> ChartData:
        """
        Parse a chart file and return ChartData.

        Automatically detects the file format based on extension
        and uses the appropriate parser.

        Args:
            filepath: Path to the chart file
            target_scale: The scale to normalize ratings to (default: Modern DDR 1-20)

        Returns:
            ChartData object with parsed information

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If file format is not supported
        """
        from stepml.utils.data_structures import ScaleType
        if target_scale is None:
            target_scale = ScaleType.MODERN_DDR

        filepath = Path(filepath)

        if not filepath.exists():
            raise FileNotFoundError(f"File not found: {filepath}")

        # Get file extension
        ext = filepath.suffix.lower()

        # Route to appropriate parser
        if ext == '.sm':
            return parse_sm_file(str(filepath), target_scale)
        elif ext == '.ssc':
            return parse_ssc_file(str(filepath), target_scale)
        elif ext == '.dwi':
            return parse_dwi_file(str(filepath), target_scale)
        else:
            raise ValueError(
                f"Unsupported file format: {ext}\n"
                f"Supported formats: {', '.join(self.SUPPORTED_FORMATS.keys())}"
            )

    def is_supported(self, filepath: Union[str, Path]) -> bool:
        """
        Check if a file format is supported.

        Args:
            filepath: Path to check

        Returns:
            True if format is supported, False otherwise
        """
        filepath = Path(filepath)
        return filepath.suffix.lower() in self.SUPPORTED_FORMATS

    def get_format_name(self, filepath: Union[str, Path]) -> str:
        """
        Get the human-readable format name for a file.

        Args:
            filepath: Path to check

        Returns:
            Format name (e.g., "StepMania 5") or "Unknown"
        """
        filepath = Path(filepath)
        ext = filepath.suffix.lower()
        return self.SUPPORTED_FORMATS.get(ext, "Unknown")


def parse_chart_file(filepath: Union[str, Path], target_scale: 'ScaleType' = None) -> ChartData:
    """
    Convenience function to parse any supported chart file.

    Automatically detects format and uses appropriate parser.

    Args:
        filepath: Path to the chart file (.sm, .ssc, or .dwi)
        target_scale: The scale to normalize ratings to (default: Modern DDR 1-20)

    Returns:
        ChartData object

    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If file format is not supported

    Example:
        >>> chart = parse_chart_file("song/chart.ssc")
        >>> print(f"Format: {chart.format}")
        >>> print(f"Charts: {len(chart.charts)}")
    """
    from stepml.utils.data_structures import ScaleType
    if target_scale is None:
        target_scale = ScaleType.MODERN_DDR
    parser = UniversalParser()
    return parser.parse_file(filepath, target_scale)


def detect_format(filepath: Union[str, Path]) -> str:
    """
    Detect the format of a chart file.

    Args:
        filepath: Path to check

    Returns:
        Format name (e.g., "StepMania", "StepMania 5", "DanceWith Intensity")
        or "Unknown" if not supported

    Example:
        >>> format_name = detect_format("chart.ssc")
        >>> print(format_name)  # "StepMania 5"
    """
    parser = UniversalParser()
    return parser.get_format_name(filepath)


def is_supported_format(filepath: Union[str, Path]) -> bool:
    """
    Check if a file format is supported.

    Args:
        filepath: Path to check

    Returns:
        True if format is supported, False otherwise

    Example:
        >>> if is_supported_format("chart.ssc"):
        ...     chart = parse_chart_file("chart.ssc")
    """
    parser = UniversalParser()
    return parser.is_supported(filepath)
