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
- Each category is matched independently over the full text. Within one category, spans are claimed longest first
  (from the most tokens down, left to right) and a token is used by at most one span of that category, so a category
  listing both "give up" and "give" counts "give up" once, not twice. Categories never take words from each other:
  if "never give up" (category A) covers the words, "never" (category B) still scores 1 there.
- Because of that, spans of different categories can sit on the same words. `MatchResult.span_overlaps` reports, for
  each pair of categories with at least one such case, how many matched spans of the first and of the second category
  sit inside or overlap a matched span of the other. The overlaps are reported for a human and never resolved here:
  no count is changed because of them.
- An entry listed under two categories is counted in BOTH, and `MatchResult.overlaps` lists every such entry so a
  human can decide what to do. Nothing is dropped or merged here.
- `ignore_exact` (optional) names tokens that are counted as words but never matched when the text spells them exactly
  that way (case-sensitive). The voice counter uses it so the all-caps "US" is not read as the pronoun "us".

Known limits (stated, not fixed)
- NEGATION IS NOT HANDLED. "not a leader" counts "leader" exactly like "a leader". Nothing is guessed about meaning.
- A possessive or a contraction is a different word from its base: "fox's" does not match the entry "fox".
- Other inflections are not matched either: "win" does not match "wins" or "winning". List each form you want.
- "data driven" (a space) does not match the entry "data-driven", and the reverse.
"""
from __future__ import annotations

import re
from collections.abc import Collection, Mapping, Sequence
from dataclasses import dataclass
from itertools import combinations
from types import MappingProxyType

# A word: letters or digits, optionally chained by an inner apostrophe or hyphen ("we're", "data-driven").
_TOKEN = re.compile(r"[^\W_]+(?:['-][^\W_]+)*")
_TYPOGRAPHIC_TO_ASCII = str.maketrans(
    {"‘": "'", "’": "'", "‐": "-", "‑": "-"},
)
# Stands in for an ignored token: still one word in the count, equal to no entry token.
_NEVER_MATCHES = ""

TokenKey = tuple[str, ...]
Span = tuple[int, int]  # token positions, end exclusive


@dataclass(frozen=True)
class Overlap:
    """One entry (lower-cased, tokens joined by single spaces) that is listed under more than one category."""

    entry: str
    categories: tuple[str, ...]


@dataclass(frozen=True)
class SpanOverlap:
    """For two categories: matched spans of each that sit inside or overlap a matched span of the other."""

    categories: tuple[str, str]
    first_overlapped: int
    second_overlapped: int


@dataclass(frozen=True)
class MatchResult:
    """Counts per category (every category appears, 0 when nothing matched), total words, and two overlap reports."""

    category_counts: Mapping[str, int]
    total_words: int
    overlaps: tuple[Overlap, ...]
    span_overlaps: tuple[SpanOverlap, ...]


def _cased_tokens(text: str) -> tuple[str, ...]:
    if not isinstance(text, str):
        raise TypeError(f"text must be a str, got {type(text).__name__}")
    return tuple(_TOKEN.findall(text.translate(_TYPOGRAPHIC_TO_ASCII)))


def tokenise(text: str) -> tuple[str, ...]:
    """Lower-cased word tokens of the text; apostrophe and hyphen variants are normalised first."""
    return tuple(token.lower() for token in _cased_tokens(text))


def _ignore_set(ignore_exact: Collection[str]) -> frozenset[str]:
    if isinstance(ignore_exact, str):
        raise TypeError("ignore_exact must be a list of str, not one str")
    ignored = []
    for token in ignore_exact:
        if not isinstance(token, str) or not token.strip():
            raise ValueError(f"ignore_exact entries must be non-empty str, got {token!r}")
        ignored.append(token.translate(_TYPOGRAPHIC_TO_ASCII))
    return frozenset(ignored)


def _text_tokens(text: str, ignored: frozenset[str]) -> TokenKey:
    return tuple(_NEVER_MATCHES if token in ignored else token.lower() for token in _cased_tokens(text))


def _entry_key(entry: str, category: str) -> TokenKey:
    if not isinstance(entry, str):
        raise TypeError(f"entry in category {category!r} must be a str, got {type(entry).__name__}")
    key = tokenise(entry)
    if not key:
        raise ValueError(f"entry {entry!r} in category {category!r} has no word characters")
    return key


def _category_keys(categories: Mapping[str, Sequence[str]]) -> dict[str, tuple[TokenKey, ...]]:
    """Category -> its entry keys in the order given; an entry repeated inside one category counts once."""
    keys: dict[str, tuple[TokenKey, ...]] = {}
    for category, entries in categories.items():
        if isinstance(entries, str):
            raise TypeError(f"entries of category {category!r} must be a list of str, not one str")
        keys[category] = tuple(dict.fromkeys(_entry_key(entry, category) for entry in entries))
    return keys


def _category_spans(tokens: TokenKey, keys: Collection[TokenKey]) -> list[Span]:
    """Spans of one category: longest first then left to right, each token used by at most one span."""
    index = frozenset(keys)
    used = [False] * len(tokens)
    spans: list[Span] = []
    for length in sorted({len(key) for key in index}, reverse=True):
        for start in range(len(tokens) - length + 1):
            end = start + length
            if tokens[start:end] not in index or any(used[start:end]):
                continue
            used[start:end] = [True] * length
            spans.append((start, end))
    return spans


def _shared_entries(keys_by_category: Mapping[str, tuple[TokenKey, ...]]) -> tuple[Overlap, ...]:
    owners: dict[TokenKey, list[str]] = {}
    for category, keys in keys_by_category.items():
        for key in keys:
            owners.setdefault(key, []).append(category)
    return tuple(Overlap(" ".join(key), tuple(listed_under)) for key, listed_under in owners.items() if len(listed_under) > 1)


def _spans_touch(first: Span, second: Span) -> bool:
    return first[0] < second[1] and second[0] < first[1]


def _overlapped(spans: Sequence[Span], others: Sequence[Span]) -> int:
    return sum(any(_spans_touch(span, other) for other in others) for span in spans)


def _span_overlaps(spans_by_category: Mapping[str, Sequence[Span]]) -> tuple[SpanOverlap, ...]:
    found: list[SpanOverlap] = []
    for first, second in combinations(spans_by_category, 2):
        first_overlapped = _overlapped(spans_by_category[first], spans_by_category[second])
        if first_overlapped == 0:
            continue
        second_overlapped = _overlapped(spans_by_category[second], spans_by_category[first])
        found.append(SpanOverlap((first, second), first_overlapped, second_overlapped))
    return tuple(found)


def match_entries(
    text: str,
    categories: Mapping[str, Sequence[str]],
    *,
    ignore_exact: Collection[str] = (),
) -> MatchResult:
    """Count dictionary entries in one text, each category independently (see module docstring).

    `categories` maps a category name to its entries. Raises TypeError for a non-str text, entry or entries list given
    as a bare str, and ValueError for an entry with no letters or digits. Negation is not handled (see module docstring).
    """
    tokens = _text_tokens(text, _ignore_set(ignore_exact))
    keys_by_category = _category_keys(categories)
    spans_by_category = {category: _category_spans(tokens, keys) for category, keys in keys_by_category.items()}
    return MatchResult(
        category_counts=MappingProxyType({category: len(spans) for category, spans in spans_by_category.items()}),
        total_words=len(tokens),
        overlaps=_shared_entries(keys_by_category),
        span_overlaps=_span_overlaps(spans_by_category),
    )
