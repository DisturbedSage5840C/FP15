"""Tests for the markdown inventory renderers. All data is synthetic."""
import zipfile
from collections.abc import Sequence
from pathlib import Path

import pandas as pd

from src.inventory_report import (
    list_zip_members,
    render_author_blocks,
    render_company_data,
    render_filled_expected_empty,
    render_layouts,
    render_odd_sheets,
    render_raw_files,
    render_report,
    render_variable_presence,
    render_workbook_summary,
    render_zip_members,
    summarise_company_data,
)
from src.loader import SheetRecord
from src.sheet_profile import LEADER_POSTS_14, SheetProfile, profile_records

STANDARD_HEADER = ["Selected_Order", "Excel_Data_Row_Number", "Excel_File_Row_Number", "Leader_Name",
                   "Company_Name", "Current_Title", "Role_Start_Year", "CEO_Type", "Platform", "Post_Date",
                   "Post_Date_Text", "Post_Text", "Link_to_Post_URL", "LinkedIn_Profile_URL"]


def _record(rows: Sequence[Sequence[object]], workbook: str = "w.xlsx", sheet: str = "S") -> SheetRecord:
    frame = pd.DataFrame([list(r) for r in rows], dtype=object)
    return SheetRecord(workbook=workbook, sheet=sheet, frame=frame, skip_reason=None)


def _standard_rows(authors: Sequence[str], date_text: str | None = "May 2024") -> list[list[object]]:
    rows: list[list[object]] = [list(STANDARD_HEADER)]
    for i, author in enumerate(authors):
        row: list[object] = [i, i, i, author, "Acme", "CEO", None, "Founder", "LinkedIn", None,
                             date_text, "secret post words", None, "u"]
        rows.append(row)
    return rows


def _profiles() -> list[SheetProfile]:
    records = [
        _record(_standard_rows(["Ann", "Ann", "Ben"]), workbook="a.xlsx", sheet="Ann Rao"),
        _record(_standard_rows(["Ann"], date_text=None), workbook="a.xlsx", sheet="Ann Rao 2"),
        _record([["x", "y", "z"], ["1", "2", "3"]], workbook="b.xlsx", sheet="Odd"),
    ]
    return profile_records(records)


def test_raw_files_table_lists_name_size_and_hash() -> None:
    text = render_raw_files({"Company_Data.xlsx": "a" * 64}, {"Company_Data.xlsx": 2048})

    assert "Company_Data.xlsx" in text
    assert "2,048" in text
    assert "a" * 64 in text


def test_zip_members_listing_marks_kind_and_skips_directories(tmp_path: Path) -> None:
    archive = tmp_path / "posts.zip"
    with zipfile.ZipFile(archive, "w") as z:
        z.writestr("batch/", b"")
        z.writestr("batch/leaders.xlsx", b"123")
        z.writestr("notes.pdf", b"%PDF")
        z.writestr("wordcount_2.py", b"x = 1")
        z.writestr("README", b"hi")

    members = list_zip_members(archive)
    text = render_zip_members(members)

    assert [m.name for m in members] == ["batch/leaders.xlsx", "notes.pdf", "wordcount_2.py", "README"]
    assert [m.kind for m in members] == ["workbook", "pdf", "script", "other"]
    assert "batch/leaders.xlsx" in text
    assert "4 members" in text


def test_workbook_summary_counts_sheets_and_data_rows_per_workbook() -> None:
    text = render_workbook_summary(_profiles())

    assert "| a.xlsx | 2 | 4 |" in text
    assert "| b.xlsx | 1 | 2 |" in text  # header-less sheet: both rows are data


def test_layout_table_groups_sheets_by_layout() -> None:
    text = render_layouts(_profiles())

    assert "| leader_posts_14 | 2 | 4 |" in text
    assert "no-header" in text or "off-layout" in text


def test_odd_sheets_table_lists_position_and_reason_but_never_the_sheet_name() -> None:
    text = render_odd_sheets(_profiles())

    assert "b.xlsx" in text
    assert "no header row" in text
    assert "Ann Rao" not in text
    assert "Odd" not in text
    assert "a.xlsx" not in text


