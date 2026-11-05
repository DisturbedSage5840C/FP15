"""Decide, sheet by sheet, which column holds what, before any row is read (harmonise step 1).

A plan is built from the header text (raw case matters: a header with a space, "Post date",
is a relative age, while "post_date" is the date column) and, only where a header is missing
or blank, from the position in the 14-column leader_posts layout. A positional guess is made
only when at least MIN_POSITIONAL_MATCHES header cells already sit at their canonical
position, so a sheet is never mapped on a hunch. Every sheet that cannot be mapped gets a
written skip reason.
"""
from __future__ import annotations

from dataclasses import dataclass

from src.loader import SheetRecord
from src.sheet_profile import LEADER_POSTS_14, SheetProfile, normalise_header

ROLE_BY_HEADER = {
    "leader_name": "leader",
    "company_name": "company",
    "current_title": "title",
    "ceo_type": "ceo_type",
    "platform": "platform",
    "post_text": "post_text",
    "cleaned_post_text": "post_text",
    "link_to_post_url": "link",
    "link_to_the_post_(if_available)": "link",
    "linkedin_profile_url": "profile_url",
    "post_date_text": "post_date_text",
    "post_date": "post_date",
    "role_start_year": "role_start_year",
}
AGE_TEXT_ROLE = "age_text"
NON_POST_LAYOUT_REASONS = {
    "roster_5": "roster sheet (the roster is loaded once from seventh_100_leaders/All_500.xlsx)",
    "word_frequency_9": "word-frequency sheet (no post text)",
    "summary_8": "summary sheet (no post text)",
}
MIN_POSITIONAL_MATCHES = 3  # header cells already at their canonical position before filling blanks


@dataclass(frozen=True)
class SheetPlan:
    skip_reason: str | None
    roles: tuple[tuple[int, str], ...]  # (column position, role), ordered by position
    first_data_row: int
    method: str  # "header" | "header+positional" | "positional" | "" when skipped
    text_kind: str  # "raw" (post_text) | "cleaned" (cleaned_post_text) | "" when skipped


def column_role(raw_header: object) -> str | None:
    """Role of a raw header cell, or None when the column is not part of the schema."""
    text = str(raw_header).strip()
    normalised = normalise_header(text)
    if normalised == "post_date" and any(ch.isspace() for ch in text):
        return AGE_TEXT_ROLE
    return ROLE_BY_HEADER.get(normalised)


def _skipped(reason: str) -> SheetPlan:
    return SheetPlan(skip_reason=reason, roles=(), first_data_row=0, method="", text_kind="")


def _first_column_per_role(roles_by_position: dict[int, str]) -> tuple[tuple[int, str], ...]:
    seen: set[str] = set()
    kept: list[tuple[int, str]] = []
    for position in sorted(roles_by_position):
        role = roles_by_position[position]
        if role not in seen:
            seen.add(role)
            kept.append((position, role))
    return tuple(kept)


def _canonical_roles() -> dict[int, str]:
    roles = {i: column_role(name) for i, name in enumerate(LEADER_POSTS_14)}
    return {i: role for i, role in roles.items() if role is not None}


def _header_roles(cells: tuple[str, ...]) -> tuple[dict[int, str], bool]:
    """Roles from header text, then blank cells filled by position; True if any fill happened."""
    roles = {i: role for i, cell in enumerate(cells) if (role := column_role(cell)) is not None}
    matches = sum(normalise_header(c) == LEADER_POSTS_14[i] for i, c in enumerate(cells[: len(LEADER_POSTS_14)]))
    if matches < MIN_POSITIONAL_MATCHES:
        return roles, False
    canonical = _canonical_roles()
    taken = set(roles.values())
    filled = {
        i: canonical[i]
        for i, cell in enumerate(cells)
        if not cell and i in canonical and canonical[i] not in taken
    }
    return {**roles, **filled}, bool(filled)


def _text_kind(roles: tuple[tuple[int, str], ...], cells: tuple[str, ...]) -> str:
    for position, role in roles:
        if role == "post_text" and position < len(cells) and normalise_header(cells[position]) == "cleaned_post_text":
            return "cleaned"
    return "raw"


def plan_sheet(record: SheetRecord, profile: SheetProfile) -> SheetPlan:
    """Plan one sheet from its record and profile; a skipped sheet carries its reason."""
    if profile.header_kind == "skipped":
        return _skipped(record.skip_reason or "unreadable sheet")
    if profile.header_kind == "blank":
        return _skipped("blank sheet")
    if profile.header_kind == "data":
        if profile.width < len(LEADER_POSTS_14):
            return _skipped(f"no header row and fewer than {len(LEADER_POSTS_14)} columns")
        roles = _first_column_per_role(_canonical_roles())
        return SheetPlan(None, roles, profile.header_row_index, "positional", "raw")
    if profile.layout in NON_POST_LAYOUT_REASONS:
        return _skipped(NON_POST_LAYOUT_REASONS[profile.layout])
    if profile.n_data_rows == 0:
        return _skipped("header only, no data rows")
    by_position, filled = _header_roles(profile.header_cells)
    roles = _first_column_per_role(by_position)
    if "post_text" not in {role for _, role in roles}:
        return _skipped("no post-text column")
    return SheetPlan(
        skip_reason=None,
        roles=roles,
        first_data_row=profile.header_row_index + 1,
        method="header+positional" if filled else "header",
        text_kind=_text_kind(roles, profile.header_cells),
    )
