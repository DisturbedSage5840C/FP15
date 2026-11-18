"""Tests for src.eda_selection: sector and size mix of the study leaders vs Company_Data overall (described, not fixed)."""
from __future__ import annotations

import pandas as pd
import pytest

from src.eda_balance import BLANK_VALUE, UNREADABLE_SIZE
from src.eda_common import EdaSettings
from src.eda_groups import size_band_label
from src.eda_selection import (
    SECTOR_FACTOR,
    SIZE_FACTOR,
    FactorMix,
    GroupMix,
    SelectionCounts,
    render_selection,
    selection_counts,
)
from src.name_key import name_key

LOOSE = EdaSettings(min_posts=2, disclosure_min=1, model_min=1, size_bands=2)
STRICT = EdaSettings(min_posts=15, disclosure_min=5, model_min=20, size_bands=4)
SENTINELS = ("Zed Sentinel", "Yara Sentinel", "Xan Sentinel", "Wil Sentinel", "Vic Sentinel")
A, B, C, D, E = SENTINELS
COMPANY_SENTINEL = "Sentinel Holdings Ltd"
LOW_BAND, HIGH_BAND = size_band_label(1, 2), size_band_label(2, 2)


def _posts() -> pd.DataFrame:
    """A, B, C have raw cells and a clear match; D has raw cells but an ambiguous match; E has a cleaned row only."""
    rows = [(A, "raw"), (A, "raw"), (B, "raw"), (C, "raw"), (D, "raw"), (E, "cleaned")]
    return pd.DataFrame(rows, columns=["leader", "text_kind"])


def _company() -> pd.DataFrame:
    """Five firms; the first three belong to A, B, C. 500+ cannot be read as a number."""
    rows = [
        (COMPANY_SENTINEL, "Tech > SaaS", "100"),
        (COMPANY_SENTINEL, "Finance > Banking", "300"),
        (COMPANY_SENTINEL, "Tech > Cloud", "500+"),
        (COMPANY_SENTINEL, "Energy", "200"),
        (COMPANY_SENTINEL, "Energy", "400"),
    ]
    return pd.DataFrame(rows, columns=["Company", "SectorPraticeAreaFeed", "NumberofEmployees"])


def _proposal() -> pd.DataFrame:
    rows = [
        (name_key(A), "clear", "row:1"),
        (name_key(B), "clear", "row:2"),
        (name_key(C), "clear", "row:3"),
        (name_key(D), "ambiguous", "row:4"),
    ]
    return pd.DataFrame(rows, columns=["key", "status", "company"])


@pytest.fixture
def counts() -> SelectionCounts:
    return selection_counts(_posts(), _proposal(), _company(), bands=2)


def _factor(counts: SelectionCounts, name: str) -> FactorMix:
    return next(factor for factor in counts.factors if factor.factor == name)


def _pair(counts: SelectionCounts, name: str, label: str) -> tuple[int, int]:
    group = next(group for group in _factor(counts, name).groups if group.label == label)
    return group.study, group.company


def _text(counts: SelectionCounts, settings: EdaSettings) -> str:
    return "\n".join(render_selection(counts, settings))


def _line(text: str, label: str) -> str:
    return next(line for line in text.splitlines() if line.startswith(f"| {label} |"))


# ---- who is in the study ----------------------------------------------------------------------


def test_the_study_is_the_leaders_with_a_raw_cell_and_a_clear_company_match(counts: SelectionCounts) -> None:
    assert counts.study_leaders == 3  # A, B, C
    assert counts.unmatched_leaders == 1  # D has raw cells but an ambiguous match; E has no raw cell at all
    assert counts.company_rows == 5


def test_the_factors_are_sector_then_size(counts: SelectionCounts) -> None:
    assert tuple(factor.factor for factor in counts.factors) == (SECTOR_FACTOR, SIZE_FACTOR)
    assert all(isinstance(group, GroupMix) for group in counts.factors[0].groups)


# ---- sector and size mix ----------------------------------------------------------------------


def test_sector_counts_compare_the_study_with_all_of_company_data(counts: SelectionCounts) -> None:
    assert _pair(counts, SECTOR_FACTOR, "Tech") == (2, 2)
    assert _pair(counts, SECTOR_FACTOR, "Finance") == (1, 1)
    assert _pair(counts, SECTOR_FACTOR, "Energy") == (0, 2)  # in Company_Data, nobody in the study


