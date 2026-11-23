"""Provisional per-post measures (step 14, part 1): first-person singular and plural rates per 100 words.

PROVISIONAL. G1 is unsigned, so raw cells stand in for posts. The counter is `src.dict_measures.count_pronouns`
(English word lists only); this is not the final choice between it and `src.voice`. Exploratory, not pre-registered.
The output is git-ignored (data/derived), holds leader_id and post_id and numbers only, and never any text.
Claims are about the image projected in public posts. The singular rate is one signal, not a narcissism score.
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

import pandas as pd

from src.dict_measures import count_pronouns
from src.post_cleaning import DEFAULT_CLEAN_PATH
from src.post_fields import HINGLISH
from src.provisional_common import DEFAULT_MEASURES_PATH, write_banner_csv
from src.verify_raw import DEFAULT_RAW_DIR, ManifestMismatch
from src.verify_raw import run as verify_raw

logger = logging.getLogger(__name__)

POST_ID_PREFIX = "p"
POST_ID_DIGITS = 6
CELL_KEY = ("leader_id", "workbook", "sheet_idx", "source_row")
INPUT_COLUMNS = (*CELL_KEY, "post_text_clean", "language")
MEASURE_COLUMNS = ("leader_id", "post_id", "word_count", "singular_per_100", "plural_per_100", "hinglish_flag")


def _require(cells: pd.DataFrame) -> None:
    missing = [column for column in INPUT_COLUMNS if column not in cells.columns]
    if missing:
        raise ValueError(f"posts_clean is missing columns {missing}")


def _sorted_cells(cells: pd.DataFrame) -> pd.DataFrame:
    """Cells in a fixed order, so post_id does not depend on the order the file happens to hold them in."""
    keyed = cells.assign(
        _sheet=pd.to_numeric(cells["sheet_idx"], errors="coerce"),
        _row=pd.to_numeric(cells["source_row"], errors="coerce"),
    )
    ordered = keyed.sort_values(["leader_id", "workbook", "_sheet", "_row"], kind="stable")
    return ordered.drop(columns=["_sheet", "_row"]).reset_index(drop=True)


def _post_id(position: int) -> str:
    """A sequential id in the fixed cell order. It holds no file name, row number or name."""
    return f"{POST_ID_PREFIX}{position:0{POST_ID_DIGITS}d}"


def _rates(text: object) -> tuple[int, float, float]:
    """(word count, singular per 100, plural per 100); a cell with no words gives NaN rates, never zero."""
    counts = count_pronouns(text if isinstance(text, str) else "")
    if counts.word_count == 0:
        return 0, float("nan"), float("nan")
    return counts.word_count, counts.singular_per_100, counts.plural_per_100


def measure_cells(cells: pd.DataFrame) -> pd.DataFrame:
    """One row per cleaned cell: ids, word count, the two rates, and a 0/1 mark for a possible-Hinglish cell."""
    _require(cells)
    ordered = _sorted_cells(cells)
    rates = [_rates(text) for text in ordered["post_text_clean"]]
    return pd.DataFrame(
        {
            "leader_id": ordered["leader_id"],
            "post_id": [_post_id(position) for position in range(1, len(ordered) + 1)],
            "word_count": [words for words, _, _ in rates],
            "singular_per_100": [singular for _, singular, _ in rates],
            "plural_per_100": [plural for _, _, plural in rates],
            "hinglish_flag": (ordered["language"] == HINGLISH).astype(int),
        },
        columns=list(MEASURE_COLUMNS),
    )


def run(
    raw_dir: Path = DEFAULT_RAW_DIR,
    clean_path: Path = DEFAULT_CLEAN_PATH,
    out_path: Path = DEFAULT_MEASURES_PATH,
) -> int:
    """Verify the raw manifest, measure every cleaned cell, write the git-ignored file; 0 on success, 1 on failure."""
    try:
        logger.info("manifest %s for %s", verify_raw(raw_dir), raw_dir)
        cells = pd.read_csv(clean_path, dtype=str, keep_default_na=False, usecols=list(INPUT_COLUMNS))
        measured = measure_cells(cells)
    except (ManifestMismatch, FileNotFoundError, ValueError) as error:
        logger.error("provisional-measures FAILED: %s", error)
        return 1
    write_banner_csv(measured, out_path)
    logger.info("wrote %s (git-ignored; ids and numbers only)", out_path)
    return 0


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    return run()


if __name__ == "__main__":
    sys.exit(main())
