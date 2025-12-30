# StepML: Machine Learning-Based Step Chart Analysis & Difficulty Rating System

This project is a machine learning approach to analyze StepMania step charts
and provide consistent difficulty ratings across all songs. The system extracts
meaningful features from .sm, .ssc, and .dwi files and use them to train models
for accurate difficulty prediction and rating standardization across multiple
historical rating scales.

It was vibe-coded using Claude Sonnet and Haiku 4.5 models, with human guidance
at important points along the way. The result is a system to produce
consistently scaled ratings across all stepcharts in your collection.

## Quick start

* Download the calculated ratings from the
  [Releases](https://github.com/ctrueden/stepml/releases) page.

* Clone my [fork of itgmania](https://github.com/ctrueden/itgmania)
  and build it from source.

* Unzip the downloaded `calculated_ratings-YYYYMMDD.zip` in the itgmania
  working copy's `Data` folder.

Now, when you launch itgmania with the built binary, it should pick up
the `calculated_ratings.json` values and prefer them to the stepchart ones.
If not, double check that songpack folder names match the ones used in the
`calculated_ratings.json` file.

## End-to-End Workflow

Want to generate difficulty ratings from your own StepMania chart collection? Here's the complete workflow:

### Prerequisites

Your directory structure should look like this:

```
stepmania/
├── stepml/              # This repository
├── Songs/               # Your StepMania song packs
│   ├── DDR 1st Mix/
│   ├── ITG 1/
│   ├── Custom Pack 1/
│   └── ...
└── Save/                # (Optional) For performance enrichment
    └── LocalProfiles/
        └── 00000000/
            └── Stats.xml
```

### Step 1: Generate Dataset

Process all your charts and extract features:

```bash
uv run generate-dataset
```

**Options:**
- `--songs-dir PATH` - Path to Songs directory (default: `../Songs`)
- `--output-dir PATH` - Output directory (default: `./data/processed`)
- `--stats-file PATH` - Path to Stats.xml for performance enrichment
- `--no-performance` - Disable performance data enrichment
- `--normalization-scale {classic_ddr,modern_ddr,itg}` - Target rating scale (default: `modern_ddr`)
  - `classic_ddr`: 1-10 scale (DDR 1st through Extreme)
  - `modern_ddr`: 1-20 scale (DDR X onwards) - **recommended**
  - `itg`: 1-12 scale (In The Groove)
- `--verbose` - Show progress for every file

**Output:**
- `data/processed/dataset.csv` - Full dataset in CSV format
- `data/processed/dataset.parquet` - Full dataset in Parquet format (more efficient)
- `data/processed/generation_stats.json` - Statistics about the generation process

**Example with custom scale:**
```bash
# Generate dataset normalized to ITG scale
uv run generate-dataset --normalization-scale itg
```

**Note:** The normalization scale affects the target rating values in the dataset. If you change the scale, you'll need to retrain your models since the target value range changes (Classic DDR: 1-10, Modern DDR: 1-20, ITG: 1-12).

### Step 2: Train ML Models

Train regression models on the extracted features:

```bash
uv run train-models
```

**What this does:**
- Trains multiple regression models (Ridge, Random Forest, Gradient Boosting, etc.)
- Performs cross-validation to evaluate model performance
- Saves the best-performing model to `data/models/best_model.pkl`
- Generates performance reports in `data/models/`

**Output:**
- `data/models/best_model.pkl` - Trained model (pickled)
- `data/models/model_comparison.csv` - Performance comparison of all models
- `data/models/training_report.txt` - Detailed training report

### Step 3: Generate Calculated Ratings

Use the trained model to predict ratings for all charts:

```bash
uv run generate-ratings
```

**What this does:**
- Loads the trained model from `data/models/best_model.pkl`
- Predicts ratings for all charts in your dataset
- Generates `calculated_ratings.json` in StepMania-compatible format

**Output:**
- `data/output/calculated_ratings.json` - Ratings in JSON format to use with itgmania
- `data/output/ratings_with_predictions.csv` - Full dataset with predicted ratings

**Format of calculated_ratings.json:**
```json
{
  "Songs/Pack Name/Song Name/chart.ssc": {
    "single_beginner": 3.2,
    "single_easy": 5.8,
    "single_medium": 8.4,
    "single_hard": 11.2,
    "single_challenge": 14.7
  }
}
```

### Step 4: Use the Ratings

Copy `calculated_ratings.json` to your StepMania/itgmania `Data` folder:

```bash
cp data/output/calculated_ratings.json ../Data/
```

Launch itgmania (using the [fork that supports this feature](https://github.com/ctrueden/itgmania)) and it will use the calculated ratings instead of the chart-specified ones.

## Playlist Generation

Once you have calculated ratings, you can generate course playlists:

```bash
uv run generate-playlists
```

**What this does:**
- Creates random course playlists based on difficulty ranges
- Generates `.crs` files in `data/courses/`
- Organizes courses by difficulty tier (beginner, intermediate, advanced, expert)

**Output:**
- `data/courses/*.crs` - StepMania course files
- Each course contains 4-5 songs within a similar difficulty range

**Using the playlists:**
```bash
# Copy courses to your StepMania Courses directory
cp data/courses/*.crs ../Courses/
```

Launch StepMania and access the courses through the "Course Mode" menu (e.g. "Marathon" mode if using [Simply Love](https://github.com/ctrueden/Simply-Love-SM5) theme).

## Available Entry Points

Full list of available commands:

| Command                    | Purpose                                |
|----------------------------|----------------------------------------|
| uv run generate-baseline   | Regenerate regression test baseline    |
| uv run generate-dataset    | Process charts and create ML dataset   |
| uv run generate-ratings    | Generate calculated difficulty ratings |
| uv run generate-playlists  | Create StepMania course playlists      |
| uv run train-models        | Train ML models on dataset             |
| uv run sync-favorites      | Sync StepMania favorites lists         |
| uv run analyze-performance | Analyze performance-enriched dataset   |

For technical details, see documentation in the `doc` directory.

## License

All copyright disclaimed; see UNLICENSE.

## Support

This is a personal project I created to scratch my own itch.
If you need help with it, your first line of attack should be
[feeding the codebase into an LLM](https://code.claude.com/docs/en/quickstart)
and asking it for clarification.

If you are still stuck after doing that, you are welcome to file an
issue and I'll try to help. PRs are also welcome, although for big
changes you might be better off forking.
