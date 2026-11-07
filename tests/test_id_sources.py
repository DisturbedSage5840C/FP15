"""Tests for turning the four people lists into matching Entities (src.id_sources). Synthetic data."""
import pandas as pd
import pytest

from src.id_sources import (
    SOURCE_COMPANY,
    SOURCE_ROSTER,
    SOURCE_SHEETS,
    SOURCE_SUMMARIES,
    company_entities,
    roster_entities,
    sheet_entities,
    summary_entities,
)
from src.loader import SheetRecord

SUMMARY_HEADER = ["Founder", "Company", "Current title", "LinkedIn profile URL"]


def _summary_record(workbook: str, rows: list[list[object]], header: list[str] = SUMMARY_HEADER) -> SheetRecord:
    frame = pd.DataFrame([header, *rows], dtype=object)
    return SheetRecord(workbook=workbook, sheet="CEO_Post_Summary", frame=frame, skip_reason=None)


def _posts_sheet_record(workbook: str) -> SheetRecord:
    frame = pd.DataFrame([["Post", "Date"], ["hello", "1d"]], dtype=object)
    return SheetRecord(workbook=workbook, sheet="Some Leader", frame=frame, skip_reason=None)


def test_sheet_entities_gives_one_entity_per_distinct_leader_key() -> None:
    posts = pd.DataFrame(
        {
            "leader": ["Ann Lee", "Lee, Ann", "Bo Rao", None],
            "company": ["Acme", "Acme", None, "Zed"],
            "workbook": ["b/w1.xlsx", "b/w1.xlsx", "b/w2.xlsx", "b/w2.xlsx"],
            "sheet_idx": ["3", "5", "1", "2"],
        }
    )

    entities = sheet_entities(posts)

    assert [e.key for e in entities] == ["ann lee", "bo rao"]
    assert {e.source for e in entities} == {SOURCE_SHEETS}
    assert entities[0].ref == "b/w1.xlsx#3"  # the first sheet in workbook then index order
    assert entities[0].company_key == "acme"


def test_sheet_entities_refs_are_unique_per_key_and_sorted_by_workbook_then_index() -> None:
    posts = pd.DataFrame(
        {
            "leader": ["Ann Lee", "Ann Lee"],
            "company": [None, "Acme"],
            "workbook": ["b/w2.xlsx", "b/w1.xlsx"],
            "sheet_idx": ["1", "9"],
        }
    )

    (entity,) = sheet_entities(posts)

    assert entity.ref == "b/w1.xlsx#9"
    assert entity.company_key == "acme"  # first filled company, missing stays missing


def test_roster_entities_use_person_name_and_company_with_row_refs() -> None:
    roster = pd.DataFrame(
        {"company": ["Acme", None], "person_name": ["Ann Lee", " "], "person_id": ["349", "350"]}
    )

    (entity,) = roster_entities(roster)

    assert (entity.source, entity.ref, entity.key, entity.company_key) == (SOURCE_ROSTER, "row:1", "ann lee", "acme")


def test_roster_entities_keep_duplicate_keys_as_separate_entities() -> None:
    roster = pd.DataFrame({"company": ["A", "B"], "person_name": ["Ann Lee", "Lee Ann"], "person_id": ["1", "2"]})

    entities = roster_entities(roster)

    assert [e.ref for e in entities] == ["row:1", "row:2"]


def test_company_entities_use_person_name_column_and_skip_blank_names() -> None:
    company = pd.DataFrame({"CompanyName": ["Acme", "Beta", "Gamma"], "Person_Name": ["Ann Lee", None, "Bo Rao"]})

    entities = company_entities(company)

    assert [(e.ref, e.key, e.company_key) for e in entities] == [
        ("row:1", "ann lee", "acme"),
        ("row:3", "bo rao", "gamma"),
    ]
    assert {e.source for e in entities} == {SOURCE_COMPANY}


def test_company_entities_raise_when_the_name_column_is_missing() -> None:
    with pytest.raises(ValueError, match="Person_Name"):
        company_entities(pd.DataFrame({"CompanyName": ["Acme"]}))


def test_summary_entities_read_first_sheet_of_wordcount_workbooks_only() -> None:
    records = [
        _summary_record("b1/wordcount_100.xlsx", [["Ann Lee", "Acme", "CEO", "u"], [None, "x", "y", "z"]]),
        _posts_sheet_record("b1/wordcount_100.xlsx"),
        _posts_sheet_record("b1/posts_100.xlsx"),
        _summary_record("b2/wordcount_200.xlsx", [["Bo Rao", "Beta", "CEO", "u"]]),
    ]

    entities, sheets = summary_entities(records)

    assert [(e.source, e.key, e.company_key) for e in entities] == [
        (SOURCE_SUMMARIES, "ann lee", "acme"),
        (SOURCE_SUMMARIES, "bo rao", "beta"),
    ]
    assert entities[0].ref == "b1/wordcount_100.xlsx#0:r2"  # Excel row 2 = first data row
    assert [(s.workbook, s.sheet_idx, s.names_filled) for s in sheets] == [
        ("b1/wordcount_100.xlsx", 0, 1),
        ("b2/wordcount_200.xlsx", 0, 1),
    ]


def test_summary_entities_ignore_a_wordcount_workbook_whose_first_sheet_was_skipped() -> None:
    skipped = SheetRecord(workbook="b/wordcount_100.xlsx", sheet="*", frame=None, skip_reason="too big")

    entities, sheets = summary_entities([skipped])

    assert entities == () and sheets == ()


def test_summary_entities_raise_when_the_founder_column_is_missing() -> None:
    record = _summary_record("b/wordcount_100.xlsx", [["x", "y"]], header=["Name", "Firm"])

    with pytest.raises(ValueError, match="Founder"):
        summary_entities([record])


def test_summary_entities_keep_repeated_names_as_separate_entities() -> None:
    record = _summary_record(
        "b/wordcount_100.xlsx", [["Ann Lee", "A", "t", "u"], ["Lee Ann", "B", "t", "u"]]
    )

    entities, _ = summary_entities([record])

    assert [e.ref for e in entities] == ["b/wordcount_100.xlsx#0:r2", "b/wordcount_100.xlsx#0:r3"]
