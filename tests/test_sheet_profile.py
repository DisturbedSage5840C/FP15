"""Tests for the sheet profiler behind reports/data_inventory.md (src.sheet_profile).

All frames are synthetic. No real names or post text appear here.
"""
from collections.abc import Sequence

import pandas as pd
import pytest

from src.sheet_profile import (
    LEADER_POSTS_14,
    STUDY_VARIABLES,
    normalise_header,
    profile_records,
    profile_sheet,
)
from src.loader import SheetRecord


def _record(rows: Sequence[Sequence[object]], workbook: str = "w.xlsx", sheet: str = "S") -> SheetRecord:
    frame = pd.DataFrame([list(r) for r in rows], dtype=object)
    return SheetRecord(workbook=workbook, sheet=sheet, frame=frame, skip_reason=None)


def _leader_sheet(data_rows: list[dict[str, object]]) -> SheetRecord:
    header = list(LEADER_POSTS_14)
    rows: list[list[object]] = [header]
    for values in data_rows:
        rows.append([values.get(column) for column in header])
    return _record(rows)


def test_normalise_header_lowercases_and_joins_words() -> None:
    assert normalise_header("  Post date text ") == "post_date_text"
    assert normalise_header("Post-Date") == "post_date"


def test_standard_leader_sheet_is_recognised_and_not_odd() -> None:
    profile = profile_sheet(_leader_sheet([{"leader_name": "A", "post_text": "t"}]), position=0)

    assert profile.layout == "leader_posts_14"
    assert profile.header_kind == "header"
    assert profile.n_data_rows == 1
    assert profile.odd_reasons == ()


def test_study_variables_are_counted_by_non_empty_values() -> None:
    sheet = _leader_sheet(
        [
            {"leader_name": "A", "role_start_year": None, "post_date": None, "post_date_text": "2 weeks ago"},
            {"leader_name": "A", "role_start_year": None, "post_date": None, "post_date_text": "   "},
            {"leader_name": "A", "role_start_year": None, "post_date": None, "post_date_text": "1 month ago"},
        ]
    )

    counts = profile_sheet(sheet, position=0).variable_counts

    assert counts["leader_name"] == 3
    assert counts["role_start_year"] == 0
    assert counts["post_date"] == 0
    assert counts["post_date_text"] == 2  # whitespace-only is blank


def test_only_study_variables_are_counted() -> None:
    counts = profile_sheet(_leader_sheet([{"leader_name": "A", "post_text": "x"}]), position=0).variable_counts

    assert set(counts) <= set(STUDY_VARIABLES) | {"Post date", "Post date text"}
    assert "post_text" not in counts


def test_variant_spelling_is_reported_under_its_raw_header() -> None:
    record = _record(
        [
            ["Platform", "Post date", "Post date text", "Cleaned post text"],
            ["LinkedIn", "2024-01-01", None, "x"],
            ["LinkedIn", None, None, "y"],
        ]
    )

    profile = profile_sheet(record, position=0)

    assert profile.variable_counts == {"Platform": 2, "Post date": 1, "Post date text": 0}
    assert profile.layout == "off-layout"
    assert any("off-layout" in reason for reason in profile.odd_reasons)


def test_off_layout_reason_names_missing_and_extra_columns_of_nearest_layout() -> None:
    header = [c for c in LEADER_POSTS_14 if c != "post_date_text"]
    record = _record([header, [None] * len(header)])

    profile = profile_sheet(record, position=3)

    assert profile.layout == "off-layout"
    reason = next(r for r in profile.odd_reasons if "off-layout" in r)
    assert "leader_posts_14" in reason
    assert "missing: post_date_text" in reason
    assert profile.position == 3


def test_unnamed_filler_columns_are_counted_not_listed_in_the_off_layout_reason() -> None:
    header = list(LEADER_POSTS_14) + [f"Unnamed: {i}" for i in range(14, 2014)]
    record = _record([header, [None] * len(header)])

    profile = profile_sheet(record, position=0)

    reason = next(r for r in profile.odd_reasons if "off-layout" in r)
    assert "2000 unnamed column(s)" in reason
    assert "unnamed:_" not in reason
    assert len(reason) < 400


