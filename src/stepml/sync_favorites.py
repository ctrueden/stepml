"""
Sync StepMania favorites between in-game favorites.txt and curated course files.

Workflow:
1. Extracts songs from Single-Favorites.songs and Double-Favorites.songs
2. Identifies new songs in in-game favorites.txt (not in either course file)
3. Writes new songs to Unsorted-Favorites.txt for manual curation
4. Overwrites in-game favorites.txt with union of both course files
"""

import re
from pathlib import Path
from typing import Set, Tuple

from .config import get_courses_dir, get_profile_dir


def parse_song_from_course(line: str) -> str | None:
    """Extract song path from #SONG: line in course file."""
    match = re.match(r'#SONG:([^:]+):\w+;', line)
    return match.group(1) if match else None


def load_songs_from_course(course_path: Path) -> Set[str]:
    """Load all songs from a .songs course file."""
    songs = set()
    if not course_path.exists():
        return songs
    
    with open(course_path, 'r') as f:
        for line in f:
            line = line.strip()
            if line.startswith('#SONG:'):
                song = parse_song_from_course(line)
                if song:
                    songs.add(song)
    return songs


def parse_song_from_favorites(line: str) -> str | None:
    """Extract song path from favorites.txt line."""
    # Format: "Game/Song Name" (second element after split by '/')
    # Example: "DDR A/ALGORITHM" or "[fraxtil] Fraxtil's Arrow Arrangements/Deal With It"
    parts = line.split('/')
    if len(parts) >= 2:
        # Rejoin in case song name has slashes
        return '/'.join(parts).strip()
    return None


def load_songs_from_favorites(favorites_path: Path) -> Set[str]:
    """Load all songs from in-game favorites.txt."""
    songs = set()
    if not favorites_path.exists():
        return songs
    
    with open(favorites_path, 'r') as f:
        for line in f:
            line = line.strip()
            # Skip header line and empty lines
            if line and not line.startswith('---'):
                song = parse_song_from_favorites(line)
                if song:
                    songs.add(song)
    return songs


def load_songs_from_unsorted(unsorted_path: Path) -> Set[str]:
    """Load all songs from Unsorted-Favorites.txt."""
    songs = set()
    if not unsorted_path.exists():
        return songs
    
    with open(unsorted_path, 'r') as f:
        for line in f:
            line = line.strip()
            # Skip comment lines and empty lines
            if line and not line.startswith('#'):
                songs.add(line)
    return songs


def write_favorites_txt(output_path: Path, songs: Set[str]) -> None:
    """Write songs to favorites.txt format."""
    sorted_songs = sorted(songs)
    
    with open(output_path, 'w') as f:
        f.write('---Curtis\'s Favorites\n')
        for song in sorted_songs:
            f.write(f'{song}\n')


def write_unsorted_favorites(output_path: Path, songs: Set[str]) -> None:
    """Write new/unsorted songs to Unsorted-Favorites.txt."""
    sorted_songs = sorted(songs)
    
    with open(output_path, 'w') as f:
        f.write('# New favorites found in-game (not yet in Single/Double-Favorites.songs)\n')
        f.write('# Move these to the appropriate .songs course files after review\n')
        f.write('\n')
        for song in sorted_songs:
            f.write(f'{song}\n')


def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Sync StepMania in-game favorites with curated course playlists"
    )
    parser.add_argument(
        "--profile",
        type=int,
        default=0,
        help="Profile number (default: 0)",
    )
    args = parser.parse_args()
    
    courses_dir = get_courses_dir() / 'Vetted'
    profile_dir = get_profile_dir(args.profile)
    
    single_course = courses_dir / 'Single-Favorites.songs'
    double_course = courses_dir / 'Double-Favorites.songs'
    unsorted_file = courses_dir / 'Unsorted-Favorites.txt'
    in_game_favorites = profile_dir / 'favorites.txt'
    
    print("Loading songs from course files...")
    single_songs = load_songs_from_course(single_course)
    double_songs = load_songs_from_course(double_course)
    unsorted_songs = load_songs_from_unsorted(unsorted_file)
    
    print(f"  Single-Favorites.songs: {len(single_songs)} songs")
    print(f"  Double-Favorites.songs: {len(double_songs)} songs")
    print(f"  Unsorted-Favorites.txt: {len(unsorted_songs)} songs")
    
    all_favorites = single_songs | double_songs | unsorted_songs
    print(f"  Combined (unique): {len(all_favorites)} songs")
    
    print("\nLoading songs from in-game favorites.txt...")
    in_game_songs = load_songs_from_favorites(in_game_favorites)
    print(f"  favorites.txt: {len(in_game_songs)} songs")
    
    # Find new songs in favorites.txt not in any of our lists
    new_songs = in_game_songs - all_favorites
    
    if new_songs:
        print(f"\n⚠️  Found {len(new_songs)} new songs in favorites.txt:")
        for song in sorted(new_songs):
            print(f"    - {song}")
        
        print(f"\nAdding new songs to Unsorted-Favorites.txt...")
        # Merge with existing unsorted songs
        combined_unsorted = unsorted_songs | new_songs
        write_unsorted_favorites(unsorted_file, combined_unsorted)
        print(f"  ✓ {len(combined_unsorted)} total songs in Unsorted-Favorites.txt")
        
        # Update all_favorites to include the new songs
        all_favorites = all_favorites | new_songs
    else:
        print("\n✓ No new songs found in favorites.txt")
    
    print(f"\nSyncing in-game favorites.txt with all sources...")
    write_favorites_txt(in_game_favorites, all_favorites)
    print(f"  ✓ Wrote {len(all_favorites)} songs to favorites.txt")
    print("    (union of Single-Favorites, Double-Favorites, and Unsorted-Favorites)")
    
    print("\n✓ Sync complete!")


if __name__ == '__main__':
    main()
