"""EDA section 4: distribution of raw cells per leader (`make eda`).

Per leader: min, quartiles, max, and the share of all cells held by the top 10% of leaders, for every leader with at
least one raw cell and for those at the post cut. Counts only: no names, ids or references. Raw cells stand in for
posts until gate G1 is signed. A group with fewer leaders than the disclosure minimum is hidden whole, because its min
and max would be single leaders' counts.
"""
from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np
import pandas as pd

from src.company_columns import leader_post_counts
from src.eda_common import SMALL, EdaSettings
from src.eda_gaps import LEADER, TEXT_KIND, _require
from src.harmonise_report import _table

TOP_SHARE = 0.10
FLOAT_NOISE_DIGITS = 9
HIDDEN_STATISTICS = 9
POST_COLUMNS = (LEADER, TEXT_KIND)


@dataclass(frozen=True)
class CellDistribution:
    """Summary of raw cells per leader for one group of leaders (all zeros for an empty group)."""

    label: str
    leaders: int
    total_cells: int
    minimum: int
    q1: float
    median: float
    q3: float
    maximum: int
    top_leaders: int
    top_cells: int


@dataclass(frozen=True)
class DistributionCounts:
    """Distributions over leaders with 1+ raw cells and over those at the cut, in that order."""

    distributions: tuple[CellDistribution, ...]
    min_posts: int
    top_share: float


def cell_distribution(label: str, cells: Sequence[int], top_share: float) -> CellDistribution:
    """Min, linear-interpolated quartiles, max, and the cells held by the top `top_share` of leaders (rounded up)."""
    if not 0 < top_share <= 1:
        raise ValueError(f"top_share must be above 0 and at most 1, got {top_share}")
    if not cells:
        return CellDistribution(label, 0, 0, 0, 0.0, 0.0, 0.0, 0, 0, 0)
    ordered = sorted(cells, reverse=True)
    top_leaders = math.ceil(round(top_share * len(ordered), FLOAT_NOISE_DIGITS))
    q1, median, q3 = (float(np.quantile(ordered, q)) for q in (0.25, 0.5, 0.75))
    return CellDistribution(
        label=label,
        leaders=len(ordered),
        total_cells=sum(ordered),
        minimum=ordered[-1],
        q1=q1,
        median=median,
        q3=q3,
        maximum=ordered[0],
        top_leaders=top_leaders,
        top_cells=sum(ordered[:top_leaders]),
    )


def distribution_counts(posts: pd.DataFrame, min_posts: int, top_share: float = TOP_SHARE) -> DistributionCounts:
    """Distribution of raw cells per leader, over leaders with at least 1 raw cell and those at the post cut."""
    _require(posts, POST_COLUMNS, "harmonised_posts")
    cells = [count for count in leader_post_counts(posts).values() if count >= 1]
    groups = (
        ("1 or more raw cells", cells),
        (f"{min_posts} or more raw cells", [count for count in cells if count >= min_posts]),
    )
    return DistributionCounts(
        distributions=tuple(cell_distribution(label, values, top_share) for label, values in groups),
        min_posts=min_posts,
        top_share=top_share,
    )


# ---- output -----------------------------------------------------------------------------------


def _row(summary: CellDistribution, disclosure_min: int) -> tuple[str, ...]:
    if summary.leaders < disclosure_min or summary.leaders == 0:
        return (summary.label, *([SMALL] * HIDDEN_STATISTICS))
    return (
        summary.label,
        f"{summary.leaders:,}",
        f"{summary.total_cells:,}",
        f"{summary.minimum:,}",
        f"{summary.q1:.1f}",
        f"{summary.median:.1f}",
        f"{summary.q3:.1f}",
        f"{summary.maximum:,}",
        f"{summary.top_leaders:,}",
        f"{100 * summary.top_cells / summary.total_cells:.1f}%",
    )


def render_distribution(counts: DistributionCounts, settings: EdaSettings) -> list[str]:
    """Markdown lines for section 4; a group below the disclosure minimum shows as "<5" across the row."""
    top = f"{counts.top_share:.0%}"
    headers = (
        "Group",
        "Leaders",
        "Raw cells",
        "Min",
        "Q1",
        "Median",
        "Q3",
        "Max",
        f"Leaders in the top {top}",
        f"Share of cells from the top {top}",
    )
    rows = [_row(summary, settings.disclosure_min) for summary in counts.distributions]
    return [
        "## 4. Distribution of cells per leader",
        "",
        f"Raw cells per leader, for leaders with at least 1 raw cell and for those at the post cut "
        f"({counts.min_posts}). Raw cells stand in for posts until G1 is signed. Quartiles use linear interpolation "
        f"between neighbouring leaders. The top {top} is the top {top} of leaders by cell count, rounded up to a whole "
        f"leader. A group with fewer than {settings.disclosure_min} leaders is hidden across the row, because its min "
        "and max would be single leaders' counts.",
        "",
        *_table(headers, rows),
        "",
    ]
