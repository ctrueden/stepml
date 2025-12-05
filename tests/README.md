# StepMania Parser & Feature Extraction Tests

Comprehensive regression test suite for the StepMania chart parser and feature extraction system.

## Overview

This test suite ensures that:
1. **Parser correctness** - SM files are parsed correctly
2. **Feature stability** - Feature extraction produces consistent results
3. **Regression prevention** - Changes don't break existing functionality
4. **Edge case coverage** - Various chart types and patterns are handled

## Test Strategy

### Baseline-Driven Regression Testing

Rather than redistributing step charts, we use a **golden baseline** approach:

```
┌─────────────────────────────────────────────────────────────┐
│  A) Extract features from representative charts             │
│     └─ Selected for edge case coverage                      │
│                                                             │
│  B) Save features to baseline_features.json                 │
│     └─ "Golden" reference data                              │
│                                                             │
│  C) Compare new extractions against baseline                │
│     └─ Detect any regressions or changes                    │
└─────────────────────────────────────────────────────────────┘
```

### Representative Chart Selection

Test charts are selected to cover specific edge cases:
- **Simple charts** - Basic timing, no gimmicks
- **High BPM** - Fast charts (>180 BPM)
- **BPM changes** - Variable tempo
- **Stops/freezes** - Timing manipulation
- **Jump patterns** - Simultaneous notes
- **Holds/rolls** - Sustained notes
- **Multiple difficulties** - Full difficulty range
- **Format variations** - .sm, .ssc, .dwi files

## Directory Structure

```
tests/
├── conftest.py                   # Pytest configuration & fixtures
├── test_parser.py                # Parser regression tests
├── test_features.py              # Feature extraction tests
├── fixtures/
│   ├── test_charts.json          # Chart selection config
│   └── baseline_features.json    # Golden baseline data
└── README.md                     # This file
```

## Usage

### 1. Initial Setup - Generate Baseline

First time setup or after intentional changes to feature extraction:

```bash
# Generate baseline from current implementation
cd /home/curtis/Games/StepMania/stepchart-reclassify
uv run python scripts/generate_baseline.py
```

This creates `baseline_features.json` with feature values from all test charts.

### 2. Running Tests

Run all tests:
```bash
cd /home/curtis/Games/StepMania/stepchart-reclassify
uv run pytest tests/ -v
```

Run specific test categories:
```bash
# Parser tests only
uv run pytest -v -m parser

# Feature extraction tests only
uv run pytest -v -m features

# Regression tests only (compare against baseline)
uv run pytest -v -m regression

# Edge case tests only
uv run pytest -v -m edge_case
```

Run specific test files:
```bash
uv run pytest tests/test_parser.py -v
uv run pytest tests/test_features.py -v
```

### 3. Understanding Test Results

**All tests pass** ✅
- Parser and features working correctly
- No regressions detected
- Ready to proceed with confidence

**Regression test fails** ❌
- Feature extraction has changed
- Review changes carefully:
  - **Intended change?** → Regenerate baseline
  - **Unintended change?** → Fix the bug

**Parser test fails** ❌
- Parser not extracting data correctly
- Fix the parser issue before continuing

### 4. Updating Baseline (Intentional Changes)

When you intentionally modify feature extraction algorithms:

```bash
# 1. Make your changes to feature_extractor.py
# 2. Verify changes are correct
# 3. Regenerate baseline
uv run python scripts/generate_baseline.py

# 4. Verify tests pass with new baseline
uv run pytest -v -m regression
```

## Adding New Test Charts

To add additional test charts (e.g., to cover new edge cases):

1. Edit `tests/fixtures/test_charts.json`:

```json
{
  "charts": [
    {
      "name": "My New Test Case",
      "path": "SongPack/SongName/chart.sm",
      "description": "Chart with specific edge case",
      "edge_cases": ["stops", "high_bpm"]
    }
  ]
}
```

2. Regenerate baseline:

```bash
uv run python scripts/generate_baseline.py
```

3. Run tests to verify:

```bash
uv run pytest -v
```

## Test Categories

### Parser Tests (`test_parser.py`)

