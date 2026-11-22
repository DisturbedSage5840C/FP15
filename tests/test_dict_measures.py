"""Dictionary-layer scoring (src/dict_measures.py). Invented sentences only: no real post text, no real data.

The first-person singular rate tested here is one signal of self-focus in public posts. It is not a narcissism score.
"""
from __future__ import annotations

import dataclasses
from pathlib import Path

import pytest

from src.dict_measures import (
    DictionaryEntries,
    count_pronouns,
    load_dictionary,
    score_dictionary,
    tokenize,
)
from src.voice import count_voice

# Hand-counted: 20 words, singular I / my / I'm = 3, plural we / our = 2.
HAND_COUNTED = "I built this with my team and we shipped it for our clients while I'm learning from all of them"
SINGULAR_FORMS = ["i", "me", "my", "mine", "myself", "i'm", "i've", "i'll", "i'd"]
PLURAL_FORMS = ["we", "us", "our", "ours", "ourselves", "we're", "we've", "we'll"]


def write_list(tmp_path: Path, content: str, name: str = "list.txt") -> Path:
    path = tmp_path / name
    path.write_text(content, encoding="utf-8")
    return path


# --- tokenize -------------------------------------------------------------------------------------------------------


def test_tokenize_lowercases_every_word() -> None:
    assert tokenize("Hello WORLD") == ("hello", "world")


def test_tokenize_keeps_apostrophes_inside_words_and_treats_curly_like_straight() -> None:
    result = tokenize("I'm sure we're ready and I\u2019ve said I'll go")

    assert result == ("i'm", "sure", "we're", "ready", "and", "i've", "said", "i'll", "go")


def test_tokenize_drops_apostrophes_that_are_not_inside_a_word() -> None:
    assert tokenize("'quoted' text and dogs' bowl") == ("quoted", "text", "and", "dogs", "bowl")


@pytest.mark.parametrize(
    "text",
    [
        "see https://example.invalid/path?x=1 now",
        "see HTTP://EXAMPLE.INVALID/a now",
        "see www.example.invalid/a now",
    ],
)
def test_tokenize_drops_urls(text: str) -> None:
    assert tokenize(text) == ("see", "now")


def test_tokenize_drops_a_url_that_contains_an_at_sign_as_one_piece() -> None:
    assert tokenize("go to https://example.invalid/@someone/post now") == ("go", "to", "now")


def test_tokenize_drops_mentions_including_dotted_and_hyphenated_handles() -> None:
    assert tokenize("thanks @jane_doe and @a.b-c today") == ("thanks", "and", "today")


def test_tokenize_keeps_hashtag_words_without_the_hash() -> None:
    assert tokenize("#Leadership and #growth") == ("leadership", "and", "growth")


def test_tokenize_drops_emoji_and_keeps_the_words_around_them() -> None:
    text = "great \U0001F680 news \U0001F44D\U0001F3FD today \u2764\ufe0f"

    assert tokenize(text) == ("great", "news", "today")


def test_tokenize_drops_keycap_emoji_so_their_digit_is_not_counted_as_a_word() -> None:
    assert tokenize("rank 1\ufe0f\u20e3 today #\ufe0f\u20e3 ok") == ("rank", "today", "ok")


def test_tokenize_keeps_numbers_as_words() -> None:
    assert tokenize("In 2024 we grew 3x") == ("in", "2024", "we", "grew", "3x")


@pytest.mark.parametrize("text", ["", "   \n", "\U0001F680\U0001F680", "!!! ???"])
def test_tokenize_gives_no_words_for_empty_or_symbol_only_text(text: str) -> None:
    assert tokenize(text) == ()


def test_tokenize_rejects_non_text_and_names_only_the_type() -> None:
    with pytest.raises(TypeError, match="got int"):
        tokenize(12345)  # type: ignore[arg-type]


def test_tokenize_splits_devanagari_words_at_vowel_marks_so_their_word_count_is_inflated() -> None:
    """Known limitation, recorded and not fixed: English-only scope. See docs/decisions.md, Findings."""
    text = "\u092e\u0948\u0902 \u0905\u092a\u0928\u0940 \u091f\u0940\u092e"  # three invented Hindi words

    assert len(tokenize(text)) > len(text.split())


# --- count_pronouns -------------------------------------------------------------------------------------------------


