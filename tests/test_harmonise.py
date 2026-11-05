"""Tests for the harmonise stage (src.harmonise). Synthetic names and text only."""
import io
import logging
import zipfile
from collections.abc import Mapping, Sequence
from pathlib import Path

import pandas as pd
import pytest

from src.harmonise import (
    SCHEMA_COLUMNS,
    batch_of,
    drop_duplicates,
    extract_rows,
    fill_leader,
    harmonise_records,
    load_roster,
    run,
    write_interim,
)
from src.harmonise_plan import plan_sheet
from src.loader import SheetRecord
from src.sheet_profile import LEADER_POSTS_14, profile_sheet
from src.verify_raw import MANIFEST_NAME

WORDCOUNT_HEADER = [
    "leader_name", "company_name", "current_title", "role_start_year", "ceo_type", "platform",
    "post_date", "post_date_text", "link_to_post_url", "linkedin_profile_url",
    "cleaned_post_text", "Post date",
]
ROSTER_HEADER = ["CompanyName", "Person_Name", "Current_Title", "LinkedIn_Profile_Link", "person_id"]
ROSTER_PATH = "Linkdln_posts_data/seventh_100_leaders/All_500.xlsx"


def _post_row(leader: str | None, text: str | None, link: str | None = None, company: str | None = "Acme") -> list[object]:
    return [1, 1, 2, leader, company, "CEO", None, "Founder", "LinkedIn", None, "May", text, link, "http://p"]


def _record(rows: Sequence[Sequence[object]], workbook: str = "Data/Batch_1/w.xlsx", sheet: str = "S") -> SheetRecord:
    frame = pd.DataFrame([list(r) for r in rows], dtype=object)
    return SheetRecord(workbook=workbook, sheet=sheet, frame=frame, skip_reason=None)


def _rows(rows: Sequence[Sequence[object]], sheet_idx: int = 0) -> pd.DataFrame:
    record = _record(rows)
    plan = plan_sheet(record, profile_sheet(record, position=sheet_idx))
    return extract_rows(record, plan, sheet_idx)


def _frame(leaders: Sequence[str | None], texts: Sequence[str]) -> pd.DataFrame:
    return _rows([list(LEADER_POSTS_14)] + [_post_row(a, t) for a, t in zip(leaders, texts)])


# ---------------------------------------------------------------- extract_rows


def test_batch_is_the_folder_of_the_workbook() -> None:
    assert batch_of("Linkdln_posts_data/First_100_leaders/First_file1_updated.xlsx") == "First_100_leaders"
    assert batch_of("loose.xlsx") == ""


def test_extract_rows_maps_columns_and_skips_blank_post_text() -> None:
    rows = _rows([
        list(LEADER_POSTS_14),
        _post_row("  Ann Rao ", "hello world", "http://x"),
        _post_row("Ann Rao", None),
        _post_row("Ann Rao", "   "),
    ])

    assert list(rows[list(SCHEMA_COLUMNS)].columns) == list(SCHEMA_COLUMNS)
    assert len(rows) == 1
    row = rows.iloc[0]
    assert row["leader"] == "Ann Rao" and row["post_text"] == "hello world" and row["link"] == "http://x"
    assert row["batch"] == "Batch_1" and row["sheet"] == "S" and row["sheet_idx"] == 0
    assert row["source_row"] == 2 and row["text_kind"] == "raw" and row["leader_source"] is None


def test_extract_rows_keeps_missing_as_none_and_integral_numbers_without_decimals() -> None:
    row = _rows([list(LEADER_POSTS_14), [1, 1, 2, "Ann", None, "CEO", 2015.0, "Founder", "LinkedIn", None, None, "t", None, None]]).iloc[0]

    assert row["company"] is None and row["link"] is None
    assert row["role_start_year"] == "2015"


def test_extract_rows_reads_a_sheet_without_header_from_row_zero() -> None:
    data = _post_row("Ann", "first row is data")
    rows = _rows([data, _post_row("Ann", "second")])

    assert list(rows["post_text"]) == ["first row is data", "second"]
    assert list(rows["source_row"]) == [1, 2]


