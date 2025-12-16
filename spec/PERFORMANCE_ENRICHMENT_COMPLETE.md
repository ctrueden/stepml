# Performance Data Enrichment Complete

**Date**: 2025-11-24
**Status**: ✅ COMPLETE

---

## Overview

Successfully integrated player performance data from Stats.xml into the ML analysis dataset. The enriched dataset now contains 14 new performance-based features that provide empirical difficulty validation and enable identification of rating anomalies.

---

## Implementation Summary

### 1. Stats.xml Parser (`parsers/stats_parser.py`)

**Features:**
- ✅ Complete XML parsing of StepMania Stats.xml format
- ✅ Extraction of per-chart performance metrics
- ✅ Detailed timing breakdown (W1/W2/W3/W4/W5/Miss counts)
- ✅ Hold note performance tracking
- ✅ Multiple score records per chart
- ✅ Calculated metrics (accuracy, consistency, perfect rate)

**Performance:**
- Parsed 1,493 songs with performance data
- Extracted 2,475 chart performances
- 1,724 charts with detailed score breakdowns

### 2. Performance Enrichment System (`utils/performance_enrichment.py`)

**Features:**
- ✅ Automatic song/chart matching between Stats.xml and dataset
- ✅ Path normalization and mapping
- ✅ 14 new performance features per chart
- ✅ Graceful handling of missing data

**New Features Added:**
1. **Play Metrics:**
   - `times_played` - Number of times chart was played
   - `has_performance_data` - Boolean flag

2. **Accuracy Metrics:**
   - `best_accuracy` - Best accuracy achieved (0.0-1.0, weighted by timing)
   - `average_accuracy` - Average across all attempts
   - `consistency_score` - Performance variance (0.0-1.0, higher = more consistent)

3. **Score Metrics:**
   - `best_percent_dp` - Best DP percentage achieved
   - `best_max_combo` - Longest combo achieved

4. **Difficulty Perception:**
   - `perceived_difficulty_factor` - Difficulty multiplier based on accuracy (0.5-3.0)
   - `has_failed` - Boolean indicating chart failure

5. **Timing Breakdown:**
   - `perfect_rate` - Percentage of W1+W2 notes
   - `great_or_worse_rate` - Percentage of W3 or worse
   - `miss_rate` - Percentage of missed notes

6. **Hold Notes:**
   - `hold_success_rate` - Percentage of holds successfully completed

7. **Grading:**
   - `high_grade` - Best grade achieved (Tier01-Tier20, Failed)

### 3. Dataset Generation Integration

**Updated `generate_dataset.py`:**
- ✅ Added `--stats-file` parameter (auto-detects default location)
- ✅ Added `--no-performance` flag to disable enrichment
- ✅ Automatic performance enrichment during dataset generation
- ✅ Enhanced statistics reporting

**Results:**
- Dataset size: 26,287 charts (unchanged)
- Dataset columns: 43 (up from 29, +14 performance features)
- Match rate: 7.9% (2,082 charts with performance data)
- Charts with detailed scores: 1,505
- Generation time: 93.59 seconds

---

## Key Findings

### Performance Statistics

**Overall Performance:**
- Average best accuracy: **92.13%**
- Median best accuracy: **95.08%**
- Average plays per chart: **2.7**

**Accuracy Distribution:**
- 90th percentile: 98.12%
- 75th percentile: 97.07%
- 50th percentile: 95.08%
- 25th percentile: 91.15%
- 10th percentile: 85.12%

### Correlation Analysis

**Performance vs. Difficulty Correlations:**
```
Feature                          Correlation with Rating
─────────────────────────────────────────────────────────
best_accuracy                    -0.087 (weak negative)
average_accuracy                 -0.082 (weak negative)
perfect_rate                     -0.092 (weak negative)
perceived_difficulty_factor      +0.086 (weak positive)
miss_rate                        +0.077 (weak positive)
times_played                     -0.018 (negligible)
```

**Interpretation:**
- Weak negative correlation between accuracy and rating is expected
- Correlation is weaker than anticipated due to:
  - Player skill improvement over time
  - Chart familiarity from repeated plays
  - Small sample size (only 7.9% of charts played)
  - Player skill level matching chart difficulty selection

### Rating Anomalies Detected

**Charts Significantly Easier Than Rated:**
1. **Lesson by DJ** (Beginner 1): 98.41% accuracy vs. 71.39% expected (+27%)
2. **Emera** (Challenge 17): 77.06% accuracy vs. 52.78% expected (+24%)
3. **ENDYMION** (Challenge 19): 68.40% accuracy vs. 46.65% expected (+22%)

*Interpretation: These charts may be under-challenging for their stated difficulty.*

**Charts Significantly Harder Than Rated:**
1. **Rough and Rugged** (Hard 13): 24.64% accuracy vs. 93.68% expected (-69%)
2. **You're Beautiful** (Challenge 12): 27.16% accuracy vs. 94.27% expected (-67%)
3. **Going Haywyre** (Edit 11): 52.08% accuracy vs. 92.61% expected (-41%)
4. **Shovel Knight** (Hard 7): 57.72% accuracy vs. 92.81% expected (-35%)

*Interpretation: These charts may have unusual patterns, gimmicks, or be significantly under-rated.*

### Accuracy by Rating Level

**Clear Trend:** Higher difficulty ratings generally correlate with lower accuracy

