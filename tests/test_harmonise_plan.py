"""Tests for sheet planning in harmonise (src.harmonise_plan). Synthetic frames only."""
from collections.abc import Sequence

import pandas as pd
import pytest

from src.harmonise_plan import column_role, plan_sheet
from src.loader import SheetRecord
from src.sheet_profile import LEADER_POSTS_14, profile_sheet


def _record(rows: Sequence[Sequence[object]]) -> SheetRecord:
    frame = pd.DataFrame([list(r) for r in rows], dtype=object)
    return SheetRecord(workbook="Data/Batch_1/w.xlsx", sheet="S", frame=frame, skip_reason=None)


def _plan(rows: Sequence[Sequence[object]]):
    record = _record(rows)
    return plan_sheet(record, profile_sheet(record, position=0))


def _roles(plan) -> dict[str, int]:
    return {role: position for position, role in plan.roles}


def test_standard_leader_sheet_maps_columns_by_header() -> None:
    row = [None] * 14
    plan = _plan([list(LEADER_POSTS_14), row])

    roles = _roles(plan)
    assert plan.skip_reason is None
    assert plan.method == "header"
    assert plan.first_data_row == 1
    assert plan.text_kind == "raw"
    assert roles["leader"] == 3 and roles["post_text"] == 11 and roles["link"] == 12
    assert roles["profile_url"] == 13 and roles["title"] == 5 and roles["post_date_text"] == 10


def test_wordcount_sheet_separates_age_text_from_post_date_by_the_raw_header() -> None:
    header = [
        "leader_name", "company_name", "current_title", "role_start_year", "ceo_type", "platform",
        "post_date", "post_date_text", "link_to_post_url", "linkedin_profile_url",
        "cleaned_post_text", "Post date",
    ]
    plan = _plan([header, [None] * 12])

    roles = _roles(plan)
    assert roles["post_date"] == 6
    assert roles["age_text"] == 11
    assert roles["post_text"] == 10
    assert plan.text_kind == "cleaned"


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Post date", "age_text"),
        ("post_date", "post_date"),
        ("Link to the post (if available)", "link"),
        ("Cleaned post text", "post_text"),
        ("selected_order", None),
    ],
)
def test_column_role_by_raw_header(raw: str, expected: str | None) -> None:
    assert column_role(raw) == expected


def test_blank_header_cell_is_recovered_by_position_when_the_rest_matches() -> None:
    header = list(LEADER_POSTS_14)
    header[11] = None  # the post_text header went missing
    plan = _plan([header, [None] * 14])

    assert plan.method == "header+positional"
    assert _roles(plan)["post_text"] == 11


def test_blank_header_cell_is_not_guessed_when_few_headers_match() -> None:
    header = ["leader_name", "company_name", "current_title", None, "x"]
    plan = _plan([header, [None] * 5])

    assert plan.skip_reason == "no post-text column"


def test_sheet_without_header_is_mapped_by_position_when_it_is_wide_enough() -> None:
    data = ["1", "9", "9", "Some Person", "Co", "CEO", None, "Founder", "LinkedIn", None, None, "text", None, None]
    plan = _plan([data, data])

    assert plan.method == "positional"
    assert plan.first_data_row == 0
    assert _roles(plan)["leader"] == 3 and _roles(plan)["post_text"] == 11


def test_narrow_sheet_without_header_is_skipped() -> None:
    plan = _plan([["a", "b", "c"], ["d", "e", "f"]])

    assert plan.skip_reason == "no header row and fewer than 14 columns"


def test_blank_rows_above_the_header_move_the_first_data_row() -> None:
    header = list(LEADER_POSTS_14)
    plan = _plan([[None] * 14, [None] * 14, header, [None] * 14])

    assert plan.first_data_row == 3


def test_header_only_sheet_is_skipped() -> None:
    plan = _plan([list(LEADER_POSTS_14)])

    assert plan.skip_reason == "header only, no data rows"


@pytest.mark.parametrize(
    ("header", "reason_start"),
    [
        (["companyname", "person_name", "current_title", "linkedin_profile_link", "person_id"], "roster sheet"),
        (
            ["source_workbook", "founder", "company", "word", "total_word_count", "posts_containing_word",
             "total_posts_for_founder", "post_presence_%", "important_word_(>50%_posts)"],
            "word-frequency sheet",
        ),
        (
            ["founder", "company", "current_title", "linkedin_profile_url", "source_workbook",
             "usable_cleaned_posts", "linkedin_activity_status", "important_words_(>50%_posts)"],
            "summary sheet",
        ),
    ],
)
def test_non_post_layouts_are_skipped_with_a_reason(header: list[str], reason_start: str) -> None:
    plan = _plan([header, [None] * len(header)])

    assert plan.skip_reason is not None and plan.skip_reason.startswith(reason_start)
    assert plan.roles == ()


def test_header_without_a_text_column_is_skipped() -> None:
    header = [c for c in LEADER_POSTS_14 if c != "post_text"]
    plan = _plan([header, [None] * len(header)])

    assert plan.skip_reason == "no post-text column"


def test_skipped_record_keeps_the_loader_reason() -> None:
    record = SheetRecord(workbook="w.xlsx", sheet="*", frame=None, skip_reason="unreadable workbook: X")
    plan = plan_sheet(record, profile_sheet(record, position=0))

    assert plan.skip_reason == "unreadable workbook: X"


def test_blank_sheet_is_skipped() -> None:
    plan = _plan([[None, None], [None, None]])

    assert plan.skip_reason == "blank sheet"
