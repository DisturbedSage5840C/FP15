"""Tests for src.eda_coverage: leaders by source list, overlap, leaders with posts and with 15+ raw cells."""
from __future__ import annotations

import pandas as pd
import pytest

from src.eda_common import SMALL, EdaSettings
from src.eda_coverage import (
    CoverageCounts,
    ListCoverage,
    coverage_counts,
    render_coverage,
)

LOOSE = EdaSettings(min_posts=2, disclosure_min=1, model_min=1, size_bands=2)
STRICT = EdaSettings(min_posts=15, disclosure_min=5, model_min=20, size_bands=4)
PROPOSAL_COLUMNS = ["leader_id", "key", "status", "sheets", "roster", "summaries", "company"]
LEADER_COLUMNS = ["leader_id", "n_raw_post_cells"]


def _proposal(rows: list[tuple[str, str, str, str, str, str]]) -> pd.DataFrame:
    """Rows are (leader_id, status, sheets, roster, summaries, company); a non-empty string means listed."""
    return pd.DataFrame(
        [(lid, f"key {lid}", status, s, r, m, c) for lid, status, s, r, m, c in rows],
        columns=PROPOSAL_COLUMNS,
    )


def _leaders(cells: dict[str, int]) -> pd.DataFrame:
    return pd.DataFrame([(lid, str(n)) for lid, n in cells.items()], columns=LEADER_COLUMNS)


@pytest.fixture
def frames() -> tuple[pd.DataFrame, pd.DataFrame]:
    proposal = _proposal(
        [
            ("L1", "clear", "w#1", "row:1", "s1", "row:1"),  # all four lists, 3 cells
            ("L2", "clear", "w#2", "row:2", "", "row:2"),  # posts + roster + company, 1 cell
            ("L3", "clear", "w#3", "", "", ""),  # posts only, 2 cells
            ("L4", "clear", "", "row:4", "s4", ""),  # no posts, roster + summaries
            ("L5", "ambiguous", "", "", "", "row:5"),  # no posts, company only, ambiguous key
        ]
    )
    leaders = _leaders({"L1": 3, "L2": 1, "L3": 2})
    return proposal, leaders


# ---- counts -----------------------------------------------------------------------------------


def test_union_and_ambiguous_counts_come_from_the_proposal(frames: tuple[pd.DataFrame, pd.DataFrame]) -> None:
    counts = coverage_counts(*frames, min_posts=2)

    assert counts.union == 5
    assert counts.ambiguous == 1


def test_each_list_reports_its_leaders_those_with_a_cell_and_those_at_the_cut(
    frames: tuple[pd.DataFrame, pd.DataFrame],
) -> None:
    counts = coverage_counts(*frames, min_posts=2)
    by_name = {entry.name: entry for entry in counts.lists}

    assert by_name["All_500 roster"] == ListCoverage("All_500 roster", leaders=3, with_cell=2, at_cut=1)
    assert by_name["Summaries"] == ListCoverage("Summaries", leaders=2, with_cell=1, at_cut=1)
    assert by_name["Company_Data"] == ListCoverage("Company_Data", leaders=3, with_cell=2, at_cut=1)
    assert by_name["Post workbooks"] == ListCoverage("Post workbooks", leaders=3, with_cell=3, at_cut=2)


def test_overlap_counts_each_membership_pattern_of_the_three_lists(
    frames: tuple[pd.DataFrame, pd.DataFrame],
) -> None:
    counts = coverage_counts(*frames, min_posts=2)
    overlap = dict(counts.overlap)

    assert overlap["All_500 + Summaries + Company_Data"] == 1
    assert overlap["All_500 + Company_Data"] == 1
    assert overlap["All_500 + Summaries"] == 1
    assert overlap["Company_Data only"] == 1
    assert overlap["none of the three lists"] == 1
    assert overlap["All_500 only"] == 0
    assert sum(overlap.values()) == counts.union


def test_leaders_with_posts_and_at_the_cut_count_the_raw_cells(
    frames: tuple[pd.DataFrame, pd.DataFrame],
) -> None:
    counts = coverage_counts(*frames, min_posts=2)

    assert counts.with_posts == 3
    assert counts.at_cut == 2
    assert counts.raw_cells == 6
    assert counts.min_posts == 2


def test_a_leader_with_a_blank_or_zero_cell_count_is_not_with_posts() -> None:
    proposal = _proposal([("L1", "clear", "w#1", "", "", "")])

    counts = coverage_counts(proposal, _leaders({"L1": 0}), min_posts=15)

    assert counts.with_posts == 0


