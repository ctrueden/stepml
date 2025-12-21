# ML Step Chart Analysis - Documentation Index

This directory contains the specification and documentation for the ML-based StepMania step chart analysis project.

## Documentation Files

### 📋 [PROJECT_STATUS.md](PROJECT_STATUS.md)
**Start here!** Comprehensive current project status with all phases complete.

- ✅ Phase 1: Complete (Parser & Feature Extraction)
- ✅ Phase 2: Complete (Scale Detection & Rating Normalization)
- ✅ Phase 3: Complete (Multi-Format Support)
- ✅ Phase 4: Complete (ML Pipeline & Model Training)

### 📖 [ml_step_chart_analysis.md](ml_step_chart_analysis.md)
**Complete technical specification** covering the project architecture and design.

- Background and problem statement
- Rating scale complexity (Classic DDR, Modern DDR, ITG)
- Technical architecture overview
- Data pipeline and processing strategy

### 🔧 [implementation_notes.md](implementation_notes.md)
**Implementation details and practical information** for working with the codebase.

- File format details (.sm, .ssc, .dwi)
- Data structures and enums
- Development environment setup
- Quick start guide with code examples

### 📄 [file_formats.md](file_formats.md)
**Reference documentation** for all three chart file formats.

- .sm format specification
- .ssc format (StepMania 5) specification
- .dwi format (legacy) encoding reference

## Project Structure

```
/home/curtis/Games/StepMania/
├── stepchart-reclassify/                  # Main implementation
│   ├── parsers/                           # Multi-format parsers
│   ├── features/                          # Feature extraction
│   ├── utils/                             # Data structures & utilities
│   ├── models/                            # Trained ML models
│   ├── data/                              # Datasets & output
│   ├── tests/                             # Test suite
│   ├── notebooks/                         # Analysis notebooks
│   ├── generate_dataset.py                # Dataset generation
│   ├── train_baseline_models.py           # Model training
│   ├── example_ml_usage.py                # ML inference examples
│   └── spec/                              # ← Documentation
│
├── Songs/                                 # Song collection (102 packs, 4,334 charts)
└── Save/LocalProfiles/00000000/Stats.xml  # Player performance history
```

## Quick Start

### Generating Predictions
```bash
cd /home/curtis/Games/StepMania/stepchart-reclassify

# Generate difficulty prediction for a chart
uv run python example_ml_usage.py "../Songs/StepMania 5/Goin' Under/Goin' Under.sm"

# Generate dataset from all charts
uv run python generate_dataset.py

# Train models
uv run python train_baseline_models.py
```

### Using the Libraries
```python
from parsers.universal_parser import parse_chart_file
from features.feature_extractor import FeatureExtractor
from models.baseline_models import RandomForestModel

# Parse any chart format
chart_data = parse_chart_file("path/to/chart.sm")  # or .ssc or .dwi

# Extract features
extractor = FeatureExtractor()
for chart in chart_data.charts:
    features = extractor.extract_features(chart_data, chart)
    print(f"{chart.difficulty.value}: {features.notes_per_second:.2f} NPS")

# Get ML predictions
model = RandomForestModel()
model.load(Path('data/models'))
prediction = model.predict(features)
```

## Project Status

✅ **All 4 Phases Complete** (2025-11-24)

**Phase 1**: Parser & Feature Extraction
- Full .sm parser with comprehensive feature extraction
- Tested on real charts from collection

**Phase 2**: Scale Detection & Rating Normalization
- Automatic scale detection (91.7% accuracy)
- Rating conversion across all historical scales

**Phase 3**: Multi-Format Support
- .ssc parser (StepMania 5 format)
- .dwi parser (legacy format)
- Universal parser with auto-detection
- **100% coverage**: 4,334 chart files from 102 packs

**Phase 4**: ML Pipeline & Model Training
- Dataset generation: 26,287 charts
- Baseline models: Linear Regression + Random Forest
- **Top performance**: Random Forest MAE 0.91, R² 0.89, ρ 0.94

## Dependencies

```
Python 3.12
uv (package manager)

Key packages:
- numpy 2.3.4
- pandas 2.3.3
- scikit-learn 1.7.2
- pyarrow 22.0.0
- scipy 1.16.3
```

## Key Achievements

1. ✅ **Universal Parser**: Parse any chart format (.sm, .ssc, .dwi)
2. ✅ **Feature Extraction**: 16 meaningful features per chart
3. ✅ **Scale Detection**: Automatic DDR/ITG/Modern classification
4. ✅ **Rating Normalization**: Unified scale across all eras
5. ✅ **ML Models**: Production-ready difficulty predictor
6. ✅ **Full Coverage**: 100% of collection (4,334 charts)

## Next Steps (Optional Enhancements)

1. **Advanced Models**: Neural networks, ensemble methods
2. **Hyperparameter Tuning**: Optimize Random Forest performance
3. **Feature Engineering**: Advanced pattern detection
4. **Web Service**: REST API for chart analysis
5. **Visualization**: Difficulty prediction plots and comparisons

---

**Last Updated**: 2025-11-24
**Project Location**: `/home/curtis/Games/StepMania/`
**Status**: ✅ All 4 Phases Complete
