# ML Step Chart Analysis - Documentation Index

This directory contains the specification and documentation for the ML-based StepMania step chart analysis project.

## Documentation Files

### 📋 [PROJECT_STATUS.md](PROJECT_STATUS.md)
**Start here!** Current project status with phase progress, test results, and quick start guide.

- ✅ Phase 1: Complete (Parser & Feature Extraction)
- 🔄 Phase 2: Next (Scale Detection)
- 📋 Phase 3-4: Planned

### 📖 [ml_step_chart_analysis.md](ml_step_chart_analysis.md)
**Complete technical specification** covering the entire project architecture.

- Background and problem statement
- Rating scale complexity (Classic DDR, Modern DDR, ITG)
- Technical architecture and data pipeline
- Feature specifications
- ML model design
- Implementation phases

### 🔧 [implementation_notes.md](implementation_notes.md)
**Implementation details and context** with practical information.

- File format discovery (.sm, .ssc, .dwi)
- Phase completion status
- Data structures (implemented)
- Development environment setup
- Quick start guide with code examples

## Project Structure

```
/home/curtis/Games/StepMania/
├── ml_analysis/                           # Main implementation
│   ├── parsers/                           # File parsers
│   ├── features/                          # Feature extraction
│   ├── utils/                             # Data structures
│   ├── models/                            # ML models (future)
│   ├── data/                              # Data storage
│   ├── test_parser.py                     # Test script
│   ├── example_usage.py                   # Usage examples
│   └── spec/                              # ← You are here
│       ├── README.md                      # This file
│       ├── project_status.md              # Current status
│       ├── ml_step_chart_analysis.md      # Main specification
│       ├── implementation_notes.md        # Implementation details
│       └── phase1.md                      # Phase 1 summary
│
├── Songs/                                 # Song collection (102 packs)
└── Save/LocalProfiles/00000000/Stats.xml  # Stats over many expert play sessions
```


## Quick Links

### Getting Started
1. Read [project_status.md](project_status.md) for current status
2. Review [ml_step_chart_analysis.md](ml_step_chart_analysis.md) for full context
3. Check [implementation_notes.md](implementation_notes.md) for usage examples
4. See [phase1.md](phase1.md) for Phase 1 details
5. Run tests: `uv run test_parser.py`

### Key Concepts

**Problem**: Multiple incompatible difficulty rating scales across DDR/ITG eras
- Classic DDR: 1-10 scale
- Modern DDR: 1-20 scale
- ITG: 1-12 scale (with "rating creep" issues)

**Solution**: ML-based system to:
1. Parse all chart formats (.sm, .ssc, .dwi)
2. Extract meaningful features (density, patterns, timing)
3. Detect source scale and normalize ratings
4. Provide unified, consistent difficulty ratings

### Current Status

✅ **Phase 1 Complete** (2025-10-15)
- Full .sm parser implemented
- 19+ features extracted per chart
- Tested on real charts from collection
- Clean, modular architecture

🔄 **Phase 2 Next**: Scale Detection & Rating Normalization

## Development

### Running Tests
```bash
cd ../ml_analysis
uv run test_parser.py
uv run test_parser.py "../Songs/[path-to-chart]/chart.sm"
uv run example_usage.py "../Songs/[path-to-chart]/chart.sm"
```

### Using the Parser
```python
from parsers.sm_parser import parse_sm_file
from features.feature_extractor import FeatureExtractor

chart_data = parse_sm_file("path/to/chart.sm")
extractor = FeatureExtractor()

for chart in chart_data.charts:
    features = extractor.extract_features(chart_data, chart)
    print(f"{chart.difficulty.value}: {features.notes_per_second:.2f} NPS")
```

### Dependencies
- Python 3.12
- uv (package manager)
- numpy 2.3.4

## Project Goals

1. **Unified Rating System**: Single 1-20 scale across all eras
2. **Scale Translation**: Accurate conversion between DDR, ITG, modern scales
3. **Multi-Format Support**: Parse .sm, .ssc, .dwi files seamlessly
4. **Automated Rating**: Instant ratings for new charts
5. **Improved Player Experience**: Predictable difficulty progression

## Background

This project analyzes a collection of 102+ StepMania song packs containing thousands of charts across multiple difficulty levels and rating scales. The goal is to create a machine learning system that can:

- Understand the nuances of different historical rating scales
- Extract meaningful features from step charts
- Provide consistent, accurate difficulty ratings
- Account for known issues like ITG "rating creep"

The system will help players have a more consistent experience across their entire song collection, regardless of which era or series each chart originated from.

---

**Last Updated**: 2025-10-15
**Project Location**: `/home/curtis/Games/StepMania/`
**Status**: Phase 1 Complete ✅
