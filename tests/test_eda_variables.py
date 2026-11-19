"""Tests for src.eda_variables: the variable map with fill rates (`make eda-variables`). Synthetic data only."""
from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd
import pytest

from src import eda_variables
from src.eda_common import SMALL, EdaSettings
from src.eda_gaps import COMPANY_COLUMNS
from src.eda_variables import (
    VariableRow,
    compare_checks,
    load_expected,
    render_variable_map,
    run,
    variable_rows,
)
from src.name_key import name_key
from src.verify_raw import ManifestMismatch

LOOSE = EdaSettings(min_posts=2, disclosure_min=1, model_min=1, size_bands=2)
STRICT = EdaSettings(min_posts=15, disclosure_min=5, model_min=20, size_bands=4)
A, B, C, E, F = "Zed Sentinel", "Yara Sentinel", "Xan Sentinel", "Wil Sentinel", "Vic Sentinel"
POST_TEXT = "SENTINEL-POST-TEXT-never-in-the-report"
LINK = "https://sentinel.example/in/zed"
EMAIL = "sentinel@example.org"
COMPANY_NAME = "Sentinel Holdings Ltd"
EXTRA_COMPANY_COLUMNS = ["CompanyName", "Person_Name", "Email", "IsIPO", "StockTicker", "Exchange", "IPODate", "Q", "V", "Z"]
POST_COLUMNS = ["leader", "text_kind", "title", "ceo_type", "role_start_year", "post_date", "post_date_text", "post_text"]


def _posts() -> pd.DataFrame:
    """8 raw cells over 5 leaders (A 3, B 1, C 2, E 1, F 1) and one cleaned row that must never count.

    Cells ending in a number: A has 2, C has 1, so 3 of 8.
    """
    rows = [
        (A, "raw", "CEO", "Professional CEO", "", "", "", "great quarter 120"),
        (A, "raw", ".", "", "", "", "", "plain text"),
        (A, "raw", "CEO", "Professional CEO", "", "", "", "line\n45"),
        (B, "raw", "", "", "", "", "", "nothing here"),
        (C, "raw", "Founder", "Founder-CEO", "2019", "", "", "wrote to 7"),
        (C, "raw", "Founder", "Founder-CEO", "", "", "", "ok"),
        (E, "raw", "COO", "Professional CEO", "", "", "", "done"),
        (F, "raw", ".", "-", "", "", "", "ok"),
        (E, "cleaned", "COO", "Professional CEO", "2020", "2024-01-01", "1d", "should not count 99"),
    ]
    frame = pd.DataFrame(rows, columns=POST_COLUMNS)
    frame["link"] = LINK
    frame["profile_url"] = LINK
    frame["company"] = COMPANY_NAME
    return frame


def _proposal() -> pd.DataFrame:
    rows = [
        (name_key(A), "clear", "row:1"),
        (name_key(B), "clear", "row:2"),
        (name_key(C), "ambiguous", "row:3"),
        (name_key(E), "clear", "row:4"),
        (name_key(F), "clear", "row:5"),
    ]
    return pd.DataFrame(rows, columns=["key", "status", "company"])


def _company() -> pd.DataFrame:
    """Rows 1, 2, 4, 5 are clear matches (A, B, E, F); row 3 is C's ambiguous one and is never read."""
    frame = pd.DataFrame("", index=range(5), columns=[*COMPANY_COLUMNS, *EXTRA_COMPANY_COLUMNS])
    frame["CompanyName"] = COMPANY_NAME
    frame["Person_Name"] = [A, B, C, E, F]
    frame["Email"] = EMAIL
    frame["Gender"] = ["1", "0", "1", "", "2"]
    frame["SectorPraticeAreaFeed"] = ["Tech > SaaS", "-", "Energy", "", ""]
    frame["NumberofEmployees"] = ["500+", "300", "900", "", "."]
    frame["FoundedYear"] = ["2001", "", "1999", "", ""]
    frame["LinkedIn_Followers"] = ["12K", "", "", "", ""]
    frame["RevenueUSD2021"] = ["186.6M", "", "", "", ""]
    frame["RevenueUSD2022"] = [".", "", "", "", ""]
    frame["IsIPO"] = ["TRUE", "", "", "", ""]
    frame["Q"] = ["7", "", "", "", ""]
    frame["Z"] = ["-", "-", "", "", ""]
    return frame


