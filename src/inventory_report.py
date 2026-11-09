"""Render the data inventory as markdown from sheet profiles.

Everything here is counts and header labels. Sheet names, file and workbook names, sheet
indexes, cell values and post text never reach the output, and author keys appear only as the
number of sheets they occur in. Workbooks are labelled workbook-NN in sorted-path order.
"""
from __future__ import annotations

import re
import zipfile
from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import cast

import pandas as pd

from src.loader import SheetRecord
from src.sheet_profile import (
    NO_HEADER_LAYOUT,
    OFF_LAYOUT,
    SKIPPED_LAYOUT,
    STUDY_VARIABLES,
    SheetProfile,
    normalise_header,
)

EXPECTED_EMPTY_VARIABLES = ("role_start_year", "post_date")
CONTACT_HEADER = re.compile(r"e-?mail|phone", re.IGNORECASE)
KIND_BY_SUFFIX = {".xlsx": "workbook", ".pdf": "pdf", ".py": "script"}
STRAY_CELLS_KIND = "known layout, with stray cells or blank rows"
NO_COLUMN = "-"


@dataclass(frozen=True)
class ZipMember:
    name: str
    size: int
    kind: str


@dataclass(frozen=True)
class CompanyDataSummary:
    n_rows: int
    n_columns: int
    contact_columns: tuple[str, ...]
    single_letter_headers: tuple[str, ...]


def _cell(value: object) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def _table(headers: Sequence[str], rows: Iterable[Sequence[object]]) -> str:
    lines = [f"| {' | '.join(headers)} |", f"|{'|'.join('---' for _ in headers)}|"]
    lines.extend(f"| {' | '.join(_cell(c) for c in row)} |" for row in rows)
    return "\n".join(lines)


def workbook_labels(profiles: Sequence[SheetProfile]) -> dict[str, str]:
    """Generic, stable labels (workbook-01, ...) in sorted-path order, so reports carry no file names."""
    return {name: f"workbook-{i:02d}" for i, name in enumerate(sorted({p.workbook for p in profiles}), start=1)}


def _header_profiles(profiles: Sequence[SheetProfile]) -> list[SheetProfile]:
    return [p for p in profiles if p.header_kind == "header"]


def list_zip_members(zip_path: Path) -> tuple[ZipMember, ...]:
    """Every non-directory member of the archive, in archive order (nothing is extracted)."""
    with zipfile.ZipFile(zip_path) as archive:
        return tuple(
            ZipMember(info.filename, info.file_size, KIND_BY_SUFFIX.get(Path(info.filename).suffix.lower(), "other"))
            for info in archive.infolist()
            if not info.is_dir()
        )


def render_raw_files(manifest: Mapping[str, str], sizes: Mapping[str, int]) -> str:
    rows = [
        (f"raw-file-{i:02d}", f"{sizes.get(name, 0):,}", digest)
        for i, (name, digest) in enumerate(sorted(manifest.items()), start=1)
    ]
    return _table(["File", "Bytes", "SHA-256 (from MANIFEST.sha256)"], rows)


def render_zip_members(members: Sequence[ZipMember]) -> str:
    kinds = Counter(m.kind for m in members)
    summary = ", ".join(f"{count} {kind}" for kind, count in sorted(kinds.items())) or "none"
    return f"{len(members)} members ({summary}). Member names are not listed."


def render_workbook_summary(profiles: Sequence[SheetProfile]) -> str:
    sheets: Counter[str] = Counter()
    rows: Counter[str] = Counter()
    for p in profiles:
        sheets[p.workbook] += 1
        rows[p.workbook] += p.n_data_rows
    labels = workbook_labels(profiles)
    body = [(labels[name], f"{sheets[name]:,}", f"{rows[name]:,}") for name in sorted(sheets)]
    return _table(["Workbook", "Sheets", "Data rows"], body)


