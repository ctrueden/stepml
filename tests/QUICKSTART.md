# Testing Quick Start

## TL;DR

```bash
# Run all tests
uv run pytest tests/ -v

# Run only regression tests
uv run pytest -v -m regression

# Generate new baseline (when you change feature extraction)
uv run python scripts/generate_baseline.py
```

## What This Does

Your testing system follows the **A → B → C** approach you suggested:

### A) Extract Features from Representative Charts
- Selected charts cover edge cases (high BPM, BPM changes, etc.)
- Charts are in your local `Songs/` folder (no redistribution needed)
- See `tests/fixtures/test_charts.json` for the list

### B) Save to Baseline
- Features saved to `tests/fixtures/baseline_features.json`
- This is your "golden baseline" for comparison
- Regenerate with `scripts/generate_baseline.py`

### C) Compare New Extractions
- Tests automatically compare current extraction vs baseline
- Detects any regressions (unintended changes)
- Tolerance built in for floating point differences

## Test Results Summary

**Current Status**: ✅ **20 tests passing, 1 skipped**

```
Tests by Category:
- Parser Tests: 11 tests
- Feature Tests: 10 tests
- Regression Tests: 5 tests (most important!)
- Edge Case Tests: 4 tests
```

## Adding More Test Charts

When you want to test additional edge cases:

1. **Edit `tests/fixtures/test_charts.json`**:
   ```json
   {
     "name": "Chart with Stops",
     "path": "SongPack/Song/chart.sm",
     "description": "Tests stop/freeze handling",
     "edge_cases": ["stops", "freezes"]
   }
   ```

2. **Regenerate baseline**:
   ```bash
   uv run python scripts/generate_baseline.py
   ```

3. **Run tests**:
   ```bash
   uv run pytest -v
   ```

## Current Test Coverage

**Edge Cases Currently Tested:**
- ✅ High BPM (210 BPM)
- ✅ Multiple difficulties (Beginner → Challenge)
- ✅ Modern format (.sm files)
- ✅ Jump patterns
- ✅ Hold notes
- ⚠️  Need to add: Stops, rolls, mines, .ssc format, .dwi format

**Suggested Additions** (see `test_charts.json`):
- Charts with stops/freezes
- Charts with heavy roll usage
- Charts with mines
- Double/couple charts
- .ssc format (StepMania 5 advanced timing)
- .dwi format (legacy DDR format)

## Interpreting Results

### All Tests Pass ✅
Great! Your parser and features are working correctly.

### Regression Test Fails ❌
Feature extraction has changed:
- **Intended?** → Regenerate baseline
- **Bug?** → Fix the code

Example output:
```
Feature regression detected:
High Speed Chart/dance-single_Challenge/notes_per_second:
  Expected 5.334135, got 5.500000 (diff: 3.11%)
```

## Daily Workflow

```bash
# Make changes to parser or feature extraction
vim parsers/sm_parser.py
vim features/feature_extractor.py

# Run tests to check for regressions
uv run pytest -v

# If regression is intentional, regenerate baseline
uv run python scripts/generate_baseline.py
```

## Benefits

✅ **Fast** - Only tests representative subset (~1 chart currently)
✅ **No Chart Redistribution** - Uses your local Songs folder
✅ **Catches Regressions** - Immediately detects unintended changes
✅ **Easy to Extend** - Add charts by editing JSON config
✅ **Confidence** - Know things work before moving forward

---

See `tests/README.md` for complete documentation.
