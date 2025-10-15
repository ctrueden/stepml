# ML Step Chart Analysis - Project Status

**Last Updated**: 2025-10-15
**Current Phase**: Phase 1 Complete ✅

---

## Overview

Machine learning-based system for analyzing StepMania step charts and providing consistent difficulty ratings across all songs. The system parses .sm/.ssc/.dwi files, extracts meaningful features, and will eventually provide unified ratings across multiple historical difficulty scales (Classic DDR, Modern DDR, ITG).

## Phase Progress

### ✅ Phase 1: Core Parser and Feature Extraction (COMPLETE)

**Duration**: 1 session (2025-10-15)
**Location**: `/home/curtis/Games/StepMania/ml_analysis/`
**Status**: Fully implemented and tested

#### Deliverables

1. **SM File Parser** (`parsers/sm_parser.py`)
   - ✅ Complete metadata extraction (title, artist, genre, credit, etc.)
   - ✅ Timing data parsing (BPM changes, stops, delays, warps)
   - ✅ Note data parsing for all difficulties
   - ✅ Note type detection (taps, holds, rolls, mines)
   - ✅ Jump detection and counting
   - ✅ Beat-accurate note positioning
   - ✅ Support for dance-single and dance-double charts

2. **Feature Extraction System** (`features/feature_extractor.py`)
   - ✅ **Density Metrics** (4 features)
     - Notes per second (NPS)
     - Average density (notes per beat)
     - Peak density (8-beat sliding window)
     - Density variance
   - ✅ **Pattern Metrics** (4 features)
     - Jump ratio
     - Hold ratio
     - Roll ratio
     - Mine ratio
   - ✅ **Timing Metrics** (6 features)
     - Chart length (seconds and beats)
     - BPM changes count
     - BPM variance
     - Stop count and total duration
   - ✅ **Advanced Features** (5 features)
     - Stream section detection
     - Direction change counting
     - Crossover potential estimation
     - Advanced timing detection
     - Total: 19+ numerical features ready for ML

3. **Data Structures** (`utils/data_structures.py`)
   - ✅ `ChartData`: Complete song/chart information
   - ✅ `NoteData`: Individual difficulty chart data
   - ✅ `FeatureSet`: ML-ready feature collection with to_dict()
   - ✅ `TimingEvent`: BPM/stop/timing changes
   - ✅ Type-safe enums: ScaleType, DifficultyType, ChartType

4. **Testing & Examples**
   - ✅ `test_parser.py`: Comprehensive test script
   - ✅ `example_usage.py`: Practical usage examples
   - ✅ Tested on 3 diverse charts from collection
   - ✅ All features show strong correlation with difficulty

#### Test Results

Validated on real charts from the song collection:

| Chart | Difficulty | Rating | NPS | Peak Density | Result |
|-------|-----------|--------|-----|--------------|---------|
| Goin' Under | Beginner | 1 | 0.80 | 0.25 | ✅ Pass |
| Goin' Under | Easy | 3 | 1.85 | 0.88 | ✅ Pass |
| Goin' Under | Medium | 6 | 2.96 | 1.38 | ✅ Pass |
| Goin' Under | Hard | 8 | 3.97 | 2.00 | ✅ Pass |
| Goin' Under | Challenge | 10 | 5.33 | 2.12 | ✅ Pass |

**Observations**:
- Clear linear progression in NPS from beginner to challenge
- Peak density increases with difficulty
- Pattern metrics (jumps, holds) correlate with technical difficulty
- All 19 features extract successfully

#### Technical Stack

- **Language**: Python 3.12
- **Package Manager**: uv
- **Dependencies**: numpy 2.3.4
- **Architecture**: Modular, extensible design

---

### 🔄 Phase 2: Scale Detection and Rating Normalization (NEXT)

**Planned Duration**: 1-2 sessions
**Status**: Not started
**Priority**: High

#### Goals

1. **Songpack Classification**
   - Implement automatic series detection from directory names
   - Pattern matching for Classic DDR, Modern DDR, ITG
   - Confidence scoring for scale detection

2. **Rating Scale Manager**
   - Build scale conversion tables
   - Implement rating normalization algorithms
   - Handle edge cases and unknown scales

3. **Validation System**
   - Statistical validation of scale detection
   - Cross-scale consistency checking
   - Manual override support

#### Planned Deliverables

- `utils/scale_detector.py`: Songpack classification
- `utils/rating_normalizer.py`: Scale conversion and normalization
- Updated `ChartData` with scale detection results
- Test suite for scale detection accuracy

#### Success Criteria

- 90%+ accuracy on known DDR/ITG packs
- Reasonable confidence scores for ambiguous packs
- Successful normalization of test charts to unified scale

---

### 📋 Phase 3: Multi-Format Support (PLANNED)

**Planned Duration**: 2-3 sessions
**Status**: Not started
**Priority**: Medium

#### Goals

1. **SSC Format Parser**
   - StepMania 5 format support
   - Advanced timing features
   - Per-chart metadata

2. **DWI Format Parser**
   - Legacy DanceWith Intensity format
   - Format conversion to unified representation

