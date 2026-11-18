"""EDA section 3: balance for the planned comparisons, each crossed with the post cut (`make eda`).

Factors: founder vs professional CEO, gender as coded, title family, sector and firm size bands. Each leader with at
least one raw cell falls in exactly one group per factor; a leader without a usable value or without a clear company
match is shown in an explicit group, never filled in. Counts only: no names, ids or references. Raw cells stand in
for posts until gate G1 is signed.
"""
from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass

import pandas as pd

from src.ceo_gender_counts import _BLANK, CEO_TYPE_COLUMN, _leader_class, _text
from src.company_columns import RAW_KIND, leader_post_counts
from src.company_data import clean_cell
from src.eda_common import SMALL, TOO_SMALL_TO_MODEL, EdaSettings, protect_cells, show_count, show_share
from src.eda_gaps import LEADER, PROPOSAL_COLUMNS, TEXT_KIND, _require
from src.eda_groups import (
    classify_matches,
    leader_title_family,
    proposal_lookup,
    sector_of,
    size_band,
    size_band_edges,
    size_band_label,
)
from src.harmonise_report import _table
from src.name_key import name_key

CEO_TYPE_FACTOR = "Founder vs professional CEO"
GENDER_FACTOR = "Gender (as coded)"
TITLE_FACTOR = "Title family"
SECTOR_FACTOR = "Sector"
SIZE_FACTOR = "Firm size band"
BLANK_VALUE = "no value"
NOT_MATCHED = "no usable company match"
UNREADABLE_SIZE = "size not readable"
OTHER_GENDER_CODE = "other code"
TITLE_COLUMN = "title"
SECTOR_COLUMN, SIZE_COLUMN, GENDER_COLUMN = "SectorPraticeAreaFeed", "NumberofEmployees", "Gender"
POST_COLUMNS = (LEADER, TEXT_KIND, TITLE_COLUMN, CEO_TYPE_COLUMN)
COMPANY_COLUMNS = (GENDER_COLUMN, SECTOR_COLUMN, SIZE_COLUMN)
SPECIAL_LABELS = frozenset({BLANK_VALUE, NOT_MATCHED, UNREADABLE_SIZE})


@dataclass(frozen=True)
class GroupCount:
    """Leaders in one group: with at least 1 raw cell, and with at least the post cut."""

    label: str
    leaders: int
    at_cut: int


@dataclass(frozen=True)
class FactorBalance:
    factor: str
    groups: tuple[GroupCount, ...]


@dataclass(frozen=True)
class BalanceCounts:
    factors: tuple[FactorBalance, ...]
    min_posts: int
    bands: int
    band_edges: tuple[float, ...]


# ---- labels -----------------------------------------------------------------------------------


def _ceo_type_label(values: set[str]) -> str:
    label = _leader_class(values)
    return BLANK_VALUE if label == _BLANK else label


def _gender_label(value: object) -> str:
    text = clean_cell(value)
    if text is None:
        return BLANK_VALUE
    return f"coded {text}" if text in ("0", "1") else OTHER_GENDER_CODE


def _sector_label(value: object) -> str:
    return sector_of(value) or BLANK_VALUE


def _size_labeller(edges: tuple[float, ...], bands: int) -> Callable[[object], str]:
    def label(value: object) -> str:
        if clean_cell(value) is None:
            return BLANK_VALUE
        band = size_band(value, edges)
        return UNREADABLE_SIZE if band is None else size_band_label(band, bands)

    return label


# ---- counting ---------------------------------------------------------------------------------


def _cell_facts(posts: pd.DataFrame, members: set[str]) -> tuple[dict[str, set[str]], dict[str, list[object]]]:
    """ceo_type values (blank markers dropped) and titles over each member leader's raw cells."""
    ceo_values: dict[str, set[str]] = defaultdict(set)
    titles: dict[str, list[object]] = defaultdict(list)
    raw = posts[posts[TEXT_KIND] == RAW_KIND]
    for leader, ceo_type, title in zip(raw[LEADER], raw[CEO_TYPE_COLUMN], raw[TITLE_COLUMN], strict=True):
        key = name_key(leader)
        if key not in members:
            continue
        titles[key].append(title)
        if text := _text(ceo_type):
            ceo_values[key].add(text)
    return ceo_values, titles


def _company_labels(
    members: set[str], positions: Mapping[str, int], column: Sequence[object], label_of: Callable[[object], str]
) -> dict[str, str]:
    return {key: label_of(column[positions[key]]) if key in positions else NOT_MATCHED for key in members}


def _group_order(counts: Mapping[str, int], natural: bool) -> list[str]:
    """Groups with a value first (largest first, or label order when `natural`), then the explicit gap groups."""
    if natural:
        return sorted(counts, key=lambda label: (label in SPECIAL_LABELS, label))
    return sorted(counts, key=lambda label: (label in SPECIAL_LABELS, -counts[label], label))


def _tally(labels: Mapping[str, str], at_cut: set[str], natural: bool = False) -> tuple[GroupCount, ...]:
    everyone: dict[str, int] = defaultdict(int)
    cut: dict[str, int] = defaultdict(int)
    for key, label in labels.items():
        everyone[label] += 1
        cut[label] += int(key in at_cut)
    return tuple(GroupCount(label, everyone[label], cut[label]) for label in _group_order(everyone, natural))


