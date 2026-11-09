"""Tests for the harmonise summary report (src.harmonise_report). Synthetic frames only."""
import pandas as pd

from src.harmonise import HarmonisedResult
from src.harmonise_report import SPOT_CHECK_SHEETS, SUPERSEDED_LEADER_NOTE, render_report

LOG_DEFAULTS = {
    "status": "used", "reason": "", "is_combined": False, "method": "header", "text_kind": "raw",
    "odd_reasons": "", "rows_with_text": 0, "rows_kept": 0, "dropped_no_leader": 0,
    "filled_from_sheet": 0, "sheet_name_conflict": 0, "cell_leader_rows": 0, "cell_matches_sheet": 0,
}


def _log(rows: list[dict[str, object]]) -> pd.DataFrame:
    return pd.DataFrame([{**LOG_DEFAULTS, **row} for row in rows])


def _posts(n: int = 3, **overrides: list[object]) -> pd.DataFrame:
    base: dict[str, list[object]] = {
        "leader": [f"Person {i}" for i in range(n)], "text_kind": ["raw"] * n,
        "post_date_is_text": [False] * n, "age_text": [None] * n, "post_date": [None] * n,
        "post_date_text": [None] * n, "role_start_year": [None] * n, "n_versions": [1] * n,
    }
    return pd.DataFrame({**base, **overrides}, dtype=object)


def _roster(n: int = 4) -> pd.DataFrame:
    return pd.DataFrame({"person_id": [str(i) for i in range(n)]})


def _result(log: list[dict[str, object]], posts: pd.DataFrame | None = None) -> HarmonisedResult:
    entries = [{**LOG_DEFAULTS, **row} for row in log]
    return HarmonisedResult(
        posts=_posts() if posts is None else posts,
        sheet_log=_log(log),
        rows_with_text=sum(int(str(e["rows_with_text"])) for e in entries),
        rows_after_leader=sum(int(str(e["rows_kept"])) for e in entries),
    )


def _basic() -> HarmonisedResult:
    return _result(
        [
            {"workbook": "D/B1/a.xlsx", "sheet_idx": 0, "sheet": "Combined", "is_combined": True,
             "rows_with_text": 5, "rows_kept": 4, "dropped_no_leader": 1},
            {"workbook": "D/B1/a.xlsx", "sheet_idx": 1, "sheet": "Zed Quill", "rows_with_text": 3,
             "rows_kept": 3, "filled_from_sheet": 3},
            {"workbook": "D/B1/a.xlsx", "sheet_idx": 2, "sheet": "Mae Pike", "status": "skipped",
             "reason": "header only, no data rows", "odd_reasons": "stray cells"},
            {"workbook": "D/B1/a.xlsx", "sheet_idx": 3, "sheet": "Ola Bend", "status": "skipped",
             "reason": "header only, no data rows"},
            {"workbook": "D/B2/b.xlsx", "sheet_idx": 0, "sheet": "Roster", "status": "skipped",
             "reason": "roster sheet"},
        ]
    )


def test_report_starts_with_the_title_and_compares_with_the_owner_figures() -> None:
    text = render_report(_basic(), _roster())

    assert text.startswith("# Harmonise summary")
    assert "32,448" in text and "22,083" in text and "544" in text and "705" in text


def test_report_marks_the_owner_leader_figure_as_superseded() -> None:
    text = render_report(_basic(), _roster())

    assert SUPERSEDED_LEADER_NOTE in text
    assert "superseded, see Findings" in SUPERSEDED_LEADER_NOTE


def test_skipped_sheets_are_counted_by_reason_without_file_names_or_indexes() -> None:
    text = render_report(_basic(), _roster())

    assert "- **header only, no data rows**: 2 sheets in 1 workbooks" in text
    assert ".xlsx" not in text
    assert "D/B1" not in text


def test_report_never_contains_sheet_or_leader_names() -> None:
    text = render_report(_basic(), _roster())

    for name in ("Zed Quill", "Mae Pike", "Ola Bend", "Person 0"):
        assert name not in text