def test_extract_rows_separates_age_text_from_post_date_and_flags_text_in_post_date() -> None:
    long_text = "word " * 12
    row = [None, None, None, None, None, None, long_text, None, None, None, "cleaned text", "3mo"]
    rows = _rows([WORDCOUNT_HEADER, row])

    only = rows.iloc[0]
    assert only["age_text"] == "3mo" and only["text_kind"] == "cleaned"
    assert only["post_date"] == long_text.strip() and bool(only["post_date_is_text"]) is True


def test_extract_rows_of_a_skipped_sheet_is_empty() -> None:
    record = _record([list(ROSTER_HEADER), ["Acme", "Ann", "CEO", "u", "1"]])
    plan = plan_sheet(record, profile_sheet(record, position=0))

    assert extract_rows(record, plan, 0).empty


# ----------------------------------------------------------------- fill_leader


def test_combined_sheet_drops_rows_without_a_leader_and_never_fills() -> None:
    rows = _frame(["Ann Rao", None, "Bob Roy"], ["a", "b", "c"])

    result = fill_leader(rows, "Combined", is_combined=True)

    assert list(result.rows["post_text"]) == ["a", "c"]
    assert result.dropped == 1 and result.filled == 0
    assert set(result.rows["leader_source"]) == {"cell"}


def test_leader_sheet_fills_blank_leaders_from_the_sheet_name() -> None:
    rows = _frame(["Ann Rao", None], ["a", "b"])

    result = fill_leader(rows, "ann  rao", is_combined=False)

    assert list(result.rows["leader"]) == ["Ann Rao", "ann  rao"]
    assert list(result.rows["leader_source"]) == ["cell", "sheet_name"]
    assert result.filled == 1 and result.conflict == 0
    assert result.cell_leader_rows == 1 and result.cell_matches_sheet == 1


def test_leader_sheet_fill_is_flagged_when_the_cell_leader_differs_from_the_sheet_name() -> None:
    rows = _frame(["Bob Roy", None], ["a", "b"])

    result = fill_leader(rows, "Ann Rao", is_combined=False)

    assert list(result.rows["leader_source"]) == ["cell", "sheet_name_conflict"]
    assert result.conflict == 1 and result.cell_matches_sheet == 0


def test_sheet_with_two_distinct_leaders_is_treated_as_multi_leader() -> None:
    rows = _frame(["Ann Rao", "Bob Roy", None], ["a", "b", "c"])

    result = fill_leader(rows, "Everyone", is_combined=False)

    assert list(result.rows["post_text"]) == ["a", "b"]
    assert result.dropped == 1 and result.filled == 0


def test_sheet_with_only_blank_leaders_takes_the_sheet_name_for_every_row() -> None:
    rows = _frame([None, None], ["a", "b"])

    result = fill_leader(rows, "Ann Rao", is_combined=False)

    assert set(result.rows["leader"]) == {"Ann Rao"}
    assert result.conflict == 0 and result.filled == 2


def test_fill_leader_does_not_change_its_input() -> None:
    rows = _frame([None], ["a"])
    before = rows.copy()

    fill_leader(rows, "Ann Rao", is_combined=False)

    pd.testing.assert_frame_equal(rows, before)


# ------------------------------------------------------------- drop_duplicates


def _posts(entries: Sequence[tuple[str, str | None, str]]) -> pd.DataFrame:
    return pd.DataFrame(
        [{"leader": a, "link": link, "post_text": text} for a, link, text in entries], dtype=object
    )


def test_duplicates_are_found_on_leader_and_link_when_a_link_exists() -> None:
    posts = _posts([("Ann Rao", "http://x", "version one"), ("rao ann", "http://x", "different text")])

    kept = drop_duplicates(posts)

    assert list(kept["post_text"]) == ["version one"]
    assert list(kept["n_copies"]) == [2]


def test_duplicates_without_a_link_use_the_first_200_characters() -> None:
    head = "x" * 200
    posts = _posts([("Ann", None, head + "tail one"), ("Ann", None, head + "tail two"), ("Ann", None, "other")])

    kept = drop_duplicates(posts)

    assert len(kept) == 2 and list(kept["n_copies"]) == [2, 1]


