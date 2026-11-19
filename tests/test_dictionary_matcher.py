"""Tests for src.dictionary_matcher: phrase-aware, longest-first matching. Made-up sentences only, no real data."""
from __future__ import annotations

import re

import pytest

from src import dictionary_matcher
from src.dictionary_matcher import MatchResult, Overlap, match_entries


def _count(text: str, entries: list[str]) -> int:
    """Matches of one category of entries in the text."""
    return match_entries(text, {"cat": entries}).category_counts["cat"]


# ---- single words -----------------------------------------------------------------------------


def test_a_single_word_is_counted_every_time_it_appears() -> None:
    assert _count("We win. Win again, win!", ["win"]) == 3


def test_matching_ignores_case_in_text_and_entry() -> None:
    assert _count("APPLE apple Apple", ["ApPlE"]) == 3


def test_a_word_entry_does_not_match_inside_a_longer_word() -> None:
    assert _count("A twin won the winner's prize while winning.", ["win"]) == 0


# ---- phrases and hyphenated words (the audit case) --------------------------------------------


def test_a_phrase_is_matched_as_a_unit() -> None:
    assert _count("He will never give up, and he will never give up again.", ["never give up"]) == 2


def test_a_phrase_does_not_match_when_only_part_of_it_appears() -> None:
    assert _count("Never give in. Give up? Never.", ["never give up"]) == 0


def test_a_phrase_matches_across_extra_spaces_and_line_breaks() -> None:
    assert _count("never  give\n up", ["never give up"]) == 1


def test_a_hyphenated_word_is_matched_as_a_unit() -> None:
    assert _count("A data-driven firm and a Data-Driven plan.", ["data-driven"]) == 2


def test_a_typographic_hyphen_matches_an_ascii_hyphen_entry() -> None:
    assert _count("A data‑driven firm.", ["data-driven"]) == 1


def test_a_one_word_tokenizer_would_score_zero_on_phrases_and_hyphenated_entries() -> None:
    text = "He will never give up. A data-driven firm."
    entries = ["never give up", "data-driven"]
    naive_tokens = re.findall(r"\w+", text.lower())  # the usual one-word tokenizer: splits on the hyphen and the spaces

    naive_score = sum(token in entries for token in naive_tokens)
    matched = match_entries(text, {"cat": entries}).category_counts["cat"]

    assert naive_score == 0
    assert matched == 2


def test_a_hyphenated_word_is_one_unit_so_its_parts_do_not_match_alone() -> None:
    assert _count("A data-driven, well-known firm.", ["data", "driven", "known", "well"]) == 0


def test_a_possessive_is_a_different_word_from_its_base_form_known_limitation() -> None:
    assert _count("The fox's den.", ["fox"]) == 0
    assert _count("The fox's den.", ["fox's"]) == 1


# ---- longest first ----------------------------------------------------------------------------


def test_the_longest_entry_wins_over_the_shorter_entries_inside_it() -> None:
    assert _count("never give up", ["give up", "never give up", "never give"]) == 1


def test_a_shorter_entry_still_counts_where_the_longer_one_is_absent() -> None:
    assert _count("never give up. Give up!", ["never give up", "give up"]) == 2


def test_overlapping_candidates_are_taken_longest_first_not_leftmost_first() -> None:
    # Leftmost-first would take "never give" and then "now" (2 matches); longest-first takes "give up now" only.
    assert _count("never give up now", ["never give", "give up now", "now"]) == 1


def test_a_longer_entry_in_one_category_takes_the_span_from_a_shorter_entry_in_another() -> None:
    result = match_entries("never give up", {"cat_a": ["never give up"], "cat_b": ["never"]})

    assert dict(result.category_counts) == {"cat_a": 1, "cat_b": 0}


# ---- apostrophes ------------------------------------------------------------------------------


