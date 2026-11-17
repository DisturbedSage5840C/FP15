"""Counts-only report on the G1 segmentation sample (`make segmentation-sample-report`).

Reads the git-ignored 200-cell sample and the raw cells, and writes counts and the seed only: no cell references,
no leader ids, no post text. It never changes the sample file, so human counts already entered are safe.
It holds no machine count and does not sign off G1: that is a human job (see docs/decisions.md).
"""
from __future__ import annotations

import logging
import sys
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from src.harmonise import DEFAULT_INTERIM_DIR
from src.harmonise_report import _fmt, _table
from src.id_key import MissingIdKey
from src.reaction_count_check import _read_posts
from src.segment import (
    DEFAULT_SAMPLE_PATH,
    SegmentSettings,
    check_frame,
    load_settings,
    raw_cell_frame,
    select_check_cells,
)
from src.verify_raw import DEFAULT_RAW_DIR, ManifestMismatch
from src.verify_raw import run as verify_raw

logger = logging.getLogger(__name__)

DEFAULT_REPORT_PATH = Path("reports/segmentation_sample.md")
SAMPLE_REQUIRED_COLUMNS = ("ref", "leader_id", "human_post_count")
YES, NO = "yes", "no"


@dataclass(frozen=True)
class SampleCounts:
    """Counts about the sample file and the cells it was drawn from; nothing here identifies a cell."""

    raw_cells: int
    leaders: int
    required: int
    seed: int
    sample_cells: int
    sample_leaders: int
    human_counts_filled: int
    matches_fresh_draw: bool


def sample_counts(frame: pd.DataFrame, sample: pd.DataFrame, settings: SegmentSettings) -> SampleCounts:
    """Count the sample against a fresh draw from the same seed (the draw is deterministic)."""
    missing = [name for name in SAMPLE_REQUIRED_COLUMNS if name not in sample.columns]
    if missing:
        raise ValueError(f"sample file: missing columns {', '.join(missing)}")
    fresh = check_frame(select_check_cells(frame, settings.check_cells, settings.seed))
    filled = [value for value in sample["human_post_count"].astype(str) if value.strip()]
    return SampleCounts(
        raw_cells=len(frame),
        leaders=len(set(frame["leader_key"])),
        required=settings.check_cells,
        seed=settings.seed,
        sample_cells=len(sample),
        sample_leaders=len(set(sample["leader_id"])),
        human_counts_filled=len(filled),
        matches_fresh_draw=set(sample["ref"]) == set(fresh["ref"]),
    )


# ---- output -----------------------------------------------------------------------------------


def render_report(counts: SampleCounts) -> str:
    """Counts-only Markdown: no references, no ids, no cell text."""
    rows = [
        ("Raw cells with a leader and some text", _fmt(counts.raw_cells)),
        ("Leaders with at least one such cell", _fmt(counts.leaders)),
        ("Cells required for the check", _fmt(counts.required)),
        ("Seed", str(counts.seed)),
        ("Cells in the sample file", _fmt(counts.sample_cells)),
        ("Leaders in the sample file", _fmt(counts.sample_leaders)),
        ("Cells with a human count filled in", _fmt(counts.human_counts_filled)),
        ("Sample matches a fresh draw from the seed", YES if counts.matches_fresh_draw else NO),
    ]
    lines = [
        "# Segmentation sample for gate G1",
        "",
        "Counts only: no cell references, no ids, no post text. The sample itself is "
        "`data/derived/segmentation_check_200.csv` (git-ignored, it holds post text).",
        "",
        *_table(("Item", "Value"), rows),
        "",
        "The draw takes one cell per leader where it can, from sorted cells with the seed above, so the same seed "
        "gives the same sample. The sample holds no machine count, so the human count is blind.",
        "",
        "G1 is not signed. A person counts the posts in each cell, then `make segmentation-score` compares those "
        "counts with the segmenter. The sign-off line goes in `docs/decisions.md` and is a human job.",
        "",
    ]
    return "\n".join(lines)


# ---- entry points -----------------------------------------------------------------------------


def run(
    raw_dir: Path = DEFAULT_RAW_DIR,
    interim_dir: Path = DEFAULT_INTERIM_DIR,
    sample_path: Path = DEFAULT_SAMPLE_PATH,
    report_path: Path = DEFAULT_REPORT_PATH,
    settings: SegmentSettings | None = None,
) -> int:
    """Verify the raw manifest, count the sample, write the report; 0 on success, 1 on a clean failure."""
    try:
        logger.info("manifest %s for %s", verify_raw(raw_dir), raw_dir)
        if not sample_path.exists():
            raise FileNotFoundError(f"{sample_path} not found: run `make segmentation-sample` first")
        chosen = load_settings() if settings is None else settings
        frame = raw_cell_frame(_read_posts(interim_dir))
        sample = pd.read_csv(sample_path, dtype=str, keep_default_na=False)
        report = render_report(sample_counts(frame, sample, chosen))
    except (ManifestMismatch, FileNotFoundError, ValueError, MissingIdKey) as error:
        logger.error("segmentation-sample-report FAILED: %s", error)
        return 1
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report, encoding="utf-8")
    logger.info("wrote %s", report_path)
    return 0


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    return run()


if __name__ == "__main__":
    sys.exit(main())