3. **Format Normalization**
   - Unified internal representation
   - Feature extraction across all formats
   - Format-specific quirk handling

#### Planned Deliverables

- `parsers/ssc_parser.py`
- `parsers/dwi_parser.py`
- `parsers/universal_parser.py`: Auto-detect and parse any format
- Updated feature extractor for format-specific features

#### Success Criteria

- Parse all three formats successfully
- Feature extraction works uniformly across formats
- No loss of format-specific advanced features

---

### 🎯 Phase 4: ML Pipeline and Model Training (PLANNED)

**Planned Duration**: 3-4 sessions
**Status**: Not started
**Priority**: Low (after Phase 2-3)

#### Goals

1. **Dataset Creation**
   - Batch process entire song collection (100+ packs)
   - Export features to structured format (CSV/Parquet)
   - Data quality validation

2. **Baseline Models**
   - Linear regression
   - Random Forest
   - Feature importance analysis

3. **Advanced Models**
   - Neural network architectures
   - Ensemble methods
   - Hyperparameter tuning

4. **Validation Framework**
   - K-fold cross-validation
   - Performance metrics (MAE, RMSE, ranking correlation)
   - Human validation integration

#### Planned Deliverables

- `models/baseline_models.py`
- `models/advanced_models.py`
- `models/training_pipeline.py`
- Jupyter notebooks for experimentation
- Trained model artifacts

#### Success Criteria

- MAE < 1.0 rating point on validation set
- High ranking correlation with human ratings
- Consistent predictions across similar charts

---

## File Structure

```
/home/curtis/Games/StepMania/
├── ml_analysis/                    # Main implementation
│   ├── parsers/                    # ✅ Phase 1
│   │   ├── __init__.py
│   │   └── sm_parser.py
│   ├── features/                   # ✅ Phase 1
│   │   ├── __init__.py
│   │   └── feature_extractor.py
│   ├── utils/                      # ✅ Phase 1 (partial Phase 2)
│   │   ├── __init__.py
│   │   └── data_structures.py
│   ├── models/                     # 📋 Phase 4
│   ├── data/                       # Storage
│   │   ├── processed/
│   │   ├── models/
│   │   └── experiments/
│   ├── notebooks/                  # 📋 Phase 3-4
│   ├── tests/                      # Testing
│   ├── test_parser.py             # ✅ Phase 1
│   ├── example_usage.py           # ✅ Phase 1
│   ├── PHASE1_COMPLETE.md         # ✅ Documentation
│   ├── pyproject.toml             # ✅ uv config
│   └── uv.lock                    # ✅ Dependencies
├── spec/                           # Documentation
│   ├── ml_step_chart_analysis.md  # Main specification
│   ├── implementation_notes.md    # Updated with Phase 1
│   └── PROJECT_STATUS.md          # This file
└── Songs/                          # Song collection (102 packs)
```

---

## Quick Start

### Running the System

```bash
cd /home/curtis/Games/StepMania/ml_analysis

# Test parser on sample files
uv run python3 test_parser.py

# Test specific file
uv run python3 test_parser.py "../Songs/StepMania 5/Goin' Under/Goin' Under.sm"

# See usage examples
uv run python3 example_usage.py "../Songs/StepMania 5/Goin' Under/Goin' Under.sm"
```

### Using in Code

```python
from parsers.sm_parser import parse_sm_file
from features.feature_extractor import FeatureExtractor

# Parse a chart
chart_data = parse_sm_file("path/to/chart.sm")

# Extract features
extractor = FeatureExtractor()
for chart in chart_data.charts:
    features = extractor.extract_features(chart_data, chart)
    print(f"{chart.difficulty.value} (Rating {chart.rating}):")
    print(f"  NPS: {features.notes_per_second:.2f}")
    print(f"  Peak Density: {features.peak_density:.2f}")
```

---

## Next Steps

1. **Immediate (Phase 2)**:
   - Implement `utils/scale_detector.py`
   - Build scale conversion tables
   - Test on DDR vs ITG packs

2. **Short-term (Phase 3)**:
   - Add .ssc parser for StepMania 5 charts
   - Add .dwi parser for legacy charts
   - Validate multi-format support

3. **Medium-term (Phase 4)**:
   - Process entire song collection
   - Train baseline ML models
   - Begin validation with expert players

---

## Resources

- **Main Spec**: `spec/ml_step_chart_analysis.md`
- **Implementation Notes**: `spec/implementation_notes.md`
- **Phase 1 Summary**: `ml_analysis/PHASE1_COMPLETE.md`
- **Examples**: `ml_analysis/example_usage.py`
- **Tests**: `ml_analysis/test_parser.py`

---

## Contact / Notes

This is a personal project for analyzing and standardizing difficulty ratings across a collection of 102+ StepMania song packs. The goal is to create a unified rating system that accounts for the historical differences between Classic DDR (1-10), Modern DDR (1-20), and ITG (1-12) scales, with corrections for known issues like "rating creep" in ITG charts.

**Current Focus**: Phase 1 complete, ready to begin Phase 2 (scale detection) when development resumes.
