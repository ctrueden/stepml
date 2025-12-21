"""
Configuration and environment-aware path handling for StepMania resources.

Allows users to override the default StepMania directory via STEPMANIA_HOME
environment variable, useful when StepMania is installed in non-standard locations.
"""
from pathlib import Path
import os


def get_stepmania_home() -> Path:
    """
    Get the StepMania home directory.

    Returns the value of STEPMANIA_HOME env var if set, otherwise defaults to
    ~/Games/StepMania (unix-style paths with ~ expansion are supported).

    Returns:
        Path: The StepMania home directory

    Examples:
        >>> # Use default location
        >>> home = get_stepmania_home()
        >>> home.exists()
        True

        >>> # Use custom location
        >>> import os
        >>> os.environ['STEPMANIA_HOME'] = '/opt/stepmania'
        >>> get_stepmania_home()
        PosixPath('/opt/stepmania')
    """
    env_path = os.environ.get("STEPMANIA_HOME")
    if env_path:
        return Path(env_path).expanduser().resolve()
    return Path("~/Games/StepMania").expanduser().resolve()


def get_songs_dir() -> Path:
    """
    Get the Songs directory within StepMania home.

    Returns:
        Path: The Songs directory

    Examples:
        >>> songs_dir = get_songs_dir()
        >>> (songs_dir / "StepMania 5").exists()
        True
    """
    return get_stepmania_home() / "Songs"


def get_courses_dir() -> Path:
    """
    Get the Courses directory within StepMania home.

    Returns:
        Path: The Courses directory
    """
    return get_stepmania_home() / "Courses"


def get_profile_dir(profile_index: int = 0) -> Path:
    """
    Get the player profile directory within StepMania home.

    Args:
        profile_index: Profile number (default: 0 for first profile).
                      Use 0, 1, 2, etc. for different profiles.

    Returns:
        Path: The profile directory (e.g., Save/LocalProfiles/00000000)

    Examples:
        >>> profile_dir = get_profile_dir()
        >>> profile_dir.name
        '00000000'

        >>> profile_dir = get_profile_dir(1)
        >>> profile_dir.name
        '00000001'
    """
    profile_id = str(profile_index).zfill(8)
    return get_stepmania_home() / "Save/LocalProfiles" / profile_id
