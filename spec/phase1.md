# Phase 1 Complete: SM Parser and Feature Extraction

## Summary

Phase 1 of the ML-based step chart analysis project has been successfully implemented. This phase includes a robust .sm file parser and comprehensive feature extraction algorithms.

## What Was Implemented

### 1. Project Structure
```
ml_analysis/
├── parsers/          # Chart file parsers
│   ├── __init__.py
│   └── sm_parser.py  # .sm format parser
├── features/         # Feature extraction
│   ├── __init__.py
│   └── feature_extractor.py
├── utils/            # Data structures and utilities
│   ├── __init__.py
│   └── data_structures.py
├── tests/            # Test files
├── data/             # Data storage
├── models/           # Future ML models
├── notebooks/        # Jupyter notebooks
└── test_parser.py    # Test script
```

### 2. Core Components

#### SM Parser (`parsers/sm_parser.py`)
- **Metadata Parsing**: Extracts title, artist, BPM, offset, and all song metadata
- **Timing Parsing**: Handles BPMs, stops, delays, and warps
- **Chart Parsing**: Processes all difficulty charts (Beginner through Challenge)
- **Note Data Parsing**: Analyzes note patterns including:
  - Tap notes, holds, rolls, and mines
  - Jump detection (simultaneous notes)
  - Beat-accurate positioning
  - Support for both single and double charts

#### Feature Extractor (`features/feature_extractor.py`)
Extracts 20+ features across multiple dimensions:

**Density Metrics:**
- Notes per second
- Average density (notes per beat)
- Peak density (using 8-beat sliding window)
- Density variance across the chart

**Pattern Metrics:**
- Jump ratio (percentage of simultaneous notes)
- Hold ratio
- Roll ratio
- Mine ratio

**Timing Metrics:**
- Chart length (seconds and beats)
- BPM changes count
- BPM variance
- Stop count and total duration

**Advanced Features:**
- Stream detection (consecutive 1/8 or 1/16 notes)
- Direction changes
- Crossover potential

### 3. Data Structures (`utils/data_structures.py`)
- **ChartData**: Complete chart information with metadata and timing
- **NoteData**: Individual difficulty chart with parsed notes
- **FeatureSet**: Organized feature collection for ML models
- **Enums**: ScaleType, DifficultyType, ChartType for type safety
- **TimingEvent**: BPM changes, stops, and timing modifications

## Test Results

Successfully tested on 3 diverse charts from your collection:

### Test 1: Goofy Goober Rock (Original Chart)
- Simple chart with 2 difficulties
- 106 BPM, no stops
- Features extracted: density, patterns, timing

### Test 2: Goin' Under (StepMania 5)
- Complex chart with 9 difficulties (single + double)
- 210 BPM high-speed chart
- Ratings 1-11 across difficulties
- Successfully extracted features showing clear difficulty progression:
  - Beginner: 0.80 notes/sec
  - Challenge: 5.33 notes/sec

### Test 3: Pokemon Heartgold/Soulsilver
- 4 difficulties with varying complexity
- 183.91 BPM
- Clear feature progression from rating 3 to 9
- Jump ratio increases from 0% to 7.92%

## Key Observations

1. **Parser Accuracy**: Successfully parsed all metadata, timing, and note data
2. **Feature Quality**: Features show clear correlation with difficulty ratings
3. **Density Metrics**: Notes per second ranges from ~0.8 (beginner) to ~6.0 (challenge)
4. **Pattern Detection**: Successfully identifies jumps, holds, streams, and crossovers
5. **Chart Length Calculation**: Accurate duration calculation accounting for BPM changes

## Feature Highlights

The feature extraction demonstrates strong difficulty indicators:
- **Peak density** correlates with hardest sections
- **Density variance** indicates consistency vs. burst difficulty
- **Jump ratio** increases with technical difficulty
- **Stream detection** identifies sustained fast sections
- **Direction changes** measure footwork complexity

## Usage Example

```python
from parsers.sm_parser import parse_sm_file
from features.feature_extractor import FeatureExtractor

# Parse a chart
chart_data = parse_sm_file("path/to/chart.sm")

# Extract features
extractor = FeatureExtractor()
for chart in chart_data.charts:
    features = extractor.extract_features(chart_data, chart)
    print(f"{chart.difficulty.value}: {features.notes_per_second:.2f} NPS")
```

## Next Steps (Phase 2)

1. **Scale Detection**: Implement songpack classification to detect DDR/ITG/Modern scales
2. **Rating Normalization**: Build scale conversion tables
3. **Multi-Format Support**: Add .ssc and .dwi parsers
4. **Batch Processing**: Process entire song collection
5. **Dataset Creation**: Build training dataset with normalized ratings

## Technical Details

- **Language**: Python 3.12
- **Dependencies**: numpy (for numerical operations)
- **Package Manager**: uv
- **Architecture**: Modular design with clean separation of concerns
- **Testing**: Validated on real charts from your 102 song pack collection

## Performance

- Fast parsing: ~instant for typical charts
- Memory efficient: Processes charts individually
- Scalable: Ready for batch processing of 1000+ charts

---

**Status**: ✅ Phase 1 Complete and Tested
**Date**: 2025-10-15
**Location**: `/home/curtis/Games/StepMania/ml_analysis/`