| Rating | Avg Accuracy | Std Dev | Charts |
|--------|--------------|---------|--------|
| 7      | 92.81%       | 10.77%  | 84     |
| 8      | 93.77%       | 9.49%   | 204    |
| 9      | 92.24%       | 5.27%   | 274    |
| 10     | 90.70%       | 8.12%   | 139    |
| 11     | 92.61%       | 11.21%  | 133    |
| 12     | 94.27%       | 7.98%   | 255    |
| 13     | 93.68%       | 11.47%  | 220    |
| 14     | 89.87%       | 10.32%  | 99     |
| 15     | 87.58%       | 7.04%   | 37     |
| 16     | 81.17%       | 17.30%  | 18     |
| 17     | 52.78%       | 39.81%  | 6      |

**Note:** Ratings 8-13 show surprisingly high and consistent accuracy, suggesting these are well-practiced charts at the player's skill level.

---

## Model Training Implications

### Should We Retrain With Performance Features?

**Challenges:**
1. **Low coverage**: Only 7.9% of charts have performance data
2. **Selection bias**: Only charts the player chose to play are represented
3. **Skill level bias**: Performance reflects one player's skill level
4. **Familiarity bias**: Repeated plays improve scores

**Recommendation:** **Do NOT retrain the main model with performance features**

**Reasoning:**
- Primary model should work for all charts (100% coverage)
- Performance data is sparse and biased
- Performance features are better suited for:
  - **Validation**: Identifying mis-rated charts
  - **Analysis**: Understanding player-chart interaction
  - **Outlier detection**: Finding unusual patterns

### Alternative Use Cases for Performance Data

1. **Rating Validation Tool**
   - Compare predicted difficulty vs. actual performance
   - Flag charts with large discrepancies
   - Suggest rating corrections

2. **Personalized Difficulty**
   - Adjust predictions based on player's historical performance
   - Recommend charts matching player skill level
   - Track skill progression over time

3. **Chart Quality Assessment**
   - Identify charts with unusual fail rates
   - Detect gimmick patterns that affect difficulty perception
   - Find well-balanced vs. poorly-designed charts

4. **Training Data Augmentation** (Future)
   - Collect performance data from multiple players
   - Use ensemble of player performances for robust difficulty estimation
   - Weight training samples by empirical difficulty consensus

---

## Files Created/Modified

### New Files
```
parsers/stats_parser.py              # Stats.xml parser
utils/performance_enrichment.py      # Performance feature extraction
test_stats_parser.py                 # Parser validation
analyze_performance_data.py          # Dataset analysis tool
spec/PERFORMANCE_ENRICHMENT_COMPLETE.md  # This document
```

### Modified Files
```
generate_dataset.py                  # Added performance enrichment
```

### Updated Dataset
```
data/processed/dataset.csv           # 26,287 rows × 43 columns (was 29)
data/processed/dataset.parquet       # 26,287 rows × 43 columns
data/processed/dataset_info.json     # Updated schema
```

---

## Usage Examples

### Generate Dataset With Performance Enrichment (Default)
```bash
python generate_dataset.py
```

### Generate Dataset Without Performance Enrichment
```bash
python generate_dataset.py --no-performance
```

### Analyze Performance Data
```bash
python analyze_performance_data.py
```

### Programmatic Access to Performance Data
```python
from parsers.stats_parser import parse_stats_file

# Parse Stats.xml
parser = parse_stats_file('../Save/LocalProfiles/00000000/Stats.xml')

# Get performance for a specific chart
perf = parser.get_performance(
    'Songs/DDR 1st Mix/Butterfly',
    'Challenge',
    'dance-single'
)

if perf:
    print(f"Played: {perf.num_times_played} times")
    print(f"Best accuracy: {perf.best_accuracy:.2%}")
    print(f"Consistency: {perf.consistency_score:.2f}")
```

---

## Statistics Summary

```
Performance Data Coverage:
  Total charts in dataset: 26,287
  Charts with performance data: 2,082 (7.9%)
  Charts with detailed scores: 1,505

Stats.xml Contents:
  Songs with data: 1,493
  Total chart performances: 2,475
  Total plays recorded: 6,415

Player Statistics:
  Average best accuracy: 92.13%
  Average plays per chart: 2.7
  Most played chart: 38 times

Dataset Enrichment:
  New features added: 14
  Total features: 43 (was 29)
  Dataset size: 22.61 MB
  Generation time: 93.59 seconds
```

---

## Next Steps (Optional Future Work)

### Immediate Opportunities
1. **Build rating validation tool** using performance anomalies
2. **Create chart recommendation system** based on player skill
3. **Export anomaly report** for manual review
4. **Visualize** difficulty vs. performance scatter plots

### Advanced Features
1. **Multi-player data collection** for robust difficulty estimation
2. **Skill progression tracking** over time
3. **Chart clustering** by actual difficulty patterns
4. **Personalized difficulty predictions** per player

### Model Enhancements (Future Phase)
1. **Separate validation model** trained only on performance data
2. **Ensemble approach** combining feature-based and performance-based models
3. **Active learning** to identify which charts need more play data
4. **Difficulty calibration** using performance consensus

---

## Conclusion

Performance data enrichment successfully adds empirical difficulty validation to the ML analysis system. While the 7.9% coverage is too sparse for direct model training, it provides valuable insights for:

- ✅ Identifying mis-rated charts
- ✅ Validating model predictions
- ✅ Understanding player-chart interaction
- ✅ Detecting unusual patterns and gimmicks

The enriched dataset is now ready for advanced analysis and validation workflows.

**Status**: ✅ **COMPLETE**

---

**Last Updated**: 2025-11-24
**Enriched Dataset**: `/home/curtis/Games/StepMania/ml_analysis/data/processed/dataset.parquet`