def test_count_pronouns_on_a_hand_counted_sentence() -> None:
    result = count_pronouns(HAND_COUNTED)

    assert (result.singular_count, result.plural_count, result.word_count) == (3, 2, 20)
    assert result.singular_per_100 == pytest.approx(15.0)
    assert result.plural_per_100 == pytest.approx(10.0)


@pytest.mark.parametrize("word", SINGULAR_FORMS)
def test_count_pronouns_counts_each_singular_form_once(word: str) -> None:
    result = count_pronouns(word)

    assert (result.singular_count, result.plural_count, result.word_count) == (1, 0, 1)


@pytest.mark.parametrize("word", PLURAL_FORMS)
def test_count_pronouns_counts_each_plural_form_once(word: str) -> None:
    result = count_pronouns(word)

    assert (result.singular_count, result.plural_count, result.word_count) == (0, 1, 1)


def test_count_pronouns_ignores_case_and_curly_apostrophes() -> None:
    result = count_pronouns("WE value MY team and Me, I\u2019m glad")

    assert (result.singular_count, result.plural_count, result.word_count) == (3, 1, 8)


def test_count_pronouns_counts_the_country_us_as_plural_because_text_is_lower_cased_first() -> None:
    """Known limitation, recorded and not fixed: src.voice skips the all-caps US, this module cannot."""
    result = count_pronouns("the US market grew")

    assert (result.plural_count, result.word_count) == (1, 4)


def test_count_pronouns_matches_whole_words_only() -> None:
    result = count_pronouns("weekend usual mighty imagine amend")

    assert (result.singular_count, result.plural_count, result.word_count) == (0, 0, 5)


def test_count_pronouns_ignores_words_inside_mentions_and_urls() -> None:
    result = count_pronouns("see @me and https://example.invalid/we now")

    assert (result.singular_count, result.plural_count, result.word_count) == (0, 0, 3)


@pytest.mark.parametrize("text", ["", "   ", "\U0001F680", "https://example.invalid/only-a-link"])
def test_count_pronouns_returns_zeros_not_an_error_when_there_are_no_words(text: str) -> None:
    result = count_pronouns(text, post_id="p-empty")

    assert result == dataclasses.replace(
        result, singular_count=0, plural_count=0, word_count=0, singular_per_100=0.0, plural_per_100=0.0
    )
    assert result.post_id == "p-empty"


def test_count_pronouns_carries_the_post_id_and_defaults_it_to_none() -> None:
    assert count_pronouns("my plan", post_id="p-001").post_id == "p-001"
    assert count_pronouns("my plan").post_id is None


def test_count_pronouns_rejects_non_text_and_names_only_the_type() -> None:
    with pytest.raises(TypeError, match="got NoneType"):
        count_pronouns(None)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "text",
    [
        "I built this with my team and we shipped it for our clients",
        "Thank you all, we're proud and I'm grateful for us",
        "The quarterly review is on Friday",
    ],
)
def test_count_pronouns_agrees_with_the_voice_counter_on_plain_sentences(text: str) -> None:
    ours = count_pronouns(text)
    theirs = count_voice(text)

    assert (ours.singular_count, ours.plural_count, ours.word_count) == (
        theirs.singular,
        theirs.plural,
        theirs.total_words,
    )


# --- load_dictionary ------------------------------------------------------------------------------------------------


def test_load_dictionary_reads_exact_entries_and_prefixes(tmp_path: Path) -> None:
    path = write_list(tmp_path, "lead*\nwin\n\n  Team  \nWIN\n")

    entries = load_dictionary(path)

    assert entries == DictionaryEntries(exact=frozenset({"win", "team"}), prefixes=("lead",))


def test_load_dictionary_tolerates_a_byte_order_mark(tmp_path: Path) -> None:
    path = tmp_path / "bom.txt"
    path.write_bytes("\ufeffwin\n".encode("utf-8"))

    assert load_dictionary(path).exact == frozenset({"win"})


def test_a_missing_dictionary_file_fails_loudly_and_creates_nothing(tmp_path: Path) -> None:
    missing = tmp_path / "external" / "absent.txt"

    with pytest.raises(FileNotFoundError) as caught:
        load_dictionary(missing)

    assert "absent.txt" in str(caught.value)
    assert "licence" in str(caught.value)
    assert not missing.exists()
    assert not missing.parent.exists()


