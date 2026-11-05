"""Tests for the workbook loader: every skipped sheet must be logged with a reason."""
import zipfile
from pathlib import Path

import pandas as pd
import pytest

from src.loader import SheetRecord, load_workbook_sheets, load_zip_workbooks, skip_log


def _write_workbook(path: Path, sheets: dict[str, pd.DataFrame]) -> None:
    with pd.ExcelWriter(path) as writer:
        for name, frame in sheets.items():
            frame.to_excel(writer, sheet_name=name, index=False, header=False)


@pytest.fixture
def workbook(tmp_path: Path) -> Path:
    path = tmp_path / "leaders.xlsx"
    _write_workbook(
        path,
        {
            "Asha Rao": pd.DataFrame([["name", "post"], ["Asha", "hello"]]),
            "Empty One": pd.DataFrame([[None, None]]),
            "Ravi Iyer": pd.DataFrame([["name", "post"], ["Ravi", "hi"], ["Ravi", "yo"]]),
        },
    )
    return path


def test_loads_every_sheet_and_flags_the_empty_one(workbook: Path) -> None:
    records = load_workbook_sheets(workbook, workbook_label="leaders.xlsx")

    by_sheet = {r.sheet: r for r in records}
    assert set(by_sheet) == {"Asha Rao", "Empty One", "Ravi Iyer"}
    assert by_sheet["Empty One"].skip_reason == "empty"
    assert by_sheet["Empty One"].frame is None
    assert by_sheet["Ravi Iyer"].skip_reason is None
    assert by_sheet["Ravi Iyer"].n_rows == 3


def test_loaded_frames_keep_the_raw_layout_without_header_inference(workbook: Path) -> None:
    record = next(r for r in load_workbook_sheets(workbook, "leaders.xlsx") if r.sheet == "Asha Rao")

    assert record.frame is not None
    assert record.frame.iloc[0].tolist() == ["name", "post"]


def test_skip_log_lists_only_skipped_sheets_with_reasons(workbook: Path) -> None:
    records = load_workbook_sheets(workbook, "leaders.xlsx")

    log = skip_log(records)

    assert list(log.columns) == ["workbook", "sheet", "reason"]
    assert log.to_dict("records") == [
        {"workbook": "leaders.xlsx", "sheet": "Empty One", "reason": "empty"}
    ]


def test_unreadable_workbook_is_logged_not_swallowed(tmp_path: Path) -> None:
    broken = tmp_path / "broken.xlsx"
    broken.write_bytes(b"this is not an excel file")

    records = load_workbook_sheets(broken, "broken.xlsx")

    assert len(records) == 1
    assert records[0].sheet == "*"
    assert records[0].skip_reason is not None
    assert records[0].skip_reason.startswith("unreadable workbook")


def test_zip_loader_reads_members_without_extracting(workbook: Path, tmp_path: Path) -> None:
    archive = tmp_path / "posts.zip"
    with zipfile.ZipFile(archive, "w") as z:
        z.write(workbook, "batch/leaders.xlsx")
        z.writestr("batch/notes.pdf", b"%PDF")
    before = sorted(p.name for p in tmp_path.iterdir())

    records = load_zip_workbooks(archive)

    assert {r.workbook for r in records} == {"batch/leaders.xlsx"}
    assert sorted(p.name for p in tmp_path.iterdir()) == before  # nothing extracted


def test_zip_loader_logs_macos_metadata_members_instead_of_dropping_them(
    workbook: Path, tmp_path: Path
) -> None:
    archive = tmp_path / "posts.zip"
    with zipfile.ZipFile(archive, "w") as z:
        z.write(workbook, "batch/leaders.xlsx")
        z.writestr("__MACOSX/batch/._leaders.xlsx", b"junk")
        z.writestr("batch/~$leaders.xlsx", b"lock")

    log = skip_log(load_zip_workbooks(archive))

    workbook_level = log[log["sheet"] == "*"]
    assert set(workbook_level["workbook"]) == {"__MACOSX/batch/._leaders.xlsx", "batch/~$leaders.xlsx"}


def test_n_rows_is_zero_for_a_skipped_sheet() -> None:
    assert SheetRecord("w", "s", None, "empty").n_rows == 0


def test_sheet_record_is_immutable() -> None:
    record = SheetRecord(workbook="w", sheet="s", frame=None, skip_reason="empty")

    with pytest.raises(AttributeError):
        record.sheet = "other"  # type: ignore[misc]