def test_leaders_with_no_id_in_the_proposal_are_counted_not_dropped_and_not_guessed() -> None:
    # The proposal leaves leader_id blank on ambiguous name keys, so these leaders cannot be joined by id.
    proposal = _proposal([("L1", "clear", "w#1", "", "", ""), ("", "ambiguous", "w#2", "", "s2", "row:2")])

    counts = coverage_counts(proposal, _leaders({"L1": 3, "L9": 4, "L8": 1}), min_posts=2)

    assert counts.unlinked == 2
    assert counts.unlinked_at_cut == 1
    assert counts.with_posts == 3
    assert counts.at_cut == 2
    assert counts.raw_cells == 8
    assert counts.union == 2


def test_unlinked_leaders_are_not_added_to_any_source_list_or_overlap_row() -> None:
    proposal = _proposal([("L1", "clear", "w#1", "row:1", "", ""), ("", "ambiguous", "w#2", "", "s2", "")])

    counts = coverage_counts(proposal, _leaders({"L1": 3, "L9": 4}), min_posts=2)
    by_name = {entry.name: entry for entry in counts.lists}

    assert by_name["Post workbooks"] == ListCoverage("Post workbooks", leaders=2, with_cell=1, at_cut=1)
    assert sum(dict(counts.overlap).values()) == counts.union


def test_no_unlinked_leaders_when_every_leader_table_id_is_in_the_proposal(
    frames: tuple[pd.DataFrame, pd.DataFrame],
) -> None:
    counts = coverage_counts(*frames, min_posts=2)

    assert counts.unlinked == 0
    assert counts.unlinked_at_cut == 0


def test_rendering_reports_the_unlinked_leaders_and_hides_small_counts() -> None:
    proposal = _proposal([("L1", "clear", "w#1", "", "", "")])
    counts = coverage_counts(proposal, _leaders({"L1": 3, "L9": 4}), min_posts=2)

    loose, strict = _text(counts, LOOSE), _text(counts, STRICT)

    assert "| Leaders with raw cells but no leader id in the proposal | 1 |" in loose
    assert f"| Leaders with raw cells but no leader id in the proposal | {SMALL} |" in strict


@pytest.mark.parametrize("missing", ["status", "roster"])
def test_a_missing_proposal_column_is_named(missing: str, frames: tuple[pd.DataFrame, pd.DataFrame]) -> None:
    proposal, leaders = frames

    with pytest.raises(ValueError, match=missing):
        coverage_counts(proposal.drop(columns=[missing]), leaders, min_posts=2)


def test_a_missing_leader_table_column_is_named(frames: tuple[pd.DataFrame, pd.DataFrame]) -> None:
    proposal, leaders = frames

    with pytest.raises(ValueError, match="n_raw_post_cells"):
        coverage_counts(proposal, leaders.drop(columns=["n_raw_post_cells"]), min_posts=2)


def test_the_counts_object_is_frozen(frames: tuple[pd.DataFrame, pd.DataFrame]) -> None:
    counts = coverage_counts(*frames, min_posts=2)

    with pytest.raises(AttributeError):
        counts.union = 99  # type: ignore[misc]


# ---- rendering --------------------------------------------------------------------------------


def _text(counts: CoverageCounts, settings: EdaSettings) -> str:
    return "\n".join(render_coverage(counts, settings))


def test_rendering_shows_numbers_when_the_disclosure_minimum_allows(
    frames: tuple[pd.DataFrame, pd.DataFrame],
) -> None:
    counts = coverage_counts(*frames, min_posts=2)

    text = _text(counts, LOOSE)

    assert "| All_500 roster | 3 | 2 | 1 |" in text
    assert "| Leaders with at least 1 raw cell | 3 |" in text


def test_rendering_hides_every_small_leader_count_with_the_strict_minimum(
    frames: tuple[pd.DataFrame, pd.DataFrame],
) -> None:
    counts = coverage_counts(*frames, min_posts=15)

    text = _text(counts, STRICT)

    assert f"| All_500 roster | {SMALL} | {SMALL} | {SMALL} |" in text
    assert f"| Leaders with at least 1 raw cell | {SMALL} |" in text


def test_rendering_states_that_cells_stand_in_for_posts_and_the_segmented_cut_is_not_computed(
    frames: tuple[pd.DataFrame, pd.DataFrame],
) -> None:
    text = _text(coverage_counts(*frames, min_posts=2), LOOSE).lower()

    assert "cells stand in for posts" in text
    assert "g1 is not signed" in text
    assert "not computed" in text


def test_rendering_names_the_cut_from_the_settings_not_a_literal(
    frames: tuple[pd.DataFrame, pd.DataFrame],
) -> None:
    text = _text(coverage_counts(*frames, min_posts=2), LOOSE)

    assert "at least 2 raw cells" in text


def test_rendering_has_no_ids_keys_or_refs(frames: tuple[pd.DataFrame, pd.DataFrame]) -> None:
    text = _text(coverage_counts(*frames, min_posts=2), LOOSE)

    for forbidden in ("L1", "key L", "row:", "w#"):
        assert forbidden not in text
