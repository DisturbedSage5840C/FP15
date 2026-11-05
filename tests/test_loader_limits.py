"""Tests for the archive safety limits: decompression bombs, path traversal, XML entity bombs."""
import io
import zipfile
from pathlib import Path

import pandas as pd
import pytest

import src.loader as loader
from src.loader import (
    ArchiveLimitError,
    UnsafeArchiveError,
    load_workbook_sheets,
    load_zip_workbooks,
    skip_log,
)

ZEROS_5_MIB = b"\x00" * (5 * 1024 * 1024)


@pytest.fixture
def workbook(tmp_path: Path) -> Path:
    path = tmp_path / "leaders.xlsx"
    with pd.ExcelWriter(path) as writer:
        pd.DataFrame([["name", "post"], ["Asha", "hello"]]).to_excel(
            writer, sheet_name="Asha Rao", index=False, header=False
        )
    return path


def _zip_with(tmp_path: Path, members: dict[str, bytes], compression: int = zipfile.ZIP_STORED) -> Path:
    archive = tmp_path / "posts.zip"
    with zipfile.ZipFile(archive, "w", compression=compression) as z:
        for name, data in members.items():
            z.writestr(name, data)
    return archive


def test_member_over_the_size_cap_is_skipped_and_logged(
    workbook: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    archive = _zip_with(tmp_path, {"batch/leaders.xlsx": workbook.read_bytes()})
    monkeypatch.setattr(loader, "MAX_MEMBER_BYTES", 1000)

    records = load_zip_workbooks(archive)

    assert len(records) == 1
    assert records[0].frame is None
    assert records[0].sheet == "*"
    assert "size cap" in (records[0].skip_reason or "")


def test_member_with_an_extreme_compression_ratio_is_skipped_and_logged(tmp_path: Path) -> None:
    archive = _zip_with(tmp_path, {"batch/bomb.xlsx": ZEROS_5_MIB}, compression=zipfile.ZIP_DEFLATED)

    log = skip_log(load_zip_workbooks(archive))

    assert list(log["workbook"]) == ["batch/bomb.xlsx"]
    assert "compression ratio" in log.iloc[0]["reason"]


def test_total_uncompressed_size_over_the_cap_rejects_the_archive(
    workbook: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    archive = _zip_with(tmp_path, {"a.xlsx": workbook.read_bytes(), "b.pdf": b"%PDF" * 100})
    monkeypatch.setattr(loader, "MAX_TOTAL_BYTES", 100)

    with pytest.raises(ArchiveLimitError, match="total"):
        load_zip_workbooks(archive)


def test_too_many_members_rejects_the_archive(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    archive = _zip_with(tmp_path, {"a.txt": b"1", "b.txt": b"2"})
    monkeypatch.setattr(loader, "MAX_MEMBERS", 1)

    with pytest.raises(ArchiveLimitError, match="members"):
        load_zip_workbooks(archive)


@pytest.mark.parametrize(
    "bad_name",
    ["../evil.xlsx", "batch/../../evil.xlsx", "/etc/evil.xlsx", "\\windows\\evil.xlsx", "C:/evil.xlsx"],
)
def test_path_traversal_member_names_reject_the_archive(tmp_path: Path, workbook: Path, bad_name: str) -> None:
    archive = _zip_with(tmp_path, {"ok.xlsx": workbook.read_bytes(), bad_name: b"x"})

    with pytest.raises(UnsafeArchiveError, match="unsafe member name"):
        load_zip_workbooks(archive)


def test_a_workbook_that_is_itself_a_decompression_bomb_is_skipped(workbook: Path, tmp_path: Path) -> None:
    bomb = tmp_path / "nested_bomb.xlsx"
    with zipfile.ZipFile(workbook) as src, zipfile.ZipFile(bomb, "w", zipfile.ZIP_DEFLATED) as dst:
        for info in src.infolist():
            dst.writestr(info.filename, src.read(info))
        dst.writestr("xl/junk.bin", ZEROS_5_MIB)

    records = load_workbook_sheets(bomb, "nested_bomb.xlsx")

    assert len(records) == 1
    assert records[0].sheet == "*"
    assert "compression ratio" in (records[0].skip_reason or "")


def test_a_workbook_with_a_path_traversal_part_is_skipped(workbook: Path, tmp_path: Path) -> None:
    hostile = tmp_path / "traversal.xlsx"
    with zipfile.ZipFile(workbook) as src, zipfile.ZipFile(hostile, "w") as dst:
        for info in src.infolist():
            dst.writestr(info.filename, src.read(info))
        dst.writestr("../escape.xml", b"x")

    records = load_workbook_sheets(hostile, "traversal.xlsx")

    assert [r.sheet for r in records] == ["*"]
    assert "unsafe member name" in (records[0].skip_reason or "")


def test_a_file_that_is_not_a_workbook_is_logged_as_unreadable(tmp_path: Path) -> None:
    not_a_workbook = tmp_path / "notes.xlsx"
    not_a_workbook.write_bytes(b"plain text, not a zip")

    records = load_workbook_sheets(not_a_workbook, "notes.xlsx")

    assert [r.sheet for r in records] == ["*"]
    assert "unreadable workbook" in (records[0].skip_reason or "")


def test_a_normal_workbook_passes_the_limits_and_the_stream_is_still_readable() -> None:
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer) as writer:
        pd.DataFrame([["a", "b"]]).to_excel(writer, sheet_name="S", index=False, header=False)

    records = load_workbook_sheets(io.BytesIO(buffer.getvalue()), "mem.xlsx")

    assert [r.skip_reason for r in records] == [None]


def test_defusedxml_is_active_in_openpyxl() -> None:
    from openpyxl.xml import DEFUSEDXML

    assert DEFUSEDXML is True


def test_xml_entity_bomb_inside_a_workbook_is_logged_not_expanded(workbook: Path, tmp_path: Path) -> None:
    # pandas writes inline strings (no sharedStrings part), so poison xl/workbook.xml,
    # which openpyxl always parses: declare nested entities right after the XML declaration.
    doctype = b'<!DOCTYPE workbook [<!ENTITY a "aaaaaaaaaa"><!ENTITY b "&a;&a;&a;&a;">]>'
    hostile = tmp_path / "entity_bomb.xlsx"
    with zipfile.ZipFile(workbook) as src, zipfile.ZipFile(hostile, "w", zipfile.ZIP_DEFLATED) as dst:
        for info in src.infolist():
            data = src.read(info)
            if info.filename == "xl/workbook.xml":
                declaration_end = data.find(b"?>") + 2 if data.startswith(b"<?xml") else 0
                data = data[:declaration_end] + doctype + data[declaration_end:]
            dst.writestr(info.filename, data)

    records = load_workbook_sheets(hostile, "entity_bomb.xlsx")

    assert all(r.frame is None for r in records)
    assert all("unreadable" in (r.skip_reason or "") for r in records)
