# Playlist Generation Guide

## Overview

The new `generate_playlists.py` script replaces manual playlist curation with automated difficulty-tiered playlists based on ML-calculated ratings.

## Key Improvements Over Manual System

### Problems Solved:
1. **No more tedious manual vetting** - Automatic generation from 26K+ rated charts
2. **Separate single/double playlists** - No more silent failures when double charts don't exist
3. **Chart-specific difficulties** - Uses actual calculated ratings, not difficulty names
4. **Consistent difficulty tiers** - Fine-grained 1.0-rating bands instead of coarse categories
5. **Respects your preferences** - Honors Veto.songs and can weight Favorites.songs

## Quick Start

### Generate Fresh Playlists

```bash
cd ~/Games/StepMania/stepchart-reclassify

# Generate playlists (100 songs per tier by default)
uv run python generate_playlists.py \\
    --output ~/Games/StepMania/Courses/Workout \\
    --favorites ~/Games/StepMania/Courses/Workout/Favorites.songs

# Generate with random course variants (like old randomize.sh)
uv run python generate_playlists.py \\
    --output ~/Games/StepMania/Courses/Workout \\
    --favorites ~/Games/StepMania/Courses/Workout/Favorites.songs \\
    --random-courses
```

### Available Tiers (Based on Your Play History)

**Single & Double charts, calculated ratings:**
- **Warmup**: 10.5-11.5 (below your median)
- **Comfortable**: 11.5-12.5 (around your median 12.5)
- **Workout**: 12.5-13.5 (above median)
- **Challenge**: 13.5-14.5 (stretch goals)
- **Intense**: 14.5-15.5 (serious challenge)
- **Super-Intense**: 15.5-17.0 (very hard)
- **Extreme**: 17.0-20.0 (expert level)

Each tier generates separate `.songs` files:
- `Warmup.songs`, `Double-Warmup.songs`
- `Workout.songs`, `Double-Workout.songs`
- etc.

## What to Keep from Old System

### Keep: Veto.songs ✓
**Purpose**: Domain knowledge the ML can't learn
- Bad charts (poorly timed, awkward patterns)
- Annoying music
- Technical issues
- Personal preferences

**Action**: Keep maintaining this list!

### Keep: Favorites.songs ✓
**Purpose**: Quality signal for playlist generation
- Songs you particularly enjoy
- Well-charted favorites
- Songs worth recommending

**Action**: The script can weight these higher when generating playlists (3x more likely to appear)

### Archive or Deprecate: Old Difficulty Lists
**Files**: Warmup.songs, Workout.songs, Intense.songs, Super-Intense.songs, Double-*.songs

**Options**:
1. **Archive them**: Move to `Courses/Workout/Archive/` as historical reference
2. **Mine for favorites**: Any song you manually added probably means you liked it - consider adding to Favorites.songs
3. **Keep temporarily**: Validate new system matches your intuition, then deprecate

**Recommendation**: Archive them. The new system provides:
- More precise difficulty tiers (7 levels vs 4)
- Separate single/double playlists
- Many more songs per tier (100+ vs 100-250 total)
- Automatic updates when ratings improve

## Customization

### Adjust Difficulty Tiers

Edit the `tiers` list in `generate_playlists.py`:

```python
tiers = [
    ("Warmup", 10.0, 11.0),      # Adjust ranges
    ("Workout", 12.0, 13.0),
    ("Challenge", 13.5, 14.5),
    # Add more tiers as needed
]
```

### Change Songs Per Tier

```bash
uv run python generate_playlists.py --songs-per-tier 150
```

### Generate Only Single or Only Double

```bash
uv run python generate_playlists.py --chart-types dance-single
uv run python generate_playlists.py --chart-types dance-double
```

## Workflow Integration

### Replacing Old Scripts

**Old**: `bin/randomize.sh`
**New**: `generate_playlists.py --random-courses`

**Old**: Manual vetting with `bin/song.sh`
**New**: No need! Charts are auto-included based on calculated rating

**Old**: `bin/unvetted.sh` (find unvetted songs)
**New**: No longer needed - all songs are automatically included

### Maintaining Veto List

Keep using your existing workflow to add bad songs:

```bash
# Add a song to veto list
echo "#SONG:PackName/SongName:HARD;" >> ~/Games/StepMania/Courses/Workout/Veto.songs

# Regenerate playlists (automatically excludes vetoed songs)
cd ~/Games/StepMania/stepchart-reclassify
uv run python generate_playlists.py --output ~/Games/StepMania/Courses/Workout
```

### Maintaining Favorites

```bash
# Add a favorite
echo "#SONG:PackName/SongName:HARD;" >> ~/Games/StepMania/Courses/Workout/Favorites.songs

# Regenerate with favorites weighted higher
uv run python generate_playlists.py \\
    --output ~/Games/StepMania/Courses/Workout \\
    --favorites ~/Games/StepMania/Courses/Workout/Favorites.songs
```

## Output Format

Generated `.songs` files include calculated rating as comments:

```
#COURSE:Workout (12.5-13.5);
#SONG:Pack/Song:HARD;  # 12.5
#SONG:Pack/Song2:MEDIUM;  # 12.8
...
```

This helps you see the actual difficulty and identify outliers.

## Future Enhancements

Possible additions:
1. **Avoid recently played** - Read Stats.xml and exclude songs played in last N days
2. **Pattern variety** - Ensure each playlist has mix of jumps, holds, streams, etc.
3. **BPM variety** - Mix slow/fast songs
4. **Pack variety** - Avoid too many songs from same pack
5. **Personalized calibration** - Adjust ratings based on your performance data
6. **Progressive playlists** - Start easy, gradually increase difficulty within a course

## Comparison: Old vs New System

| Feature | Old Manual System | New Automated System |
|---------|------------------|---------------------|
| Song count | 770 total vetted | 26K+ rated, auto-generated |
| Difficulty tiers | 4 broad categories | 7 precise tiers |
| Single/Double | Mixed, silent failures | Separate, guaranteed compatibility |
| Maintenance | Manual vetting required | Automatic, regenerate anytime |
| Precision | Difficulty names (HARD) | Calculated ratings (12.5) |
| Coverage | Only vetted songs | All non-vetoed songs |
| Updates | Manual re-vetting | Re-run script |

## Tips

1. **Start conservatively**: Use default 100 songs per tier
2. **Check the output**: Review a few generated playlists to ensure they feel right
3. **Adjust tiers**: Move boundaries if tiers feel too easy/hard
4. **Keep veto updated**: Add bad songs as you discover them
5. **Regenerate regularly**: After adding new song packs or improving ratings
6. **Use random courses**: Fresh 4-song combinations for variety

## Questions?

The script has extensive help:
```bash
uv run python generate_playlists.py --help
```
