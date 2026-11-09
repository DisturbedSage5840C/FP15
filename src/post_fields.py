"""Per-cell fields read from the raw post text: relative age in months and a language flag.

Claim limit: the age is LinkedIn's rounded relative age ("5yr", "3mo") turned into months. It is never turned
into a date, because the scrape date is unknown. The language flag first looks at script (Devanagari versus
Latin letters). Text that is mostly Latin letters is then checked for romanised Hindi function words and flagged
"Hinglish" (possible) when enough of them appear; see src/hinglish.py for the method and the list.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path

import yaml

from src.hinglish import hinglish_hits

DEFAULT_THRESHOLDS_PATH = Path("configs/thresholds.yaml")

ENGLISH, HINGLISH, MIXED, HINDI, OTHER = "English", "Hinglish", "mixed", "Hindi", "other"
LANGUAGE_FLAGS = (ENGLISH, HINGLISH, MIXED, HINDI, OTHER)

MONTHS_PER_YEAR = 12
WEEKS_PER_YEAR = 52
DAYS_PER_YEAR = 365
HOURS_PER_YEAR = 365 * 24
MONTHS_PER_UNIT = {
    "yr": float(MONTHS_PER_YEAR),
    "mo": 1.0,
    "w": MONTHS_PER_YEAR / WEEKS_PER_YEAR,
    "d": MONTHS_PER_YEAR / DAYS_PER_YEAR,
    "h": MONTHS_PER_YEAR / HOURS_PER_YEAR,
}
AGE_DECIMALS = 4
# An age line starts with the token and is followed by the bullet LinkedIn prints after it.
_AGE_LINE = re.compile(r"^(\d{1,3})(yr|mo|w|d|h)\s*•")
KNOWN_SCRIPT_MIN_SHARE = 0.5
LANGUAGE_KEYS = ("language_min_letters", "language_minor_share", "hinglish_min_hits", "hinglish_min_share")


def age_months(text: str) -> float | None:
    """Months for the first relative-age line in the cell, or None when there is no such line."""
    for line in text.split("\n"):
        found = _AGE_LINE.match(line.strip())
        if found:
            return round(int(found.group(1)) * MONTHS_PER_UNIT[found.group(2)], AGE_DECIMALS)
    return None


@dataclass(frozen=True)
class LanguageSettings:
    """Settings read from configs/thresholds.yaml (method settings, not pass marks)."""

    min_letters: int
    minor_share: float
    hinglish_min_hits: int
    hinglish_min_share: float


def load_language_settings(path: Path = DEFAULT_THRESHOLDS_PATH) -> LanguageSettings:
    """Read the language keys; a missing key is named in the error."""
    values = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    for key in LANGUAGE_KEYS:
        if key not in values:
            raise ValueError(f"{path}: missing key {key}")
    return LanguageSettings(
        int(values["language_min_letters"]),
        float(values["language_minor_share"]),
        int(values["hinglish_min_hits"]),
        float(values["hinglish_min_share"]),
    )


def _script_counts(text: str) -> tuple[int, int, int]:
    """Counts of (Devanagari letters, Latin letters, all letters)."""
    devanagari = latin = letters = 0
    for char in text:
        if not char.isalpha():
            continue
        letters += 1
        name = unicodedata.name(char, "")
        devanagari += name.startswith("DEVANAGARI")
        latin += name.startswith("LATIN")
    return devanagari, latin, letters


def language_flag(text: str, settings: LanguageSettings) -> str:
    """English, Hinglish, Hindi, mixed or other: script shares first, then romanised Hindi words in Latin text."""
    devanagari, latin, letters = _script_counts(text)
    known = devanagari + latin
    if letters < settings.min_letters or known / letters < KNOWN_SCRIPT_MIN_SHARE:
        return OTHER
    if devanagari / known <= settings.minor_share:
        return HINGLISH if _possible_hinglish(text, settings) else ENGLISH
    if latin / known <= settings.minor_share:
        return HINDI
    return MIXED


def _possible_hinglish(text: str, settings: LanguageSettings) -> bool:
    """True when enough Latin-letter words are romanised Hindi function words, by count and by share."""
    hits, words = hinglish_hits(text)
    return hits >= settings.hinglish_min_hits and hits / words >= settings.hinglish_min_share
