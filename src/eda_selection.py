"""EDA section 6: possible selection bias, described and not fixed (`make eda`).

Compares the sector and size mix of the study leaders (a raw post cell and a clear Company_Data match) with all of
Company_Data. Size bands are cut once over every Company_Data row, so both sides use the same bands. Nothing is
reweighted, filled in or dropped. Counts and shares only: no names, ids, company names or references. A count below
the disclosure minimum (zero included) is shown as "<5", with its share and difference.
"""
from __future__ import annotations

from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass

import pandas as pd

from src.company_columns import leader_post_counts
from src.eda_balance import SECTOR_COLUMN, SIZE_COLUMN, SPECIAL_LABELS, _sector_label, _size_labeller
from src.eda_common import SMALL, TOTAL_LABEL, EdaSettings, protect_cells, show_count
from src.eda_gaps import LEADER, PROPOSAL_COLUMNS, TEXT_KIND, _require
from src.eda_groups import classify_matches, proposal_lookup, size_band_edges
from src.harmonise_report import _table

SECTOR_FACTOR = "Sector"
SIZE_FACTOR = "Firm size (employees)"
POST_COLUMNS = (LEADER, TEXT_KIND)
COMPANY_COLUMNS = (SECTOR_COLUMN, SIZE_COLUMN)
FULL_SHARE = "100.0%"
NO_SHARE = "n/a"


@dataclass(frozen=True)
class GroupMix:
    """Study leaders and Company_Data firms in one group."""

    label: str
    study: int
    company: int


@dataclass(frozen=True)
class FactorMix:
    """The mix of one factor, one group per label."""

    factor: str
    groups: tuple[GroupMix, ...]


@dataclass(frozen=True)
class SelectionCounts:
    """Study size, leaders left out for want of a clear match, Company_Data size, and the mix per factor."""

    study_leaders: int
    unmatched_leaders: int
    company_rows: int
    factors: tuple[FactorMix, ...]


def _by_company_size(label: str, company: Counter[str]) -> tuple[object, ...]:
    """Largest in Company_Data first, ties by label, the blank and unreadable groups last."""
    return (label in SPECIAL_LABELS, -company[label], label)


def _by_label(label: str, company: Counter[str]) -> tuple[object, ...]:
    """Natural label order (size bands from the smallest), the blank and unreadable groups last."""
    return (label in SPECIAL_LABELS, label)


def _mix(
    factor: str,
    study: list[str],
    company: list[str],
    order: Callable[[str, Counter[str]], tuple[object, ...]],
) -> FactorMix:
    study_counts, company_counts = Counter(study), Counter(company)
    labels = sorted(set(study_counts) | set(company_counts), key=lambda label: order(label, company_counts))
    return FactorMix(factor, tuple(GroupMix(label, study_counts[label], company_counts[label]) for label in labels))


def selection_counts(posts: pd.DataFrame, proposal: pd.DataFrame, company: pd.DataFrame, bands: int) -> SelectionCounts:
    """Sector and size mix of the study leaders beside all of Company_Data (no input is changed)."""
    _require(posts, POST_COLUMNS, "harmonised_posts")
    _require(proposal, PROPOSAL_COLUMNS, "leader_id_proposal")
    _require(company, COMPANY_COLUMNS, "company_data")
    members = [key for key, cells in leader_post_counts(posts).items() if cells >= 1]
    positions, others = classify_matches(members, proposal_lookup(proposal), len(company))
    rows = sorted(positions.values())
    size_label = _size_labeller(size_band_edges(company[SIZE_COLUMN], bands), bands)
    factors = []
    for factor, column, label_of, order in (
        (SECTOR_FACTOR, SECTOR_COLUMN, _sector_label, _by_company_size),
        (SIZE_FACTOR, SIZE_COLUMN, size_label, _by_label),
    ):
        values = company[column].tolist()
        study_labels = [label_of(values[row]) for row in rows]
        factors.append(_mix(factor, study_labels, [label_of(value) for value in values], order))
    return SelectionCounts(
        study_leaders=len(rows),
        unmatched_leaders=sum(others.values()),
        company_rows=len(company),
        factors=tuple(factors),
    )


# ---- output -----------------------------------------------------------------------------------


def _share(count: int, total: int) -> float:
    return 100 * count / total if total else 0.0


def _side(count: int, total: int, shown: str) -> tuple[str, str]:
    """Count text and share text for one side; a hidden count hides its share."""
    if shown == SMALL:
        return SMALL, SMALL
    return shown, f"{_share(count, total):.1f}%" if total else NO_SHARE


def _row(group: GroupMix, shown: tuple[str, str], counts: SelectionCounts) -> tuple[str, ...]:
    study_text, study_share = _side(group.study, counts.study_leaders, shown[0])
    company_text, company_share = _side(group.company, counts.company_rows, shown[1])
    if SMALL in (study_text, company_text) or NO_SHARE in (study_share, company_share):
        difference = SMALL
    else:
        gap = _share(group.study, counts.study_leaders) - _share(group.company, counts.company_rows)
        difference = f"{gap:+.1f}"
    return (group.label, study_text, study_share, company_text, company_share, difference)


def _total_row(counts: SelectionCounts, minimum: int) -> tuple[str, ...]:
    study, company = show_count(counts.study_leaders, minimum), show_count(counts.company_rows, minimum)
    return (
        TOTAL_LABEL,
        study,
        SMALL if study == SMALL else FULL_SHARE,
        company,
        SMALL if company == SMALL else FULL_SHARE,
        "",
    )


def _factor_table(factor: FactorMix, counts: SelectionCounts, minimum: int) -> list[str]:
    study_shown = protect_cells({group.label: group.study for group in factor.groups}, minimum)
    company_shown = protect_cells({group.label: group.company for group in factor.groups}, minimum)
    header = ("Group", "Study leaders", "Study share", "Company_Data firms", "Company_Data share", "Difference (points)")
    rows = [_row(group, (study_shown[group.label], company_shown[group.label]), counts) for group in factor.groups]
    return [*_table(header, [*rows, _total_row(counts, minimum)]), ""]


def render_selection(counts: SelectionCounts, settings: EdaSettings) -> list[str]:
    """Markdown lines for section 6; counts below the disclosure minimum show as "<5"."""
    minimum = settings.disclosure_min
    study = show_count(counts.study_leaders, minimum)
    unmatched = show_count(counts.unmatched_leaders, minimum)
    lines = [
        "## 6. Possible selection bias",
        "",
        "Who is in the sample compared with Company_Data overall, sector and size mix only. Selection bias is described, "
        "not corrected: nothing is reweighted, filled in or dropped here. The study here means leaders with at least "
        "one raw post cell and a clear Company_Data match (raw cells stand in for posts until G1 is signed): "
        f"{study} leaders, against {counts.company_rows:,} Company_Data firms. {unmatched} further leaders with raw "
        "cells have no clear Company_Data match, so they have no sector or size and are in neither table. Firm size "
        "bands are cut once over all Company_Data rows, so both sides use the same bands. Every firm in Company_Data "
        "is listed, so listed vs unlisted cannot be compared. The differences say who is in the sample, nothing about "
        f'how leaders present themselves. A count below {minimum} (zero included) shows as "<5", with its share and '
        "difference.",
        "",
    ]
    for factor in counts.factors:
        lines += [f"### {factor.factor}", "", *_factor_table(factor, counts, minimum)]
    return lines
