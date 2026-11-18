"""Tests for src.eda_groups: sector, size bands, title family and the Company_Data match lookup."""
from __future__ import annotations

import pandas as pd
import pytest

from src.eda_groups import (
    BLANK_TITLE,
    MIXED_TITLES,
    OTHER_TITLE,
    classify_matches,
    leader_title_family,
    proposal_lookup,
    sector_of,
    size_band,
    size_band_edges,
    size_band_label,
)

# ---- sector -----------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("Tech > SaaS", "Tech"),
        ("  Finance  >  Banking > Retail ", "Finance"),
        ("Energy", "Energy"),
        ("-", None),
        (".", None),
        ("", None),
        (" > Orphan", None),
        (None, None),
    ],
)
def test_sector_is_the_first_segment_as_coded(value: object, expected: str | None) -> None:
    assert sector_of(value) == expected


# ---- size bands -------------------------------------------------------------------------------


def test_size_band_edges_are_quantile_cut_points_of_the_readable_values() -> None:
    values = ["100", "200", "300", "400", "500+", "", "-"]

    assert size_band_edges(values, bands=2) == (250.0,)


def test_size_band_edges_use_one_parser_for_suffixes() -> None:
    values = ["1K", "2K", "3K", "4K"]

    assert size_band_edges(values, bands=2) == (2500.0,)


def test_size_band_edges_need_at_least_one_value_per_band() -> None:
    with pytest.raises(ValueError, match="readable"):
        size_band_edges(["100", "200", "x"], bands=4)


def test_a_value_on_an_edge_falls_in_the_lower_band() -> None:
    edges = (250.0,)

    assert size_band("250", edges) == 1
    assert size_band("251", edges) == 2
    assert size_band("100", edges) == 1


def test_an_unreadable_size_has_no_band() -> None:
    assert size_band("500+", (250.0,)) is None
    assert size_band("", (250.0,)) is None


def test_band_labels_name_the_smallest_and_largest() -> None:
    assert size_band_label(1, 4) == "size band 1 (smallest)"
    assert size_band_label(2, 4) == "size band 2"
    assert size_band_label(4, 4) == "size band 4 (largest)"


# ---- title family -----------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("titles", "expected"),
    [
        (["CEO"], "CEO"),
        (["Founder & CEO"], "CEO"),
        (["Chief Executive Officer"], "CEO"),
        (["Managing Director"], "Managing director"),
        (["Chairman and Managing Director"], "Managing director"),
        (["Chairperson"], "Chair"),
        (["Co-Founder"], "Founder"),
        (["President"], "President"),
        (["CFO"], "Other chief officer"),
        (["Chief Technology Officer"], "Other chief officer"),
        (["Head of Strategy"], OTHER_TITLE),
        (["CEO", "Founder & CEO"], "CEO"),
        (["CEO", "Managing Director"], MIXED_TITLES),
        ([], BLANK_TITLE),
        (["", ".", "-", None], BLANK_TITLE),
    ],
)
def test_title_family_is_a_keyword_rule_pooled_over_a_leaders_titles(titles: list[object], expected: str) -> None:
    assert leader_title_family(titles) == expected


def test_a_word_that_only_contains_ceo_letters_is_not_a_ceo() -> None:
    assert leader_title_family(["Surceon"]) == OTHER_TITLE


# ---- company match lookup ---------------------------------------------------------------------


def _proposal() -> pd.DataFrame:
    rows = [
        ("k1", "clear", "row:1"),
        ("k2", "clear", "row:3"),
        ("k3", "ambiguous", "row:2"),
        ("k4", "clear", ""),
    ]
    return pd.DataFrame(rows, columns=["key", "status", "company"])


def test_the_lookup_maps_each_key_to_status_and_reference() -> None:
    assert proposal_lookup(_proposal())["k3"] == ("ambiguous", "row:2")


def test_matches_are_split_into_positions_and_every_other_outcome() -> None:
    lookup = proposal_lookup(_proposal())

    positions, others = classify_matches({"k1", "k2", "k3", "k4", "k9"}, lookup, company_rows=3)

    assert positions == {"k1": 0, "k2": 2}
    assert others == {"ambiguous": 1, "no_company_row": 1, "not_in_proposal": 1}


def test_a_reference_beyond_the_company_rows_is_an_error() -> None:
    lookup = proposal_lookup(_proposal())

    with pytest.raises(ValueError, match="beyond"):
        classify_matches({"k2"}, lookup, company_rows=2)
