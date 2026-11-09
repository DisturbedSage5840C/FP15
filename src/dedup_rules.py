"""Pure rules for telling duplicate post cells from different ones (no I/O, no network).

Used by the harmonise dedupe and by the characterisation report. Link types come from the domain and path
pattern only; a link is never fetched.
"""
from __future__ import annotations

import re
from collections.abc import Sequence

MAX_HEAD_LINES = 5
LINK_TYPES = ("linkedin_post", "linkedin_profile_or_company", "linkedin_other_path", "other_domain", "no_link")
RELATIONS = ("trailing_only", "prefix", "first_lines", "other")

_LINKEDIN = re.compile(r"^(?:https?://)?(?:[\w-]+\.)*linkedin\.com(?P<path>/[^?#]*)?", re.IGNORECASE)
_POST_PATHS = ("/posts/", "/feed/update/", "/pulse/", "/embed/feed/update/")
_PROFILE_PATHS = ("/in/", "/company/", "/school/", "/showcase/")
_TRAILING_LINE = re.compile(r"^(?:\d[\d,.]*\s*[KkMm]?|\d{1,3}\s*(?:yr|mo|w|d|h)\b.*)$")


def link_type(link: str) -> str:
    """One of LINK_TYPES, from the domain and path pattern alone."""
    text = link.strip()
    if not text:
        return "no_link"
    found = _LINKEDIN.match(text)
    if found is None:
        return "other_domain"
    path = (found.group("path") or "/").lower()
    if path.startswith(_POST_PATHS):
        return "linkedin_post"
    if path.startswith(_PROFILE_PATHS):
        return "linkedin_profile_or_company"
    return "linkedin_other_path"


def _flat(text: str) -> str:
    return " ".join(text.split())


def strip_trailing(text: str) -> str:
    """The text without trailing lines that are a bare count or a relative-age line, whitespace-flattened."""
    lines = text.strip().splitlines()
    while lines and _TRAILING_LINE.match(lines[-1].strip()):
        lines.pop()
    return _flat("\n".join(lines))


def _drop_head(text: str, n: int) -> str:
    return _flat("\n".join(text.strip().splitlines()[n:]))


def _all_equal(values: Sequence[str]) -> bool:
    return len(set(values)) == 1


def relation(texts: Sequence[str]) -> str:
    """How the texts of one group differ (they are not all identical): one of RELATIONS."""
    if _all_equal([strip_trailing(t) for t in texts]):
        return "trailing_only"
    flat = sorted((_flat(t) for t in texts), key=len)
    if all(other.startswith(flat[0]) for other in flat[1:]):
        return "prefix"
    for n in range(1, MAX_HEAD_LINES + 1):
        heads = [_drop_head(t, n) for t in texts]
        if heads[0] and _all_equal(heads):
            return "first_lines"
    return "other"


def collapses_into(kept: str, row: str, is_post_url: bool) -> bool:
    """True when `row` is a duplicate of the kept (longer or equal) text under the conservative rule.

    (a) identical raw text; (b) the row is the start of the kept text; (c) for a LinkedIn post URL, the texts
    differ only in the trailing number or age line.
    """
    if kept == row:
        return True
    flat_row = _flat(row)
    if flat_row and _flat(kept).startswith(flat_row):
        return True
    return is_post_url and strip_trailing(kept) != "" and strip_trailing(kept) == strip_trailing(row)
