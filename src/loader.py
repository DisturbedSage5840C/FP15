"""Workbook loader: reads every sheet as-is and records why any sheet was skipped.

Sheets are read with header=None and dtype=object so the raw layout is preserved and no
value is coerced or guessed. Nothing here writes to disk, and zip members are read in
memory, so data/raw is never touched.

Archives are checked before anything is decompressed: unsafe member names reject the whole
archive, as do too many members or too large a total; a single oversized or
extreme-ratio member is skipped and logged. The same checks run on each .xlsx (itself a
zip). XML is parsed through defusedxml (openpyxl uses it when installed), so entity bombs
are refused and logged as unreadable.
"""
from __future__ import annotations

import io
import logging
import re
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO

import pandas as pd

logger = logging.getLogger(__name__)

WORKBOOK_LEVEL_SHEET = "*"
SKIP_LOG_COLUMNS = ["workbook", "sheet", "reason"]
EXCEL_SUFFIX = ".xlsx"

# Archive safety limits. Measured on the project data: largest member 42.5 MB, highest
# compression ratio 11, at most 101 parts per workbook. These leave wide headroom.
MAX_MEMBER_BYTES = 256 * 1024 * 1024
MAX_TOTAL_BYTES = 1024 * 1024 * 1024
MAX_MEMBERS = 1000
MAX_COMPRESSION_RATIO = 100
RATIO_CHECK_FLOOR_BYTES = 1024 * 1024  # tiny parts can compress well without being a bomb

_WINDOWS_DRIVE = re.compile(r"^[A-Za-z]:")


class ArchiveLimitError(Exception):
    """The archive as a whole exceeds a safety limit (member count or total size)."""


class UnsafeArchiveError(Exception):
    """A member name could escape the archive (absolute path, drive letter or '..')."""


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


def _is_unsafe_name(name: str) -> bool:
    normalised = name.replace("\\", "/")
    return (
        normalised.startswith("/")
        or ".." in normalised.split("/")
        or bool(_WINDOWS_DRIVE.match(normalised))
    )


def check_archive_limits(infos: list[zipfile.ZipInfo]) -> None:
    """Reject the whole archive on unsafe names, too many members or too large a total."""
    for info in infos:
        if _is_unsafe_name(info.filename):
            raise UnsafeArchiveError(f"unsafe member name: {info.filename!r}")
    if len(infos) > MAX_MEMBERS:
        raise ArchiveLimitError(f"too many members: {len(infos)} > {MAX_MEMBERS}")
    total = sum(info.file_size for info in infos)
    if total > MAX_TOTAL_BYTES:
        raise ArchiveLimitError(f"total uncompressed size {total} exceeds cap {MAX_TOTAL_BYTES} bytes")


def _member_limit_reason(info: zipfile.ZipInfo) -> str | None:
    """Why one member must not be decompressed, or None if it is within limits."""
    if info.file_size > MAX_MEMBER_BYTES:
        return f"member exceeds size cap ({info.file_size} > {MAX_MEMBER_BYTES} bytes)"
    if info.file_size >= RATIO_CHECK_FLOOR_BYTES:
        ratio = info.file_size / max(info.compress_size, 1)
        if ratio > MAX_COMPRESSION_RATIO:
            return f"compression ratio {ratio:.0f} exceeds cap {MAX_COMPRESSION_RATIO}"
    return None


def _workbook_limit_reason(source: Path | BinaryIO) -> str | None:
    """Apply the archive limits to an .xlsx (a zip); not-a-zip is left for ExcelFile to report."""
    try:
        with zipfile.ZipFile(source) as archive:
            infos = archive.infolist()
    except zipfile.BadZipFile:
        return None
    finally:
        if not isinstance(source, Path):
            source.seek(0)
    try:
        check_archive_limits(infos)
    except (ArchiveLimitError, UnsafeArchiveError) as error:
        return str(error)
    return next((r for r in map(_member_limit_reason, infos) if r), None)


def _read_sheet(excel: pd.ExcelFile, workbook: str, sheet: str) -> SheetRecord:
    try:
        frame = pd.read_excel(excel, sheet_name=sheet, header=None, dtype=object)
    except Exception as error:  # noqa: BLE001 - recorded in the skip log, never swallowed
        return _skipped(workbook, sheet, f"unreadable sheet: {type(error).__name__}: {error}")
    if frame.dropna(how="all").empty:
        return _skipped(workbook, sheet, "empty")
    return SheetRecord(workbook=workbook, sheet=sheet, frame=frame, skip_reason=None)


def load_workbook_sheets(source: Path | BinaryIO, workbook_label: str) -> list[SheetRecord]:
    """Load every sheet of one workbook; unreadable or unsafe workbooks come back as one skipped record."""
    unsafe = _workbook_limit_reason(source)
    if unsafe is not None:
        return [_skipped(workbook_label, WORKBOOK_LEVEL_SHEET, f"unsafe workbook: {unsafe}")]
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
        infos = archive.infolist()
        check_archive_limits(infos)
        workbooks = sorted(
            (i for i in infos if not i.is_dir() and i.filename.lower().endswith(EXCEL_SUFFIX)),
            key=lambda i: i.filename,
        )
        for info in workbooks:
            member = info.filename
            if _is_macos_or_lock_artefact(member):
                records.append(_skipped(member, WORKBOOK_LEVEL_SHEET, "macOS/Office metadata file, not a workbook"))
                continue
            reason = _member_limit_reason(info)
            if reason is not None:
                records.append(_skipped(member, WORKBOOK_LEVEL_SHEET, reason))
                continue
            records.extend(load_workbook_sheets(io.BytesIO(archive.read(info)), member))
    return records


def skip_log(records: list[SheetRecord]) -> pd.DataFrame:
    """One row per skipped sheet: workbook, sheet, reason."""
    rows = [
        {"workbook": r.workbook, "sheet": r.sheet, "reason": r.skip_reason}
        for r in records
        if r.skip_reason is not None
    ]
    return pd.DataFrame(rows, columns=SKIP_LOG_COLUMNS)