def test_curly_and_straight_apostrophes_match_each_other() -> None:
    assert _count("Don’t stop. don't quit.", ["don't"]) == 2
    assert _count("Don’t stop. don't quit.", ["don’t"]) == 2


def test_a_contraction_is_one_word_so_its_first_part_alone_does_not_match() -> None:
    assert _count("I'm here. I’m there.", ["i"]) == 0
    assert _count("I'm here. I’m there.", ["i'm"]) == 2


def test_a_curly_quote_around_a_word_is_not_part_of_the_word() -> None:
    assert _count("He said ‘apple’ twice.", ["apple"]) == 1


# ---- categories and overlaps ------------------------------------------------------------------


def test_each_category_is_counted_separately() -> None:
    result = match_entries("An apple and a red fox.", {"fruit": ["apple"], "animal": ["red fox"], "none": ["plum"]})

    assert dict(result.category_counts) == {"fruit": 1, "animal": 1, "none": 0}


def test_an_entry_listed_under_two_categories_is_counted_in_both() -> None:
    result = match_entries("The apple fell.", {"cat_a": ["apple", "pear"], "cat_b": ["Apple"]})

    assert dict(result.category_counts) == {"cat_a": 1, "cat_b": 1}


def test_overlapping_entries_are_reported_with_their_categories() -> None:
    result = match_entries("", {"cat_a": ["apple", "pear"], "cat_b": ["Apple", "plum"], "cat_c": ["apple"]})

    assert result.overlaps == (Overlap(entry="apple", categories=("cat_a", "cat_b", "cat_c")),)


def test_overlaps_are_found_whether_or_not_the_entry_appears_in_the_text() -> None:
    result = match_entries("Nothing relevant here.", {"cat_a": ["red fox"], "cat_b": ["red  fox"]})

    assert [overlap.entry for overlap in result.overlaps] == ["red fox"]


def test_no_overlap_is_reported_when_no_entry_is_shared() -> None:
    assert match_entries("An apple.", {"cat_a": ["apple"], "cat_b": ["plum"]}).overlaps == ()


def test_the_same_entry_listed_twice_in_one_category_counts_once() -> None:
    result = match_entries("An apple.", {"cat_a": ["apple", "Apple"]})

    assert result.category_counts["cat_a"] == 1
    assert result.overlaps == ()


# ---- negation and total words -----------------------------------------------------------------


def test_negation_is_not_handled_so_a_negated_entry_still_counts() -> None:
    assert _count("We do not like the apple.", ["apple"]) == 1


def test_the_module_docstring_states_that_negation_is_not_handled() -> None:
    assert "NEGATION IS NOT HANDLED" in (dictionary_matcher.__doc__ or "")


def test_total_words_counts_hyphenated_words_and_contractions_as_one_word_each() -> None:
    result = match_entries("A data-driven firm — we’re here.", {"cat": ["firm"]})

    assert result.total_words == 5


def test_empty_text_gives_zero_counts_and_zero_words() -> None:
    result = match_entries("", {"cat": ["apple"]})

    assert dict(result.category_counts) == {"cat": 0}
    assert result.total_words == 0


# ---- input checks and immutability ------------------------------------------------------------


@pytest.mark.parametrize("bad_entry", ["", "   ", "!!!", "-"])
def test_an_entry_with_no_word_characters_is_refused(bad_entry: str) -> None:
    with pytest.raises(ValueError):
        match_entries("An apple.", {"cat": ["apple", bad_entry]})


def test_text_that_is_not_a_string_is_refused() -> None:
    with pytest.raises(TypeError):
        match_entries(None, {"cat": ["apple"]})  # type: ignore[arg-type]


def test_the_result_cannot_be_changed() -> None:
    result = match_entries("An apple.", {"cat": ["apple"]})

    assert isinstance(result, MatchResult)
    with pytest.raises(TypeError):
        result.category_counts["cat"] = 99  # type: ignore[index]
    with pytest.raises(AttributeError):
        result.total_words = 99  # type: ignore[misc]
