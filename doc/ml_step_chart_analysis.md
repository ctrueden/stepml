# Machine Learning-Based Step Chart Analysis and Difficulty Rating System

## Overview

This specification outlines a machine learning approach to analyze StepMania step charts and provide consistent difficulty ratings across all songs. The system will extract meaningful features from .sm, .ssc, and .dwi files and use these to train models for accurate difficulty prediction and rating standardization across multiple historical rating scales.

## Background

### Current State Analysis
Based on examination of your StepMania assets and the ITGMania fork:

- **Song Collection**: 102 song packs with thousands of charts across multiple difficulty levels
- **File Formats**: .sm (StepMania), .ssc (StepMania 5), .dwi (DWI/StepMania legacy)
- **Rating Scale Complexity**: Multiple historical difficulty scales across different series:

#### Rating Scale Evolution
1. **Classic DDR (pre-X)**: 1-9 scale (later extended to 10)
   - Established the foundational difficulty curve
   - 10s added later were significantly harder than 9s
   - "Flashing 10s" represented extreme difficulty

2. **Modern DDR (X onwards)**: 1-18/20 scale
   - Approximate conversion: old-7 ≈ new-10, old-8 ≈ new-12, old-9 ≈ new-13
   - old-10 ≈ new-14/15, old-flashing-10 ≈ new-16
   - Scale roughly doubled from classic system

3. **In the Groove (ITG)**: 1-12 scale
   - Originally intended to match classic DDR scale
   - Extended to 12 for harder content
   - Suffered from "rating creep": ITG-8 ≈ classic-DDR-9
   - ITG-9 could be hard classic-DDR-9 or even classic-DDR-10

### Problem Statement
Multiple compounding issues create rating inconsistency:
- **Scale Variation**: Different eras use incompatible difficulty scales
- **Rating Creep**: Systematic underrating in certain series (especially ITG)
- **Creator Subjectivity**: Individual chart creators' varying standards
- **Poor Player Experience**: Unpredictable difficulty progression across song packs

## Technical Architecture

### 1. Data Pipeline

#### 1.1 Multi-Format Chart Parser
```python
class UniversalChartParser:
    def parse_chart_file(self, filepath: str) -> ChartData:
        file_ext = Path(filepath).suffix.lower()
        if file_ext == '.sm':
            return self.parse_sm_file(filepath)
        elif file_ext == '.ssc':
            return self.parse_ssc_file(filepath)
        elif file_ext == '.dwi':
            return self.parse_dwi_file(filepath)
        else:
            raise UnsupportedFormatError(f"Format {file_ext} not supported")

    def parse_sm_file(self, filepath: str) -> ChartData:
        # Standard StepMania format
        # Extract metadata: BPM, stops, title, artist, pack info
        # Parse note patterns for each difficulty
        # Handle both single and double charts

    def parse_ssc_file(self, filepath: str) -> ChartData:
        # StepMania 5 format with enhanced features
        # Support for advanced timing, per-chart metadata
        # Additional note types and effects

    def parse_dwi_file(self, filepath: str) -> ChartData:
        # Legacy DanceWith Intensity format
        # Convert to standardized internal representation
```

#### 1.2 Rating Scale Detection and Normalization
```python
class RatingScaleManager:
    def detect_scale_type(self, songpack_path: str, charts: List[ChartData]) -> ScaleType:
        # Analyze songpack name/path for series indicators
        # Statistical analysis of rating distributions
        # Pattern matching against known series characteristics

    def normalize_rating(self, original_rating: int, source_scale: ScaleType,
                        target_scale: ScaleType = ScaleType.UNIFIED) -> float:
        # Convert between different rating scales
        # Account for rating creep in specific series
        # Handle edge cases and uncertain mappings

    SCALE_CONVERSIONS = {
        ScaleType.CLASSIC_DDR: {
            7: 10.0,   # Classic 7 → Unified 10
            8: 12.0,   # Classic 8 → Unified 12
            9: 13.0,   # Classic 9 → Unified 13
            10: 14.5,  # Classic 10 → Unified 14.5
        },
        ScaleType.ITG: {
            8: 13.0,   # ITG 8 → Unified 13 (rating creep adjustment)
            9: 15.0,   # ITG 9 → Unified 15 (hard 9s/easy 10s)
            10: 16.0,  # ITG 10 → Unified 16
            11: 17.5,  # ITG 11 → Unified 17.5
            12: 19.0,  # ITG 12 → Unified 19
        },
        ScaleType.MODERN_DDR: {
            # Direct mapping since modern scale is reference
            10: 10.0, 12: 12.0, 13: 13.0, 14: 14.0, 15: 15.0, 16: 16.0
        }
    }
```

