"""
Scrape authoritative classic-DDR foot ratings from DDRFreak.

DDRFreak (https://www.ddrfreak.com/versions/songlist.php?mix=ID) lists the
original arcade foot ratings for every classic DDR / Dancing Stage mix. We use
these as ground-truth training labels for classic packs whose in-file ratings
have been partially modernized (see utils/ddrfreak_ratings.py).

This downloads the song list for every mix referenced by ddrfreak_mixes.yaml
and writes a flat table to ddrfreak_ratings.csv:

    mix_id, title, title_key, artist, chart_type, difficulty, rating

title_key is a normalized join key (lowercased, alphanumerics only) used to
match against simfile titles. Re-run this only when the mix mapping changes;
the resulting CSV is committed so dataset generation needs no network access.

Usage:
    uv run scrape-ddrfreak
"""

import argparse
import csv
import html
import logging
import re
import sys
import urllib.request
from pathlib import Path

import yaml

from stepml.utils import get_stepml_root

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

SONGLIST_URL = "https://www.ddrfreak.com/versions/songlist.php?mix={mix_id}"
USER_AGENT = "Mozilla/5.0 (stepml ddrfreak scraper)"

# DDRFreak difficulty column label -> our DifficultyType value.
DIFFICULTY_MAP = {
    "beginner": "Beginner",
    "basic": "Easy",
    "light": "Easy",
    "trick": "Medium",
    "standard": "Medium",
    "another": "Medium",
    "maniac": "Hard",
    "heavy": "Hard",
    "ssr": "Hard",
    "challenge": "Challenge",
    "oni": "Challenge",
}

# DDRFreak mode group label -> our ChartType value. Solo mixes label their
# columns "4 PANEL" (standard 4-arrow) and "6 PANEL" (solo); "3 PANEL" has no
# StepMania equivalent and is left unmapped.
MODE_MAP = {
    "single": "dance-single",
    "double": "dance-double",
    "solo": "dance-solo",
    "4 panel": "dance-single",
    "6 panel": "dance-solo",
}


def title_key(title: str) -> str:
    """Normalize a song title to a robust match key (alphanumerics, lowercase)."""
    return re.sub(r"[^a-z0-9]", "", html.unescape(title).lower())


def _strip_tags(cell: str) -> str:
    return re.sub(r"<[^>]+>", "", html.unescape(cell)).strip()


def _cells(row_html: str):
    """Return list of (text, colspan, rowspan) for each cell in a table row."""
    out = []
    for m in re.finditer(r"<t[dh]([^>]*)>(.*?)</t[dh]>", row_html, re.S):
        attrs, body = m.group(1), m.group(2)
        colspan = (
            int((re.search(r"colspan=(\d+)", attrs) or [0, 1])[1])
            if "colspan" in attrs
            else 1
        )
        rowspan = (
            int((re.search(r"rowspan=(\d+)", attrs) or [0, 1])[1])
            if "rowspan" in attrs
            else 1
        )
        out.append((_strip_tags(body), colspan, rowspan))
    return out


def parse_songlist(page: str):
    """
    Parse a DDRFreak song-list page.

    Returns (columns, rows) where columns is an ordered list of
    (chart_type, difficulty) and rows is a list of (title, artist, [rating_cells]).
    """
    table_m = re.search(
        r'<table[^>]*class=["\']?songlist["\']?[^>]*>(.*?)</table>', page, re.S | re.I
    )
    if not table_m:
        raise ValueError("no songlist table found")
    table = table_m.group(1)

    rows_html = re.findall(r"<tr[^>]*>(.*?)</tr>", table, re.S)
    if len(rows_html) < 3:
        raise ValueError("songlist table too short")

    # Header row 1: leading rowspan=2 columns (spacer/Song/Artist) then mode
    # groups (Single/Double/...) each spanning `colspan` difficulty columns.
    h1 = _cells(rows_html[0])
    n_lead = sum(1 for _, _, rs in h1 if rs >= 2)
    modes = [(text, colspan) for text, colspan, rs in h1 if rs < 2]

    # Header row 2: difficulty labels in order across all mode groups.
    h2 = [text for text, _, _ in _cells(rows_html[1])]

    columns = []
    di = 0
    for mode_text, span in modes:
        chart_type = MODE_MAP.get(mode_text.strip().lower())
        for _ in range(span):
            diff_label = h2[di].strip().lower() if di < len(h2) else ""
            difficulty = DIFFICULTY_MAP.get(diff_label)
            columns.append((chart_type, difficulty))
            di += 1

    data_rows = []
    for row_html in rows_html[2:]:
        cells = [
            _strip_tags(c) for c in re.findall(r"<td[^>]*>(.*?)</td>", row_html, re.S)
        ]
        if len(cells) <= n_lead:
            continue
        title = cells[1] if n_lead >= 2 else cells[0]
        artist = cells[2] if n_lead >= 3 else ""
        ratings = cells[n_lead:]
        if not title:
            continue
        data_rows.append((title, artist, ratings))

    return columns, data_rows


def fetch(mix_id: int) -> str:
    url = SONGLIST_URL.format(mix_id=mix_id)
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8", errors="replace")


def scrape(mix_ids, output_path: Path):
    records = []
    for mix_id in sorted(mix_ids):
        logger.info(f"Fetching mix {mix_id}...")
        try:
            page = fetch(mix_id)
            columns, rows = parse_songlist(page)
        except Exception as e:
            logger.warning(f"  Failed to parse mix {mix_id}: {e}")
            continue

        n = 0
        for title, artist, ratings in rows:
            for (chart_type, difficulty), value in zip(columns, ratings):
                if chart_type is None or difficulty is None:
                    continue
                m = re.search(r"\d+", value)
                if not m:
                    continue
                rating = int(m.group())
                if rating <= 0:
                    continue
                records.append(
                    {
                        "mix_id": mix_id,
                        "title": title,
                        "title_key": title_key(title),
                        "artist": artist,
                        "chart_type": chart_type,
                        "difficulty": difficulty,
                        "rating": rating,
                    }
                )
                n += 1
        logger.info(f"  {len(rows)} songs, {n} ratings")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "mix_id",
                "title",
                "title_key",
                "artist",
                "chart_type",
                "difficulty",
                "rating",
            ],
        )
        writer.writeheader()
        writer.writerows(records)
    logger.info(f"Wrote {len(records)} ratings to {output_path}")
    return records


def main():
    stepml_root = get_stepml_root()
    parser = argparse.ArgumentParser(
        description="Scrape classic-DDR ratings from DDRFreak"
    )
    parser.add_argument(
        "--mixes",
        type=Path,
        default=stepml_root / "ddrfreak_mixes.yaml",
        help="Path to pack->mix mapping YAML (default: ddrfreak_mixes.yaml)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=stepml_root / "ddrfreak_ratings.csv",
        help="Output CSV path (default: ddrfreak_ratings.csv)",
    )
    args = parser.parse_args()

    if not args.mixes.exists():
        logger.error(f"Mix mapping not found: {args.mixes}")
        sys.exit(1)

    with open(args.mixes) as f:
        mapping = yaml.safe_load(f) or {}
    mix_ids = sorted(set(mapping.get("mixes", {}).values()))
    if not mix_ids:
        logger.error("No mix ids found in mapping file")
        sys.exit(1)

    logger.info(f"Scraping {len(mix_ids)} mix(es): {mix_ids}")
    scrape(mix_ids, args.output)


if __name__ == "__main__":
    main()