def test_first_row_that_is_data_is_flagged_and_counted_as_a_data_row() -> None:
    record = _record([["1", "9", "9", "Some Person", "Some Co", "CEO", None], ["2", "10", "10", "Other", "Co", "CEO", None]])

    profile = profile_sheet(record, position=0)

    assert profile.header_kind == "data"
    assert profile.n_data_rows == 2
    assert profile.variable_counts == {}
    assert "no header row (first row is data)" in profile.odd_reasons


def test_blank_first_row_is_skipped_to_find_the_header() -> None:
    header = list(LEADER_POSTS_14)
    record = _record([[None] * len(header), header, [None] * len(header)])

    profile = profile_sheet(record, position=0)

    assert profile.layout == "leader_posts_14"
    assert profile.header_row_index == 1
    assert profile.n_data_rows == 1
    assert "1 blank row(s) above the header" in profile.odd_reasons


def test_header_far_below_many_blank_rows_is_still_found() -> None:
    header = list(LEADER_POSTS_14)
    record = _record([[None] * len(header)] * 46 + [header])

    profile = profile_sheet(record, position=0)

    assert profile.header_kind == "header"
    assert profile.layout == "leader_posts_14"
    assert profile.header_row_index == 46
    assert profile.n_data_rows == 0


def test_trailing_blank_header_cells_are_trimmed_and_blank_width_is_noted() -> None:
    header = list(LEADER_POSTS_14) + [None, None]
    record = _record([header, [None] * len(header)])

    profile = profile_sheet(record, position=0)

    assert profile.layout == "leader_posts_14"
    assert profile.width == 16
    assert "2 blank column(s) beyond the header" in profile.odd_reasons


def test_non_empty_cells_beyond_the_header_are_counted_without_exposing_them() -> None:
    header = ["CompanyName", "Person_Name", "Current_Title", "LinkedIn_Profile_Link", "person_id"]
    record = _record([header + [None], ["c", "p", "t", "l", "1", "a collector note"]])

    profile = profile_sheet(record, position=0)

    assert profile.layout == "roster_5"
    assert profile.extra_nonempty_cells == 1
    assert "1 non-empty cell(s) beyond the header" in profile.odd_reasons
    assert "a collector note" not in repr(profile)


def test_author_blocks_count_runs_of_the_leader_column_and_hash_the_keys() -> None:
    sheet = _leader_sheet(
        [{"leader_name": n} for n in ["Ann Lee", "Ann Lee", "Bo Chen", "Ann Lee"]]
    )

    profile = profile_sheet(sheet, position=0)

    assert profile.author_blocks == 3
    assert profile.author_distinct == 2
    assert len(profile.author_hashes) == 2
    assert "Ann" not in repr(profile)


def test_author_blocks_are_none_without_an_author_column() -> None:
    record = _record([["Platform", "Post date"], ["LinkedIn", None]])

    profile = profile_sheet(record, position=0)

    assert profile.author_blocks is None
    assert profile.author_distinct is None


def test_skipped_records_are_profiled_with_their_reason() -> None:
    skipped = SheetRecord(workbook="w.xlsx", sheet="*", frame=None, skip_reason="unreadable workbook: X")

    profile = profile_sheet(skipped, position=0)

    assert profile.header_kind == "skipped"
    assert profile.skip_reason == "unreadable workbook: X"
    assert profile.n_data_rows == 0


def test_profile_records_numbers_sheets_per_workbook() -> None:
    records = [
        _record([list(LEADER_POSTS_14)], workbook="a.xlsx", sheet="x"),
        _record([list(LEADER_POSTS_14)], workbook="a.xlsx", sheet="y"),
        _record([list(LEADER_POSTS_14)], workbook="b.xlsx", sheet="z"),
    ]

    profiles = profile_records(records)

    assert [(p.workbook, p.position) for p in profiles] == [("a.xlsx", 0), ("a.xlsx", 1), ("b.xlsx", 0)]


def test_profiles_never_carry_the_sheet_name() -> None:
    record = _record([list(LEADER_POSTS_14)], sheet="Ann Lee")

    assert "Ann Lee" not in repr(profile_sheet(record, position=0))


@pytest.mark.parametrize("variable", STUDY_VARIABLES)
def test_study_variables_match_the_project_list(variable: str) -> None:
    assert variable == normalise_header(variable)
