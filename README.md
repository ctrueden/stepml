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

## Available entry points

If you want to play around with rerunning the training and data generation
on your own collection of songpacks, you can use these commands:

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
