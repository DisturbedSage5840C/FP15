"""Tests for src.eda_quality: quality issues already found, as counts only (nothing is corrected here)."""
from __future__ import annotations

import pandas as pd
import pytest

from src.ceo_gender_counts import CeoTypeCounts
from src.eda_common import EdaSettings
from src.eda_quality import QualityCounts, quality_counts, render_quality
from src.name_key import name_key

LOOSE = EdaSettings(min_posts=3, disclosure_min=1, model_min=1, size_bands=2)
STRICT = EdaSettings(min_posts=15, disclosure_min=5, model_min=20, size_bands=4)
SENTINELS = ("Zed Sentinel", "Yara Sentinel", "Xan Sentinel", "Wil Sentinel")
A, B, C, D = SENTINELS
LEAKY_VALUE = "LEAKY-CEO-VALUE"
LEADER_IDS = ("LEADERID-SENTINEL-1", "LEADERID-SENTINEL-2")
REF = "ZREF"


def _posts() -> pd.DataFrame:
    """A: 2 professional cells. B: 1 founder + 1 blank. C: 2 blank. D: 1 cell that is neither label."""
    rows = [
        (A, "Professional CEO", "raw"),
        (A, "Professional CEO", "raw"),
        (B, "Founder-CEO", "raw"),
        (B, "", "raw"),
        (C, "", "raw"),
        (C, ".", "raw"),
        (D, LEAKY_VALUE, "raw"),
    ]
    return pd.DataFrame(rows, columns=["leader", "ceo_type", "text_kind"])


def _leaders() -> pd.DataFrame:
    rows = [(LEADER_IDS[0], "exact", "5")] * 3 + [(LEADER_IDS[1], "none", "4"), (LEADER_IDS[1], "ambiguous", "2")]
    return pd.DataFrame(rows, columns=["leader_id", "company_match", "n_raw_post_cells"])


def _proposal() -> pd.DataFrame:
    """Repeated names: roster 2 keys, summaries 2 keys, sheets and company none."""
    rows = [
        ("k1", "clear", f"{REF}1", f"{REF}2;{REF}3", f"{REF}4;{REF}5", f"{REF}6"),
        ("k2", "ambiguous", "", f"{REF}7;{REF}8", "", ""),
        ("k3", "clear", f"{REF}9", f"{REF}10", f"{REF}11;{REF}12", ""),
    ]
    return pd.DataFrame(rows, columns=["key", "status", "sheets", "roster", "summaries", "company"])


def _matches() -> pd.DataFrame:
    rows = [
        ("sheets", "company", "true"),
        ("sheets", "company", "true"),
        ("sheets", "company", "false"),
        ("sheets", "company", ""),
        ("roster", "company", "false"),
        ("roster", "company", "false"),
        ("summaries", "roster", "true"),
    ]
    return pd.DataFrame(rows, columns=["source_a", "source_b", "company_agrees"])


def _clean() -> pd.DataFrame:
    languages = ["English"] * 4 + ["Hinglish"] * 2 + ["mixed"]
    return pd.DataFrame({"leader_id": [LEADER_IDS[0]] * 7, "language": languages})


def _frames() -> dict[str, pd.DataFrame]:
    return {"posts": _posts(), "leaders": _leaders(), "proposal": _proposal(), "matches": _matches(), "clean": _clean()}


def _counts(**replace: pd.DataFrame) -> QualityCounts:
    return quality_counts(**{**_frames(), **replace})


@pytest.fixture
def counts() -> QualityCounts:
    return _counts()


def _text(counts: QualityCounts, settings: EdaSettings) -> str:
    return "\n".join(render_quality(counts, settings))


def _line(text: str, label: str) -> str:
    return next(line for line in text.splitlines() if line.startswith(f"| {label} |"))


# ---- counting ---------------------------------------------------------------------------------


def test_the_ceo_type_split_reuses_the_committed_counts_with_shifted_and_blank_cells_apart(
    counts: QualityCounts,
) -> None:
    assert isinstance(counts.ceo_type, CeoTypeCounts)
    assert (counts.ceo_type.cells_unrecognised, counts.ceo_type.unrecognised_only) == (1, 1)
    assert (counts.ceo_type.cells_blank, counts.ceo_type.blank) == (3, 1)  # blank markers count as blank


