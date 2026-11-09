"""Repeated LinkedIn interface lines inside raw post cells: classify, count, and remove into a new column.

Rules are whole-line matches (after trimming). APPLIED rules are interface text that is never post content
and are removed from the clean column only; the raw `post_text` is never touched. PROPOSED rules are lines
that are often interface but can also be real content (a lone dot, a bare link host, a bare number that may
be a reaction count), so they are counted and reported but not applied until a human agrees.
"""
from __future__ import annotations

import re
from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass

DIGIT_MASK = "<n>"
_DIGITS = re.compile(r"\d+")


@dataclass(frozen=True)
class InterfaceRule:
    """One whole-line rule. `description` is generic wording for the report, never a quoted post line."""

    name: str
    description: str
    pattern: re.Pattern[str]
    applied: bool

    def matches(self, line: str) -> bool:
        return self.pattern.match(line) is not None


def _rule(name: str, description: str, pattern: str, applied: bool) -> InterfaceRule:
    return InterfaceRule(name, description, re.compile(pattern), applied)


APPLIED_RULES: tuple[InterfaceRule, ...] = (
    _rule("connection_marker", "connection-degree marker line after the author name", r"^•\s*(?:1st|2nd|3rd\+?|Following)$", True),
    _rule("follow", "Follow button text", r"^\+?\s*Follow$", True),
    _rule("see_more", "see-more truncation marker", r"^(?:…|\.\.\.)\s*more$", True),
    _rule("image_prompt", "image accessibility prompt", r"^Activate to view larger image,?$", True),
    _rule("age_line", "relative post age line", r"^\d{1,3}(?:yr|mo|w|d|h)\s*•", True),
    _rule("like_comment_repost_send", "reaction-bar button labels", r"^(?:Like|Comment|Repost|Send)$", True),
    _rule("document_loading", "embedded-document loading notice", r"^Your document is loading", True),
)
PROPOSED_RULES: tuple[InterfaceRule, ...] = (
    _rule("join", "event or group Join button", r"^Join$", False),
    _rule("view_job", "job card View job button", r"^View job$", False),
    _rule("lone_dot", "a line holding only a full stop", r"^\.$", False),
    _rule("bare_digits", "a line holding only a number (may be a reaction count)", r"^\d[\d,]*$", False),
    _rule("bare_host", "a line holding only a link host name", r"^(?=.*[A-Za-z])[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+$", False),
)
ALL_RULES = (*APPLIED_RULES, *PROPOSED_RULES)


@dataclass(frozen=True)
class LinePattern:
    """A normalised line seen in many cells, with how often and for how many leaders."""

    pattern: str
    lines: int
    leaders: int


def classify_line(line: str) -> InterfaceRule | None:
    """The first rule the trimmed line matches, or None when it looks like post content."""
    stripped = line.strip()
    return next((rule for rule in ALL_RULES if rule.matches(stripped)), None)


def normalise_line(line: str) -> str:
    """Trim and mask digit runs so counts group (a reaction count of 12 and of 345 are one pattern)."""
    return _DIGITS.sub(DIGIT_MASK, line.strip())


def clean_text(text: str) -> str:
    """The cell without APPLIED interface lines, blank runs collapsed and the ends trimmed."""
    kept: list[str] = []
    for line in text.split("\n"):
        rule = classify_line(line)
        if rule is not None and rule.applied:
            continue
        if not line.strip() and kept and not kept[-1].strip():
            continue
        kept.append(line)
    return "\n".join(kept).strip()


def rule_counts(cells: Iterable[str]) -> dict[str, tuple[int, int]]:
    """(lines, cells) per rule name over the cells, with every rule present even when it never matched."""
    lines: Counter[str] = Counter()
    in_cells: Counter[str] = Counter()
    for text in cells:
        seen: set[str] = set()
        for line in text.split("\n"):
            rule = classify_line(line)
            if rule is None:
                continue
            lines[rule.name] += 1
            seen.add(rule.name)
        in_cells.update(seen)
    return {rule.name: (lines[rule.name], in_cells[rule.name]) for rule in ALL_RULES}


def line_frequencies(cells: Iterable[tuple[str, str]], min_leaders: int) -> list[LinePattern]:
    """Normalised lines seen for at least `min_leaders` leaders, most widespread first."""
    lines: Counter[str] = Counter()
    leaders: dict[str, set[str]] = {}
    for leader, text in cells:
        for line in text.split("\n"):
            pattern = normalise_line(line)
            if not pattern:
                continue
            lines[pattern] += 1
            leaders.setdefault(pattern, set()).add(leader)
    found = [LinePattern(pattern, lines[pattern], len(who)) for pattern, who in leaders.items() if len(who) >= min_leaders]
    return sorted(found, key=lambda item: (-item.leaders, -item.lines, item.pattern))
