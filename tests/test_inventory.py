"""End-to-end test of the inventory stage on a synthetic raw folder."""
import io
import logging
import zipfile
from pathlib import Path

import pandas as pd
import pytest

from src.inventory import build_report, main
from src.verify_raw import MANIFEST_NAME

HEADER = ["Selected_Order", "Excel_Data_Row_Number", "Excel_File_Row_Number", "Leader_Name",
          "Company_Name", "Current_Title", "Role_Start_Year", "CEO_Type", "Platform", "Post_Date",
          "Post_Date_Text", "Post_Text", "Link_to_Post_URL", "LinkedIn_Profile_URL"]


def _xlsx_bytes(sheets: dict[str, list[list[object]]]) -> bytes:
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer) as writer:
        for name, rows in sheets.items():
            pd.DataFrame(rows).to_excel(writer, sheet_name=name, index=False, header=False)
    return buffer.getvalue()


@pytest.fixture
def raw_dir(tmp_path: Path) -> Path:
    raw = tmp_path / "raw"
    raw.mkdir()
    (raw / "Company_Data.xlsx").write_bytes(
        _xlsx_bytes({"Sheet1": [["Name", "Email", "Q"], ["Acme", "a@b.com", "x"]]})
    )
    posts = [HEADER, [0, 0, 0, "Ann Rao", "Acme", "CEO", None, "Founder", "LinkedIn", None,
                      "May 2024", "secret post words", None, "u"]]
    with zipfile.ZipFile(raw / "posts.zip", "w") as archive:
        archive.writestr("batch/leaders.xlsx", _xlsx_bytes({"Ann Rao": posts}))
        archive.writestr("batch/notes.pdf", b"%PDF")
    return raw


def test_report_covers_files_members_layouts_and_company_data(raw_dir: Path) -> None:
    from src.verify_raw import run

    run(raw_dir)

    text = build_report(raw_dir)

    assert "Company_Data.xlsx" in text
    assert "posts.zip" in text
    assert "batch/leaders.xlsx" in text
    assert "leader_posts_14" in text
    assert "| Email" not in text.split("## Company_Data")[0]
    assert "Email" in text.split("## Company_Data")[1]


def test_report_never_contains_names_post_text_or_contact_values(raw_dir: Path) -> None:
    from src.verify_raw import run

    run(raw_dir)

    text = build_report(raw_dir)

    for secret in ("Ann Rao", "secret post words", "a@b.com"):
        assert secret not in text


def test_main_writes_manifest_then_report_and_leaves_raw_files_untouched(raw_dir: Path, tmp_path: Path) -> None:
    report = tmp_path / "reports" / "data_inventory.md"
    before = {p.name: p.read_bytes() for p in raw_dir.iterdir()}

    assert main(raw_dir=raw_dir, report_path=report) == 0

    assert report.read_text().startswith("# Data inventory")
    assert (raw_dir / MANIFEST_NAME).exists()
    after = {p.name: p.read_bytes() for p in raw_dir.iterdir() if p.name != MANIFEST_NAME}
    assert after == before


def test_main_refuses_to_run_when_the_manifest_no_longer_matches(
    raw_dir: Path, tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    report = tmp_path / "data_inventory.md"
    assert main(raw_dir=raw_dir, report_path=report) == 0
    report.unlink()
    (raw_dir / "Company_Data.xlsx").write_bytes(b"tampered")

    with caplog.at_level(logging.ERROR):
        assert main(raw_dir=raw_dir, report_path=report) == 1

    assert not report.exists()
    assert "FAILED" in caplog.text


def test_main_fails_cleanly_when_company_data_is_missing(raw_dir: Path, tmp_path: Path) -> None:
    (raw_dir / "Company_Data.xlsx").unlink()
    report = tmp_path / "data_inventory.md"

    assert main(raw_dir=raw_dir, report_path=report) == 1
    assert not report.exists()