def _clean() -> pd.DataFrame:
    ages = ["3.0", "", "12.0", "", "1.0", "", "24.0", ""]
    return pd.DataFrame({"leader_id": ["LEADERID-SENTINEL"] * 8, "age_months": ages})


@pytest.fixture
def rows() -> dict[str, VariableRow]:
    built = variable_rows(_posts(), _proposal(), _company(), _clean())
    return {row.key: row for row in built}


# ---- leader-level variables from the post workbooks -------------------------------------------


def test_post_variables_count_leaders_with_at_least_one_filled_cell(rows: dict[str, VariableRow]) -> None:
    assert (rows["ceo_type"].filled, rows["ceo_type"].total) == (3, 5)
    assert (rows["role_start_year"].filled, rows["role_start_year"].total) == (1, 5)


def test_a_dot_or_dash_in_a_post_cell_is_blank(rows: dict[str, VariableRow]) -> None:
    assert (rows["current_title"].filled, rows["current_title"].total) == (3, 5)


def test_cleaned_rows_never_fill_a_variable(rows: dict[str, VariableRow]) -> None:
    assert rows["post_date"].filled == 0
    assert rows["post_date_text"].filled == 0


# ---- Company_Data variables -------------------------------------------------------------------


def test_company_variables_use_only_leaders_with_a_clear_match(rows: dict[str, VariableRow]) -> None:
    assert rows["sector"].total == 4
    assert rows["sector"].filled == 1


def test_a_number_that_cannot_be_read_counts_as_missing(rows: dict[str, VariableRow]) -> None:
    assert rows["firm_size"].filled == 1


def test_numeric_company_variables_are_counted_with_the_shared_parser(rows: dict[str, VariableRow]) -> None:
    assert rows["followers"].filled == 1
    assert rows["revenue_2021"].filled == 1
    assert rows["revenue_2022"].filled == 0


def test_gender_is_split_exactly_as_coded(rows: dict[str, VariableRow]) -> None:
    assert (rows["gender_coded"].filled, rows["gender_coded"].total) == (3, 4)
    assert rows["gender_coded_1"].filled == 1
    assert rows["gender_coded_0"].filled == 1
    assert rows["gender_coded_other"].filled == 1
    assert rows["gender_no_value"].filled == 1
    assert rows["gender_coded_1"].total == 4


def test_gender_split_adds_up_to_the_matched_leaders(rows: dict[str, VariableRow]) -> None:
    parts = ("gender_coded_1", "gender_coded_0", "gender_coded_other", "gender_no_value")

    assert sum(rows[key].filled or 0 for key in parts) == rows["gender_coded"].total


# ---- cell-level variables ---------------------------------------------------------------------


def test_relative_age_counts_cells_with_a_parsed_age(rows: dict[str, VariableRow]) -> None:
    assert (rows["age_parsed"].filled, rows["age_parsed"].total) == (4, 8)


def test_cells_ending_in_a_number_are_counted_over_raw_cells_only(rows: dict[str, VariableRow]) -> None:
    assert (rows["ends_in_number"].filled, rows["ends_in_number"].total) == (3, 8)


def test_cells_ending_in_a_number_are_marked_unverified_and_not_usable(rows: dict[str, VariableRow]) -> None:
    assert rows["ends_in_number"].usable == "no"
    assert "unverified" in rows["ends_in_number"].reason.lower()


# ---- not usable and the usable flag -----------------------------------------------------------


