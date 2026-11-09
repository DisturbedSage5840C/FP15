"""Tests for src.post_fields: relative post age in months and the language flag (synthetic text only)."""
from __future__ import annotations

from pathlib import Path

import pytest

from src.post_fields import (
    ENGLISH,
    HINDI,
    MIXED,
    OTHER,
    LanguageSettings,
    age_months,
    language_flag,
    load_language_settings,
)

SETTINGS = LanguageSettings(min_letters=10, minor_share=0.2)
HINDI_TEXT = "यह एक परीक्षण वाक्य है जो हिंदी में लिखा गया है"
ENGLISH_TEXT = "This is a plain test sentence written in English"


def _cell(age_line: str) -> str:
    return f"Person Name\n• 3rd+\nHeadline\n{age_line}\nBody of the post\nFollow"


@pytest.mark.parametrize(
    ("age_line", "expected"),
    [
        ("5yr •", 60.0),
        ("3mo •", 3.0),
        ("1yr • Edited •", 12.0),
        ("2w •", 2 * 12 / 52),
        ("10d •", 10 * 12 / 365),
        ("4h •", 4 * 12 / 8760),
    ],
)
def test_age_line_becomes_months(age_line: str, expected: float) -> None:
    assert age_months(_cell(age_line)) == pytest.approx(expected, abs=1e-4)


def test_no_age_line_gives_none_and_is_not_zero() -> None:
    assert age_months("Person\n• 3rd+\nBody with no age line") is None


def test_age_token_inside_a_sentence_is_not_an_age_line() -> None:
    assert age_months("Person\nI waited 5yr • for this") is None


def test_the_first_age_line_wins() -> None:
    text = "Name\n• 3rd+\n2yr •\nBody\nName\n• 3rd+\n5yr •\nBody"

    assert age_months(text) == pytest.approx(24.0)


def test_empty_text_has_no_age() -> None:
    assert age_months("") is None


def test_english_text_is_flagged_english() -> None:
    assert language_flag(ENGLISH_TEXT, SETTINGS) == ENGLISH


def test_devanagari_text_is_flagged_hindi() -> None:
    assert language_flag(HINDI_TEXT, SETTINGS) == HINDI


def test_both_scripts_in_similar_shares_is_mixed() -> None:
    assert language_flag(f"{HINDI_TEXT} {ENGLISH_TEXT}", SETTINGS) == MIXED


def test_a_small_amount_of_the_other_script_does_not_make_it_mixed() -> None:
    text = f"{ENGLISH_TEXT} {ENGLISH_TEXT} {ENGLISH_TEXT} नमस्ते"

    assert language_flag(text, SETTINGS) == ENGLISH


def test_too_few_letters_is_other() -> None:
    assert language_flag("Ok 👍 123", SETTINGS) == OTHER


def test_another_script_is_other() -> None:
    assert language_flag("இது ஒரு சோதனை வாக்கியம் ஆகும் தமிழ்", SETTINGS) == OTHER


def test_hindi_in_latin_letters_is_not_detected_and_counts_as_english() -> None:
    assert language_flag("Aap sabhi ko nav varsh ki hardik shubhkamnayen", SETTINGS) == ENGLISH


def test_settings_load_from_the_thresholds_file(tmp_path: Path) -> None:
    path = tmp_path / "t.yaml"
    path.write_text("language_min_letters: 15\nlanguage_minor_share: 0.25\n", encoding="utf-8")

    assert load_language_settings(path) == LanguageSettings(min_letters=15, minor_share=0.25)


def test_a_missing_settings_key_is_named_in_the_error(tmp_path: Path) -> None:
    path = tmp_path / "t.yaml"
    path.write_text("language_min_letters: 15\n", encoding="utf-8")

    with pytest.raises(ValueError, match="language_minor_share"):
        load_language_settings(path)