def test_same_text_by_different_leaders_is_not_a_duplicate() -> None:
    posts = _posts([("Ann Rao", None, "same"), ("Bob Roy", None, "same")])

    assert len(drop_duplicates(posts)) == 2


def test_dedupe_keeps_the_first_occurrence_and_resets_the_index() -> None:
    posts = _posts([("Ann", "l", "first"), ("Ann", "l", "second"), ("Bob", "m", "third")])

    kept = drop_duplicates(posts)

    assert list(kept["post_text"]) == ["first", "third"]
    assert list(kept.index) == [0, 1]


# ------------------------------------------------------------ harmonise_records


def _workbook_records() -> list[SheetRecord]:
    wb = "Data/Batch_1/a.xlsx"
    header = list(LEADER_POSTS_14)
    return [
        _record([header, _post_row("Ann Rao", "a1", "http://1"), _post_row("Ann Rao", "a2"),
                 _post_row(None, "orphan"), _post_row("Bob Roy", "b1")], wb, "Combined"),
        _record([header, _post_row(None, "a2"), _post_row(None, "a4")], wb, "Ann Rao"),
        _record([ROSTER_HEADER, ["Acme", "Ann", "CEO", "u", "1"]], "Data/Batch_2/b.xlsx", "Roster"),
        _record([header, _post_row("Cy Sen", "c1")], "Data/Batch_2/b.xlsx", "Combined"),
        _record([header], "Data/Batch_2/b.xlsx", "Cy Sen"),
    ]


def test_harmonise_records_counts_rows_through_each_step() -> None:
    result = harmonise_records(_workbook_records())

    assert result.rows_with_text == 7
    assert result.rows_after_leader == 6
    assert len(result.posts) == 5
    assert sorted(result.posts["post_text"]) == ["a1", "a2", "a4", "b1", "c1"]


def test_first_post_sheet_of_each_workbook_is_the_combined_sheet() -> None:
    log = harmonise_records(_workbook_records()).sheet_log

    combined = log[log["is_combined"]]
    assert sorted(zip(combined["workbook"], combined["sheet_idx"])) == [
        ("Data/Batch_1/a.xlsx", 0), ("Data/Batch_2/b.xlsx", 1),
    ]


def test_every_sheet_gets_a_log_row_and_skipped_sheets_carry_a_reason() -> None:
    log = harmonise_records(_workbook_records()).sheet_log

    assert len(log) == 5
    skipped = log[log["status"] == "skipped"]
    assert sorted(skipped["reason"]) == ["header only, no data rows", "roster sheet (the roster is loaded once from seventh_100_leaders/All_500.xlsx)"]
    assert set(log[log["status"] == "used"]["reason"]) == {""}


def test_sheet_name_fills_are_counted_in_the_sheet_log() -> None:
    log = harmonise_records(_workbook_records()).sheet_log

    ann = log[(log["workbook"] == "Data/Batch_1/a.xlsx") & (log["sheet_idx"] == 1)].iloc[0]
    assert ann["filled_from_sheet"] == 2 and ann["rows_with_text"] == 2


def test_duplicate_across_combined_and_leader_sheet_is_dropped_once() -> None:
    posts = harmonise_records(_workbook_records()).posts

    assert (posts["post_text"] == "a2").sum() == 1
    assert posts.loc[posts["post_text"] == "a2", "n_copies"].iloc[0] == 2


def test_unreadable_workbook_is_logged_as_skipped() -> None:
    broken = SheetRecord(workbook="Data/Batch_9/x.xlsx", sheet="*", frame=None, skip_reason="unreadable workbook: X")

    log = harmonise_records([broken]).sheet_log

    assert list(log["status"]) == ["skipped"] and list(log["reason"]) == ["unreadable workbook: X"]


# ----------------------------------------------------------------- load_roster


def test_roster_is_loaded_once_from_the_seventh_folder_only() -> None:
    other = _record([ROSTER_HEADER, ["Other", "Zed", "CEO", "u", "9"]], "Linkdln_posts_data/Third_100_leaders/All_500.xlsx", "R")
    chosen = _record(
        [ROSTER_HEADER, ["Acme", "Ann Rao", "CEO", "http://p", "1"], [None] * 5, ["Beta", "Bob Roy", "CFO", None, "2"]],
        ROSTER_PATH, "R",
    )

    roster = load_roster([other, chosen])

    assert list(roster.columns) == ["company", "person_name", "title", "profile_url", "person_id"]
    assert list(roster["person_id"]) == ["1", "2"]