#### 1.3 Feature Extraction Engine
Extract features across multiple dimensions:

**Temporal Features:**
- BPM analysis (base BPM, BPM changes, variance)
- Note density over time (notes per measure, rolling averages)
- Rest periods and their distribution
- Tempo stability metrics

**Pattern Complexity Features:**
- Arrow sequence analysis (runs, jumps, holds)
- Cross-over patterns and foot positioning complexity
- Direction changes and flow patterns
- Jump complexity (simultaneous arrows)

**Technical Features:**
- Hold note patterns and overlapping holds
- Mine placement (if present)
- Stop/freeze timing analysis
- Gallop and roll patterns

**Statistical Features:**
- Total note count
- Note type distribution (taps, holds, jumps)
- Pattern repetition analysis
- Difficulty progression within chart

### 2. Feature Engineering

#### 2.1 Temporal Window Analysis
```python
def extract_temporal_features(chart_data, window_size=8):
    # Analyze chart in 8-beat windows
    # Calculate local difficulty metrics
    # Identify peak difficulty sections
    # Measure difficulty consistency
```

#### 2.2 Pattern Recognition
- **Footwork Complexity**: Analyze required foot movements
- **Stream Density**: Detect and rate stream sections
- **Technical Patterns**: Identify specific challenging patterns
- **Reading Difficulty**: Measure visual complexity

#### 2.3 Comparative Features
- Compare with similar BPM charts
- Analyze relative to song pack average
- Cross-reference with existing ratings

### 2.5 Songpack Classification and Validation

#### 2.5.1 Automatic Series Detection
```python
class SongpackClassifier:
    SERIES_PATTERNS = {
        ScaleType.CLASSIC_DDR: [
            r'DDR.*([1-5]|MAX|EXTREME)',
            r'Dance Dance Revolution.*(1st|2nd|3rd|4th|5th|MAX)',
            r'DDR.*(1st|2nd|3rd|4th|5th|MAX|EXTREME)'
        ],
        ScaleType.MODERN_DDR: [
            r'DDR.*(X[0-9]*|A[0-9]*|WORLD)',
            r'Dance Dance Revolution.*(X|SuperNOVA|HOTTEST PARTY)'
        ],
        ScaleType.ITG: [
            r'(ITG|In[_\s]?The[_\s]?Groove)',
            r'Rebirth',
            r'OpenITG'
        ]
    }

    def detect_series_from_path(self, songpack_path: str) -> Optional[ScaleType]:
        pack_name = Path(songpack_path).name.upper()
        for scale_type, patterns in self.SERIES_PATTERNS.items():
            if any(re.search(pattern, pack_name, re.IGNORECASE) for pattern in patterns):
                return scale_type
        return None

    def validate_scale_detection(self, charts: List[ChartData],
                                detected_scale: ScaleType) -> float:
        # Statistical validation of detected scale
        # Compare rating distributions against expected ranges
        # Return confidence score (0.0-1.0)
```

#### 2.5.2 Cross-Series Validation Features
- **Reference Chart Matching**: Compare similar BPM/length charts across series
- **Difficulty Distribution Analysis**: Validate rating curves match expected patterns
- **Outlier Detection**: Identify charts that don't fit their assigned scale
- **Manual Override System**: Allow user correction of automatic detection

### 3. Machine Learning Models

#### 3.1 Multi-Task Learning Architecture
```
Input: Extracted Features (300+ dimensions)
    ↓
Shared Dense Layers (256 → 128 → 64)
    ↓
Split into task-specific heads:
    ├── Absolute Difficulty Rating (1-20 scale)
    ├── Relative Difficulty (compared to song pack)
    └── Technical Category Classification
```

#### 3.2 Model Types
1. **Regression Model**: Continuous difficulty rating (1-20 scale)
2. **Classification Model**: Discrete difficulty buckets
3. **Ensemble Model**: Combines multiple approaches
4. **Transformer-based Model**: For sequential pattern analysis

#### 3.3 Multi-Scale Training Strategy

##### 3.3.1 Scale-Aware Training Data
```python
class ScaleAwareDataset:
    def __init__(self):
        self.charts_by_scale = {
            ScaleType.CLASSIC_DDR: [],
            ScaleType.MODERN_DDR: [],
            ScaleType.ITG: [],
            ScaleType.UNKNOWN: []
        }

    def add_chart(self, chart_data: ChartData, detected_scale: ScaleType,
                  confidence: float):
        # Store original and normalized ratings
        # Track scale detection confidence
        # Enable scale-specific model training

    def get_normalized_dataset(self) -> List[TrainingExample]:
        # Return dataset with all ratings normalized to unified scale
        # Include scale confidence as feature weight
```

