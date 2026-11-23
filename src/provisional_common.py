"""Shared pieces of the provisional run (step 14): the banner and the banner-first CSV reader and writer.

Every output of the provisional stages, tracked or git-ignored, starts with the same banner so nobody can read a
number from it without the limits. Nothing here decides what a construct means.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

BANNER = (
    "PROVISIONAL. G1 unsigned so raw cells stand in for posts; English-only pronoun counts; no gold-set check; "
    "exploratory, not pre-registered. Claims are about the image projected in public posts, never personality. "
    "The I-rate is one signal, not a narcissism score."
)
COMMENT_PREFIX = "# "
DEFAULT_DERIVED_DIR = Path("data/derived")
DEFAULT_MEASURES_PATH = DEFAULT_DERIVED_DIR / "provisional_post_measures.csv"
DEFAULT_REPORT_DIR = Path("reports")


def write_banner_csv(frame: pd.DataFrame, path: Path) -> None:
    """Write the frame as CSV under a one-line banner comment. The parent folder is created."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        handle.write(f"{COMMENT_PREFIX}{BANNER}\n")
        frame.to_csv(handle, index=False)


def read_banner_csv(path: Path) -> pd.DataFrame:
    """Read a file written by `write_banner_csv`; ids are read as text, blanks stay missing."""
    return pd.read_csv(path, comment="#", dtype={"leader_id": str, "post_id": str})
