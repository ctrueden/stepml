# stepml project notes

## Running Python

Always use `uv run python` (not plain `python3`) to run Python in this project.
The project uses a uv-managed virtual environment.

Example:
```
uv run python -c "import pandas; ..."
uv run python src/stepml/generate_dataset.py
```

## Project shortcuts

Use `make run` to compute calculated ratings for all rating scales.
Use `make test` to run the test suite.
