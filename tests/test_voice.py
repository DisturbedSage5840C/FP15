"""Tests for src.voice: first-person singular and plural counts and the singular share. Made-up sentences only."""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from src import voice
from src.voice import PronounLists, VoiceCounts, count_voice, load_pronouns

ROOT = Path(__file__).resolve().parent.parent
PRONOUNS_YAML = ROOT / "configs" / "pronouns.yaml"

SINGULAR = {"i", "me", "my", "mine", "myself", "i'm", "i've", "i'll", "i'd"}
PLURAL = {"we", "us", "our", "ours", "ourselves", "we're", "we've", "we'll", "we'd"}


# ---- the pronoun config -----------------------------------------------------------------------


def test_the_default_config_holds_exactly_the_specified_pronouns() -> None:
    pronouns = load_pronouns()

    assert set(pronouns.singular) == SINGULAR
    assert set(pronouns.plural) == PLURAL


def test_the_config_file_holds_only_the_two_pronoun_lists_and_no_construct_words() -> None:
    raw = yaml.safe_load(PRONOUNS_YAML.read_text(encoding="utf-8"))

    assert set(raw) == {"first_person_singular", "first_person_plural"}


def _write_config(tmp_path: Path, content: str) -> Path:
    path = tmp_path / "pronouns.yaml"
    path.write_text(content, encoding="utf-8")
    return path


def test_a_config_missing_a_list_is_refused(tmp_path: Path) -> None:
    path = _write_config(tmp_path, "first_person_singular: [i]\n")

    with pytest.raises(ValueError, match="first_person_plural"):
        load_pronouns(path)


def test_a_config_with_a_pronoun_in_both_lists_is_refused(tmp_path: Path) -> None:
    path = _write_config(tmp_path, "first_person_singular: [i, we]\nfirst_person_plural: [we, us]\n")

    with pytest.raises(ValueError, match="both"):
        load_pronouns(path)


def test_a_config_with_an_empty_list_is_refused(tmp_path: Path) -> None:
    path = _write_config(tmp_path, "first_person_singular: []\nfirst_person_plural: [we]\n")

    with pytest.raises(ValueError, match="first_person_singular"):
        load_pronouns(path)


def test_a_missing_config_file_is_reported_not_swallowed(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load_pronouns(tmp_path / "absent.yaml")


# ---- counting ---------------------------------------------------------------------------------


def test_singular_pronouns_are_counted() -> None:
    counts = count_voice("I think my team and I did it myself, and the win is mine. Ask me.")

    assert counts.singular == 6
    assert counts.plural == 0


def test_plural_pronouns_are_counted() -> None:
    counts = count_voice("We built it. Our team gave us this; the credit is ours. We thank ourselves.")

    assert counts.plural == 6
    assert counts.singular == 0


def test_singular_contractions_are_counted() -> None:
    assert count_voice("I'm sure I've seen it; I'll go and I'd stay.").singular == 4


def test_plural_contractions_are_counted() -> None:
    assert count_voice("We're ready, we've won, we'll go and we'd stay.").plural == 4


def test_curly_apostrophes_count_like_straight_ones() -> None:
    counts = count_voice("I’m here and we’re here.")

    assert (counts.singular, counts.plural) == (1, 1)


def test_pronouns_are_counted_whatever_their_case() -> None:
    assert count_voice("i ME My MINE").singular == 4


def test_a_pronoun_inside_a_longer_word_is_not_counted() -> None:
    counts = count_voice("Mining hours at the business; a window, a mist, an issue, a user.")

    assert (counts.singular, counts.plural) == (0, 0)


def test_a_contraction_counts_once_and_its_first_part_is_not_counted_again() -> None:
    counts = count_voice("I'm here.")

    assert counts.singular == 1
    assert counts.total_words == 2


def test_total_words_counts_hyphenated_words_as_one_word() -> None:
    assert count_voice("I run a data-driven team.").total_words == 5


# ---- the share --------------------------------------------------------------------------------


def test_the_singular_share_is_singular_count_over_total_words() -> None:
    counts = count_voice("I I I we")

    assert counts.singular_share == pytest.approx(0.75)


def test_plural_pronouns_do_not_enter_the_singular_share() -> None:
    assert count_voice("we we we I").singular_share == pytest.approx(0.25)


def test_a_text_without_first_person_has_a_zero_share() -> None:
    assert count_voice("The team shipped the product.").singular_share == 0.0


@pytest.mark.parametrize("empty_text", ["", "   ", "\n", "...", "— !"])
def test_a_text_with_no_words_has_no_share_instead_of_a_made_up_zero(empty_text: str) -> None:
    counts = count_voice(empty_text)

    assert counts.total_words == 0
    assert counts.singular_share is None


# ---- the all-caps "US" rule -------------------------------------------------------------------


def test_the_all_caps_token_us_is_not_counted_as_first_person_plural() -> None:
    assert count_voice("the US market").plural == 0


def test_lower_case_us_is_still_counted_as_first_person_plural() -> None:
    assert count_voice("tell us").plural == 1


def test_capitalised_us_at_the_start_of_a_sentence_is_still_counted() -> None:
    assert count_voice("Us too").plural == 1


def test_the_ignored_all_caps_us_is_still_a_word_in_the_total() -> None:
    counts = count_voice("the US market")

    assert counts.total_words == 3
    assert counts.singular_share == 0.0


def test_a_text_with_both_us_spellings_counts_only_the_lower_case_one() -> None:
    assert count_voice("US firms tell us what we need").plural == 2


def test_a_sentence_written_entirely_in_capitals_loses_its_us_known_blind_spot() -> None:
    # Records the CURRENT behaviour, not an endorsement: in an all-caps sentence "US" is a pronoun but is ignored.
    assert count_voice("TELL US NOW").plural == 0


# ---- known limitation: Roman numeral I --------------------------------------------------------


def test_a_roman_numeral_i_is_counted_as_first_person_singular_known_limitation() -> None:
    # Records the CURRENT behaviour; it is not a fix and not an endorsement. "I" in "Phase I" is not a pronoun.
    counts = count_voice("Phase I of the plan.")

    assert counts.singular == 1


# ---- injection, input checks, immutability, docstring -----------------------------------------


def test_a_caller_can_pass_its_own_pronoun_lists() -> None:
    custom = PronounLists(singular=("ego",), plural=("collective",))

    counts = count_voice("ego ego I collective", custom)

    assert (counts.singular, counts.plural) == (2, 1)


def test_text_that_is_not_a_string_is_refused() -> None:
    with pytest.raises(TypeError):
        count_voice(None)  # type: ignore[arg-type]


def test_the_result_cannot_be_changed() -> None:
    counts = count_voice("I am here.")

    assert isinstance(counts, VoiceCounts)
    with pytest.raises(AttributeError):
        counts.singular = 99  # type: ignore[misc]


def test_the_docstring_says_the_share_is_one_signal_and_not_a_narcissism_score() -> None:
    doc = voice.__doc__ or ""

    assert "one signal" in doc
    assert "not a narcissism score" in doc
    assert "Roman numeral" in doc


def test_the_docstring_states_the_all_caps_us_rule_and_its_blind_spot() -> None:
    doc = voice.__doc__ or ""

    assert 'all-caps "US"' in doc
    assert "in capitals" in doc
