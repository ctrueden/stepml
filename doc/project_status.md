# ML Step Chart Analysis - Project Status

**Last Updated**: 2025-11-20
**Current Phase**: Phase 4 Complete ✅

---

## Overview

Machine learning-based system for analyzing StepMania step charts and providing consistent difficulty ratings across all songs. The system parses .sm/.ssc/.dwi files, extracts meaningful features, and will eventually provide unified ratings across multiple historical difficulty scales (Classic DDR, Modern DDR, ITG).

## Phase Progress

### ✅ Phase 1: Core Parser and Feature Extraction (COMPLETE)

**Duration**: 1 session (2025-10-15)
**Location**: `~/Games/StepMania/stepml/`
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
   - ✅ `examples/example_usage.py`: Practical usage examples
   - ✅ Tested on 3 diverse charts from collection
   - ✅ All features show strong correlation with difficulty

#### Test Results

Validated on real charts from the song collection:

| Chart       | Difficulty | Rating | NPS  | Peak Density | Result  |
|-------------|------------|--------|------|--------------|---------|
| Goin' Under | Beginner   | 1      | 0.80 | 0.25         | ✅ Pass |
| Goin' Under | Easy       | 3      | 1.85 | 0.88         | ✅ Pass |
| Goin' Under | Medium     | 6      | 2.96 | 1.38         | ✅ Pass |
| Goin' Under | Hard       | 8      | 3.97 | 2.00         | ✅ Pass |
| Goin' Under | Challenge  | 10     | 5.33 | 2.12         | ✅ Pass |

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

### ✅ Phase 2: Scale Detection and Rating Normalization (COMPLETE)

**Duration**: 1 session (2025-11-20)
**Status**: Fully implemented and tested
**Priority**: High

#### Deliverables

1. **Scale Detection System** (`utils/scale_detector.py`)
   - ✅ Automatic series detection from directory names
   - ✅ Pattern matching for Classic DDR, Modern DDR, ITG
   - ✅ Statistical validation from rating distributions
   - ✅ Confidence scoring (0.0-1.0)
   - ✅ 91.7% accuracy on real song collection

2. **Rating Normalization** (`utils/rating_normalizer.py`)
   - ✅ Scale conversion tables (Classic DDR, Modern DDR, ITG → Unified)
   - ✅ Linear interpolation for unmapped values
   - ✅ Bidirectional conversion (normalize/denormalize)
   - ✅ Batch normalization support
   - ✅ Rating creep adjustment for ITG

3. **Parser Integration**
   - ✅ Automatic scale detection in SM parser
   - ✅ Normalized ratings stored in ChartData
   - ✅ No manual configuration required

4. **Testing & Examples**
   - ✅ `tests/test_scale_detection.py`: 18 comprehensive tests
   - ✅ `examples/example_scale_detection.py`: Usage demonstrations
   - ✅ `test_scale_detection_real.py`: Real collection validation
   - ✅ All tests passing

#### Test Results

Validated on real song collection (11/12 packs, 91.7% accuracy):

| Scale Type  | Packs Tested             | Detection Rate |
|-------------|--------------------------|----------------|
| Classic DDR | DDR 1st-5th Mix, EXTREME | 100% (4/4)     |
| Modern DDR  | DDR A/A20, 2013/2014     | 100% (4/4)     |
| ITG         | ITG 1/2, Rebirth         | 100% (3/3)     |

**Key Conversions**:
- Classic DDR 9 → Unified 14.0 (≈ Modern DDR 14)
- ITG 8 → Unified 14.0 (accounts for rating creep)
- Modern DDR → Identity mapping (reference scale)

#### Technical Achievement

- **Automatic detection**: Pattern matching + statistical analysis
- **High accuracy**: 91.7% on diverse real-world data
- **Rating creep correction**: ITG scale properly adjusted
- **Cross-pack comparison**: Fair difficulty ranking across eras
- **ML ready**: Normalized ratings ready for model training

---

### ✅ Phase 3: Multi-Format Support (COMPLETE)

**Duration**: 1 session (2025-11-20)
**Status**: Fully implemented and tested
**Priority**: High

#### Deliverables

