"""Tests for src.eda_gaps: share missing per variable, overall and among leaders at the post cut."""
from __future__ import annotations

import pandas as pd
import pytest

from src.eda_common import SMALL, EdaSettings
from src.eda_gaps import (
    ALL_BUT_SMALL,
    GapBase,
    GapCounts,
    GapRow,
    cell_gap_texts,
    gap_counts,
    gap_texts,
    render_gaps,
)
from src.name_key import name_key

LOOSE = EdaSettings(min_posts=2, disclosure_min=1, model_min=1)
STRICT = EdaSettings(min_posts=15, disclosure_min=5, model_min=20)
SENTINELS = ("Zed Sentinel", "Yara Sentinel", "Xan Sentinel", "Wil Sentinel", "Vic Sentinel")
A, B, C, D, E = SENTINELS
POST_COLUMNS = ["leader", "text_kind", "title", "ceo_type", "role_start_year", "post_date", "post_date_text"]
COMPANY_COLUMNS = [
    "Gender", "SectorPraticeAreaFeed", "NumberofEmployees", "FoundedYear", "LinkedIn_Followers",
    *(f"RevenueUSD{year}" for year in range(2021, 2025)),
    *(f"ProfitUSD{year}" for year in range(2021, 2025)),
]


def _posts() -> pd.DataFrame:
    """A: 3 raw cells, B: 1, C: 2, E: 1 raw cell; D has only a cleaned row, which never counts."""
    rows = [
        (A, "raw", "CEO", "Professional CEO", "", "", "3mo"),
        (A, "raw", "CEO", "", "", "", ""),
        (A, "raw", ".", "Professional CEO", "", "", "-"),
        (B, "raw", "", "", "", "", ""),
        (C, "raw", "Founder", "Founder-CEO", "2019", "", "1y"),
        (C, "raw", "Founder", "Founder-CEO", "", "", "2y"),
        (E, "raw", "COO", "Professional CEO", "", "", "5d"),
        (D, "cleaned", "CEO", "Professional CEO", "2020", "2024-01-01", "1d"),
    ]
    return pd.DataFrame(rows, columns=POST_COLUMNS)


def _company() -> pd.DataFrame:
    """Row 1 is A's, row 2 is B's, row 3 is C's (an ambiguous match, so never used)."""
    blank = {name: "" for name in COMPANY_COLUMNS}
    row_a = {**blank, "Gender": "1", "SectorPraticeAreaFeed": "Tech > SaaS", "NumberofEmployees": "500+",
             "FoundedYear": "2001", "LinkedIn_Followers": "12K", "RevenueUSD2021": "186.6M", "RevenueUSD2022": "."}
    row_b = {**blank, "SectorPraticeAreaFeed": "-"}
    row_c = {**blank, "Gender": "0"}
    return pd.DataFrame([row_a, row_b, row_c], columns=COMPANY_COLUMNS)


def _proposal() -> pd.DataFrame:
    rows = [
        (name_key(A), "clear", "row:1"),
        (name_key(B), "clear", "row:2"),
        (name_key(C), "ambiguous", "row:3"),
        (name_key(D), "clear", ""),
    ]
    return pd.DataFrame(rows, columns=["key", "status", "company"])


@pytest.fixture
def counts() -> GapCounts:
    return gap_counts(_posts(), _proposal(), _company(), min_posts=2)


def _row(base: GapBase, variable: str) -> GapRow:
    return next(row for row in base.rows if row.variable == variable)


# ---- who is in each base ----------------------------------------------------------------------


def test_bases_count_leaders_with_a_raw_cell_and_those_at_the_cut(counts: GapCounts) -> None:
    assert counts.with_posts.leaders == 4
    assert counts.at_cut.leaders == 2
    assert counts.min_posts == 2


def test_a_leader_with_only_a_cleaned_row_is_not_counted(counts: GapCounts) -> None:
    assert counts.with_posts.leaders == 4  # D has a cleaned row only


def test_company_match_status_is_counted_for_each_base(counts: GapCounts) -> None:
    everyone = counts.with_posts

    assert (everyone.matched, everyone.ambiguous, everyone.no_company_row, everyone.not_in_proposal) == (2, 1, 0, 1)
    assert (counts.at_cut.matched, counts.at_cut.ambiguous) == (1, 1)


# ---- post-cell variables ----------------------------------------------------------------------


@pytest.mark.parametrize(
    ("variable", "missing_all", "missing_cut"),
    [
        ("ceo_type", 1, 0),
        ("current_title", 1, 0),
        ("role_start_year", 3, 1),
        ("post_date", 4, 2),
        ("post_date_text", 1, 0),
    ],
)
def test_a_leader_is_missing_a_post_variable_only_when_every_raw_cell_is_blank(
    counts: GapCounts, variable: str, missing_all: int, missing_cut: int
) -> None:
    assert (_row(counts.with_posts, variable).leaders, _row(counts.with_posts, variable).missing) == (4, missing_all)
    assert _row(counts.at_cut, variable).missing == missing_cut


def test_the_dot_and_dash_markers_count_as_blank_cells(counts: GapCounts) -> None:
    row = _row(counts.with_posts, "post_date_text")

    # Blank cells: A's "" and "-", and B's "". Seven raw cells in all.
    assert (row.blank_cells, row.cells) == (3, 7)


