"""EDA section 2, gaps: share of leaders missing each variable, overall and among leaders at the post cut.

Counts only. Missing means blank, "." or "-" (`clean_cell`), or, for a number, text that `parse_quantity` cannot read
("500+" is not guessed at). A cell-level variable (ceo_type, title, role_start_year, post_date, post_date_text) is
missing for a leader only when every raw cell of that leader is blank. Company_Data variables are read for leaders with
a clear match and a company row; ambiguous and unmatched leaders are counted and left out, never guessed.
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import pandas as pd

from src.company_columns import RAW_KIND, leader_post_counts
from src.company_data import clean_cell, parse_quantity
from src.eda_common import SMALL, EdaSettings, protect_cells, show_count
from src.eda_groups import (
    AMBIGUOUS,
    NO_COMPANY_ROW,
    NOT_IN_PROPOSAL,
    classify_matches,
    proposal_lookup,
)
from src.harmonise_report import _table
from src.name_key import name_key

ALL_BUT_SMALL = f"all but {SMALL}"
POST_SOURCE = "post workbooks"
COMPANY_SOURCE = "Company_Data"
NOT_APPLICABLE = "n/a"
LEADER, TEXT_KIND = "leader", "text_kind"
PROPOSAL_COLUMNS = ("key", "status", "company")

# (name shown, column in harmonised_posts)
POST_VARIABLES = (
    ("ceo_type", "ceo_type"),
    ("current_title", "title"),
    ("role_start_year", "role_start_year"),
    ("post_date", "post_date"),
    ("post_date_text", "post_date_text"),
)
# (name shown, column in company_data, is a number read by parse_quantity)
_YEARS = range(2021, 2025)
COMPANY_VARIABLES = (
    ("gender (as coded)", "Gender", False),
    ("sector", "SectorPraticeAreaFeed", False),
    ("firm size (employees)", "NumberofEmployees", True),
    ("firm age (founded year)", "FoundedYear", True),
    ("LinkedIn followers", "LinkedIn_Followers", True),
    *((f"revenue {year}", f"RevenueUSD{year}", True) for year in _YEARS),
    *((f"profit {year}", f"ProfitUSD{year}", True) for year in _YEARS),
)
POST_COLUMNS = (LEADER, TEXT_KIND, *(column for _, column in POST_VARIABLES))
COMPANY_COLUMNS = tuple(column for _, column, _ in COMPANY_VARIABLES)


@dataclass(frozen=True)
class GapRow:
    """One variable in one base: leaders in the base, leaders missing it, and (cell variables) blank cells."""

    variable: str
    source: str
    leaders: int
    missing: int
    cells: int
    blank_cells: int


@dataclass(frozen=True)
class GapBase:
    """A set of leaders (all with posts, or those at the cut), their company-match status and a row per variable."""

    leaders: int
    cells: int
    matched: int
    ambiguous: int
    no_company_row: int
    not_in_proposal: int
    rows: tuple[GapRow, ...]


@dataclass(frozen=True)
class GapCounts:
    with_posts: GapBase
    at_cut: GapBase
    min_posts: int


def _require(frame: pd.DataFrame, columns: Sequence[str], name: str) -> None:
    missing = [column for column in columns if column not in frame.columns]
    if missing:
        raise ValueError(f"{name}: missing columns {', '.join(missing)}")


# ---- post-cell variables ----------------------------------------------------------------------


def _blank_flags(raw: pd.DataFrame, keys: pd.Series) -> pd.DataFrame:
    """One True/False column per post variable (cell is blank), plus the leader's name key."""
    flags = pd.DataFrame(
        {name: raw[column].map(lambda value: clean_cell(value) is None) for name, column in POST_VARIABLES}
    )
    flags["_key"] = keys
    return flags


def _post_rows(flags: pd.DataFrame, members: set[str]) -> tuple[GapRow, ...]:
    """A row per post variable for the leaders in `members`."""
    inside = flags[flags["_key"].isin(list(members))]
    rows = []
    for name, _ in POST_VARIABLES:
        per_leader = inside.groupby("_key")[name]
        rows.append(
            GapRow(
                variable=name,
                source=POST_SOURCE,
                leaders=len(members),
                missing=sum(1 for every_blank in per_leader.all() if every_blank),
                cells=len(inside),
                blank_cells=sum(1 for blank in inside[name] if blank),
            )
        )
    return tuple(rows)


# ---- Company_Data variables -------------------------------------------------------------------


def _is_missing(value: object, is_number: bool) -> bool:
    return parse_quantity(value) is None if is_number else clean_cell(value) is None


def _company_rows(company: pd.DataFrame, positions: list[int]) -> tuple[GapRow, ...]:
    matched = company.iloc[positions]
    return tuple(
        GapRow(
            variable=name,
            source=COMPANY_SOURCE,
            leaders=len(positions),
            missing=int(sum(_is_missing(value, is_number) for value in matched[column])),
            cells=0,
            blank_cells=0,
        )
        for name, column, is_number in COMPANY_VARIABLES
    )


# ---- counts -----------------------------------------------------------------------------------


