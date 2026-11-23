"""Counts-only report for the leader master table (Step 14A, `make leader-master`).

No names, ids, links or reversible references appear here: counts only, with '<5' under
the disclosure minimum.
"""
from __future__ import annotations

from collections.abc import Sequence

import pandas as pd

from src.eda_common import EdaSettings, show_count
from src.harmonise_report import _fmt, _pct, _table
from src.leader_ladder import AMBIGUOUS, COMPANY_NAME, DOMAIN, NAME_EXACT, NAME_LOOSE, NONE

MATCH_ORDER = (NAME_EXACT, NAME_LOOSE, COMPANY_NAME, DOMAIN, AMBIGUOUS, NONE)


def _safe_count(frame: pd.DataFrame, mask: pd.Series) -> str:
    return _fmt(int(mask.sum()))


def render_report(
    frame: pd.DataFrame,
    excluded_ambiguous_keys: int,
    settings: EdaSettings,
) -> str:
    """Counts-only Markdown report for leader_master.md.

    Parameters
    ----------
    frame:                   the full master frame (one row per leader)
    excluded_ambiguous_keys: name keys shared inside one source (get no id; counted here)
    settings:                EDA settings (min_posts, disclosure_min, ...)
    """
    disc = settings.disclosure_min
    min_posts = settings.min_posts

    n = len(frame)

    # --- source overlap ---
    has_posts = frame["in_posts"].astype(bool)
    has_roster = frame["in_roster"].astype(bool)
    has_summaries = frame["in_summaries"].astype(bool)
    has_company = frame["in_company"].astype(bool)

    n_posts = int(has_posts.sum())
    n_roster = int(has_roster.sum())
    n_summaries = int(has_summaries.sum())
    n_company = int(has_company.sum())

    # --- post counts ---
    raw_cells = frame["raw_post_cells"].astype(int)
    with_posts = int((raw_cells > 0).sum())
    without_posts = n - with_posts
    with_min = int((raw_cells >= min_posts).sum())

    # --- match method counts ---
    mm = frame["match_method"]
    mm_counts = {m: int((mm == m).sum()) for m in MATCH_ORDER}

    # --- Company_Data columns coverage ---
    has_company_data = int((mm.isin([NAME_EXACT, NAME_LOOSE, COMPANY_NAME, DOMAIN])).sum())

    # added by company_name or domain steps (beyond name-only)
    added_by_step3 = int((mm.isin([COMPANY_NAME, DOMAIN])).sum())

    # --- blanks ---
    has_cn = frame["has_company_name"].astype(bool)
    has_dom = frame["has_domain"].astype(bool)
    both_blank = int((~has_cn & ~has_dom).sum())
    still_ambiguous = mm_counts[AMBIGUOUS]

    # --- 15+ raw cells ---
    at_15 = int((raw_cells >= 15).sum())

    # protect small cells
    def _p(count: int) -> str:
        return show_count(count, disc)

    sections = [
        "# Leader master table (Step 14A)",
        "",
        "Universe: every distinct leader key across the four sources (post sheets, roster, "
        "wordcount summaries, Company_Data). The post-based analysis still needs at least "
        f"{min_posts} raw post cells. Counts only: no names, no ids, no workbook or sheet "
        "references. The row-level table is `data/interim/leader_master.csv` (git-ignored).",
        "",
        "Information in this report is relayed from `data/interim` files; it was not changed here.",
        "",
        f"- Universe size (all four sources): **{n:,}**",
        f"- Keys excluded (shared inside one source, no id assigned): {_p(excluded_ambiguous_keys)}",
        "",
        "## Source overlap",
        "",
        *_table(
            ("Source", "Leaders"),
            [
                ("post sheets", _p(n_posts)),
                ("roster", _p(n_roster)),
                ("wordcount summaries", _p(n_summaries)),
                ("Company_Data", _p(n_company)),
                ("universe (union)", _fmt(n)),
            ],
        ),
        "",
        "## Leaders with posts versus without",
        "",
        *_table(
            ("Group", "Leaders"),
            [
                (f"with at least 1 raw post cell", _p(with_posts)),
                (f"with at least {min_posts} raw post cells (post-analysis denominator)", _p(with_min)),
                ("with no raw post cell", _p(without_posts)),
                ("all", _fmt(n)),
            ],
        ),
        "",
        "## Match method (Company_Data matching ladder)",
        "",
        *_table(
            ("Match method", "Leaders"),
            [(m, _p(mm_counts[m])) for m in MATCH_ORDER],
        ),
        "",
        f"- Leaders with Company_Data columns attached: {_p(has_company_data)}",
        f"- Added by company-name or domain step (over name-only): {_p(added_by_step3)}",
        "",
        "## Completeness",
        "",
        f"- Leaders with Company_Data columns: {_p(has_company_data)}",
        f"- Leaders with both company name and domain blank: {_p(both_blank)}",
        f"- Still ambiguous (not resolved): {_p(still_ambiguous)}",
        "",
        "## Post-analysis denominator (leaders with 15+ raw cells)",
        "",
        *_table(
            ("Group", "Leaders (15+ raw cells)"),
            [
                ("name_exact", _p(int(((mm == NAME_EXACT) & (raw_cells >= 15)).sum()))),
                ("name_loose", _p(int(((mm == NAME_LOOSE) & (raw_cells >= 15)).sum()))),
                ("company_name", _p(int(((mm == COMPANY_NAME) & (raw_cells >= 15)).sum()))),
                ("domain", _p(int(((mm == DOMAIN) & (raw_cells >= 15)).sum()))),
                ("ambiguous", _p(int(((mm == AMBIGUOUS) & (raw_cells >= 15)).sum()))),
                ("none", _p(int(((mm == NONE) & (raw_cells >= 15)).sum()))),
                ("all with 15+", _p(at_15)),
            ],
        ),
        "",
        f"The {min_posts}-post threshold comes from `configs/thresholds.yaml`. "
        "Raw post cells stand in for posts until segmentation is confirmed (G1 unsigned).",
        "",
    ]

    return "\n".join(sections) + "\n"
