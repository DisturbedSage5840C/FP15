"""Sorted-token name key: the one definition of "same name" used for dedupe and ID matching.

The key lowercases, folds accents, splits on anything that is not a letter or digit, and sorts
the tokens, so "Lee, Ann" and "ann  LEE" give the same key. It never infers anything beyond
the characters it is given. Two different people can share a key; matching code must report
those collisions and never resolve them silently.
"""
from __future__ import annotations

import math
import re
import unicodedata

_TOKEN = re.compile(r"[a-z0-9]+")


def name_key(text: object) -> str:
    """Return the sorted-token key of a name cell, or "" when the cell is blank."""
    if text is None or (isinstance(text, float) and math.isnan(text)):
        return ""
    decomposed = unicodedata.normalize("NFKD", str(text))
    folded = "".join(ch for ch in decomposed if not unicodedata.combining(ch)).lower()
    return " ".join(sorted(_TOKEN.findall(folded)))