##### 3.3.2 Training Phases
1. **Scale-Specific Models**: Train separate models for each known scale
   - Pure classic DDR model (high confidence classic charts)
   - Pure ITG model (accounting for rating creep)
   - Modern DDR reference model

2. **Cross-Scale Validation**: Use overlapping difficulty ranges for validation
   - ITG 8-9 vs Classic DDR 8-9 comparison
   - Modern DDR 10-13 vs Classic DDR 7-9 alignment

3. **Unified Model Training**:
   - **Ground Truth**: Manual ratings from expert players familiar with all scales
   - **Semi-supervised Learning**: Use normalized existing ratings as weak labels
   - **Active Learning**: Focus on boundary cases between scales
   - **Transfer Learning**: Knowledge transfer between scale-specific models

##### 3.3.3 Validation Strategy
- **Cross-scale consistency**: Ensure similar features yield similar unified ratings
- **Expert validation**: Human raters validate conversion accuracy
- **A/B testing**: Compare predicted vs expected difficulty in gameplay

### 4. Implementation Plan

#### Phase 1: Data Collection and Preprocessing
1. **Multi-Format Chart Parsing**:
   - Implement robust parsers for .sm, .ssc, and .dwi formats
   - Handle format-specific features (SSC timing events, DWI legacy syntax)
   - Normalize to common internal representation

2. **Scale Detection and Classification**:
   - Implement songpack series detection
   - Statistical validation of detected scales
   - Manual override system for edge cases

3. **Feature Extraction**: Build comprehensive feature pipeline
   - Account for format differences in feature calculation
   - Handle missing data gracefully across formats

4. **Data Validation and Normalization**:
   - Cross-scale rating normalization
   - Quality assurance for parsed data
   - Outlier detection and flagging

5. **Initial Dataset**: Process your existing 100+ song packs
   - Categorize by detected series/scale
   - Generate confidence metrics for each classification

#### Phase 2: Player Performance Integration & Scale Detection
1. **Player Stats Parser**: Extract performance data from `Stats.xml`
   - Parse per-chart performance metrics (times played, grades, accuracy)
   - Extract global skill indicators (meter distribution, play count patterns)
   - Build performance database for chart validation

2. **Performance-Based Features**: Augment chart features with empirical difficulty
   - `perceived_difficulty`: Based on player performance vs. rating
   - `sight_read_difficulty`: Adjusting for familiarity (times played)
   - `consistency_score`: Grade variance across attempts
   - `difficulty_delta`: Stated rating minus perceived difficulty

3. **Ground Truth Validation**: Use 25 years of performance data
   - Charts with high grades + many plays → Correctly rated for skill level
   - Charts with low grades despite many plays → Potentially underrated or skill gaps
   - Charts rarely played → Outside comfort zone (too easy/hard)
   - Gallop/triplet course performance → Pattern-specific skill indicators

4. **Scale Detection with Performance Validation**:
   - Implement songpack series detection
   - Validate detected scales against performance patterns
   - Use player stats to identify rating creep (e.g., ITG charts feeling harder than rating suggests)
   - Build confidence scores incorporating both metadata and performance

5. **Training Data Enrichment**:
   - Mark charts with sufficient play history as high-confidence labels
   - Weight training samples by play count and performance stability
   - Separate "mastered" charts (validation set) from learning set

#### Phase 3: Baseline Model Development
1. **Simple Models**: Linear regression, Random Forest on enriched features
2. **Feature Selection**: Identify most predictive features (chart + performance)
3. **Validation Framework**: K-fold cross-validation using play history stratification
4. **Performance Metrics**: MAE, RMSE, ranking correlation weighted by confidence

#### Phase 4: Advanced Model Training
1. **Deep Learning Models**: Neural networks with specialized architectures
2. **Pattern Recognition**: CNN/RNN for sequence analysis
3. **Hyperparameter Tuning**: Optimize model performance
4. **Ensemble Methods**: Combine multiple model predictions

#### Phase 5: Validation and Deployment
1. **Performance-Based Validation**: Compare predictions with actual player results
2. **A/B Testing**: Sight-reading vs. practiced chart difficulty predictions
3. **Calibration**: Ensure ratings match 25-year performance baseline
4. **Production System**: Automated rating pipeline with stats integration

### 5. Feature Specifications

