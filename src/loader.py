"""Workbook loader: reads every sheet as-is and records why any sheet was skipped.

Sheets are read with header=None and dtype=object so the raw layout is preserved and no
value is coerced or guessed. Nothing here writes to disk, and zip members are read in
memory, so data/raw is never touched.
"""
from __future__ import annotations

import io
import logging
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO

import pandas as pd

logger = logging.getLogger(__name__)

WORKBOOK_LEVEL_SHEET = "*"
SKIP_LOG_COLUMNS = ["workbook", "sheet", "reason"]
EXCEL_SUFFIX = ".xlsx"


@dataclass(frozen=True)
class SheetRecord:
    workbook: str
    sheet: str
    frame: pd.DataFrame | None
    skip_reason: str | None

    @property
    def n_rows(self) -> int:
        return 0 if self.frame is None else len(self.frame)


def _skipped(workbook: str, sheet: str, reason: str) -> SheetRecord:
    logger.warning("skipped %s :: %s (%s)", workbook, sheet, reason)
    return SheetRecord(workbook=workbook, sheet=sheet, frame=None, skip_reason=reason)


def _read_sheet(excel: pd.ExcelFile, workbook: str, sheet: str) -> SheetRecord:
    try:
        frame = pd.read_excel(excel, sheet_name=sheet, header=None, dtype=object)
    except Exception as error:  # noqa: BLE001 - recorded in the skip log, never swallowed
        return _skipped(workbook, sheet, f"unreadable sheet: {type(error).__name__}: {error}")
    if frame.dropna(how="all").empty:
        return _skipped(workbook, sheet, "empty")
    return SheetRecord(workbook=workbook, sheet=sheet, frame=frame, skip_reason=None)


def load_workbook_sheets(source: Path | BinaryIO, workbook_label: str) -> list[SheetRecord]:
    """Load every sheet of one workbook; unreadable workbooks come back as one skipped record."""
    try:
        excel = pd.ExcelFile(source, engine="openpyxl")
    except Exception as error:  # noqa: BLE001 - recorded in the skip log, never swallowed
        reason = f"unreadable workbook: {type(error).__name__}: {error}"
        return [_skipped(workbook_label, WORKBOOK_LEVEL_SHEET, reason)]
    with excel:
        return [_read_sheet(excel, workbook_label, sheet) for sheet in excel.sheet_names]


def _is_macos_or_lock_artefact(member: str) -> bool:
    name = member.rsplit("/", 1)[-1]
    return member.startswith("__MACOSX/") or name.startswith("._") or name.startswith("~$")


def load_zip_workbooks(zip_path: Path) -> list[SheetRecord]:
    """Load every .xlsx member of a zip in memory (nothing is extracted to disk)."""
    records: list[SheetRecord] = []
    with zipfile.ZipFile(zip_path) as archive:
        members = sorted(m for m in archive.namelist() if m.lower().endswith(EXCEL_SUFFIX))
        for member in members:
            if _is_macos_or_lock_artefact(member):
                records.append(_skipped(member, WORKBOOK_LEVEL_SHEET, "macOS/Office metadata file, not a workbook"))
                continue
            records.extend(load_workbook_sheets(io.BytesIO(archive.read(member)), member))
    return records


def skip_log(records: list[SheetRecord]) -> pd.DataFrame:
    """One row per skipped sheet: workbook, sheet, reason."""
    rows = [
        {"workbook": r.workbook, "sheet": r.sheet, "reason": r.skip_reason}
        for r in records
        if r.skip_reason is not None
    ]
    return pd.DataFrame(rows, columns=SKIP_LOG_COLUMNS)
