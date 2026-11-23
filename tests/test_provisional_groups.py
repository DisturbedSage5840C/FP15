"""Per-leader group labels for the provisional comparisons (src/provisional_groups.py). Invented names and numbers only.

Firm and group variables come from the leader master; ceo_type and title come from the post sheets. Labels are keyed
by leader_id: the name key is turned into an id in memory, so no name reaches a file.
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
    OTHER_GENDER_CODE,
    SECTOR_FACTOR,
    SIZE_FACTOR,
    TITLE_FACTOR,
)
from src.name_key import name_key
from src.provisional_groups import FACTORS, GROUP_COLUMNS, leader_groups

SENTINELS = ("Zed Sentinel", "Yara Sentinel", "Xan Sentinel", "Wil Sentinel", "Vic Sentinel", "Uma Sentinel")
A, B, C, D, E, G = SENTINELS
NOT_IN_POSTS = "Tee Sentinel"
CODING = {"1": "man", "0": "woman"}


def fake_id(key: str) -> str:
    """A stable stand-in for the keyed HMAC id: unique per key, and not reversible to it."""
    return "L" + hashlib.sha256(key.encode("utf-8")).hexdigest()[:10]


def _posts() -> pd.DataFrame:
    """A: 3 raw cells, B: 2, C: 1, D: 2 (conflicting ceo_type), G: 1; E has a cleaned row only, so never counts."""
    rows = [
        (A, "raw", "CEO", "Professional CEO"),
        (A, "raw", "CEO", "Professional CEO"),
        (A, "raw", ".", ""),
        (B, "raw", "Founder & CEO", "Founder-CEO"),
        (B, "raw", "Founder & CEO", "Founder-CEO"),
        (C, "raw", "Managing Director", ""),
        (D, "raw", "CEO", "Professional CEO"),
        (D, "raw", "CEO", "Founder-CEO"),
        (G, "raw", "CEO", "Founder-CEO"),
        (E, "cleaned", "CEO", "Professional CEO"),
    ]
    return pd.DataFrame(rows, columns=["leader", "text_kind", "title", "ceo_type"])


def _master() -> pd.DataFrame:
    """A man, B woman, C blank gender, D no firm columns, G an unexpected code, E no raw cells, a leader not in posts."""
    rows = [
        (A, "person_and_firm", "1", "Tech > SaaS", "100"),
        (B, "person_and_firm", "0", "Finance > Banking", "300"),
        (C, "person_and_firm", "", "Tech > Cloud", "500+"),
        (D, "none", "", "", ""),
        (E, "person_and_firm", "1", "Energy", "200"),
        (NOT_IN_POSTS, "person_and_firm", "0", "Energy", "400"),
        (G, "person_and_firm", "2", "Energy", "150"),
    ]
    frame = pd.DataFrame(
        rows, columns=["name", "columns_scope", "Gender", "SectorPraticeAreaFeed", "NumberofEmployees"]
    )
    frame.insert(0, "leader_id", [fake_id(name_key(name)) for name in frame.pop("name")])
    return frame


def _labels(**overrides: object) -> pd.DataFrame:
    args: dict[str, object] = {"posts": _posts(), "master": _master(), "bands": 2, "id_of": fake_id, "coding": CODING}
    args.update(overrides)
    return leader_groups(**args)  # type: ignore[arg-type]


def _row(labels: pd.DataFrame, name: str) -> dict[str, str]:
    return dict(labels.loc[labels["leader_id"] == fake_id(name_key(name))].iloc[0])


def test_columns_are_the_id_then_the_five_factors() -> None:
    labels = _labels()

    assert tuple(labels.columns) == GROUP_COLUMNS
    assert GROUP_COLUMNS == ("leader_id", *FACTORS)
    assert FACTORS == (CEO_TYPE_FACTOR, TITLE_FACTOR, GENDER_FACTOR, SECTOR_FACTOR, SIZE_FACTOR)


def test_one_row_per_leader_with_a_raw_cell_and_others_are_left_out() -> None:
    labels = _labels()

    assert len(labels) == 5
    assert labels["leader_id"].is_unique
    assert fake_id(name_key(E)) not in set(labels["leader_id"])
    assert fake_id(name_key(NOT_IN_POSTS)) not in set(labels["leader_id"])


def test_no_name_or_name_key_appears_anywhere_in_the_frame() -> None:
    text = _labels().to_csv(index=False)

    for name in SENTINELS:
        assert name not in text
        assert name_key(name) not in text


def test_ceo_type_and_title_family_come_from_the_leaders_post_cells() -> None:
    labels = _labels()

    assert _row(labels, A)[CEO_TYPE_FACTOR] == "Professional CEO"
    assert _row(labels, B)[CEO_TYPE_FACTOR] == "Founder-CEO"
    assert _row(labels, C)[CEO_TYPE_FACTOR] == BLANK_VALUE
    assert _row(labels, D)[CEO_TYPE_FACTOR] == "conflicting"
    assert _row(labels, C)[TITLE_FACTOR] == "Managing director"


def test_gender_uses_the_confirmed_labels_and_blank_stays_missing() -> None:
    labels = _labels()

    assert _row(labels, A)[GENDER_FACTOR] == "man"
    assert _row(labels, B)[GENDER_FACTOR] == "woman"
    assert _row(labels, C)[GENDER_FACTOR] == BLANK_VALUE
    assert _row(labels, D)[GENDER_FACTOR] == NOT_MATCHED
    assert _row(labels, G)[GENDER_FACTOR] == OTHER_GENDER_CODE


def test_gender_words_come_from_the_coding_passed_in() -> None:
    labels = _labels(coding={"1": "label-one", "0": "label-zero"})

    assert _row(labels, A)[GENDER_FACTOR] == "label-one"
    assert _row(labels, B)[GENDER_FACTOR] == "label-zero"


def test_a_code_missing_from_the_coding_is_shown_as_the_bare_code_not_guessed() -> None:
    labels = _labels(coding={"1": "man"})

    assert _row(labels, B)[GENDER_FACTOR] == "coded 0"


def test_sector_and_size_band_follow_the_master_row() -> None:
    labels = _labels()

    assert _row(labels, A)[SECTOR_FACTOR] == "Tech"
    assert _row(labels, B)[SECTOR_FACTOR] == "Finance"
    assert _row(labels, D)[SECTOR_FACTOR] == NOT_MATCHED
    assert _row(labels, A)[SIZE_FACTOR] == "size band 1 (smallest)"
    assert _row(labels, B)[SIZE_FACTOR] == "size band 2 (largest)"
    assert _row(labels, D)[SIZE_FACTOR] == NOT_MATCHED


def test_a_post_leader_missing_from_the_master_is_an_error_not_a_silent_drop() -> None:
    with pytest.raises(ValueError, match="not in the leader master"):
        _labels(master=_master().iloc[1:])


def test_a_missing_master_column_is_named_in_the_error() -> None:
    with pytest.raises(ValueError, match="Gender"):
        _labels(master=_master().drop(columns=["Gender"]))


def test_a_missing_post_column_is_named_in_the_error() -> None:
    with pytest.raises(ValueError, match="ceo_type"):
        _labels(posts=_posts().drop(columns=["ceo_type"]))


FIRM_ONLY_LEADER = "Sam Sentinel"


def _with_firm_only_leader() -> tuple[pd.DataFrame, pd.DataFrame]:
    """The usual posts and master plus one leader matched to a firm only: firm columns filled, person columns blank."""
    posts = pd.concat(
        [_posts(), pd.DataFrame([(FIRM_ONLY_LEADER, "raw", "CEO", "Professional CEO")], columns=_posts().columns)],
        ignore_index=True,
    )
    extra = pd.DataFrame(
        [(fake_id(name_key(FIRM_ONLY_LEADER)), "firm_only", "", "Energy > Solar", "100")], columns=_master().columns
    )
    return posts, pd.concat([_master(), extra], ignore_index=True)


def test_a_firm_only_leader_keeps_sector_and_size_but_gender_is_not_matched() -> None:
    posts, master = _with_firm_only_leader()

    labels = _labels(posts=posts, master=master)

    row = _row(labels, FIRM_ONLY_LEADER)
    assert row[SECTOR_FACTOR] == "Energy"
    assert row[SIZE_FACTOR] == "size band 1 (smallest)"
    assert row[GENDER_FACTOR] == NOT_MATCHED


def test_a_leader_with_a_shared_key_entry_id_gets_an_error_that_names_the_shared_key() -> None:
    master = _master()
    shared = master["leader_id"] == fake_id(name_key(A))
    master.loc[shared, "leader_id"] = fake_id(f"{name_key(A)}|sheets|1")

    with pytest.raises(ValueError, match="shared"):
        _labels(master=master)


def test_duplicate_leader_ids_in_the_master_are_an_error_not_an_arbitrary_pick() -> None:
    master = _master()
    duplicate = master.iloc[[0]].assign(Gender="0")

    with pytest.raises(ValueError, match="duplicate"):
        _labels(master=pd.concat([master, duplicate], ignore_index=True))


def test_size_band_edges_come_from_every_firm_row_in_the_master_not_only_the_posting_leaders() -> None:
    posts = _posts().query("leader in [@A, @B]")
    far = pd.DataFrame(
        [(fake_id(name_key(f"Far{i} Sentinel")), "person_and_firm", "1", "Energy", str(size)) for i, size in enumerate((1000, 2000, 3000))],
        columns=_master().columns,
    )
    master = pd.concat([_master().iloc[:2], far], ignore_index=True)

    labels = _labels(posts=posts, master=master)

    assert _row(labels, B)[SIZE_FACTOR] == "size band 1 (smallest)"
