#!/bin/sh

if ! command -v uv >/dev/null 2>&1; then
  echo "Please install uv (https://docs.astral.sh/uv/getting-started/installation/)."
  exit 1
fi

# Define the three normalization scales
SCALES="itg modern_ddr classic_ddr"

# Process each scale
for scale in $SCALES; do
  echo "========================================="
  echo "Processing scale: $scale"
  echo "========================================="

  # Define output directories for this scale
  PROCESSED_DIR="data/${scale}/processed"
  MODELS_DIR="data/${scale}/models"
  OUTPUT_DIR="data/${scale}/output"

  echo ""
  echo "Step 1/3: Generating dataset for $scale..."
  uv run generate-dataset \
    --normalization-scale "$scale" \
    --output-dir "$PROCESSED_DIR"

  if [ $? -ne 0 ]; then
    echo "Error: Dataset generation failed for $scale"
    exit 1
  fi

  echo ""
  echo "Step 2/3: Training models for $scale..."
  uv run train-models \
    --dataset "$PROCESSED_DIR/dataset.parquet" \
    --output-dir "$MODELS_DIR"

  if [ $? -ne 0 ]; then
    echo "Error: Model training failed for $scale"
    exit 1
  fi

  echo ""
  echo "Step 3/3: Generating ratings for $scale..."
  mkdir -p "$OUTPUT_DIR"
  uv run generate-ratings \
    --dataset "$PROCESSED_DIR/dataset.parquet" \
    --model-dir "$MODELS_DIR" \
    --output "$OUTPUT_DIR/calculated_ratings.json"

  if [ $? -ne 0 ]; then
    echo "Error: Ratings generation failed for $scale"
    exit 1
  fi

  echo ""
  echo "Completed $scale successfully!"
  echo ""
done

echo "========================================="
echo "All scales processed successfully!"
echo "========================================="
echo ""
echo "Output locations:"
for scale in $SCALES; do
  echo "  $scale: data/${scale}/output/calculated_ratings.json"
done
echo ""