def render_layouts(profiles: Sequence[SheetProfile]) -> str:
    groups: dict[str, list[SheetProfile]] = defaultdict(list)
    for p in profiles:
        groups[p.layout].append(p)
    body = []
    for layout, members in sorted(groups.items(), key=lambda item: -len(item[1])):
        widths = sorted({len(p.header_cells) for p in members if p.header_cells})
        body.append((layout, f"{len(members):,}", f"{sum(p.n_data_rows for p in members):,}",
                     ", ".join(map(str, widths)) or NO_COLUMN))
    return _table(["Layout", "Sheets", "Data rows", "Header cells"], body)


def _odd_kind(profile: SheetProfile) -> str:
    known = {OFF_LAYOUT, NO_HEADER_LAYOUT, SKIPPED_LAYOUT}
    return profile.layout if profile.layout in known else STRAY_CELLS_KIND


def render_odd_sheets(profiles: Sequence[SheetProfile]) -> str:
    odd = [p for p in profiles if p.odd_reasons]
    if not odd:
        return "No odd sheets: every sheet follows a known layout."
    kinds = Counter(_odd_kind(p) for p in odd)
    intro = (
        f"{len(odd)} of {len(profiles):,} sheets have at least one oddity. docs/FIRST_PROMPT.md names 4 "
        "odd sheets; the tables below count every sheet with any oddity. Which four were meant is for the "
        "project owner to pick out; the per-sheet list is in the git-ignored data/interim files."
    )
    kind_table = _table(["Kind of oddity", "Sheets"], kinds.most_common())
    reasons = Counter(reason for p in odd for reason in p.odd_reasons)
    reason_table = _table(["Reason", "Sheets"], reasons.most_common())
    return f"{intro}\n\n{kind_table}\n\n{reason_table}"


def _spelling_totals(profiles: Sequence[SheetProfile]) -> dict[tuple[str, str, str], tuple[int, int, int]]:
    """(layout, study variable, raw header) -> (sheets with the column, non-empty cells, data rows)."""
    totals: dict[tuple[str, str, str], tuple[int, int, int]] = {}
    for p in _header_profiles(profiles):
        for raw, non_empty in p.variable_counts.items():
            key = (p.layout, normalise_header(raw), raw)
            sheets, filled, rows = totals.get(key, (0, 0, 0))
            totals[key] = (sheets + 1, filled + non_empty, rows + p.n_data_rows)
    return totals


def render_variable_presence(profiles: Sequence[SheetProfile]) -> str:
    """One table per layout; counts are per exact column header, so two date columns never merge."""
    totals = _spelling_totals(profiles)
    sections = []
    for layout in sorted({layout for layout, _, _ in totals}):
        keys = sorted((k for k in totals if k[0] == layout), key=lambda k: (STUDY_VARIABLES.index(k[1]), k[2]))
        rows = [(variable, raw, totals[(layout, variable, raw)][0],
                 f"{totals[(layout, variable, raw)][1]:,} / {totals[(layout, variable, raw)][2]:,}")
                for _, variable, raw in keys]
        absent = [v for v in STUDY_VARIABLES if all(k[1] != v for k in keys)]
        note = f"\n\nNot present in this layout: {', '.join(absent)}." if absent else ""
        sections.append(f"### {layout}\n\n{_table(['Variable', 'Raw header', 'Sheets', 'Non-empty / rows'], rows)}{note}")
    return "\n\n".join(sections)


def render_filled_expected_empty(profiles: Sequence[SheetProfile]) -> str:
    """Workbooks where role_start_year or any post_date spelling holds values."""
    filled: dict[tuple[str, str], tuple[int, int]] = {}
    for p in _header_profiles(profiles):
        for raw, non_empty in p.variable_counts.items():
            if normalise_header(raw) in EXPECTED_EMPTY_VARIABLES and non_empty:
                count, rows = filled.get((p.workbook, raw), (0, 0))
                filled[(p.workbook, raw)] = (count + non_empty, rows + p.n_data_rows)
    if not filled:
        return "role_start_year and every post_date spelling are empty in every workbook."
    labels = workbook_labels(profiles)
    rows_out = [(labels[wb], raw, f"{count:,} / {rows:,}") for (wb, raw), (count, rows) in sorted(filled.items())]
    return _table(["Workbook", "Column", "Non-empty / rows"], rows_out)