#### 5.1 Core Features (High Priority)
```python
CORE_FEATURES = {
    # Density metrics
    'notes_per_second': float,
    'peak_density': float,
    'density_variance': float,

    # Pattern complexity
    'jump_ratio': float,
    'crossover_count': int,
    'direction_changes': int,
    'stream_sections': int,

    # Technical elements
    'hold_complexity': float,
    'bpm_changes': int,
    'stop_count': int,
    'freeze_count': int,  # SSC-specific

    # Statistical
    'total_notes': int,
    'chart_length': float,
    'difficulty_curve_slope': float,

    # Scale-aware features
    'original_rating': int,
    'detected_scale': str,
    'scale_confidence': float,
    'normalized_rating': float,

    # Format-specific metadata
    'file_format': str,  # '.sm', '.ssc', '.dwi'
    'has_advanced_timing': bool,  # SSC timing events
    'has_warps': bool,  # Format-dependent warp support

    # Player performance features (from Stats.xml)
    'times_played': int,  # Play count for this chart
    'average_grade': float,  # Average grade (0-1 normalized)
    'grade_variance': float,  # Performance consistency
    'last_played_days_ago': int,  # Recency indicator
    'perceived_difficulty': float,  # Empirical difficulty from performance
    'difficulty_delta': float,  # Stated - perceived difficulty
    'is_sight_readable': bool,  # Played ≤ 2 times (sight-reading indicator)
    'is_mastered': bool,  # High grade + multiple plays
}
```

#### 5.2 Format-Specific Feature Handling
```python
class FormatAwareFeatureExtractor:
    def extract_timing_features(self, chart_data: ChartData) -> Dict:
        if chart_data.format == '.ssc':
            # Advanced SSC timing: per-chart BPM changes, stops, delays
            return self.extract_ssc_timing(chart_data)
        elif chart_data.format == '.sm':
            # Standard SM timing: global BPM/stops
            return self.extract_sm_timing(chart_data)
        else:  # .dwi
            # Legacy DWI timing: simpler model
            return self.extract_dwi_timing(chart_data)

    def normalize_note_types(self, raw_notes: str, format: str) -> StandardNotes:
        # Convert format-specific note representations to unified format
        # Handle format differences in holds, rolls, mines
        # Account for format-specific note type availability
```

#### 5.2 Advanced Features (Secondary)
- **Foot positioning analysis**: Simulate player movement
- **Reading complexity**: Visual clustering metrics
- **Stamina requirements**: Sustained difficulty periods
- **Technical skill requirements**: Specific pattern categories

### 6. Quality Assurance

#### 6.1 Validation Methods
1. **Cross-validation**: Ensure generalization across song packs
2. **Human validation**: Expert player rating comparison
3. **Consistency checks**: Rating stability across similar charts
4. **Edge case handling**: Unusual charts and patterns

#### 6.2 Rating Calibration
- **Reference Charts**: Establish benchmark difficulties
- **Player Skill Curves**: Account for skill development
- **Community Feedback**: Incorporate player ratings
- **Iterative Refinement**: Continuous model improvement

### 7. Expected Outcomes

#### 7.1 Primary Goals
- **Unified Rating System**: Single consistent 1-20 scale across all historical series
- **Scale Translation**: Accurate conversion between DDR, ITG, and modern scales
- **Multi-Format Support**: Seamless handling of .sm, .ssc, and .dwi files
- **Improved Player Experience**: Predictable difficulty progression regardless of source
- **Automated Rating**: Instant ratings for new charts with scale context

#### 7.2 Scale-Specific Benefits
- **Historical Accuracy**: Preserve the intent of original rating scales
- **Rating Creep Correction**: Account for systematic underrating in ITG series
- **Cross-Series Validation**: Enable comparison of charts from different eras
- **Expert Validation**: Ratings validated by players familiar with all scales

#### 7.3 Secondary Benefits
- **Intelligent Chart Recommendation**: Scale-aware suggestions based on player skill
- **Smart Pack Organization**: Sort mixed-era collections coherently
- **Creator Education**: Help new chart creators understand historical context
- **Advanced Analytics**: Series-specific difficulty trends and evolution

### 8. Technical Requirements

#### 8.1 Development Environment
- Python 3.8+ with scikit-learn, tensorflow/pytorch
- Jupyter notebooks for experimentation
- Version control with Git
- Docker for reproducible environments

#### 8.2 Data Storage
- Processed features in structured format (HDF5/Parquet)
- Raw chart cache for reprocessing
- Model versioning and experiment tracking
- Results database for validation

#### 8.3 Computational Requirements
- GPU acceleration for deep learning models
- Parallel processing for feature extraction
- Memory efficient processing for large datasets
- Scalable architecture for future expansion

## Next Steps

1. **Implement Chart Parser**: Start with robust .sm file parsing
2. **Feature Engineering**: Develop and test feature extraction pipeline
3. **Baseline Models**: Train simple models to establish performance floor
4. **Expert Validation**: Gather ground truth ratings from skilled players
5. **Iterative Improvement**: Continuously refine based on validation results

This system will provide a foundation for consistent difficulty rating across your entire StepMania collection while being extensible for future enhancements and new chart formats.