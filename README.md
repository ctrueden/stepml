# StepML: Machine Learning-Based Step Chart Analysis & Difficulty Rating System

This project is a machine learning approach to analyze StepMania step charts
and provide consistent difficulty ratings across all songs. The system extracts
meaningful features from .sm, .ssc, and .dwi files and use them to train models
for accurate difficulty prediction and rating standardization across multiple
historical rating scales.

It was vibe-coded using Claude Sonnet and Haiku 4.5 models, with human guidance
at important points along the way. The result is a system to produce
consistently scaled ratings across all stepcharts in your collection.

## Available entry points

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
feeding the codebase into an LLM and asking it for clarification.

If you are still stuck after doing that, you are welcome to file an
issue and I'll try to help. PRs are also welcome, although for big
changes you might be better off forking.
