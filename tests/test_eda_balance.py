"""Tests for src.eda_balance: the planned comparisons, each crossed with the post cut (cells stand in for posts)."""
from __future__ import annotations

import pandas as pd
import pytest

from src.eda_balance import (
    BLANK_VALUE,
    CEO_TYPE_FACTOR,
    GENDER_FACTOR,
    NOT_MATCHED,
    SECTOR_FACTOR,
    SIZE_FACTOR,
    TITLE_FACTOR,
    UNREADABLE_SIZE,
    BalanceCounts,
    FactorBalance,
    GroupCount,
    balance_counts,
    render_balance,
)
from src.eda_common import SMALL, EdaSettings
from src.name_key import name_key

LOOSE = EdaSettings(min_posts=2, disclosure_min=1, model_min=1, size_bands=2)
FLAGGING = EdaSettings(min_posts=2, disclosure_min=1, model_min=2, size_bands=2)
STRICT = EdaSettings(min_posts=15, disclosure_min=5, model_min=20, size_bands=4)
SENTINELS = ("Zed Sentinel", "Yara Sentinel", "Xan Sentinel", "Wil Sentinel", "Vic Sentinel")
A, B, C, D, E = SENTINELS
FACTORS = (CEO_TYPE_FACTOR, GENDER_FACTOR, TITLE_FACTOR, SECTOR_FACTOR, SIZE_FACTOR)


def _posts() -> pd.DataFrame:
    """A: 3 raw cells, B: 2, C: 1, D: 2 (conflicting ceo_type); E has a cleaned row only, so never counts."""
    rows = [
        (A, "raw", "CEO", "Professional CEO"),
        (A, "raw", "CEO", "Professional CEO"),
        (A, "raw", ".", ""),
        (B, "raw", "Founder & CEO", "Founder-CEO"),
        (B, "raw", "Founder & CEO", "Founder-CEO"),
        (C, "raw", "Managing Director", ""),
        (D, "raw", "CEO", "Professional CEO"),
        (D, "raw", "CEO", "Founder-CEO"),
        (E, "cleaned", "CEO", "Professional CEO"),
    ]
    return pd.DataFrame(rows, columns=["leader", "text_kind", "title", "ceo_type"])


def _company() -> pd.DataFrame:
    """Rows 1-3 are A, B, C. Rows 4-5 belong to nobody in the posts; they only help set the size bands."""
    rows = [
        ("1", "Tech > SaaS", "100"),
        ("0", "Finance > Banking", "300"),
        ("-", "Tech > Cloud", "500+"),
        ("1", "Energy", "200"),
        ("0", "Energy", "400"),
    ]
    return pd.DataFrame(rows, columns=["Gender", "SectorPraticeAreaFeed", "NumberofEmployees"])


def _proposal() -> pd.DataFrame:
    rows = [
        (name_key(A), "clear", "row:1"),
        (name_key(B), "clear", "row:2"),
        (name_key(C), "clear", "row:3"),
        (name_key(D), "ambiguous", "row:4"),
    ]
    return pd.DataFrame(rows, columns=["key", "status", "company"])


@pytest.fixture
def counts() -> BalanceCounts:
    return balance_counts(_posts(), _proposal(), _company(), min_posts=2, bands=2)


def _factor(counts: BalanceCounts, name: str) -> FactorBalance:
    return next(factor for factor in counts.factors if factor.factor == name)


def _group(counts: BalanceCounts, name: str, label: str) -> GroupCount:
    return next(group for group in _factor(counts, name).groups if group.label == label)


def _pair(counts: BalanceCounts, name: str, label: str) -> tuple[int, int]:
    group = _group(counts, name, label)
    return group.leaders, group.at_cut


# ---- structure --------------------------------------------------------------------------------


def test_every_planned_comparison_has_a_factor(counts: BalanceCounts) -> None:
    assert tuple(factor.factor for factor in counts.factors) == FACTORS


@pytest.mark.parametrize("name", FACTORS)
def test_the_groups_of_every_factor_add_up_to_the_leaders_with_a_raw_cell(counts: BalanceCounts, name: str) -> None:
    groups = _factor(counts, name).groups

    assert sum(group.leaders for group in groups) == 4  # E has a cleaned row only
    assert sum(group.at_cut for group in groups) == 3  # A, B and D have at least 2 raw cells


def test_the_cut_and_the_band_settings_are_recorded(counts: BalanceCounts) -> None:
    assert (counts.min_posts, counts.bands) == (2, 2)
    assert counts.band_edges == (250.0,)


# ---- founder vs professional ------------------------------------------------------------------


def test_ceo_type_is_pooled_per_leader_and_kept_apart_when_conflicting_or_blank(counts: BalanceCounts) -> None:
    assert _pair(counts, CEO_TYPE_FACTOR, "Professional CEO") == (1, 1)
    assert _pair(counts, CEO_TYPE_FACTOR, "Founder-CEO") == (1, 1)
    assert _pair(counts, CEO_TYPE_FACTOR, "conflicting") == (1, 1)
    assert _pair(counts, CEO_TYPE_FACTOR, BLANK_VALUE) == (1, 0)


