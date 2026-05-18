#!/usr/bin/env bash
# Query calculated_ratings.csv interactively via fzf.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CSV="$SCRIPT_DIR/../data/calculated_ratings/calculated_ratings.csv"

if [[ ! -f "$CSV" ]]; then
    echo "No calculated_ratings.csv found at: $CSV" >&2
    exit 1
fi

# Format: PACK | TITLE | TYPE | DIFFICULTY | ORIG→CALC (or just CALC if equal)
awk -F, 'NR > 1 {
    pack   = $2
    title  = $3
    ctype  = $4
    diff   = $5
    orig   = $6
    calc   = $7
    rating = (orig == calc) ? calc : orig "→" calc
    printf "%-30s  %-40s  %-14s  %-10s  %s\n", pack, title, ctype, diff, rating
}' "$CSV" | fzf \
    --header="$(printf '%-30s  %-40s  %-14s  %-10s  %s' PACK TITLE TYPE DIFFICULTY RATING)" \
    --header-lines=0 \
    --layout=reverse \
    --no-sort \
    "$@"
