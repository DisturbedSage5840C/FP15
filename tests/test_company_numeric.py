"""Tests for Step 3 (src.company_numeric): numeric versions of three named Company_Data columns."""
from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd
import pytest

from src import company_numeric
from src.company_numeric import (
    COLUMN_MAP,
    NUMERIC_COLUMNS,
    UNVERIFIED_SCALE,
    build_numeric,
    column_summaries,
    render_report,
)
from src.verify_raw import ManifestMismatch

SOURCE_COLUMNS = [source for _, source in COLUMN_MAP]


def _company(*rows: tuple[str, str, str], extra: dict[str, list[str]] | None = None) -> pd.DataFrame:
    frame = pd.DataFrame(list(rows), columns=SOURCE_COLUMNS)
    frame["Person_Name"] = [f"Person {i}" for i in range(len(rows))]
    for name, values in (extra or {}).items():
        frame[name] = values
    return frame


def test_suffixed_and_plain_values_are_parsed_to_numbers() -> None:
    company = _company(("186.6M", "1,250", "2.5B"))

    result = build_numeric(company)

    assert result.iloc[0]["revenue_usd_latest"] == pytest.approx(186.6e6)
    assert result.iloc[0]["employees"] == pytest.approx(1250.0)
    assert result.iloc[0]["profit_usd_2024"] == pytest.approx(2.5e9)


def test_blank_markers_stay_missing_and_are_not_zero() -> None:
    company = _company((".", "-", ""))

    result = build_numeric(company)

    assert result[list(NUMERIC_COLUMNS)].isna().all(axis=None)


def test_an_unparseable_cell_stays_missing_and_is_not_guessed() -> None:
    company = _company(("500+", "n/a", "about 2M"))

    result = build_numeric(company)

    assert result[list(NUMERIC_COLUMNS)].isna().all(axis=None)


def test_rows_are_keyed_by_company_row_and_carry_no_names() -> None:
    company = _company(("1M", "5", "2M"), ("2M", "6", "3M"))

    result = build_numeric(company)

    assert list(result["company_row"]) == ["row:1", "row:2"]
    assert not any("Person" in str(v) for v in result.to_numpy().ravel())
    assert "Person_Name" not in result.columns


def test_bracketed_columns_are_never_read() -> None:
    company = _company(("1M", "5", "2M"), extra={"AnnualRevenueUSD": ["[1M]"], "TotalEmployeeCount": ["[9]"]})

    result = build_numeric(company)

    assert set(result.columns) == {"company_row", *NUMERIC_COLUMNS, UNVERIFIED_SCALE}


def test_a_plain_profit_number_without_a_suffix_is_flagged_not_rescaled() -> None:
    company = _company(("1M", "5", "102.2"), ("1M", "5", "2.5M"), ("1M", "5", ""))

    result = build_numeric(company)

    assert list(result[UNVERIFIED_SCALE]) == [True, False, False]
    assert result.iloc[0]["profit_usd_2024"] == pytest.approx(102.2)


def test_summaries_count_filled_blank_parsed_and_unparsed() -> None:
    company = _company(("1M", "5", "2M"), (".", "x", "500+"), ("", "7", "102.2"))

    summaries = {s.output_column: s for s in column_summaries(company)}

    employees = summaries["employees"]
    assert (employees.rows, employees.blank, employees.filled, employees.parsed, employees.unparsed) == (3, 0, 3, 2, 1)
    revenue = summaries["revenue_usd_latest"]
    assert (revenue.rows, revenue.blank, revenue.filled) == (3, 2, 1)
    profit = summaries["profit_usd_2024"]
    assert (profit.filled, profit.parsed, profit.unparsed, profit.unverified_scale) == (3, 2, 1, 1)


def test_a_missing_source_column_is_a_clear_error() -> None:
    company = pd.DataFrame({"LatestRevenueUSD": ["1M"]})

    with pytest.raises(ValueError, match="NumberofEmployees"):
        build_numeric(company)


def test_report_has_counts_and_header_only_fiscal_year_statement_and_no_values() -> None:
    company = _company(("186.6M", "1,250", "2.5B"))

    text = render_report(column_summaries(company))

    assert "LatestRevenueUSD" in text and "NumberofEmployees" in text and "ProfitUSD2024" in text
    assert "fiscal year" in text.lower()
    assert "186.6" not in text and "Person" not in text


@pytest.fixture
def interim(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    folder = tmp_path / "interim"
    folder.mkdir()
    _company(("1M", "5", "2M"), ("2M", "6", "102.2")).to_csv(folder / "company_data.csv", index=False)
    monkeypatch.setattr(company_numeric, "verify_raw", lambda raw_dir: "ok")
    return folder


def test_run_writes_the_numeric_table_and_a_counts_only_report(
    interim: Path, tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    report = tmp_path / "reports" / "company_numeric.md"

    with caplog.at_level(logging.INFO):
        code = company_numeric.run(tmp_path / "raw", interim, report)

    table = pd.read_csv(interim / "company_numeric.csv", dtype=str, keep_default_na=False)
    assert code == 0
    assert list(table["company_row"]) == ["row:1", "row:2"]
    assert "Person" not in report.read_text(encoding="utf-8")


def test_run_fails_when_the_manifest_does_not_match(interim: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def _bad(raw_dir: Path) -> str:
        raise ManifestMismatch("changed")

    monkeypatch.setattr(company_numeric, "verify_raw", _bad)

    assert company_numeric.run(tmp_path / "raw", interim, tmp_path / "r.md") == 1


def test_run_fails_when_company_data_is_missing(interim: Path, tmp_path: Path) -> None:
    (interim / "company_data.csv").unlink()

    assert company_numeric.run(tmp_path / "raw", interim, tmp_path / "r.md") == 1


def test_run_fails_when_a_named_column_is_missing(interim: Path, tmp_path: Path) -> None:
    pd.DataFrame({"LatestRevenueUSD": ["1M"]}).to_csv(interim / "company_data.csv", index=False)

    assert company_numeric.run(tmp_path / "raw", interim, tmp_path / "r.md") == 1


def test_main_returns_the_exit_code_of_run(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(company_numeric, "run", lambda: 0)

    assert company_numeric.main() == 0