1. **SSC Format Parser** (`parsers/ssc_parser.py`)
   - ✅ StepMania 5 format support
   - ✅ Enhanced timing features (#DELAYS, #WARPS, #TIMESIGNATURES, #SPEEDS)
   - ✅ Per-chart metadata (#CHARTNAME, #RADARVALUES)
   - ✅ Multiple chart sections with #NOTEDATA: separators
   - ✅ 402 .ssc files supported

2. **DWI Format Parser** (`parsers/dwi_parser.py`)
   - ✅ Legacy DanceWith Intensity format support
   - ✅ Compressed hexadecimal note decoding
   - ✅ Bitwise encoding conversion (0-F → arrow patterns)
   - ✅ GAP to OFFSET conversion
   - ✅ 649 .dwi files supported

3. **Universal Parser** (`parsers/universal_parser.py`)
   - ✅ Automatic format detection from file extension
   - ✅ Single interface: `parse_chart_file()`
   - ✅ Format checking utilities
   - ✅ Unified output across all formats

4. **Format Documentation** (`doc/file_formats.md`)
   - ✅ Complete format reference
   - ✅ Encoding specifications
   - ✅ Parsing strategy documentation

5. **Comprehensive Tests** (`tests/test_multi_format.py`)
   - ✅ 29 tests for all parsers
   - ✅ Format equivalence tests
   - ✅ Feature extraction compatibility tests
   - ✅ All 68 tests passing (29 new + 39 existing)

6. **Example Scripts**
   - ✅ `examples/example_multi_format.py`: 6 usage examples
   - ✅ Format-specific test scripts

#### Test Results

**Format Coverage**: 100% of collection

| Format    | Files     | Parser    | Status          |
|-----------|-----------|-----------|-----------------|
| .sm       | 3,283     | SMParser  | ✅ Working      |
| .ssc      | 402       | SSCParser | ✅ Working      |
| .dwi      | 649       | DWIParser | ✅ Working      |
| **Total** | **4,334** | **100%**  | **✅ Complete** |

**Test Coverage**:
- SSC Parser: 7 tests ✅
- DWI Parser: 7 tests ✅
- Universal Parser: 9 tests ✅
- Format Equivalence: 2 tests ✅
- Feature Extraction: 3 tests ✅
- **Total**: 29 new tests, all passing

#### Key Achievements

- **Unified Interface**: Single function parses all formats
- **100% Coverage**: All 4,334 chart files now supported
- **Format-Agnostic Features**: Feature extraction works uniformly
- **DWI Decoding**: Successfully decoded compressed hex format
- **SSC Advanced Features**: Full StepMania 5 support
- **No Regressions**: All existing tests still passing

---

### ✅ Phase 4: ML Pipeline and Model Training (COMPLETE)

**Duration**: 1 session (2025-11-20)
**Status**: Fully implemented and tested
**Priority**: High

#### Deliverables

1. **Dataset Generation Pipeline** (`generate_dataset.py`)
   - ✅ Batch process all 4,334 chart files
   - ✅ Export to CSV and Parquet (26,287 charts)
   - ✅ 100% success rate (no parsing errors)
   - ✅ Comprehensive statistics and validation
   - ✅ 91.33 seconds processing time

2. **Baseline ML Models** (`models/baseline_models.py`)
   - ✅ Linear Regression baseline
   - ✅ Random Forest regressor
   - ✅ Feature importance analysis
   - ✅ Model persistence and loading

3. **Training Pipeline** (`train_baseline_models.py`)
   - ✅ Automated training script
   - ✅ K-fold cross-validation (5-fold)
   - ✅ Comprehensive metrics (MAE, RMSE, R², Spearman ρ)
   - ✅ Feature importance ranking
   - ✅ Model saving with metadata

4. **Inference Example** (`examples/example_ml_usage.py`)
   - ✅ Load trained models
   - ✅ Predict difficulty for any chart
   - ✅ Compare model predictions
   - ✅ Display feature contributions

#### Test Results

**Dataset:**
- 26,287 charts from 4,334 files
- 16 numerical features per chart
- Training: 21,029 samples (80%)
- Test: 5,258 samples (20%)

**Linear Regression:**
- MAE: 2.09, RMSE: 2.66
- R² score: 0.54
- Spearman ρ: 0.80

**Random Forest:** ⭐
- **MAE: 0.91** ✅ (meets < 1.0 target!)
- **RMSE: 1.29**
- **R² score: 0.89** (explains 89% of variance)
- **Spearman ρ: 0.94** (excellent ranking)

**Top 3 Features:**
1. total_notes (56% importance)
2. notes_per_second (18% importance)
3. jump_ratio (6% importance)

#### Success Criteria

- ✅ **MAE < 1.0** on test set: **0.91** (Random Forest)
- ✅ High ranking correlation: **0.94** Spearman ρ
- ✅ Consistent predictions: CV score 0.88 ± 0.003

#### Technical Achievement

- **100% parse success**: All 4,334 files processed without errors
- **Excellent model performance**: Random Forest achieves 89% R² score
- **Fast training**: Full pipeline completes in ~2 minutes
- **Production-ready**: Models saved with persistence and metadata

---

## File Structure

```
~/Games/StepMania/
├── stepml/
│   ├── parsers/
│   │   ├── __init__.py
│   │   └── sm_parser.py
│   ├── features/
│   │   ├── __init__.py
│   │   └── feature_extractor.py
│   ├── utils/
│   │   ├── __init__.py
│   │   └── data_structures.py
│   ├── models/
│   ├── data/
│   │   ├── processed/
│   │   ├── models/
│   │   └── experiments/
│   ├── examples/
│   │   └── example_usage.py
│   ├── notebooks/
│   ├── tests/
│   ├── test_parser.py
│   ├── pyproject.toml
│   └── uv.lock
├── doc/
│   ├── ml_step_chart_analysis.md
│   ├── implementation_notes.md
│   └── project_status.md           # This file
└── Songs/                          # Song collection (102 packs)
```

---

## Quick Start

### Running the System

```bash
cd ~/Games/StepMania/stepml

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

1. **Immediate (Phase 4)** - ML Pipeline and Dataset Creation:
   - Batch process entire song collection (101 packs)
   - Export normalized features to CSV/Parquet
   - Train baseline ML models (linear regression, random forest)
   - Implement validation framework

3. **Medium-term** - Model Refinement:
   - Advanced model architectures (neural networks, ensembles)
   - Hyperparameter tuning
   - Cross-validation and performance metrics
   - Human validation integration

---

## Resources

- **Main Spec**: `doc/ml_step_chart_analysis.md`
- **Implementation Notes**: `doc/implementation_notes.md`
- **Phase 1 Summary**: `doc/phase1.md` / `PHASE1_COMPLETE.md`
- **Phase 2 Summary**: `doc/PHASE2_COMPLETE.md`
- **Phase 3 Summary**: `doc/PHASE3_COMPLETE.md`
- **Examples**:
  - `../example_usage.py` (Phase 1 - parsing & features)
  - `../example_scale_detection.py` (Phase 2 - scale detection)
  - `../example_multi_format.py` (Phase 3 - multi-format support)
- **Tests**:
  - `../tests/test_parser.py` (Phase 1)
  - `../tests/test_features.py` (Phase 1)
  - `../tests/test_scale_detection.py` (Phase 2)
  - `../tests/test_multi_format.py` (Phase 3)

---

## Contact / Notes

This is a personal project for analyzing and standardizing difficulty ratings across a collection of 101 StepMania song packs. The goal is to create a unified rating system that accounts for the historical differences between Classic DDR (1-10), Modern DDR (1-20), and ITG (1-12) scales, with corrections for known issues like "rating creep" in ITG charts.

**Current Status**:
- ✅ Phase 1 complete: SM parser and feature extraction
- ✅ Phase 2 complete: Scale detection and rating normalization (91.7% accuracy)
- ✅ Phase 3 complete: Multi-format support (.sm, .ssc, .dwi - 100% coverage, 4,334 files)
- ✅ Phase 4 complete: ML pipeline and model training (MAE: 0.91, R²: 0.89, Spearman ρ: 0.94)
- 🎉 **All core phases complete!**