def test_not_usable_rows_carry_a_reason(rows: dict[str, VariableRow]) -> None:
    for key in ("ipo_columns", "unnamed_q", "unnamed_v", "unnamed_z", "contact_columns"):
        assert rows[key].role == "not usable"
        assert rows[key].usable == "no"
        assert rows[key].reason


def test_ipo_reason_says_every_firm_is_listed(rows: dict[str, VariableRow]) -> None:
    assert "listed" in rows["ipo_columns"].reason.lower()


def test_unnamed_columns_are_counted_over_matched_leaders(rows: dict[str, VariableRow]) -> None:
    assert (rows["unnamed_q"].filled, rows["unnamed_q"].total) == (1, 4)
    assert rows["unnamed_v"].filled == 0
    assert rows["unnamed_z"].filled == 0


def test_contact_columns_have_no_fill_rate_because_they_are_dropped_at_load(rows: dict[str, VariableRow]) -> None:
    assert rows["contact_columns"].filled is None
    assert "dropped at load" in rows["contact_columns"].reason.lower()


def test_a_variable_with_no_filled_value_is_not_usable_and_one_with_values_is(rows: dict[str, VariableRow]) -> None:
    assert rows["post_date"].usable == "no"
    assert rows["ceo_type"].usable == "yes"


def test_every_row_has_one_of_the_allowed_study_roles(rows: dict[str, VariableRow]) -> None:
    allowed = {"Y source", "X leader block", "X firm block", "control", "outcome", "linking only", "not usable"}

    assert {row.role for row in rows.values()} <= allowed


# ---- checks against the write-up --------------------------------------------------------------


def test_compare_checks_flags_a_difference_and_passes_an_agreement(rows: dict[str, VariableRow]) -> None:
    expected = {"ceo_type": 3, "gender_coded": 4, "sector": 1}

    checks = {check.key: check for check in compare_checks(tuple(rows.values()), expected)}

    assert checks["ceo_type"].matches is True
    assert checks["sector"].matches is True
    assert checks["gender_coded"].matches is False
    assert (checks["gender_coded"].expected, checks["gender_coded"].observed) == (4, 3)


def test_compare_checks_names_an_expected_key_that_has_no_row(rows: dict[str, VariableRow]) -> None:
    with pytest.raises(ValueError, match="no_such_variable"):
        compare_checks(tuple(rows.values()), {"no_such_variable": 1})


def test_load_expected_reads_the_write_up_numbers(tmp_path: Path) -> None:
    path = tmp_path / "writeup.yaml"
    path.write_text("ceo_type: 518\nsector: 527\n", encoding="utf-8")

    assert load_expected(path) == {"ceo_type": 518, "sector": 527}


def test_load_expected_rejects_a_value_that_is_not_a_whole_number(tmp_path: Path) -> None:
    path = tmp_path / "writeup.yaml"
    path.write_text("ceo_type: many\n", encoding="utf-8")

    with pytest.raises(ValueError, match="ceo_type"):
        load_expected(path)


# ---- the report -------------------------------------------------------------------------------


def _report(settings: EdaSettings = LOOSE, expected: dict[str, int] | None = None) -> str:
    built = variable_rows(_posts(), _proposal(), _company(), _clean())
    checks = compare_checks(built, expected or {"ceo_type": 3, "gender_coded": 4})
    return render_variable_map(built, checks, settings)


def test_the_report_table_has_the_six_columns() -> None:
    header = "| Variable | Source | Study role | Filled n of N | Share missing | Usable? |"

    assert header in _report()


def test_the_report_states_the_claim_limit_and_the_unverified_counts() -> None:
    text = _report().lower()

    assert "image projected in public posts" in text
    assert "unverified" in text
    assert "as coded" in text


def test_the_report_has_a_checks_section_that_lists_a_difference() -> None:
    text = _report()
    checks = text[text.index("## Checks"):]

    assert "gender_coded" in checks
    assert "differs" in checks.lower()