def test_odd_sheets_says_so_when_there_are_none() -> None:
    profiles = profile_records([_record(_standard_rows(["Ann"]))])

    assert "No odd sheets" in render_odd_sheets(profiles)


def test_variable_presence_reports_empty_columns_as_zero_of_rows_per_layout() -> None:
    text = render_variable_presence(_profiles())

    assert "### leader_posts_14" in text
    assert "| role_start_year | Role_Start_Year | 2 | 0 / 4 |" in text
    assert "| post_date | Post_Date | 2 | 0 / 4 |" in text
    assert "| leader_name | Leader_Name | 2 | 4 / 4 |" in text
    assert "| post_date_text | Post_Date_Text | 2 | 3 / 4 |" in text


def test_two_spellings_of_one_variable_stay_in_separate_rows() -> None:
    header = ["leader_name", "post_date", "post_date_text", "Post date"]
    rows = [header, ["Ann", None, "May", "2024-05-01"], ["Ann", None, "June", "2024-06-01"]]

    text = render_variable_presence(profile_records([_record(rows)]))

    assert "| post_date | post_date | 1 | 0 / 2 |" in text
    assert "| post_date | Post date | 1 | 2 / 2 |" in text


def test_variable_presence_never_prints_post_text() -> None:
    assert "secret post words" not in render_variable_presence(_profiles())


def test_filled_expected_empty_columns_are_listed_per_workbook() -> None:
    rows = _standard_rows(["Ann", "Ann"])
    rows[1][9] = "2024-05-01"  # Post_Date filled in one row

    text = render_filled_expected_empty(profile_records([_record(rows, workbook="f.xlsx")]))

    assert "| f.xlsx | Post_Date | 1 / 2 |" in text
    assert "Role_Start_Year" not in text


def test_filled_expected_empty_says_so_when_nothing_is_filled() -> None:
    text = render_filled_expected_empty(profile_records([_record(_standard_rows(["Ann"]))]))

    assert "empty in every workbook" in text


def test_author_blocks_histogram_and_leader_sheet_counts_use_no_names() -> None:
    text = render_author_blocks(_profiles())

    assert "Ann" not in text
    assert "Ben" not in text
    assert "| 1 | 1 |" in text
    assert "| 2 | 1 |" in text
    assert "appear in more than one sheet" in text


def test_company_data_summary_lists_contact_columns_by_name_only() -> None:
    header = ["Name", "Email", "CompanyPhoneNumbers", "Q", "Revenue"]
    record = _record([header, ["A", "a@b.com", "12345", "x", "1"], ["B", "c@d.com", "6789", "y", "2"]],
                     workbook="Company_Data.xlsx", sheet="Sheet1")

    summary = summarise_company_data(record)
    text = render_company_data(summary)

    assert (summary.n_rows, summary.n_columns) == (2, 5)
    assert summary.contact_columns == ("Email", "CompanyPhoneNumbers")
    assert summary.single_letter_headers == ("Q",)
    assert "Email" in text
    assert "a@b.com" not in text
    assert "12345" not in text


def test_full_report_has_every_section_and_a_title() -> None:
    summary = summarise_company_data(_record([["Name", "Email"], ["A", "a@b.com"]], workbook="Company_Data.xlsx"))

    text = render_report(
        manifest={"Company_Data.xlsx": "b" * 64},
        sizes={"Company_Data.xlsx": 10},
        members=(),
        profiles=_profiles(),
        company=summary,
    )

    assert text.startswith("# Data inventory")
    for heading in ("## Raw files", "## Zip members", "## Workbooks", "## Header layouts",
                    "## Odd sheets", "## Study variables", "## Author blocks", "## Company_Data"):
        assert heading in text


def test_leader_posts_14_constant_matches_the_standard_header() -> None:
    assert len(LEADER_POSTS_14) == len(STANDARD_HEADER)