def test_size_counts_use_company_data_wide_bands_and_keep_unreadable_sizes_apart(counts: SelectionCounts) -> None:
    assert _pair(counts, SIZE_FACTOR, LOW_BAND) == (1, 2)
    assert _pair(counts, SIZE_FACTOR, HIGH_BAND) == (1, 2)
    assert _pair(counts, SIZE_FACTOR, UNREADABLE_SIZE) == (1, 1)


def test_a_blank_sector_is_its_own_group_not_a_guess() -> None:
    company = _company()
    company.loc[0, "SectorPraticeAreaFeed"] = "."

    result = selection_counts(_posts(), _proposal(), company, bands=2)

    assert _pair(result, SECTOR_FACTOR, BLANK_VALUE) == (1, 1)


def test_groups_are_ordered_largest_in_company_data_first_with_gap_groups_last(counts: SelectionCounts) -> None:
    labels = [group.label for group in _factor(counts, SECTOR_FACTOR).groups]

    assert labels == ["Energy", "Tech", "Finance"]  # 2, 2, 1 firms; ties by label


def test_both_bases_sum_to_their_totals(counts: SelectionCounts) -> None:
    for factor in counts.factors:
        assert sum(group.study for group in factor.groups) == counts.study_leaders
        assert sum(group.company for group in factor.groups) == counts.company_rows


# ---- guards -----------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("frame", "column"),
    [("posts", "text_kind"), ("proposal", "status"), ("company", "NumberofEmployees")],
)
def test_a_missing_column_is_named(frame: str, column: str) -> None:
    frames = {"posts": _posts(), "proposal": _proposal(), "company": _company()}
    frames[frame] = frames[frame].drop(columns=[column])

    with pytest.raises(ValueError, match=column):
        selection_counts(frames["posts"], frames["proposal"], frames["company"], bands=2)


def test_a_company_reference_beyond_the_company_rows_is_refused() -> None:
    proposal = pd.DataFrame([(name_key(A), "clear", "row:99")], columns=["key", "status", "company"])

    with pytest.raises(ValueError, match="beyond"):
        selection_counts(_posts(), proposal, _company(), bands=2)


def test_the_counts_are_frozen(counts: SelectionCounts) -> None:
    with pytest.raises(AttributeError):
        counts.study_leaders = 99  # type: ignore[misc]


def test_the_inputs_are_not_changed() -> None:
    frames = (_posts(), _proposal(), _company())
    before = [frame.copy() for frame in frames]

    selection_counts(*frames, bands=2)

    for frame, original in zip(frames, before, strict=True):
        pd.testing.assert_frame_equal(frame, original)


# ---- rendering --------------------------------------------------------------------------------


def test_rendering_shows_counts_shares_and_the_difference_in_points(counts: SelectionCounts) -> None:
    line = _line(_text(counts, LOOSE), LOW_BAND)

    assert "| 1 | 33.3% | 2 | 40.0% | -6.7 |" in line


def test_rendering_shows_the_study_and_company_totals(counts: SelectionCounts) -> None:
    text = _text(counts, LOOSE)

    assert "| all | 3 | 100.0% | 5 | 100.0% |" in text


def test_rendering_hides_counts_shares_and_differences_under_the_disclosure_minimum(counts: SelectionCounts) -> None:
    text = _text(counts, STRICT)

    assert "| Tech | <5 | <5 | <5 | <5 | <5 |" in text
    assert "%" not in "".join(line for line in text.splitlines() if line.startswith("| Tech"))


def test_rendering_states_the_basis_the_section_and_that_nothing_is_fixed(counts: SelectionCounts) -> None:
    text = _text(counts, LOOSE).lower()

    assert "## 6. possible selection bias" in text
    assert "described, not corrected" in text
    assert "sector and size mix only" in text
    assert "stand in for posts until g1" in text


def test_rendering_has_no_names_company_names_keys_or_refs(counts: SelectionCounts) -> None:
    text = _text(counts, LOOSE)

    for forbidden in (*SENTINELS, COMPANY_SENTINEL, name_key(A), "row:"):
        assert forbidden not in text
