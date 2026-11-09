"""Draw a seeded random set of cells flagged `Hinglish` for a human precision check (`make hinglish-check`).

The output is git-ignored (it holds post text). The human fills `human_right` with 1 (a person would call it
Hindi in Latin letters) or 0; the committed report then states only the count right. This module draws the
cells and never judges them, and it never overwrites a file a human may have started filling in.
"""
from __future__ import annotations

import logging
import random
import sys
from collections.abc import Sequence
from pathlib import Path

import pandas as pd
import yaml

from src.post_fields import HINGLISH
from src.reaction_count_check import spreadsheet_safe
from src.verify_raw import DEFAULT_RAW_DIR, ManifestMismatch
from src.verify_raw import run as verify_raw

logger = logging.getLogger(__name__)

DEFAULT_THRESHOLDS_PATH = Path("configs/thresholds.yaml")
DEFAULT_CLEAN_PATH = Path("data/interim/posts_clean.csv")
DEFAULT_CHECK_PATH = Path("data/derived/hinglish_check_30.csv")
CHECK_COLUMNS = ["n", "leader_id", "ref", "post_text", "human_right"]
_KEYS = ("hinglish_check_cells", "hinglish_check_seed")


def draw_cells(clean: pd.DataFrame, n: int, seed: int) -> pd.DataFrame:
    """`n` flagged cells (all of them if fewer); sorted before drawing so the seed alone decides the result."""
    flagged = clean[clean["language"] == HINGLISH]
    ordered = flagged.sort_values(["leader_id", "workbook", "sheet_idx", "source_row"], kind="stable")
    ordered = ordered.reset_index(drop=True)
    picks = sorted(random.Random(seed).sample(range(len(ordered)), min(n, len(ordered))))
    rows = [
        (
            str(i + 1),
            row.leader_id,
            f"{row.workbook}#{row.sheet_idx}:r{row.source_row}",
            spreadsheet_safe(row.post_text_clean),
            "",
        )
        for i, row in enumerate(ordered.iloc[picks].itertuples(index=False))
    ]
    return pd.DataFrame(rows, columns=CHECK_COLUMNS)


def _load_keys(path: Path) -> tuple[int, int]:
    values = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    for key in _KEYS:
        if key not in values:
            raise ValueError(f"{path}: missing key {key}")
    return int(values["hinglish_check_cells"]), int(values["hinglish_check_seed"])


def run(
    raw_dir: Path = DEFAULT_RAW_DIR,
    clean_path: Path = DEFAULT_CLEAN_PATH,
    check_path: Path = DEFAULT_CHECK_PATH,
    thresholds_path: Path = DEFAULT_THRESHOLDS_PATH,
) -> int:
    """Verify the raw manifest, draw the cells, write the check file; 0 on success."""
    try:
        logger.info("manifest %s for %s", verify_raw(raw_dir), raw_dir)
        if check_path.exists():
            raise ValueError(f"{check_path} exists; it may hold human work, so it is not overwritten")
        n, seed = _load_keys(thresholds_path)
        drawn = draw_cells(pd.read_csv(clean_path, dtype=str, keep_default_na=False), n, seed)
    except (ManifestMismatch, FileNotFoundError, ValueError) as error:
        logger.error("hinglish-check FAILED: %s", error)
        return 1
    check_path.parent.mkdir(parents=True, exist_ok=True)
    drawn.to_csv(check_path, index=False)
    logger.info("wrote %s (%d cells)", check_path, len(drawn))
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    return run()


if __name__ == "__main__":
    sys.exit(main())
