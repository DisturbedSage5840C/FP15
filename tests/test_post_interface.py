"""Tests for src.post_interface: repeated interface lines, removal rules and frequency profiling (synthetic text)."""
from __future__ import annotations

import pytest

from src.post_interface import (
    APPLIED_RULES,
    PROPOSED_RULES,
    classify_line,
    clean_text,
    line_frequencies,
    normalise_line,
    rule_counts,
)

CELL = (
    "Person Name\n• 3rd+\nHeadline text\n5yr •\nA real sentence of the post.\n"
    "…more\nFollow\nActivate to view larger image,\nLike\nComment\nRepost\nSend\n42"
)


@pytest.mark.parametrize(
    "line",
    ["• 3rd+", "• Following", "• 3rd", "Follow", "+ Follow", "…more", "Activate to view larger image,",
     "5yr •", "1yr • Edited •", "Like", "Comment", "Repost", "Send", "Your document is loading"],
)
def test_interface_lines_match_an_applied_rule(line: str) -> None:
    rule = classify_line(line)

    assert rule is not None and rule.applied


@pytest.mark.parametrize("line", ["Join", "View job", ".", "youtube.com", "bit.ly", "42", "1,204"])
def test_ambiguous_lines_match_a_proposed_rule_that_is_not_applied(line: str) -> None:
    rule = classify_line(line)

    assert rule is not None and not rule.applied


@pytest.mark.parametrize("line", ["A real sentence.", "I like this", "Follow your dreams daily", ""])
def test_post_text_matches_no_rule(line: str) -> None:
    assert classify_line(line) is None


def test_every_rule_has_a_unique_name() -> None:
    names = [rule.name for rule in (*APPLIED_RULES, *PROPOSED_RULES)]

    assert len(names) == len(set(names))


def test_clean_text_drops_only_applied_interface_lines() -> None:
    cleaned = clean_text(CELL)

    assert "A real sentence of the post." in cleaned
    assert "Person Name" in cleaned and "Headline text" in cleaned
    assert "Follow" not in cleaned and "…more" not in cleaned and "5yr" not in cleaned
    assert cleaned.endswith("42")


def test_clean_text_never_changes_the_input() -> None:
    original = CELL

    clean_text(original)

    assert original == CELL


def test_clean_text_collapses_blank_runs_and_trims() -> None:
    assert clean_text("\n\nFollow\n\n\nBody\n\n\n") == "Body"


def test_clean_text_of_only_interface_lines_is_empty() -> None:
    assert clean_text("Follow\nLike\nComment") == ""


def test_normalise_line_trims_and_masks_digits() -> None:
    assert normalise_line("  1,204 reactions  ") == "<n>,<n> reactions"


def test_rule_counts_give_lines_and_cells_per_rule() -> None:
    cells = [CELL, "Body\nFollow", "Nothing here"]

    counts = rule_counts(cells)

    assert counts["follow"] == (2, 2)
    assert counts["like_comment_repost_send"] == (4, 1)


def test_rule_counts_include_proposed_rules_with_zero_when_absent() -> None:
    counts = rule_counts(["Body"])

    assert counts["join"] == (0, 0)


def test_line_frequencies_keep_patterns_seen_for_enough_leaders() -> None:
    cells = [("a", "Shared line\nOnly a"), ("b", "Shared line"), ("c", "Shared line\nOnly c")]

    result = line_frequencies(cells, min_leaders=3)

    assert [(p.pattern, p.lines, p.leaders) for p in result] == [("Shared line", 3, 3)]


def test_line_frequencies_count_a_repeat_within_one_leader_once_for_leaders() -> None:
    cells = [("a", "Same\nSame"), ("a", "Same"), ("b", "Same")]

    result = line_frequencies(cells, min_leaders=2)

    assert [(p.lines, p.leaders) for p in result] == [(4, 2)]


def test_line_frequencies_are_ordered_by_leaders_then_lines_then_text() -> None:
    cells = [("a", "x\ny"), ("b", "x\ny"), ("c", "x")]

    result = line_frequencies(cells, min_leaders=2)

    assert [p.pattern for p in result] == ["x", "y"]


def test_line_frequencies_ignore_blank_lines() -> None:
    cells = [("a", "\n  \nx"), ("b", "x\n\n")]

    result = line_frequencies(cells, min_leaders=2)

    assert [p.pattern for p in result] == ["x"]


def test_line_frequencies_mask_digits_so_counts_group() -> None:
    cells = [("a", "12"), ("b", "345"), ("c", "7")]

    result = line_frequencies(cells, min_leaders=3)

    assert [p.pattern for p in result] == ["<n>"]