def render_author_blocks(profiles: Sequence[SheetProfile]) -> str:
    authored = [p for p in profiles if p.author_blocks is not None and p.author_distinct is not None]
    blocks = Counter(p.author_blocks for p in authored)
    distinct = Counter(p.author_distinct for p in authored)
    split = sum(1 for p in authored if (p.author_blocks or 0) > (p.author_distinct or 0))
    sheets_per_leader = Counter(h for p in authored for h in p.author_hashes)
    repeated = sum(1 for n in sheets_per_leader.values() if n > 1)
    return "\n\n".join([
        f"{len(authored):,} sheets have a leader/founder column. A block is a run of consecutive rows by the "
        "same leader key; the key is the exact text of the cell, so near-duplicate spellings count as "
        "different leaders until the ID matching step.",
        _table(["Author blocks in a sheet", "Sheets"], sorted(blocks.items())),
        _table(["Distinct leader keys in a sheet", "Sheets"], sorted(distinct.items())),
        f"{split:,} sheets have more blocks than distinct leaders (a leader's rows are split into separate runs).",
        f"{len(sheets_per_leader):,} distinct leader keys in total; {repeated:,} of them appear in more than one sheet.",
    ])


def _label(value: object) -> str:
    return "" if cast(bool, pd.isna(value)) else str(value).strip()


def summarise_company_data(record: SheetRecord) -> CompanyDataSummary:
    """Shape and header names of Company_Data; no cell value is read into the summary."""
    if record.frame is None:
        raise ValueError(f"{record.workbook} was not loaded: {record.skip_reason}")
    header = tuple(_label(v) for v in record.frame.iloc[0].tolist())
    return CompanyDataSummary(
        n_rows=len(record.frame) - 1,
        n_columns=record.frame.shape[1],
        contact_columns=tuple(h for h in header if CONTACT_HEADER.search(h)),
        single_letter_headers=tuple(h for h in header if len(h) == 1),
    )


def render_company_data(summary: CompanyDataSummary) -> str:
    contact = ", ".join(summary.contact_columns) or "none"
    single = ", ".join(summary.single_letter_headers) or "none"
    return "\n".join([
        f"- Data rows: {summary.n_rows:,}; columns: {summary.n_columns:,} (one sheet).",
        f"- Contact columns found by header name (to be dropped at load in Step 3): {contact}.",
        f"- Single-letter headers (meaning unknown, logged under Findings): {single}.",
    ])


def render_report(
    manifest: Mapping[str, str],
    sizes: Mapping[str, int],
    members: Sequence[ZipMember],
    profiles: Sequence[SheetProfile],
    company: CompanyDataSummary,
) -> str:
    sections = [
        ("Raw files", render_raw_files(manifest, sizes)),
        ("Zip members", render_zip_members(members)),
        ("Workbooks", render_workbook_summary(profiles)),
        ("Header layouts", render_layouts(profiles)),
        ("Odd sheets", render_odd_sheets(profiles)),
        ("Study variables",
         f"{render_variable_presence(profiles)}\n\n### Where role_start_year or post_date holds values\n\n"
         f"{render_filled_expected_empty(profiles)}"),
        ("Author blocks", render_author_blocks(profiles)),
        ("Company_Data", render_company_data(company)),
    ]
    intro = (
        "Counts and header labels only: no sheet names, file names, sheet indexes, cell values or post text appear here. Read straight "
        "from data/raw after the manifest check; nothing is harmonised, filled in or guessed."
    )
    body = "\n\n".join(f"## {title}\n\n{text}" for title, text in sections)
    return f"# Data inventory\n\n{intro}\n\n{body}\n"