def test_missing_roster_is_an_error() -> None:
    with pytest.raises(ValueError, match="roster"):
        load_roster([_record([list(LEADER_POSTS_14)])])


# ------------------------------------------------------------- write_interim / run


def test_write_interim_writes_four_csvs_with_the_schema(tmp_path: Path) -> None:
    result = harmonise_records(_workbook_records())
    roster = pd.DataFrame({"company": ["Acme"], "person_name": ["Ann"], "title": ["CEO"], "profile_url": ["u"], "person_id": ["1"]})

    paths = write_interim(result, roster, tmp_path / "interim")

    assert sorted(p.name for p in paths) == [
        "harmonise_sheet_log.csv", "harmonise_skipped.csv", "harmonised_posts.csv", "roster.csv",
    ]
    full_log = pd.read_csv(tmp_path / "interim" / "harmonise_sheet_log.csv", dtype=str)
    assert len(full_log) == len(result.sheet_log)
    posts = pd.read_csv(tmp_path / "interim" / "harmonised_posts.csv", dtype=str)
    assert set(SCHEMA_COLUMNS) <= set(posts.columns)
    skipped = pd.read_csv(tmp_path / "interim" / "harmonise_skipped.csv", dtype=str)
    assert set(skipped["status"]) == {"skipped"}


def _xlsx_bytes(sheets: Mapping[str, Sequence[Sequence[object]]]) -> bytes:
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer) as writer:
        for name, rows in sheets.items():
            pd.DataFrame(rows).to_excel(writer, sheet_name=name, index=False, header=False)
    return buffer.getvalue()


@pytest.fixture
def raw_dir(tmp_path: Path) -> Path:
    raw = tmp_path / "raw"
    raw.mkdir()
    header = list(LEADER_POSTS_14)
    posts = {
        "Combined": [header, _post_row("Ann Rao", "secret words one")],
        "Ann Rao": [header, _post_row(None, "secret words two")],
    }
    with zipfile.ZipFile(raw / "posts.zip", "w") as archive:
        archive.writestr("batch/leaders.xlsx", _xlsx_bytes(posts))
        archive.writestr(ROSTER_PATH, _xlsx_bytes({"R": [ROSTER_HEADER, ["Acme", "Ann Rao", "CEO", "u", "1"]]}))
    return raw


def test_run_writes_interim_files_and_the_report_without_names_or_text(raw_dir: Path, tmp_path: Path) -> None:
    interim, report = tmp_path / "interim", tmp_path / "reports" / "harmonise_summary.md"

    assert run(raw_dir=raw_dir, interim_dir=interim, report_path=report) == 0

    assert (interim / "harmonised_posts.csv").exists() and (interim / "roster.csv").exists()
    text = report.read_text()
    assert text.startswith("# Harmonise summary")
    assert "Ann Rao" not in text and "secret words" not in text


def test_run_leaves_the_raw_folder_unchanged(raw_dir: Path, tmp_path: Path) -> None:
    before = {p.name: p.read_bytes() for p in raw_dir.iterdir()}

    run(raw_dir=raw_dir, interim_dir=tmp_path / "i", report_path=tmp_path / "r.md")

    after = {p.name: p.read_bytes() for p in raw_dir.iterdir() if p.name != MANIFEST_NAME}
    assert after == before


def test_run_refuses_when_the_manifest_no_longer_matches(
    raw_dir: Path, tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    run(raw_dir=raw_dir, interim_dir=tmp_path / "i", report_path=tmp_path / "r.md")
    (raw_dir / "posts.zip").write_bytes(b"changed")

    with caplog.at_level(logging.ERROR):
        code = run(raw_dir=raw_dir, interim_dir=tmp_path / "i2", report_path=tmp_path / "r2.md")

    assert code == 1 and not (tmp_path / "i2").exists()
    assert "FAILED" in caplog.text
