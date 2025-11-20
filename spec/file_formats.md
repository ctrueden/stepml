# StepMania File Format Reference

## Format Comparison

| Feature | .sm | .ssc | .dwi |
|---------|-----|------|------|
| Version Tag | No | Yes (#VERSION) | No |
| Timing Offset | #OFFSET | #OFFSET | #GAP |
| Chart Separator | #NOTES | #NOTEDATA | #SINGLE/DOUBLE:difficulty:rating: |
| Note Encoding | 4-digit columns | 4-digit columns | Compressed single digits |
| Measure Separator | Comma (,) | Comma (,) | None |
| Advanced Timing | Limited | Full (#DELAYS, #WARPS, etc.) | Limited |

## .ssc Format (StepMania 5)

### Key Differences from .sm

**Additional Global Tags**:
- `#VERSION:` - Format version (e.g., 0.83)
- `#DELAYS:` - Delay events (beat=delay_seconds)
- `#WARPS:` - Warp segments
- `#TIMESIGNATURES:` - Time signature changes
- `#TICKCOUNTS:` - Tick count changes
- `#COMBOS:` - Combo multiplier settings
- `#SPEEDS:` - Speed changes
- `#SCROLLS:` - Scroll rate changes
- `#FAKES:` - Fake note segments
- `#LABELS:` - Beat labels
- `#ATTACKS:` - Attack patterns (for battle mode)
- `#KEYSOUNDS:` - Key sound mappings

**Per-Chart Tags** (after #NOTEDATA:):
- `#CHARTNAME:` - Custom chart name
- `#CHARTSTYLE:` - Chart style descriptor
- `#RADARVALUES:` - Extended radar statistics (28 comma-separated values)

**Note Data**: Identical to .sm format (4-digit columns, comma-separated measures)

### Parsing Strategy

1. Parse global metadata (same as .sm)
2. Parse enhanced timing data (#DELAYS, #WARPS, etc.)
3. Split on `#NOTEDATA:` markers
4. For each chart section:
   - Parse per-chart metadata
   - Parse #NOTES: section (identical to .sm)

## .dwi Format (Legacy DanceWith Intensity)

### Format Structure

```
#CDTITLE:path/to/cdtitle.png;
#TITLE:Song Title;
#ARTIST:Artist Name;
#BPM:180.0;
#GAP:116;
#SAMPLESTART:0.01;

#SINGLE:BASIC:6:[note_data];
#SINGLE:ANOTHER:7:[note_data];
#SINGLE:MANIAC:9:[note_data];
#DOUBLE:BASIC:5:[note_data];
```

### Difficulty Mapping

| DWI Name | Standard Name | Enum |
|----------|---------------|------|
| BASIC | Easy | DifficultyType.EASY |
| ANOTHER | Medium/Hard | DifficultyType.MEDIUM or HARD |
| MANIAC | Challenge | DifficultyType.CHALLENGE |

### Note Encoding

DWI uses a compressed format with single-digit codes representing 4-beat subdivisions:

**Single Mode (4-panel)**:
- `0` = no notes
- `1` = left (L)
- `2` = down (D)
- `4` = up (U)
- `8` = right (R)
- `3` = L+D jump
- `5` = L+U jump
- `6` = D+U jump
- `9` = L+R jump (crossover)
- `A` (10) = D+R jump
- `C` (12) = U+R jump
- `7` = L+D+U
- `B` (11) = L+D+R
- `D` (13) = L+U+R
- `E` (14) = D+U+R
- `F` (15) = L+D+U+R (quad)

**Hold Notes**:
- Hold start uses same encoding as taps
- Hold end indicated by `!` marker (needs verification)

### Timing

- `#GAP:` is in milliseconds (vs #OFFSET in seconds)
- `#BPM:` is a single value (no BPM changes in DWI)
- No explicit measure markers - notes are time-based on BPM

### Parsing Strategy

1. Parse metadata tags
2. Convert #GAP (ms) to #OFFSET (seconds): `offset = gap / 1000`
3. For each `#SINGLE:` or `#DOUBLE:` line:
   - Extract difficulty name and rating from format `TYPE:DIFF:RATING:DATA`
   - Decode compressed note string using bit mapping
   - Convert to 4-digit column format
   - Calculate beat positions based on BPM and string position
   - Group into measures (4 beats per measure)

## Unified Internal Representation

All three formats convert to the same `ChartData` structure:

```python
ChartData(
    title: str
    artist: str
    bpms: List[TimingEvent]
    charts: List[NoteData]
    # ... other fields
)
```

This ensures feature extraction works uniformly across all formats.