def balance_counts(
    posts: pd.DataFrame, proposal: pd.DataFrame, company: pd.DataFrame, min_posts: int, bands: int
) -> BalanceCounts:
    """Group counts for every planned comparison, over leaders with at least 1 raw cell and those at the cut."""
    _require(posts, POST_COLUMNS, "harmonised_posts")
    _require(proposal, PROPOSAL_COLUMNS, "leader_id_proposal")
    _require(company, COMPANY_COLUMNS, "company_data")
    cells = leader_post_counts(posts)
    members = {key for key, count in cells.items() if count >= 1}
    at_cut = {key for key in members if cells[key] >= min_posts}
    positions, _ = classify_matches(members, proposal_lookup(proposal), len(company))
    ceo_values, titles = _cell_facts(posts, members)
    edges = size_band_edges(company[SIZE_COLUMN], bands)
    sizes = _company_labels(members, positions, company[SIZE_COLUMN].tolist(), _size_labeller(edges, bands))
    factors = (
        FactorBalance(
            CEO_TYPE_FACTOR, _tally({key: _ceo_type_label(ceo_values.get(key, set())) for key in members}, at_cut)
        ),
        FactorBalance(
            GENDER_FACTOR,
            _tally(_company_labels(members, positions, company[GENDER_COLUMN].tolist(), _gender_label), at_cut),
        ),
        FactorBalance(
            TITLE_FACTOR, _tally({key: leader_title_family(titles.get(key, [])) for key in members}, at_cut)
        ),
        FactorBalance(
            SECTOR_FACTOR,
            _tally(_company_labels(members, positions, company[SECTOR_COLUMN].tolist(), _sector_label), at_cut),
        ),
        FactorBalance(SIZE_FACTOR, _tally(sizes, at_cut, natural=True)),
    )
    return BalanceCounts(factors=factors, min_posts=min_posts, bands=bands, band_edges=edges)


# ---- output -----------------------------------------------------------------------------------


def _basis_texts(counts: Mapping[str, int], minimum: int) -> dict[str, tuple[str, str]]:
    """(count, share) per group for one basis; a hidden count hides its share too."""
    total = sum(counts.values())
    shown = protect_cells(counts, minimum)
    return {
        label: (text, SMALL if text == SMALL else show_share(counts[label], total, minimum))
        for label, text in shown.items()
    }


def _factor_table(balance: FactorBalance, settings: EdaSettings) -> list[str]:
    minimum = settings.disclosure_min
    everyone = _basis_texts({group.label: group.leaders for group in balance.groups}, minimum)
    at_cut = _basis_texts({group.label: group.at_cut for group in balance.groups}, minimum)
    rows = [
        (
            group.label,
            *everyone[group.label],
            *at_cut[group.label],
            TOO_SMALL_TO_MODEL if group.at_cut < settings.model_min else "",
        )
        for group in balance.groups
    ]
    total = sum(group.leaders for group in balance.groups)
    total_cut = sum(group.at_cut for group in balance.groups)
    rows.append(
        (
            "all",
            show_count(total, minimum),
            show_share(total, total, minimum),
            show_count(total_cut, minimum),
            show_share(total_cut, total_cut, minimum),
            "",
        )
    )
    headers = (
        "Group",
        "Leaders with 1+ raw cell",
        "Share",
        f"Leaders with {settings.min_posts}+ raw cells",
        "Share",
        "Flag at the cut",
    )
    return _table(headers, rows)


def _edge_note(counts: BalanceCounts) -> str:
    cuts = ", ".join(f"{edge:,.0f}" for edge in counts.band_edges)
    return (
        f"Firm size is cut into {counts.bands} quantile bands of the readable employee counts over all of "
        f"Company_Data (cut points, employees: {cuts}). A size that cannot be read (\"500+\") is not guessed at."
    )


def render_balance(counts: BalanceCounts, settings: EdaSettings) -> list[str]:
    """Markdown lines for section 3; counts below the disclosure minimum show as "<5"."""
    cut = counts.min_posts
    lines = [
        "## 3. Balance for the planned comparisons",
        "",
        f"Each factor is crossed with the post cut: leaders with at least 1 raw cell, and leaders with at least {cut} "
        f"raw cells. Raw cells stand in for posts until G1 is signed. A group with fewer than {settings.model_min} "
        f"leaders at the cut is flagged \"{TOO_SMALL_TO_MODEL}\"; that is a working flag for the EDA, not the "
        "modelling rule (that belongs in the pre-registration, gate G3). Founder vs professional uses ceo_type pooled "
        "per leader (conflicting and unrecognised kept apart). Gender is shown as coded in the file and is not "
        "interpreted. Title family, sector (first segment of the coded sector path) and size bands are a proposal "
        "for the mentors, not a decision. A leader with no usable value or no clear Company_Data match is shown in "
        "its own group, never filled in.",
        "",
        _edge_note(counts),
        "",
    ]
    for balance in counts.factors:
        lines += [f"### {balance.factor}", "", *_factor_table(balance, settings), ""]
    return lines
