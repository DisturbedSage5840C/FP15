"""Profile one loaded sheet: header layout, row counts, study-variable occupancy, author blocks.

Read-only and in memory. A profile carries counts and header labels only: never the sheet
name (sheet names can be people's names), never cell text, and author keys only as short
hashes. Variable occupancy is matched on header names; nothing is filled in or guessed.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from itertools import groupby
from typing import cast

import pandas as pd

from src.loader import SheetRecord

STUDY_VARIABLES = (
    "leader_name",
    "company_name",
    "current_title",
    "role_start_year",
    "ceo_type",
    "platform",
    "post_date",
    "post_date_text",
)

LEADER_POSTS_14 = (
    "selected_order", "excel_data_row_number", "excel_file_row_number", "leader_name",
    "company_name", "current_title", "role_start_year", "ceo_type", "platform", "post_date",
    "post_date_text", "post_text", "link_to_post_url", "linkedin_profile_url",
)
WORDCOUNT_LEADER_12 = (
    "leader_name", "company_name", "current_title", "role_start_year", "ceo_type", "platform",
    "post_date", "post_date_text", "link_to_post_url", "linkedin_profile_url",
    "cleaned_post_text", "post_date",
)
WORD_FREQUENCY_9 = (
    "source_workbook", "founder", "company", "word", "total_word_count",
    "posts_containing_word", "total_posts_for_founder", "post_presence_%",
    "important_word_(>50%_posts)",
)
SUMMARY_8 = (
    "founder", "company", "current_title", "linkedin_profile_url", "source_workbook",
    "usable_cleaned_posts", "linkedin_activity_status", "important_words_(>50%_posts)",
)
ROSTER_5 = ("companyname", "person_name", "current_title", "linkedin_profile_link", "person_id")

LAYOUTS: dict[str, tuple[str, ...]] = {
    "leader_posts_14": LEADER_POSTS_14,
    "wordcount_leader_12": WORDCOUNT_LEADER_12,
    "word_frequency_9": WORD_FREQUENCY_9,
    "summary_8": SUMMARY_8,
    "roster_5": ROSTER_5,
}
OFF_LAYOUT = "off-layout"
NO_HEADER_LAYOUT = "no-header"
SKIPPED_LAYOUT = "skipped"

AUTHOR_COLUMNS = ("leader_name", "founder", "person_name")
HEADER_VOCABULARY = frozenset(c for layout in LAYOUTS.values() for c in layout) | frozenset(STUDY_VARIABLES)
MIN_HEADER_HITS = 3  # known header words needed before a row is called a header
MAX_LEADING_BLANK_ROWS = 20
AUTHOR_HASH_CHARS = 12


@dataclass(frozen=True)
class SheetProfile:
    workbook: str
    position: int
    skip_reason: str | None
    header_kind: str  # "header" | "data" | "blank" | "skipped"
    header_row_index: int
    header_cells: tuple[str, ...]
    width: int
    n_data_rows: int
    layout: str
    variable_counts: dict[str, int]
    author_blocks: int | None
    author_distinct: int | None
    author_hashes: tuple[str, ...]
    extra_nonempty_cells: int
    odd_reasons: tuple[str, ...]


def normalise_header(text: object) -> str:
    return re.sub(r"[\s\-]+", "_", str(text).strip().lower())


def _cell_text(value: object) -> str:
    return "" if cast(bool, pd.isna(value)) else str(value).strip()


def _nonblank(frame: pd.DataFrame) -> pd.DataFrame:
    """True where a cell holds something other than whitespace."""
    if frame.shape[1] == 0:
        return pd.DataFrame(index=frame.index)
    text = frame.astype(str).apply(lambda column: column.str.strip())
    return frame.notna() & (text != "")


def _header_cells(row: pd.Series) -> tuple[str, ...]:
    """Header labels with trailing blank cells trimmed."""
    cells = [_cell_text(v) for v in row.tolist()]
    while cells and not cells[-1]:
        cells.pop()
    return tuple(cells)


def _first_nonblank_row(frame: pd.DataFrame) -> int | None:
    head = frame.iloc[:MAX_LEADING_BLANK_ROWS].dropna(axis=1, how="all")
    filled = _nonblank(head).any(axis=1)
    return int(filled.to_numpy().argmax()) if filled.any() else None


def _looks_like_header(normalised: tuple[str, ...]) -> bool:
    return sum(name in HEADER_VOCABULARY for name in normalised) >= MIN_HEADER_HITS


UNNAMED_HEADER = re.compile(r"unnamed:_\d+")


def _nearest_layout_reason(normalised: tuple[str, ...]) -> str:
    present = set(normalised)

    def similarity(name: str) -> float:
        known = set(LAYOUTS[name])
        return len(known & present) / len(known | present)

    nearest = max(LAYOUTS, key=similarity)
    missing = [c for c in LAYOUTS[nearest] if c not in present]
    distinct = list(dict.fromkeys(normalised))
    extra = [c for c in distinct if c not in LAYOUTS[nearest] and not UNNAMED_HEADER.fullmatch(c)]
    n_unnamed = sum(1 for c in distinct if UNNAMED_HEADER.fullmatch(c))
    if n_unnamed:
        extra.append(f"{n_unnamed} unnamed column(s)")
    return (
        f"{OFF_LAYOUT} (nearest: {nearest}; missing: {', '.join(missing) or '-'}; "
        f"extra: {', '.join(extra) or '-'})"
    )


def _hash_key(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:AUTHOR_HASH_CHARS]


def _author_stats(
    cells: tuple[str, ...], data: pd.DataFrame, filled: pd.DataFrame
) -> tuple[int | None, int | None, tuple[str, ...]]:
    column = next((i for i, c in enumerate(cells) if normalise_header(c) in AUTHOR_COLUMNS), None)
    if column is None:
        return None, None, ()
    keys = [_cell_text(v) for v in data.iloc[:, column][filled.iloc[:, column]].tolist()]
    blocks = sum(1 for _ in groupby(keys))
    hashes = tuple(sorted({_hash_key(k) for k in keys}))
    return blocks, len(hashes), hashes


def _beyond_header(frame: pd.DataFrame, header_width: int, first_row: int) -> tuple[int, int]:
    """(non-empty cells, entirely blank columns) to the right of the header."""
    extra = frame.iloc[first_row:, header_width:]
    nonempty_columns = extra.dropna(axis=1, how="all")
    nonempty_cells = int(_nonblank(nonempty_columns).to_numpy().sum())
    return nonempty_cells, extra.shape[1] - nonempty_columns.shape[1]


def _skipped_profile(record: SheetRecord, position: int) -> SheetProfile:
    return SheetProfile(
        workbook=record.workbook, position=position, skip_reason=record.skip_reason,
        header_kind="skipped", header_row_index=0, header_cells=(), width=0, n_data_rows=0,
        layout=SKIPPED_LAYOUT, variable_counts={}, author_blocks=None, author_distinct=None,
        author_hashes=(), extra_nonempty_cells=0, odd_reasons=(),
    )


def _odd_reasons(
    layout: str, nearest: str, first_row: int, nonempty_extra: int, blank_columns: int, is_header: bool
) -> tuple[str, ...]:
    reasons = [nearest] if layout == OFF_LAYOUT else []
    if not is_header:
        reasons.append("no header row (first row is data)")
    if first_row:
        reasons.append(f"{first_row} blank row(s) above the header" if is_header else f"{first_row} blank row(s) above the data")
    if nonempty_extra:
        reasons.append(f"{nonempty_extra} non-empty cell(s) beyond the header")
    if blank_columns:
        reasons.append(f"{blank_columns} blank column(s) beyond the header")
    return tuple(reasons)


def profile_sheet(record: SheetRecord, position: int) -> SheetProfile:
    """Profile one sheet record; ``position`` is its index inside the workbook."""
    frame = record.frame
    if frame is None:
        return _skipped_profile(record, position)
    first_row = _first_nonblank_row(frame)
    if first_row is None:
        return SheetProfile(
            workbook=record.workbook, position=position, skip_reason=None, header_kind="blank",
            header_row_index=0, header_cells=(), width=frame.shape[1], n_data_rows=0,
            layout=SKIPPED_LAYOUT, variable_counts={}, author_blocks=None, author_distinct=None,
            author_hashes=(), extra_nonempty_cells=0, odd_reasons=("sheet is blank",),
        )

    cells = _header_cells(frame.iloc[first_row])
    normalised = tuple(normalise_header(c) for c in cells)
    is_header = _looks_like_header(normalised)
    if not is_header:
        return SheetProfile(
            workbook=record.workbook, position=position, skip_reason=None, header_kind="data",
            header_row_index=first_row, header_cells=(), width=frame.shape[1],
            n_data_rows=len(frame) - first_row, layout=NO_HEADER_LAYOUT, variable_counts={},
            author_blocks=None, author_distinct=None, author_hashes=(), extra_nonempty_cells=0,
            odd_reasons=_odd_reasons(NO_HEADER_LAYOUT, "", first_row, 0, 0, False),
        )

    layout = next((name for name, known in LAYOUTS.items() if known == normalised), OFF_LAYOUT)
    nearest = _nearest_layout_reason(normalised) if layout == OFF_LAYOUT else ""
    data = frame.iloc[first_row + 1 :, : len(cells)]
    filled = _nonblank(data)
    counts = {
        raw: int(filled.iloc[:, i].sum())
        for i, raw in enumerate(cells)
        if normalise_header(raw) in STUDY_VARIABLES
    }
    blocks, distinct, hashes = _author_stats(cells, data, filled)
    nonempty_extra, blank_columns = _beyond_header(frame, len(cells), first_row)
    return SheetProfile(
        workbook=record.workbook, position=position, skip_reason=None, header_kind="header",
        header_row_index=first_row, header_cells=cells, width=frame.shape[1], n_data_rows=len(data),
        layout=layout, variable_counts=counts, author_blocks=blocks, author_distinct=distinct,
        author_hashes=hashes, extra_nonempty_cells=nonempty_extra,
        odd_reasons=_odd_reasons(layout, nearest, first_row, nonempty_extra, blank_columns, True),
    )


def profile_records(records: list[SheetRecord]) -> list[SheetProfile]:
    """Profile every record; sheets are numbered from 0 within each workbook, in load order."""
    profiles: list[SheetProfile] = []
    for _, group in groupby(records, key=lambda r: r.workbook):
        profiles.extend(profile_sheet(record, position) for position, record in enumerate(group))
    return profiles
