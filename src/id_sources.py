"""Turn the four people lists into matching Entities. Pure frame-in, entities-out; no file I/O.

Sources (ref = an opaque pointer, never a name):
- sheets: one entity per distinct leader key in the harmonised posts; ref = "<workbook>#<sheet_idx>"
  of the first sheet (workbook then index order) that holds that leader;
- roster: one entity per roster row; ref = "row:<n>" (1-based data row);
- summaries: one entity per filled name cell on sheet index 0 of every wordcount_* workbook;
  ref = "<workbook>#0:r<excel row>";
- company: one entity per Company_Data row with a name; ref = "row:<n>".
Repeated names inside roster, summaries and company stay separate entities so the matcher reports
them as ambiguous instead of merging two people.
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, replace
from pathlib import PurePosixPath

import pandas as pd

from src.id_matching import Entity, make_entity
from src.loader import SheetRecord

SOURCE_SHEETS = "sheets"
SOURCE_ROSTER = "roster"
SOURCE_SUMMARIES = "summaries"
SOURCE_COMPANY = "company"

SUMMARY_WORKBOOK_PREFIX = "wordcount_"
SUMMARY_SHEET_POSITION = 0
SUMMARY_NAME_HEADER = "founder"
SUMMARY_COMPANY_HEADER = "company"
COMPANY_NAME_COLUMN = "Person_Name"
COMPANY_FIRM_COLUMN = "CompanyName"


@dataclass(frozen=True)
class SummarySheet:
    """One wordcount summary sheet: where it is and how many name cells it holds."""

    workbook: str
    sheet_idx: int
    names_filled: int


def _keep_first_company(found: dict[str, Entity], entity: Entity) -> None:
    held = found.get(entity.key)
    if held is None:
        found[entity.key] = entity
    elif not held.company_key and entity.company_key:
        found[entity.key] = replace(held, company_key=entity.company_key)


def sheet_entities(posts: pd.DataFrame) -> tuple[Entity, ...]:
    """One entity per distinct leader key; ref points at the first sheet that holds the leader."""
    ordered = posts.assign(_idx=pd.to_numeric(posts["sheet_idx"])).sort_values(
        ["workbook", "_idx"], kind="stable"
    )
    found: dict[str, Entity] = {}
    for leader, company, workbook, idx in zip(
        ordered["leader"], ordered["company"], ordered["workbook"], ordered["sheet_idx"], strict=True
    ):
        entity = make_entity(SOURCE_SHEETS, f"{workbook}#{idx}", leader, company)
        if entity is not None:
            _keep_first_company(found, entity)
    return tuple(found.values())


def _row_entities(source: str, names: Sequence[object], companies: Sequence[object] | None) -> tuple[Entity, ...]:
    firms: Sequence[object] = companies if companies is not None else [None] * len(names)
    made = (
        make_entity(source, f"row:{position}", name, firm)
        for position, (name, firm) in enumerate(zip(names, firms, strict=True), start=1)
    )
    return tuple(entity for entity in made if entity is not None)


def roster_entities(roster: pd.DataFrame) -> tuple[Entity, ...]:
    return _row_entities(SOURCE_ROSTER, roster["person_name"].tolist(), roster["company"].tolist())


def company_entities(company: pd.DataFrame) -> tuple[Entity, ...]:
    if COMPANY_NAME_COLUMN not in company.columns:
        raise ValueError(f"Company_Data has no {COMPANY_NAME_COLUMN} column")
    firms = company[COMPANY_FIRM_COLUMN].tolist() if COMPANY_FIRM_COLUMN in company.columns else None
    return _row_entities(SOURCE_COMPANY, company[COMPANY_NAME_COLUMN].tolist(), firms)


def _is_summary_candidate(record: SheetRecord, position: int) -> bool:
    name = PurePosixPath(record.workbook).name.lower()
    return (
        position == SUMMARY_SHEET_POSITION
        and record.frame is not None
        and name.startswith(SUMMARY_WORKBOOK_PREFIX)
    )


def _header_column(header: Sequence[object], wanted: str) -> int | None:
    for position, cell in enumerate(header):
        if str(cell).strip().lower() == wanted:
            return position
    return None


def _sheet_summary_entities(record: SheetRecord, frame: pd.DataFrame) -> tuple[Entity, ...]:
    header = frame.iloc[0].tolist()
    name_col = _header_column(header, SUMMARY_NAME_HEADER)
    if name_col is None:
        raise ValueError(f"summary sheet {record.workbook} has no Founder column")
    company_col = _header_column(header, SUMMARY_COMPANY_HEADER)
    made: list[Entity | None] = []
    for row_index in range(1, len(frame)):
        company = frame.iat[row_index, company_col] if company_col is not None else None
        ref = f"{record.workbook}#{SUMMARY_SHEET_POSITION}:r{row_index + 1}"
        made.append(make_entity(SOURCE_SUMMARIES, ref, frame.iat[row_index, name_col], company))
    return tuple(entity for entity in made if entity is not None)


def summary_entities(records: Sequence[SheetRecord]) -> tuple[tuple[Entity, ...], tuple[SummarySheet, ...]]:
    """Name cells of the wordcount summary sheets, plus one SummarySheet per sheet read."""
    positions: dict[str, int] = {}
    entities: list[Entity] = []
    sheets: list[SummarySheet] = []
    for record in records:
        position = positions.get(record.workbook, 0)
        positions[record.workbook] = position + 1
        if not _is_summary_candidate(record, position) or record.frame is None:
            continue
        found = _sheet_summary_entities(record, record.frame)
        entities.extend(found)
        sheets.append(SummarySheet(record.workbook, position, len(found)))
    return tuple(entities), tuple(sheets)
