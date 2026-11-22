"""Dictionary-layer scoring: first-person pronoun counts and word-list counts for one text, as rates per 100 words.

Functions only. Nothing here reads real data, and it has been tested on invented sentences only: G1 (segmentation) is
not signed, so no segmented text is in use. No function returns, logs or prints text. Outputs carry post_id and numbers.

How to read the first-person singular rate
It is one signal of self-focus in public posts. It is not a narcissism score and says nothing about personality.
The plural rate is reported beside it so the two can be read together. What any dictionary category means is a
human and mentor decision; this module only counts the words it is given.

Known limitations (stated, not fixed)
- English only. The word lists are English, so Hindi and mixed Hindi-English posts are missed. The 300-post gold set
  is the check (docs/decisions.md, Findings). Devanagari words are also split at their vowel marks, which inflates
  the word count and deflates every rate for such text.
- The text is lower-cased first, so the country "US" counts as the plural "us". src.voice skips the all-caps "US";
  this module cannot, because the spec lower-cases before matching.
- A hyphenated word is two words here ("data-driven"), but one word in src.voice. Rates differ slightly on such text.
- Negation is not handled: "not my decision" counts "my".
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from src.voice import load_pronouns

RATE_BASE = 100
WILDCARD = "*"
EXTERNAL_DICTIONARY_HINT = (
    "Place the file under data/external/ after a human has checked its licence. "
    "This code never creates a placeholder list."
)

_APOSTROPHE_VARIANTS = str.maketrans({"\u2019": "'", "\u2018": "'", "\u02bc": "'"})
_URL = re.compile(r"(?:https?://|www\.)\S+")
_MENTION = re.compile(r"@\w+(?:[.\-]\w+)*")
# A keycap emoji such as 1 + FE0F + 20E3 would otherwise leave its digit behind as a word.
_KEYCAP_EMOJI = re.compile(r"[0-9#*]\ufe0f?\u20e3")
# Letters and digits, with apostrophes allowed only inside a word. Emoji, hashes and punctuation never match.
_WORD = re.compile(r"[^\W_]+(?:'[^\W_]+)*")


@dataclass(frozen=True)
class PronounCounts:
    """First-person pronoun counts for one post. Only the post id and numbers: no text."""

    post_id: str | None
    singular_count: int
    plural_count: int
    word_count: int
    singular_per_100: float
    plural_per_100: float


@dataclass(frozen=True)
class DictionaryScore:
    """Word-list matches for one post. Only the post id and numbers: no text."""

    post_id: str | None
    match_count: int
    word_count: int
    rate_per_100: float


@dataclass(frozen=True)
class DictionaryEntries:
    """A loaded word list: whole-word entries and prefix entries (written with a trailing star in the file)."""

    exact: frozenset[str]
    prefixes: tuple[str, ...]


def _require_text(text: object) -> str:
    if not isinstance(text, str):
        raise TypeError(f"text must be str, got {type(text).__name__}")
    return text


def _require_entries(entries: object) -> DictionaryEntries:
    if not isinstance(entries, DictionaryEntries):
        raise TypeError(f"entries must come from load_dictionary(), got {type(entries).__name__}")
    return entries


def tokenize(text: str) -> tuple[str, ...]:
    """Split one text into lower-case words.

    URLs and @mentions are dropped, hashtag words are kept without the hash, emoji are dropped, and an apostrophe is
    kept only inside a word (curly and straight apostrophes are treated alike). Empty text gives an empty tuple.
    """
    cleaned = _require_text(text).translate(_APOSTROPHE_VARIANTS).lower()
    for pattern in (_URL, _MENTION, _KEYCAP_EMOJI):
        cleaned = pattern.sub(" ", cleaned)
    return tuple(_WORD.findall(cleaned))


def _rate_per_100(count: int, word_count: int) -> float:
    return count * RATE_BASE / word_count if word_count else 0.0


@lru_cache(maxsize=1)
def _pronoun_words() -> tuple[frozenset[str], frozenset[str]]:
    lists = load_pronouns()
    return (
        frozenset(word.lower() for word in lists.singular),
        frozenset(word.lower() for word in lists.plural),
    )


def count_pronouns(text: str, post_id: str | None = None) -> PronounCounts:
    """Count first-person singular and plural pronouns and give both as rates per 100 words.

    The word lists come from configs/pronouns.yaml. Text with no words returns zeros, not an error.
    The singular rate is one signal of self-focus, not a narcissism score.
    """
    tokens = tokenize(text)
    singular_words, plural_words = _pronoun_words()
    singular = sum(1 for token in tokens if token in singular_words)
    plural = sum(1 for token in tokens if token in plural_words)
    word_count = len(tokens)
    return PronounCounts(
        post_id=post_id,
        singular_count=singular,
        plural_count=plural,
        word_count=word_count,
        singular_per_100=_rate_per_100(singular, word_count),
        plural_per_100=_rate_per_100(plural, word_count),
    )


def _parse_entry(entry: str, line_number: int) -> tuple[str, bool]:
    """Return (word, is_prefix) for one non-blank line. Errors name the line number, never the entry."""
    is_prefix = entry.endswith(WILDCARD)
    body = entry[:-1] if is_prefix else entry
    if WILDCARD in body:
        raise ValueError(f"line {line_number}: '{WILDCARD}' is only allowed as the last character of an entry")
    words = tokenize(body)
    if not words:
        raise ValueError(f"line {line_number}: the entry has no word characters")
    if len(words) != 1:
        raise ValueError(
            f"line {line_number}: an entry must be exactly one word (phrases and hyphenated words are not supported)"
        )
    return words[0], is_prefix


def load_dictionary(path: Path | str) -> DictionaryEntries:
    """Read a word list: one entry per line, a trailing star means a prefix match (LIWC style).

    Raises FileNotFoundError if the file is missing (no placeholder is ever created) and ValueError for an empty file
    or a malformed line.
    """
    file_path = Path(path)
    try:
        raw = file_path.read_text(encoding="utf-8-sig")
    except FileNotFoundError as error:
        raise FileNotFoundError(f"dictionary file not found: {file_path}. {EXTERNAL_DICTIONARY_HINT}") from error

    exact: set[str] = set()
    prefixes: set[str] = set()
    for line_number, line in enumerate(raw.splitlines(), start=1):
        entry = line.strip()
        if not entry:
            continue
        word, is_prefix = _parse_entry(entry, line_number)
        (prefixes if is_prefix else exact).add(word)
    if not exact and not prefixes:
        raise ValueError(f"dictionary file has no entries: {file_path.name}")
    return DictionaryEntries(exact=frozenset(exact), prefixes=tuple(sorted(prefixes)))


def score_dictionary(text: str, entries: DictionaryEntries, post_id: str | None = None) -> DictionaryScore:
    """Count the words of one text that match a loaded word list, as a count and a rate per 100 words.

    A word matching both an exact entry and a prefix entry is counted once. Text with no words returns zeros.
    """
    word_list = _require_entries(entries)
    tokens = tokenize(text)
    matches = sum(1 for token in tokens if token in word_list.exact or token.startswith(word_list.prefixes))
    return DictionaryScore(
        post_id=post_id,
        match_count=matches,
        word_count=len(tokens),
        rate_per_100=_rate_per_100(matches, len(tokens)),
    )