def test_leader_fill_counts_are_reported() -> None:
    text = render_report(_basic(), _roster())

    assert "dropped (combined sheet, no leader)" in text
    assert "filled from the sheet name" in text


def _checkable_sheets(n: int) -> list[dict[str, object]]:
    return [
        {"workbook": f"D/B/w{i}.xlsx", "sheet_idx": 1, "sheet": f"S{i}", "rows_with_text": 4,
         "rows_kept": 4, "cell_leader_rows": 2, "cell_matches_sheet": 2 if i % 2 else 1,
         "filled_from_sheet": 2}
        for i in range(n)
    ]


def test_spot_check_lists_no_per_sheet_lines() -> None:
    text = render_report(_result(_checkable_sheets(SPOT_CHECK_SHEETS + 10)), _roster())

    assert not [line for line in text.splitlines() if line.startswith("- D/B/w")]
    assert "D/B/w" not in text
    assert f"Agreement on all {SPOT_CHECK_SHEETS + 10} comparable sheets" in text


def test_spot_check_is_deterministic_and_reports_an_agreement_rate() -> None:
    result = _result(_checkable_sheets(30))

    first, second = render_report(result, _roster()), render_report(result, _roster())

    assert first == second
    assert "agreement" in first.lower() and "%" in first


def test_spot_check_without_checkable_sheets_says_so() -> None:
    text = render_report(_basic(), _roster())

    assert "no sheet has both" in text.lower()


def test_odd_sheets_are_counted_without_file_names_or_indexes() -> None:
    text = render_report(_basic(), _roster())

    assert "1 sheets in 1 workbooks" in text.split("Sheets the profiler flagged")[1]


def test_column_fill_counts_cover_age_text_post_date_and_text_like_dates() -> None:
    posts = _posts(
        3, age_text=["3mo", None, "1yr"], post_date=["x" * 59, None, None],
        post_date_is_text=[True, False, False],
    )

    text = render_report(_result([{"workbook": "D/w.xlsx", "sheet_idx": 0, "sheet": "C"}], posts), _roster())

    assert "age_text | 2" in text
    assert "post_date holds post text | 1" in text


def test_report_handles_an_empty_run() -> None:
    result = HarmonisedResult(
        posts=_posts(0), sheet_log=_log([]), rows_with_text=0, rows_after_leader=0
    )

    assert render_report(result, _roster(0)).startswith("# Harmonise summary")


def _mixed() -> HarmonisedResult:
    posts = _posts(
        5, leader=["Ann Rao", "Bo Lee", "Cy Dunn", "Ann Rao", "Bo Lee"],
        text_kind=["raw", "raw", "raw", "cleaned", "cleaned"],
    )
    return _result(
        [
            {"workbook": "D/B/a.xlsx", "sheet_idx": 0, "sheet": "S", "text_kind": "raw",
             "rows_with_text": 4, "rows_kept": 4},
            {"workbook": "D/B/wordcount_1.xlsx", "sheet_idx": 3, "sheet": "T", "text_kind": "cleaned",
             "rows_with_text": 3, "rows_kept": 3},
            {"workbook": "D/B/wordcount_1.xlsx", "sheet_idx": 4, "sheet": "U", "text_kind": "cleaned",
             "rows_with_text": 2, "rows_kept": 2},
        ],
        posts,
    )


def test_headline_separates_raw_text_from_cleaned_text_copies() -> None:
    text = render_report(_mixed(), _roster())
    headline = text.split("## Headline")[1].split("## Sheets")[0]

    assert "| Non-empty post_text rows | 32,448 | 4 | -32,444 | 5 | 9 |" in headline
    assert "| Sheets with post text | 705 | 1 | -704 | 2 | 3 |" in headline
    assert "| Unique posts after dedupe | 22,083 | 3 | -22,080 | 2 | 5 |" in headline
    assert "| Leaders | 544 | 3 | -541 | 2 | 3 |" in headline


def test_headline_explains_the_cleaned_text_copies() -> None:
    text = render_report(_mixed(), _roster())

    assert "cleaned_post_text" in text.split("## Sheets")[0]