def test_blank_cells_are_counted_for_the_variable_among_the_bases_cells(counts: GapCounts) -> None:
    ceo_type = _row(counts.with_posts, "ceo_type")

    assert (ceo_type.cells, ceo_type.blank_cells) == (7, 2)
    assert (_row(counts.at_cut, "ceo_type").cells, _row(counts.at_cut, "ceo_type").blank_cells) == (5, 1)


# ---- Company_Data variables -------------------------------------------------------------------


def test_company_variables_are_counted_over_matched_leaders_only(counts: GapCounts) -> None:
    gender = _row(counts.with_posts, "gender (as coded)")

    assert (gender.leaders, gender.missing) == (2, 1)
    assert gender.source == "Company_Data"


def test_a_dash_sector_is_missing(counts: GapCounts) -> None:
    assert _row(counts.with_posts, "sector").missing == 1


def test_a_numeric_variable_that_does_not_parse_is_missing_and_a_suffixed_one_is_not(counts: GapCounts) -> None:
    assert _row(counts.with_posts, "firm size (employees)").missing == 2  # "500+" is not guessed, and B is blank
    assert _row(counts.with_posts, "revenue 2021").missing == 1  # "186.6M" parses
    assert _row(counts.with_posts, "revenue 2022").missing == 2  # "." is blank


def test_every_requested_company_variable_has_a_row(counts: GapCounts) -> None:
    names = {row.variable for row in counts.with_posts.rows}

    expected = {"gender (as coded)", "sector", "firm size (employees)", "firm age (founded year)", "LinkedIn followers"}
    expected |= {f"revenue {y}" for y in range(2021, 2025)} | {f"profit {y}" for y in range(2021, 2025)}
    assert expected <= names


def test_company_cell_columns_are_not_applicable(counts: GapCounts) -> None:
    row = _row(counts.with_posts, "sector")

    assert (row.cells, row.blank_cells) == (0, 0)


# ---- errors and immutability ------------------------------------------------------------------


def test_a_missing_posts_column_is_named() -> None:
    with pytest.raises(ValueError, match="post_date_text"):
        gap_counts(_posts().drop(columns=["post_date_text"]), _proposal(), _company(), min_posts=2)


def test_a_missing_company_column_is_named() -> None:
    with pytest.raises(ValueError, match="FoundedYear"):
        gap_counts(_posts(), _proposal(), _company().drop(columns=["FoundedYear"]), min_posts=2)


def test_a_missing_proposal_column_is_named() -> None:
    with pytest.raises(ValueError, match="status"):
        gap_counts(_posts(), _proposal().drop(columns=["status"]), _company(), min_posts=2)


def test_the_counts_are_frozen(counts: GapCounts) -> None:
    with pytest.raises(AttributeError):
        counts.min_posts = 99  # type: ignore[misc]


# ---- the "<5" rule ----------------------------------------------------------------------------


def test_gap_texts_show_numbers_when_both_sides_are_large_enough() -> None:
    assert gap_texts(10, 100, 5) == ("10", "10.0%")


@pytest.mark.parametrize(("missing", "total"), [(3, 100), (0, 100), (1, 3), (0, 0)])
def test_gap_texts_hide_a_small_missing_count_or_a_small_base(missing: int, total: int) -> None:
    assert gap_texts(missing, total, 5) == (SMALL, SMALL)


def test_gap_texts_say_all_but_small_when_nearly_everything_is_missing() -> None:
    assert gap_texts(98, 100, 5) == (ALL_BUT_SMALL, ALL_BUT_SMALL) == ("all but <5", "all but <5")


def test_cell_texts_follow_the_leader_level_hiding() -> None:
    leader_texts = (ALL_BUT_SMALL, ALL_BUT_SMALL)

    assert cell_gap_texts(26931, 26945, leader_texts) == leader_texts


def test_cell_texts_show_numbers_when_the_leader_counts_are_shown() -> None:
    assert cell_gap_texts(2, 8, ("1", "25.0%")) == ("2", "25.0%")


# ---- rendering --------------------------------------------------------------------------------


def _text(counts: GapCounts, settings: EdaSettings) -> str:
    return "\n".join(render_gaps(counts, settings))


def test_rendering_shows_a_leader_row_with_base_missing_and_share(counts: GapCounts) -> None:
    assert "| ceo_type | post workbooks | 4 | 1 | 25.0% |" in _text(counts, LOOSE)


def test_rendering_hides_small_counts_under_the_strict_minimum(counts: GapCounts) -> None:
    text = _text(counts, STRICT)

    assert f"| ceo_type | post workbooks | {SMALL} | {SMALL} | {SMALL} |" in text


def test_rendering_states_the_bases_and_what_missing_means(counts: GapCounts) -> None:
    text = _text(counts, LOOSE).lower()

    assert "## 2. gaps" in text
    assert "every raw cell" in text
    assert "at least 2 raw cells" in text
    assert "ambiguous" in text


def test_rendering_has_no_names_keys_or_refs(counts: GapCounts) -> None:
    text = _text(counts, LOOSE)

    for forbidden in (*SENTINELS, "row:", name_key(A)):
        assert forbidden not in text
