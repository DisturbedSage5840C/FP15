"""Voice counter: first-person singular and plural pronouns in one text, and the singular share (I-rate).

Built on src.dictionary_matcher and tested on made-up sentences only. It has NOT been run on any post text or data:
G1 (segmentation) is not signed, so no segmented text exists yet. It reads configs/pronouns.yaml and nothing else.

What it counts
- Singular: I, me, my, mine, myself and the contractions I'm, I've, I'll, I'd.
- Plural: we, us, our, ours, ourselves and the contractions we're, we've, we'll, we'd.
- Total words: every word token, with a hyphenated word or a contraction counted as one word.
- Singular share = singular count / total words. It is None (missing, not 0.0) when the text has no words.

How to read the share
The singular share is one signal about the image a leader projects in public posts. It is not a narcissism score, and
it says nothing about personality. Plural voice is reported beside it so the two can be read together.

Known limitations (stated, not fixed)
- A standalone capital I can be a Roman numeral ("Phase I"). It is counted as first-person singular anyway, because
  telling the two apart needs judgment this counter does not make. A test records the current behaviour.
- Matching ignores case, so "US" (the country) counts as the plural "us", and "mine" as a noun counts as a pronoun.
- Negation is not handled (see src.dictionary_matcher): "not my decision" counts "my".
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import yaml

from src.dictionary_matcher import match_entries, tokenise

DEFAULT_PRONOUNS_PATH = Path(__file__).resolve().parent.parent / "configs" / "pronouns.yaml"
SINGULAR_KEY = "first_person_singular"
PLURAL_KEY = "first_person_plural"


@dataclass(frozen=True)
class PronounLists:
    """The two first-person lists. A pronoun may be in one list only, or it would be counted twice."""

    singular: tuple[str, ...]
    plural: tuple[str, ...]

    def __post_init__(self) -> None:
        shared = {tokenise(word) for word in self.singular} & {tokenise(word) for word in self.plural}
        if shared:
            words = ", ".join(sorted(" ".join(tokens) for tokens in shared))
            raise ValueError(f"pronouns listed in both singular and plural: {words}")


@dataclass(frozen=True)
class VoiceCounts:
    """Pronoun counts for one text. singular_share is None when the text has no words."""

    singular: int
    plural: int
    total_words: int
    singular_share: float | None


def _word_list(values: object, key: str, path: Path) -> tuple[str, ...]:
    if not isinstance(values, dict) or not isinstance(values.get(key), list) or not values[key]:
        raise ValueError(f"{path.name} needs a non-empty list named {key}")
    words = values[key]
    if not all(isinstance(word, str) and word.strip() for word in words):
        raise ValueError(f"{path.name}: every entry of {key} must be a non-empty string")
    return tuple(words)


def load_pronouns(path: Path = DEFAULT_PRONOUNS_PATH) -> PronounLists:
    """Read the pronoun lists; a missing file raises FileNotFoundError, a malformed one ValueError."""
    values = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return PronounLists(
        singular=_word_list(values, SINGULAR_KEY, path),
        plural=_word_list(values, PLURAL_KEY, path),
    )


@lru_cache(maxsize=1)
def _default_pronouns() -> PronounLists:
    return load_pronouns()


def count_voice(text: str, pronouns: PronounLists | None = None) -> VoiceCounts:
    """Count first-person singular and plural pronouns and total words in one text.

    Uses the lists in configs/pronouns.yaml unless `pronouns` is given. Raises TypeError for a non-str text.
    """
    lists = pronouns if pronouns is not None else _default_pronouns()
    result = match_entries(text, {"singular": lists.singular, "plural": lists.plural})
    singular = result.category_counts["singular"]
    total_words = result.total_words
    return VoiceCounts(
        singular=singular,
        plural=result.category_counts["plural"],
        total_words=total_words,
        singular_share=singular / total_words if total_words else None,
    )
