"""Phrase-aware dictionary matcher: counts entries in text (the matching engine of the dictionary layer).

Built and tested on made-up sentences only. It has NOT been run on any post text or data: G1 (segmentation) is not
signed, so no segmented text exists yet. It reads no files, writes nothing and uses no network.

How matching works
- Text and entries are split into word tokens by the same function, so they always agree. A token is letters and digits,
  optionally joined by an apostrophe or hyphen that sits between letters or digits. So "data-driven", "we're" and
  "fox's" are each ONE token, which is why a hyphenated word is matched as a unit and its parts do not match alone.
- Case is ignored. Curly apostrophes (U+2018, U+2019) match the straight one, and U+2010 and U+2011 match "-".
- An entry is one or more tokens ("win", "never give up", "data-driven"). Phrases must match whole tokens in a row,
  so an entry never matches inside a longer word. Spacing and line breaks between the words of a phrase do not matter.
- Longest first: spans are claimed from the most tokens down, left to right, and a token is used by at most one span.
  A short entry therefore cannot take words from a longer phrase that contains it. This holds across categories too:
  if "never give up" (category A) covers the words, "never" (category B) scores 0 there.
- An entry listed under two categories is counted in BOTH, and `MatchResult.overlaps` lists every such entry so a
  human can decide what to do. Nothing is dropped or merged here.

Known limits (stated, not fixed)
- NEGATION IS NOT HANDLED. "not a leader" counts "leader" exactly like "a leader". Nothing is guessed about meaning.
- A possessive or a contraction is a different word from its base: "fox's" does not match the entry "fox".
- Other inflections are not matched either: "win" does not match "wins" or "winning". List each form you want.
- "data driven" (a space) does not match the entry "data-driven", and the reverse.
"""
from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType

# A word: letters or digits, optionally chained by an inner apostrophe or hyphen ("we're", "data-driven").
_TOKEN = re.compile(r"[^\W_]+(?:['-][^\W_]+)*")
_TYPOGRAPHIC_TO_ASCII = str.maketrans(
    {"‘": "'", "’": "'", "‐": "-", "‑": "-"},
)

TokenKey = tuple[str, ...]


@dataclass(frozen=True)
class Overlap:
    """One entry (lower-cased, tokens joined by single spaces) that is listed under more than one category."""

    entry: str
    categories: tuple[str, ...]


@dataclass(frozen=True)
class MatchResult:
    """Counts per category (every category appears, 0 when nothing matched), total words, and shared entries."""

    category_counts: Mapping[str, int]
    total_words: int
    overlaps: tuple[Overlap, ...]


def tokenise(text: str) -> tuple[str, ...]:
    """Lower-cased word tokens of the text; apostrophe and hyphen variants are normalised first."""
    if not isinstance(text, str):
        raise TypeError(f"text must be a str, got {type(text).__name__}")
    return tuple(_TOKEN.findall(text.translate(_TYPOGRAPHIC_TO_ASCII).lower()))


def _entry_key(entry: str, category: str) -> TokenKey:
    if not isinstance(entry, str):
        raise TypeError(f"entry in category {category!r} must be a str, got {type(entry).__name__}")
    key = tokenise(entry)
    if not key:
        raise ValueError(f"entry {entry!r} in category {category!r} has no word characters")
    return key


def _build_index(categories: Mapping[str, Sequence[str]]) -> dict[TokenKey, tuple[str, ...]]:
    """Entry key -> the categories that list it, in the order given; an entry repeated in one category counts once."""
    owners: dict[TokenKey, list[str]] = {}
    for category, entries in categories.items():
        if isinstance(entries, str):
            raise TypeError(f"entries of category {category!r} must be a list of str, not one str")
        for entry in entries:
            listed_under = owners.setdefault(_entry_key(entry, category), [])
            if category not in listed_under:
                listed_under.append(category)
    return {key: tuple(listed_under) for key, listed_under in owners.items()}


def _claimed_spans(tokens: TokenKey, index: Mapping[TokenKey, tuple[str, ...]]) -> list[TokenKey]:
    """The entry keys matched in the text, longest first then left to right, each token used at most once."""
    used = [False] * len(tokens)
    matched: list[TokenKey] = []
    for length in sorted({len(key) for key in index}, reverse=True):
        for start in range(len(tokens) - length + 1):
            window = tokens[start : start + length]
            if window not in index or any(used[start : start + length]):
                continue
            used[start : start + length] = [True] * length
            matched.append(window)
    return matched


def _overlaps(index: Mapping[TokenKey, tuple[str, ...]]) -> tuple[Overlap, ...]:
    return tuple(Overlap(" ".join(key), listed_under) for key, listed_under in index.items() if len(listed_under) > 1)


def match_entries(text: str, categories: Mapping[str, Sequence[str]]) -> MatchResult:
    """Count dictionary entries in one text.

    `categories` maps a category name to its entries. Raises TypeError for a non-str text, entry or entries list given
    as a bare str, and ValueError for an entry with no letters or digits. Negation is not handled (see module docstring).
    """
    tokens = tokenise(text)
    index = _build_index(categories)
    counts = {category: 0 for category in categories}
    for key in _claimed_spans(tokens, index):
        for category in index[key]:
            counts[category] += 1
    return MatchResult(
        category_counts=MappingProxyType(counts),
        total_words=len(tokens),
        overlaps=_overlaps(index),
    )