def test_load_dictionary_rejects_a_file_with_no_entries(tmp_path: Path) -> None:
    path = write_list(tmp_path, "\n  \n")

    with pytest.raises(ValueError, match="no entries"):
        load_dictionary(path)


@pytest.mark.parametrize(
    ("line", "reason"),
    [
        ("*", "no word characters"),
        ("le*d", "last character"),
        ("lead**", "last character"),
        ("give up", "exactly one word"),
        ("data-driven", "exactly one word"),
    ],
)
def test_load_dictionary_rejects_malformed_lines_and_names_the_line_number(
    tmp_path: Path, line: str, reason: str
) -> None:
    path = write_list(tmp_path, f"win\n{line}\n")

    with pytest.raises(ValueError, match=rf"line 2.*{reason}"):
        load_dictionary(path)


# --- score_dictionary -----------------------------------------------------------------------------------------------


@pytest.fixture
def entries(tmp_path: Path) -> DictionaryEntries:
    return load_dictionary(write_list(tmp_path, "lead*\nwin\ngrow*\n"))


def test_score_dictionary_counts_exact_and_wildcard_matches_on_a_hand_counted_sentence(
    entries: DictionaryEntries,
) -> None:
    # 10 words; matches: Leaders, lead, win, leadership, grows, win = 6
    result = score_dictionary("Leaders lead and win; leadership grows, we win again today", entries)

    assert (result.match_count, result.word_count) == (6, 10)
    assert result.rate_per_100 == pytest.approx(60.0)


def test_a_wildcard_prefix_matches_the_bare_prefix_word_itself(entries: DictionaryEntries) -> None:
    assert score_dictionary("lead", entries).match_count == 1


def test_a_wildcard_matches_only_at_the_start_of_a_word(entries: DictionaryEntries) -> None:
    assert score_dictionary("mislead regrow", entries).match_count == 0


def test_an_exact_entry_does_not_match_a_longer_word(entries: DictionaryEntries) -> None:
    assert score_dictionary("winning wind", entries).match_count == 0


def test_a_word_listed_exactly_and_by_prefix_is_counted_once(tmp_path: Path) -> None:
    both = load_dictionary(write_list(tmp_path, "lead\nlead*\n"))

    assert score_dictionary("lead", both).match_count == 1


def test_score_dictionary_sees_hashtag_words_but_not_words_inside_urls_or_mentions(
    entries: DictionaryEntries,
) -> None:
    result = score_dictionary("#leadership https://example.invalid/leader @leader.win", entries)

    assert (result.match_count, result.word_count) == (1, 1)


@pytest.mark.parametrize("text", ["", "  ", "\U0001F680"])
def test_score_dictionary_returns_zeros_not_an_error_for_text_without_words(
    entries: DictionaryEntries, text: str
) -> None:
    result = score_dictionary(text, entries)

    assert (result.match_count, result.word_count, result.rate_per_100) == (0, 0, 0.0)


def test_score_dictionary_carries_the_post_id(entries: DictionaryEntries) -> None:
    assert score_dictionary("win", entries, post_id="p-007").post_id == "p-007"


def test_score_dictionary_rejects_a_bare_list_instead_of_loaded_entries() -> None:
    with pytest.raises(TypeError, match="load_dictionary"):
        score_dictionary("win", ["win"])  # type: ignore[arg-type]


# --- outputs hold only post_id and numbers --------------------------------------------------------------------------


def test_outputs_hold_only_post_id_and_numbers(entries: DictionaryEntries) -> None:
    results = [count_pronouns(HAND_COUNTED, post_id="p-1"), score_dictionary(HAND_COUNTED, entries, post_id="p-1")]

    for result in results:
        values = {field.name: getattr(result, field.name) for field in dataclasses.fields(result)}
        assert values.pop("post_id") == "p-1"
        assert all(isinstance(value, (int, float)) for value in values.values())


def test_no_text_is_returned_logged_or_printed(
    entries: DictionaryEntries, caplog: pytest.LogCaptureFixture, capsys: pytest.CaptureFixture[str]
) -> None:
    secret = "confidential invented sentence about my plan to win"

    results = [count_pronouns(secret), score_dictionary(secret, entries)]

    assert all("confidential" not in repr(result) for result in results)
    assert caplog.records == []
    captured = capsys.readouterr()
    assert (captured.out, captured.err) == ("", "")