def _base(
    members: set[str], flags: pd.DataFrame, lookup: dict[str, tuple[str, str]], company: pd.DataFrame
) -> GapBase:
    matched, others = classify_matches(members, lookup, len(company))
    positions = list(matched.values())
    post_rows = _post_rows(flags, members)
    return GapBase(
        leaders=len(members),
        cells=post_rows[0].cells,
        matched=len(positions),
        ambiguous=others[AMBIGUOUS],
        no_company_row=others[NO_COMPANY_ROW],
        not_in_proposal=others[NOT_IN_PROPOSAL],
        rows=(*post_rows, *_company_rows(company, positions)),
    )


def gap_counts(posts: pd.DataFrame, proposal: pd.DataFrame, company: pd.DataFrame, min_posts: int) -> GapCounts:
    """Missingness for leaders with at least 1 raw cell, and for those with at least `min_posts` raw cells."""
    _require(posts, POST_COLUMNS, "harmonised_posts")
    _require(proposal, PROPOSAL_COLUMNS, "leader_id_proposal")
    _require(company, COMPANY_COLUMNS, "company_data")
    raw = posts[posts[TEXT_KIND] == RAW_KIND]
    keys = raw[LEADER].map(name_key)
    keep = keys != ""
    flags = _blank_flags(raw[keep], keys[keep])
    cells = leader_post_counts(posts)
    lookup = proposal_lookup(proposal)
    everyone = {key for key, count in cells.items() if count >= 1}
    at_cut = {key for key, count in cells.items() if count >= min_posts}
    return GapCounts(
        with_posts=_base(everyone, flags, lookup, company),
        at_cut=_base(at_cut, flags, lookup, company),
        min_posts=min_posts,
    )


# ---- the "<5" rule ----------------------------------------------------------------------------


def gap_texts(missing: int, total: int, minimum: int) -> tuple[str, str]:
    """(count, share) as text. A small base or a small missing count shows "<5"; if fewer than 5 are not missing,
    "all but <5", because the visible count would otherwise give a hidden one back."""
    if total < minimum or missing < minimum:
        return SMALL, SMALL
    if total - missing < minimum:
        return ALL_BUT_SMALL, ALL_BUT_SMALL
    return f"{missing:,}", f"{100 * missing / total:.1f}%"


def cell_gap_texts(blank_cells: int, cells: int, leader_texts: tuple[str, str]) -> tuple[str, str]:
    """Blank-cell count and share; hidden whenever the leader-level counts for the same row are hidden."""
    if leader_texts[0] in (SMALL, ALL_BUT_SMALL) or cells == 0:
        return leader_texts
    return f"{blank_cells:,}", f"{100 * blank_cells / cells:.1f}%"


# ---- output -----------------------------------------------------------------------------------


def _gap_table(base: GapBase, settings: EdaSettings) -> list[str]:
    rows: list[tuple[str, ...]] = []
    for row in base.rows:
        leader_texts = gap_texts(row.missing, row.leaders, settings.disclosure_min)
        if row.source == POST_SOURCE:
            cell_texts = cell_gap_texts(row.blank_cells, row.cells, leader_texts)
        else:
            cell_texts = (NOT_APPLICABLE, NOT_APPLICABLE)
        leaders = show_count(row.leaders, settings.disclosure_min)
        rows.append((row.variable, row.source, leaders, *leader_texts, *cell_texts))
    headers = (
        "Variable", "Source", "Leaders in base", "Leaders missing", "Share missing", "Blank cells", "Share of cells blank",
    )
    return _table(headers, rows)


def _match_table(base: GapBase, settings: EdaSettings) -> list[str]:
    parts = {
        "Clear match with a company row (Company_Data variables read)": base.matched,
        "Ambiguous name key (left out)": base.ambiguous,
        "Clear match without a company row (left out)": base.no_company_row,
        "Not in the leader proposal (left out)": base.not_in_proposal,
    }
    shown = protect_cells(parts, settings.disclosure_min)
    rows = list(shown.items())
    rows.append(("Leaders in this base", show_count(base.leaders, settings.disclosure_min)))
    return _table(("Company_Data match", "Leaders"), rows)


def _base_section(title: str, base: GapBase, settings: EdaSettings) -> list[str]:
    return [
        f"### {title}",
        "",
        *_match_table(base, settings),
        "",
        *_gap_table(base, settings),
        "",
    ]


def render_gaps(counts: GapCounts, settings: EdaSettings) -> list[str]:
    """Markdown lines for section 2; counts below the disclosure minimum show as "<5"."""
    cut = counts.min_posts
    return [
        "## 2. Gaps",
        "",
        "Share of leaders missing each variable. Blank, \".\" and \"-\" count as missing, and so does a number that "
        "cannot be read (\"500+\" is not guessed at). A post-workbook variable is missing for a leader only when every raw "
        "cell of that leader is blank; the blank-cell columns count cells instead. Company_Data variables are read for "
        "leaders with a clear match and a company row only: ambiguous and unmatched leaders are counted and left out. "
        "\"all but <5\" means fewer than 5 leaders have the value. Raw cells stand in for posts until G1 is signed. "
        "Gender is shown as coded in the file and is not interpreted.",
        "",
        *_base_section("Leaders with at least 1 raw cell", counts.with_posts, settings),
        *_base_section(f"Leaders with at least {cut} raw cells", counts.at_cut, settings),
    ]