# ---- gender as coded --------------------------------------------------------------------------


def test_gender_is_counted_as_coded_with_blank_and_unmatched_apart(counts: BalanceCounts) -> None:
    assert _pair(counts, GENDER_FACTOR, "coded 1 (man)") == (1, 1)
    assert _pair(counts, GENDER_FACTOR, "coded 0 (woman)") == (1, 1)
    assert _pair(counts, GENDER_FACTOR, BLANK_VALUE) == (1, 0)
    assert _pair(counts, GENDER_FACTOR, NOT_MATCHED) == (1, 1)  # D is ambiguous, so never guessed


# ---- title family -----------------------------------------------------------------------------


def test_title_family_follows_the_keyword_rule_pooled_over_a_leaders_cells(counts: BalanceCounts) -> None:
    assert _pair(counts, TITLE_FACTOR, "CEO") == (3, 3)  # "Founder & CEO" is a CEO title
    assert _pair(counts, TITLE_FACTOR, "Managing director") == (1, 0)


# ---- sector and size --------------------------------------------------------------------------


def test_sector_is_the_first_segment_with_unmatched_leaders_apart(counts: BalanceCounts) -> None:
    assert _pair(counts, SECTOR_FACTOR, "Tech") == (2, 1)
    assert _pair(counts, SECTOR_FACTOR, "Finance") == (1, 1)
    assert _pair(counts, SECTOR_FACTOR, NOT_MATCHED) == (1, 1)


def test_size_bands_are_cut_over_the_whole_company_table_and_unreadable_sizes_stay_apart(
    counts: BalanceCounts,
) -> None:
    assert _pair(counts, SIZE_FACTOR, "size band 1 (smallest)") == (1, 1)
    assert _pair(counts, SIZE_FACTOR, "size band 2 (largest)") == (1, 1)
    assert _pair(counts, SIZE_FACTOR, UNREADABLE_SIZE) == (1, 0)  # "500+" is not guessed at
    assert _pair(counts, SIZE_FACTOR, NOT_MATCHED) == (1, 1)


# ---- errors and immutability ------------------------------------------------------------------


@pytest.mark.parametrize("column", ["title", "ceo_type"])
def test_a_missing_posts_column_is_named(column: str) -> None:
    with pytest.raises(ValueError, match=column):
        balance_counts(_posts().drop(columns=[column]), _proposal(), _company(), min_posts=2, bands=2)


def test_a_missing_company_column_is_named() -> None:
    with pytest.raises(ValueError, match="NumberofEmployees"):
        balance_counts(_posts(), _proposal(), _company().drop(columns=["NumberofEmployees"]), min_posts=2, bands=2)


def test_a_missing_proposal_column_is_named() -> None:
    with pytest.raises(ValueError, match="status"):
        balance_counts(_posts(), _proposal().drop(columns=["status"]), _company(), min_posts=2, bands=2)


def test_the_counts_are_frozen(counts: BalanceCounts) -> None:
    with pytest.raises(AttributeError):
        counts.min_posts = 99  # type: ignore[misc]


def test_the_inputs_are_not_changed() -> None:
    posts, company = _posts(), _company()
    before = (posts.copy(), company.copy())

    balance_counts(posts, _proposal(), company, min_posts=2, bands=2)

    pd.testing.assert_frame_equal(posts, before[0])
    pd.testing.assert_frame_equal(company, before[1])


# ---- rendering --------------------------------------------------------------------------------


def _text(counts: BalanceCounts, settings: EdaSettings) -> str:
    return "\n".join(render_balance(counts, settings))


def _line(text: str, label: str) -> str:
    return next(line for line in text.splitlines() if line.startswith(f"| {label} |"))


def test_rendering_shows_leaders_and_shares_for_both_bases(counts: BalanceCounts) -> None:
    assert "| Tech | 2 | 50.0% | 1 | 33.3% |" in _text(counts, LOOSE)


def test_rendering_hides_small_counts_under_the_strict_minimum(counts: BalanceCounts) -> None:
    assert f"| Tech | {SMALL} | {SMALL} | {SMALL} | {SMALL} |" in _text(counts, STRICT)


def test_a_group_below_the_modelling_minimum_at_the_cut_is_flagged(counts: BalanceCounts) -> None:
    text = _text(counts, FLAGGING)

    assert "too small to model" in _line(text, "Managing director")  # no leader at the cut
    assert "too small to model" not in _line(text, "CEO")  # 3 leaders at the cut


def test_rendering_names_the_factors_the_cut_and_the_caveats(counts: BalanceCounts) -> None:
    text = _text(counts, LOOSE).lower()

    assert "## 3. balance" in text
    for name in FACTORS:
        assert f"### {name}".lower() in text
    assert "at least 2 raw cells" in text
    assert "stand in for posts until g1" in text
    assert "proposal for the mentors" in text
    assert "as coded" in text


def test_rendering_has_no_names_keys_or_refs(counts: BalanceCounts) -> None:
    text = _text(counts, LOOSE)

    for forbidden in (*SENTINELS, "row:", name_key(A)):
        assert forbidden not in text
