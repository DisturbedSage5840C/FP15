"""Tests for the per-text feature rules (Step B). Synthetic strings only; no study text."""

from __future__ import annotations

import pytest

from src.text_features import (
    ROMAN_HINDI_MARKERS,
    TextFeatures,
    compute_features,
)


def _f(text: str) -> TextFeatures:
    return compute_features(text)


# ---- length -----------------------------------------------------------------------------------


def test_length_counts_characters_and_words_of_the_stripped_text() -> None:
    features = _f("  Hello brave new world \n")

    assert (features.chars, features.words) == (21, 4)


def test_empty_text_gives_all_zero_features() -> None:
    features = _f("")

    assert features == TextFeatures()


# ---- hashtags ---------------------------------------------------------------------------------


def test_counts_hashtags_that_contain_a_letter() -> None:
    assert _f("Proud of #AI and #Leadership2024 today").hashtags == 2


def test_numeric_only_hashtags_are_counted_apart() -> None:
    features = _f("#1 priority and #2 goal, plus #Growth")

    assert (features.hashtags, features.numeric_hashtags) == (1, 2)


def test_hashtag_must_not_be_glued_to_a_word_or_sit_in_a_url_fragment() -> None:
    features = _f("C# is fine, word#tag too, see https://a.test/page#section")

    assert (features.hashtags, features.numeric_hashtags) == (0, 0)


def test_devanagari_hashtags_are_counted() -> None:
    assert _f("आज का दिन #भारत").hashtags == 1


# ---- mentions ---------------------------------------------------------------------------------


def test_counts_at_mentions() -> None:
    assert _f("Thanks @Priya and (@acme)!").mentions == 2


def test_emails_are_not_mentions() -> None:
    features = _f("Write to ceo@firm.test today")

    assert features.mentions == 0


def test_a_stray_at_sign_is_counted_apart() -> None:
    features = _f("Meet @ 5pm, then @ the office, ping @Dev")

    assert (features.mentions, features.stray_at) == (1, 2)


# ---- links ------------------------------------------------------------------------------------


def test_counts_scheme_urls_www_urls_and_short_link_hosts() -> None:
    text = "Read https://a.test/x and www.b.test/y, also lnkd.in/abc123."

    assert _f(text).urls == 3


def test_a_bare_domain_without_scheme_is_counted_apart_and_not_as_url() -> None:
    features = _f("Visit firm.com for details")

    assert (features.urls, features.bare_domains) == (0, 1)


def test_an_email_domain_is_not_a_bare_domain() -> None:
    assert _f("Mail ceo@firm.com").bare_domains == 0


def test_a_domain_inside_a_url_is_not_counted_twice() -> None:
    features = _f("See https://firm.com/page now")

    assert (features.urls, features.bare_domains) == (1, 0)


# ---- question marks ---------------------------------------------------------------------------


def test_counts_question_marks_outside_urls() -> None:
    assert _f("Why? Really? See https://a.test/?q=1").question_marks == 2


def test_question_mark_runs_are_counted_apart() -> None:
    features = _f("Really?? Sure?! Maybe!? Yes?")

    assert (features.question_marks, features.question_runs) == (5, 3)


# ---- emoji ------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "text",
    ["🎉", "👍🏽", "👨‍👩‍👧", "🇮🇳", "1️⃣", "✅", "❤️"],
)
def test_each_emoji_cluster_counts_once(text: str) -> None:
    assert _f(f"Great {text} news").emoji == 1


def test_two_separate_emoji_count_twice() -> None:
    assert _f("🎉🎉").emoji == 2


def test_text_style_symbols_are_counted_apart_from_emoji() -> None:
    features = _f("➡ next ✔ done © 2024")

    assert (features.emoji, features.symbols) == (0, 2)


def test_plain_digits_and_copyright_are_not_emoji() -> None:
    features = _f("Q4 2024 © ™")

    assert (features.emoji, features.symbols) == (0, 0)


# ---- Hinglish ---------------------------------------------------------------------------------


def test_devanagari_words_are_counted() -> None:
    features = _f("आज का दिन अच्छा है")

    assert features.devanagari_tokens == 5


def test_roman_hindi_markers_are_counted_from_the_list() -> None:
    features = _f("Hum sab ko milkar kaam karna hai")

    assert features.roman_markers == 6  # hum, sab, ko, kaam, karna, hai ("milkar" is not in the list)
    assert features.word_tokens == 7


def test_english_words_that_look_like_hindi_are_not_in_the_list() -> None:
    for word in ("the", "to", "me", "so", "do", "ho", "hi", "main", "par", "is", "us", "or", "no"):
        assert word not in ROMAN_HINDI_MARKERS


def test_urls_hashtags_and_mentions_do_not_feed_the_word_tokens() -> None:
    features = _f("hai https://a.test/hai #hai @hai")

    assert (features.roman_markers, features.word_tokens) == (1, 1)


def test_numbers_are_not_word_tokens() -> None:
    assert _f("2024 hai 12").word_tokens == 1


# ---- repost markers and page chrome -----------------------------------------------------------


def test_a_repost_line_is_flagged() -> None:
    assert _f("Someone\nRepost\nText").repost_line is True


def test_a_repost_word_inside_a_sentence_is_not_a_repost_line() -> None:
    features = _f("I reposted my old note because it still holds")

    assert (features.repost_line, features.repost_phrase, features.repost_word_in_text) == (False, False, True)


@pytest.mark.parametrize(
    "line",
    ["A B reposted this", "A B shared this", "A B celebrates this", "A B likes this", "A B commented on this"],
)
def test_engagement_phrases_mark_someone_elses_post(line: str) -> None:
    assert _f(f"{line}\nBody").repost_phrase is True


def test_follow_lines_are_counted() -> None:
    assert _f("Name\nFollow\nText\n+ Follow\nMore\nFollowing").follow_lines == 2


def test_plain_text_has_no_repost_markers() -> None:
    features = _f("Proud of the team")

    assert (features.repost_line, features.repost_phrase, features.repost_word_in_text) == (False, False, False)