def test_the_checks_section_says_so_when_everything_agrees() -> None:
    text = _report(expected={"ceo_type": 3})

    assert "no difference" in text[text.index("## Checks"):].lower()


def test_a_count_under_the_disclosure_minimum_is_shown_as_small() -> None:
    text = _report(STRICT)
    sector_line = next(line for line in text.splitlines() if line.startswith("| sector "))

    assert SMALL in sector_line


def test_the_report_never_carries_names_text_links_emails_ids_or_refs() -> None:
    text = _report()
    forbidden = (A, B, C, E, F, POST_TEXT, LINK, EMAIL, COMPANY_NAME, "LEADERID", name_key(A), "row:", "http", "@")

    for value in forbidden:
        assert value not in text


def test_the_report_ends_with_one_newline() -> None:
    text = _report()

    assert text.endswith("\n") and not text.endswith("\n\n")


# ---- run --------------------------------------------------------------------------------------


def _write_interim(directory: Path) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    tables = {
        "harmonised_posts": _posts(),
        "leader_id_proposal": _proposal(),
        "posts_clean": _clean(),
        "company_data": _company(),
    }
    for name, frame in tables.items():
        frame.to_csv(directory / f"{name}.csv", index=False)


@pytest.fixture
def workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, Path]:
    monkeypatch.setattr(eda_variables, "verify_raw", lambda directory: "ok")
    interim = tmp_path / "interim"
    _write_interim(interim)
    thresholds = tmp_path / "thresholds.yaml"
    thresholds.write_text(
        "min_posts_per_leader: 2\neda_disclosure_min_leaders: 1\neda_model_min_leaders: 1\neda_size_bands: 2\n",
        encoding="utf-8",
    )
    expected = tmp_path / "writeup.yaml"
    expected.write_text("ceo_type: 3\ngender_coded: 4\n", encoding="utf-8")
    return {
        "raw": tmp_path / "raw",
        "interim": interim,
        "report": tmp_path / "reports" / "eda_variable_map.md",
        "thresholds": thresholds,
        "expected": expected,
    }


def _run(workspace: dict[str, Path]) -> int:
    return run(workspace["raw"], workspace["interim"], workspace["report"], workspace["thresholds"], workspace["expected"])


def test_run_writes_the_report_and_returns_zero(workspace: dict[str, Path]) -> None:
    assert _run(workspace) == 0

    assert "## Checks" in workspace["report"].read_text(encoding="utf-8")


def test_run_report_has_no_names_text_links_or_emails(workspace: dict[str, Path]) -> None:
    _run(workspace)

    text = workspace["report"].read_text(encoding="utf-8")
    for forbidden in (A, B, C, E, F, POST_TEXT, LINK, EMAIL, COMPANY_NAME, "LEADERID"):
        assert forbidden not in text


def test_run_verifies_the_raw_manifest_first(workspace: dict[str, Path], monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[Path] = []
    monkeypatch.setattr(eda_variables, "verify_raw", lambda directory: seen.append(directory) or "ok")

    _run(workspace)

    assert seen == [workspace["raw"]]


def test_run_stops_and_writes_nothing_when_the_manifest_does_not_match(
    workspace: dict[str, Path], monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    def refuse(directory: Path) -> str:
        raise ManifestMismatch("raw changed")

    monkeypatch.setattr(eda_variables, "verify_raw", refuse)

    with caplog.at_level(logging.ERROR):
        code = _run(workspace)

    assert code == 1
    assert not workspace["report"].exists()
    assert "eda-variables FAILED" in caplog.text


def test_run_fails_cleanly_when_an_interim_file_is_missing(workspace: dict[str, Path]) -> None:
    (workspace["interim"] / "posts_clean.csv").unlink()

    assert _run(workspace) == 1
    assert not workspace["report"].exists()