**Basic Functionality**
- Returns correct data structures
- Extracts metadata (title, artist, BPM, etc.)
- Parses timing data (BPM changes, stops)
- Extracts chart data (difficulties, ratings)

**Note Data**
- Counts notes correctly (taps, holds, rolls, mines)
- Detects jumps (simultaneous notes)
- Validates note positions
- Ensures count consistency

**Edge Cases**
- High BPM charts
- BPM changes
- Multiple difficulties
- Stops and timing gimmicks

**Error Handling**
- Missing files
- Invalid paths
- Malformed data

### Feature Tests (`test_features.py`)

**Basic Features**
- Returns FeatureSet objects
- All values are valid (non-negative, proper ranges)
- Converts to dict correctly
- Contains expected feature keys

**Advanced Features**
- Stream detection
- Direction changes
- Crossover potential

**Regression Tests** ⭐ **Most Important**
- Compares current features vs. baseline
- Detects unintended changes
- Tolerates floating-point precision differences
- Reports specific mismatches

**Scaling Behavior**
- Features scale with difficulty rating
- Peak density ≥ average density
- Higher difficulties have more notes

## Configuration

### Pytest Configuration (`pytest.ini`)

```ini
[pytest]
testpaths = tests
markers =
    parser: Parser tests
    features: Feature extraction tests
    regression: Regression tests
    edge_case: Edge case tests
```

### Test Fixtures (`conftest.py`)

Shared fixtures available in all tests:
- `songs_dir` - Path to Songs folder
- `test_charts_config` - Test chart configuration
- `baseline_features` - Baseline feature data
- `test_chart_paths` - Resolved chart paths
- `feature_extractor` - FeatureExtractor instance
- `advanced_feature_extractor` - AdvancedFeatureExtractor instance

## Tolerance Settings

Regression tests use tolerance for floating-point comparisons:

- **Relative tolerance**: 1% (0.01) for non-zero values
- **Absolute tolerance**: 0.001 for near-zero values

This accounts for minor numerical differences while catching real regressions.

## Workflow

### Normal Development

```bash
# Make changes to parser or feature extractor
vim parsers/sm_parser.py

# Run tests to check for regressions
uv run pytest -v

# If tests pass: ✅ You're good!
# If tests fail: Fix the issue or regenerate baseline
```

### Adding New Features

```bash
# 1. Add new feature to FeatureSet
vim utils/data_structures.py

# 2. Implement feature extraction
vim features/feature_extractor.py

# 3. Regenerate baseline (new features won't be in old baseline)
uv run python scripts/generate_baseline.py

# 4. Run tests
uv run pytest -v
```

### Before Committing

```bash
# Always run full test suite before committing
uv run pytest -v

# Ensure no regressions
uv run pytest -v -m regression
```

## Benefits

✅ **No Chart Redistribution** - Tests use your local Songs folder
✅ **Fast Execution** - Only tests representative subset
✅ **Regression Safety** - Catch unintended changes immediately
✅ **Edge Case Coverage** - Comprehensive without being exhaustive
✅ **Easy Maintenance** - Add new tests by updating JSON config
✅ **Confidence** - Move forward knowing things work correctly

## Troubleshooting

**"No test charts available"**
- Check that `test_charts.json` paths are correct relative to Songs/
- Verify Songs directory structure matches paths
- Some charts missing is OK - tests will skip them

**"No baseline data available"**
- Run `uv run python scripts/generate_baseline.py` first
- Baseline must be generated before regression tests

**"Feature regression detected"**
- Review the specific mismatches reported
- Determine if change was intentional
- If intentional: regenerate baseline
- If not: fix the bug

**Tests fail after parser changes**
- Expected if parser behavior changed
- Review changes carefully
- Regenerate baseline if changes are correct
- Otherwise, fix the parser

## Future Enhancements

Potential additions to test suite:
- [ ] Performance benchmarks
- [ ] Stress tests (1000+ chart batch processing)
- [ ] .ssc format specific tests
- [ ] .dwi format specific tests
- [ ] Malformed file handling
- [ ] Memory usage tests
- [ ] Parallel processing tests

---

**Last Updated**: 2025-10-15
**Test Framework**: pytest 8.0+
**Python Version**: 3.12+
