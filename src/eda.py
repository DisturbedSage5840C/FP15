"""Exploratory data analysis of the data we already have, to document its limits (`make eda`).

Assembles six counts-only sections into reports/eda_limitations.md: coverage, gaps, balance, distribution of cells per
leader, quality issues already found, and possible selection bias. The raw manifest is verified first. Post text, links
and profile urls are dropped when the posts table is read, so they are never held in memory. No network, no scraping,
nothing is filled in or guessed, and no gate is signed off.
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

import pandas as pd

from src.eda_balance import balance_counts, render_balance
from src.eda_common import DEFAULT_THRESHOLDS_PATH, EdaSettings, load_eda_settings
from src.eda_coverage import coverage_counts, render_coverage
from src.eda_distribution import distribution_counts, render_distribution
from src.eda_gaps import gap_counts, render_gaps
from src.eda_quality import quality_counts, render_quality
from src.eda_selection import render_selection, selection_counts
from src.harmonise import DEFAULT_INTERIM_DIR
from src.verify_raw import DEFAULT_RAW_DIR, ManifestMismatch
from src.verify_raw import run as verify_raw

logger = logging.getLogger(__name__)

DEFAULT_REPORT_PATH = Path("reports/eda_limitations.md")
# Interim table name -> file. Each is read whole as strings, except the columns in NEVER_LOADED.
INTERIM_FILES = {
    "posts": "harmonised_posts.csv",
    "leaders": "leader_table.csv",
    "proposal": "leader_id_proposal.csv",
    "matches": "id_matches.csv",
    "clean": "posts_clean.csv",
    "company": "company_data.csv",
}
NEVER_LOADED = frozenset({"post_text", "post_text_clean", "link", "profile_url"})


def _header(settings: EdaSettings) -> list[str]:
    return [
        "# EDA: limits of the data we already have",
        "",
        "Counts and aggregates only: no names, post text, links, emails or leader ids appear here. A count below "
        f'{settings.disclosure_min} shows as "<5" instead of its number, and a group with fewer than '
        f"{settings.model_min} leaders is flagged as too small to model.",
        "",
        "Every statement is about the image projected in public posts, never about personality. Raw post cells stand "
        "in for posts until G1 is signed (G1 is the segmentation gate), so every count of leaders at the "
        f"{settings.min_posts}-post cut is a count of raw cells, and the cut once segmented is not computed. Nothing is "
        "filled in or guessed: missing stays missing. No gate is signed off by this report. No scraping and no "
        "network were used, and scraping_approved stays false.",
        "",
    ]


def build_report(
    posts: pd.DataFrame,
    leaders: pd.DataFrame,
    proposal: pd.DataFrame,
    matches: pd.DataFrame,
    clean: pd.DataFrame,
    company: pd.DataFrame,
    settings: EdaSettings,
) -> str:
    """The whole report as Markdown text, ending in one newline (no input is changed)."""
    bands = settings.size_bands
    sections = (
        render_coverage(coverage_counts(proposal, leaders, settings.min_posts), settings),
        render_gaps(gap_counts(posts, proposal, company, settings.min_posts), settings),
        render_balance(balance_counts(posts, proposal, company, settings.min_posts, bands), settings),
        render_distribution(distribution_counts(posts, settings.min_posts), settings),
        render_quality(quality_counts(posts, leaders, proposal, matches, clean), settings),
        render_selection(selection_counts(posts, proposal, company, bands), settings),
    )
    lines = [*_header(settings), *(line for section in sections for line in section)]
    return "\n".join(lines).rstrip("\n") + "\n"


def _read_inputs(interim_dir: Path) -> dict[str, pd.DataFrame]:
    """Read each interim table as strings; blank cells stay "" and the NEVER_LOADED columns are skipped."""
    return {
        name: pd.read_csv(
            interim_dir / file, dtype=str, keep_default_na=False, usecols=lambda column: column not in NEVER_LOADED
        )
        for name, file in INTERIM_FILES.items()
    }


def run(
    raw_dir: Path = DEFAULT_RAW_DIR,
    interim_dir: Path = DEFAULT_INTERIM_DIR,
    report_path: Path = DEFAULT_REPORT_PATH,
    thresholds_path: Path = DEFAULT_THRESHOLDS_PATH,
) -> int:
    """Verify the raw manifest, build the report, write it; 0 on success, 1 on a clean failure (nothing written)."""
    try:
        logger.info("manifest %s for %s", verify_raw(raw_dir), raw_dir)
        settings = load_eda_settings(thresholds_path)
        text = build_report(settings=settings, **_read_inputs(interim_dir))
    except (ManifestMismatch, FileNotFoundError, ValueError, KeyError) as error:
        logger.error("eda FAILED: %s", error)
        return 1
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(text, encoding="utf-8")
    logger.info("wrote %s", report_path)
    return 0


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    return run()


if __name__ == "__main__":
    sys.exit(main())
