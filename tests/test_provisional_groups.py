"""Per-leader group labels for the provisional comparisons (src/provisional_groups.py). Invented names and numbers only.

Labels are keyed by leader_id: the name key is turned into an id in memory, so no name reaches a file.
"""
from __future__ import annotations

import hashlib

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
)
from src.name_key import name_key
from src.provisional_groups import FACTORS, GROUP_COLUMNS, leader_groups

SENTINELS = ("Zed Sentinel", "Yara Sentinel", "Xan Sentinel", "Wil Sentinel", "Vic Sentinel")
A, B, C, D, E = SENTINELS


def fake_id(key: str) -> str:
    """A stable stand-in for the keyed HMAC id: unique per key, and not reversible to it."""
    return "L" + hashlib.sha256(key.encode("utf-8")).hexdigest()[:10]


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


def _labels() -> pd.DataFrame:
    return leader_groups(_posts(), _proposal(), _company(), bands=2, id_of=fake_id)


def _row(labels: pd.DataFrame, name: str) -> pd.Series:
    return labels.loc[labels["leader_id"] == fake_id(name_key(name))].iloc[0]


def test_columns_are_the_id_then_the_five_factors() -> None:
    labels = _labels()

    assert tuple(labels.columns) == GROUP_COLUMNS
    assert GROUP_COLUMNS == ("leader_id", *FACTORS)
    assert FACTORS == (CEO_TYPE_FACTOR, TITLE_FACTOR, GENDER_FACTOR, SECTOR_FACTOR, SIZE_FACTOR)


def test_one_row_per_leader_with_a_raw_cell_and_the_cleaned_only_leader_is_left_out() -> None:
    labels = _labels()

    assert len(labels) == 4
    assert labels["leader_id"].is_unique
    assert fake_id(name_key(E)) not in set(labels["leader_id"])


def test_no_name_or_name_key_appears_anywhere_in_the_frame() -> None:
    labels = _labels()
    text = labels.to_csv(index=False)

    for name in SENTINELS:
        assert name not in text
        assert name_key(name) not in text


def test_ceo_type_and_title_family_come_from_the_leaders_cells() -> None:
    labels = _labels()

    assert _row(labels, A)[CEO_TYPE_FACTOR] == "Professional CEO"
    assert _row(labels, B)[CEO_TYPE_FACTOR] == "Founder-CEO"
    assert _row(labels, C)[CEO_TYPE_FACTOR] == BLANK_VALUE
    assert _row(labels, D)[CEO_TYPE_FACTOR] == "conflicting"
    assert _row(labels, C)[TITLE_FACTOR] == "Managing director"


def test_gender_is_used_as_coded_and_never_guessed_for_an_unmatched_leader() -> None:
    labels = _labels()

    assert _row(labels, A)[GENDER_FACTOR] == "coded 1"
    assert _row(labels, B)[GENDER_FACTOR] == "coded 0"
    assert _row(labels, C)[GENDER_FACTOR] == BLANK_VALUE
    assert _row(labels, D)[GENDER_FACTOR] == NOT_MATCHED


def test_sector_and_size_band_follow_the_company_match() -> None:
    labels = _labels()

    assert _row(labels, A)[SECTOR_FACTOR] == "Tech"
    assert _row(labels, B)[SECTOR_FACTOR] == "Finance"
    assert _row(labels, D)[SECTOR_FACTOR] == NOT_MATCHED
    assert _row(labels, A)[SIZE_FACTOR] == "size band 1 (smallest)"
    assert _row(labels, B)[SIZE_FACTOR] == "size band 2 (largest)"


def test_a_missing_column_is_named_in_the_error() -> None:
    broken = _company().drop(columns=["Gender"])

    with pytest.raises(ValueError, match="Gender"):
        leader_groups(_posts(), _proposal(), broken, bands=2, id_of=fake_id)