def test_repeated_names_are_keys_held_by_two_or_more_entities_per_source_list(counts: QualityCounts) -> None:
    assert dict(counts.repeated_keys) == {"sheets": 0, "roster": 2, "summaries": 2, "company": 0}


def test_keys_flagged_ambiguous_in_the_id_proposal_are_counted(counts: QualityCounts) -> None:
    assert counts.ambiguous_keys == 1


def test_company_matches_are_counted_by_kind_largest_first(counts: QualityCounts) -> None:
    assert counts.company_match[0] == ("exact", 3)
    assert dict(counts.company_match) == {"exact": 3, "none": 1, "ambiguous": 1}


def test_a_blank_company_match_gets_its_own_label() -> None:
    leaders = pd.DataFrame({"company_match": ["", "exact"]})

    assert dict(_counts(leaders=leaders).company_match) == {"exact": 1, "blank": 1}


def test_company_differs_counts_rows_where_the_company_disagrees_for_every_source_pair(counts: QualityCounts) -> None:
    assert dict(counts.company_differs) == {"sheets to company": 1, "roster to company": 2, "summaries to roster": 0}


def test_languages_are_counted_with_their_total(counts: QualityCounts) -> None:
    assert dict(counts.languages) == {"English": 4, "Hinglish": 2, "mixed": 1}
    assert counts.language_rows == 7


@pytest.mark.parametrize(
    ("frame", "column"),
    [
        ("posts", "ceo_type"),
        ("leaders", "company_match"),
        ("proposal", "roster"),
        ("matches", "company_agrees"),
        ("clean", "language"),
    ],
)
def test_a_missing_column_is_named(frame: str, column: str) -> None:
    with pytest.raises(ValueError, match=column):
        _counts(**{frame: _frames()[frame].drop(columns=[column])})


def test_the_counts_are_frozen(counts: QualityCounts) -> None:
    with pytest.raises(AttributeError):
        counts.language_rows = 99  # type: ignore[misc]


def test_the_inputs_are_not_changed() -> None:
    frames = _frames()
    before = {name: frame.copy() for name, frame in frames.items()}

    quality_counts(**frames)

    for name, frame in frames.items():
        pd.testing.assert_frame_equal(frame, before[name])


# ---- rendering --------------------------------------------------------------------------------


def test_rendering_shows_the_ceo_type_issues_as_leaders_and_cells(counts: QualityCounts) -> None:
    text = _text(counts, LOOSE)

    assert "| 1 | 3 |" in _line(text, "ceo_type blank")
    assert "| 1 | 1 |" in _line(text, "ceo_type neither label (shifted)")


def test_rendering_shows_repeated_names_per_source_list(counts: QualityCounts) -> None:
    text = _text(counts, LOOSE)

    assert "| roster | 2 |" in text
    assert "| summaries | 2 |" in text
    assert "| keys flagged ambiguous | 1 |" in text


def test_rendering_shows_company_matches_mismatches_and_languages_with_totals(counts: QualityCounts) -> None:
    text = _text(counts, LOOSE)

    assert "| exact | 3 |" in text
    assert "| roster to company | 2 |" in text
    assert "| Hinglish | 2 |" in text
    assert "| all | 7 |" in text  # the language total


def test_rendering_hides_every_count_under_the_disclosure_minimum(counts: QualityCounts) -> None:
    text = _text(counts, STRICT)

    assert "| exact | <5 |" in text
    assert "| Hinglish | <5 |" in text
    assert "| roster | <5 |" in text
    assert "<5 | <5 |" in _line(text, "ceo_type blank")


def test_rendering_names_the_section_and_says_nothing_was_corrected(counts: QualityCounts) -> None:
    text = _text(counts, LOOSE).lower()

    assert "## 5. quality issues already found" in text
    assert "counts only" in text
    assert "nothing here was corrected" in text


def test_rendering_has_no_names_values_ids_or_refs(counts: QualityCounts) -> None:
    text = _text(counts, LOOSE)

    for forbidden in (*SENTINELS, name_key(A), LEAKY_VALUE, *LEADER_IDS, REF, "row:"):
        assert forbidden not in text
