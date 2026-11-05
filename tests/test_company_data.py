"""Tests for Company_Data loading and profiling (src.company_data). Synthetic data only."""
from pathlib import Path

import pandas as pd
import pytest

from src.company_data import (
    CONTACT_COLUMNS,
    clean_cell,
    is_contact_column,
    load_company_data,
    parse_quantity,
    profile_company_data,
    render_profile,
    run,
    with_numeric_columns,
    write_interim,
)
from src.verify_raw import run as verify_raw

HEADER = [
    "CompanyName", "Person_Name", "Email", "KeyPeopleEmailIds", "CompanyEmails",
    "CompanyPhoneNumbers", "Gender", "RevenueUSD2023", "Q", "V", "Z", "AltContactEmail",
    "MobileDownloads",
]


def _row(**cells: object) -> list[object]:
    base: dict[str, object] = {name: None for name in HEADER}
    base.update(cells)
    return [base[name] for name in HEADER]


def _write_workbook(path: Path, rows: list[list[object]], header: list[str] = HEADER) -> Path:
    pd.DataFrame([header, *rows]).to_excel(path, header=False, index=False)
    return path


def _sample_rows() -> list[list[object]]:
    return [
        _row(CompanyName="Acme", Person_Name="Ann Rao", Email="ann@example.com", Gender=1,
             RevenueUSD2023="186.6M", Q="0%", V="14%", Z="-3%", MobileDownloads=1200),
        _row(CompanyName="Beta", Person_Name="Bo Lee", CompanyPhoneNumbers="+91 98765 43210",
             Gender=0, RevenueUSD2023="2.5B", Q="5%", V="-", Z=".", MobileDownloads=None),
        _row(CompanyName="Gamma", Person_Name="Cy Dunn", Gender=None, RevenueUSD2023="-",
             Q="0%", V="14%", Z="0%"),
    ]


def test_contact_columns_are_the_four_named_ones() -> None:
    assert CONTACT_COLUMNS == frozenset(
        {"Email", "KeyPeopleEmailIds", "CompanyEmails", "CompanyPhoneNumbers"}
    )


@pytest.mark.parametrize("name", ["Email", "CompanyEmails", "AltContactEmail", "Phone", "Telephone_No"])
def test_is_contact_column_catches_email_and_phone_names(name: str) -> None:
    assert is_contact_column(name)


@pytest.mark.parametrize("name", ["Gender", "MobileDownloads", "LinkedIn_Profile_Link", "Website"])
def test_is_contact_column_leaves_other_columns(name: str) -> None:
    assert not is_contact_column(name)


@pytest.mark.parametrize("value", [None, "", "  ", ".", "-", " - ", float("nan")])
def test_clean_cell_treats_blank_markers_as_missing(value: object) -> None:
    assert clean_cell(value) is None


def test_clean_cell_keeps_real_values_as_text() -> None:
    assert clean_cell(" 14% ") == "14%"
    assert clean_cell(1) == "1"
    assert clean_cell(0) == "0"


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("186.6M", 186_600_000.0),
        ("2.5B", 2_500_000_000.0),
        ("12K", 12_000.0),
        ("1.2T", 1_200_000_000_000.0),
        ("1,250", 1250.0),
        ("-3.5M", -3_500_000.0),
        ("14%", 14.0),
        ("-3%", -3.0),
        (42, 42.0),
        ("0", 0.0),
    ],
)
def test_parse_quantity_reads_suffixed_percent_and_plain_numbers(text: object, expected: float) -> None:
    assert parse_quantity(text) == pytest.approx(expected)


@pytest.mark.parametrize("text", [None, "", ".", "-", "500+", "n/a", "12 apples", "M", float("nan")])
def test_parse_quantity_returns_none_when_it_cannot_read_the_value(text: object) -> None:
    assert parse_quantity(text) is None


def test_load_drops_contact_columns_by_name_and_by_pattern(tmp_path: Path) -> None:
    path = _write_workbook(tmp_path / "c.xlsx", _sample_rows())

    loaded = load_company_data(path)

    for name in ("Email", "KeyPeopleEmailIds", "CompanyEmails", "CompanyPhoneNumbers", "AltContactEmail"):
        assert name not in loaded.frame.columns
    assert set(loaded.dropped) == {
        "Email", "KeyPeopleEmailIds", "CompanyEmails", "CompanyPhoneNumbers", "AltContactEmail",
    }
    assert len(loaded.frame) == 3


def test_load_never_keeps_contact_values_anywhere_in_the_frame(tmp_path: Path) -> None:
    path = _write_workbook(tmp_path / "c.xlsx", _sample_rows())

    loaded = load_company_data(path)

    cells = {str(v) for v in loaded.frame.to_numpy().ravel() if v is not None}
    assert "ann@example.com" not in cells
    assert "+91 98765 43210" not in cells


def test_load_turns_blank_markers_into_missing(tmp_path: Path) -> None:
    path = _write_workbook(tmp_path / "c.xlsx", _sample_rows())

    frame = load_company_data(path).frame

    assert frame["V"].tolist() == ["14%", None, "14%"]
    assert frame["RevenueUSD2023"].tolist() == ["186.6M", "2.5B", None]


def test_load_keeps_gender_exactly_as_coded(tmp_path: Path) -> None:
    path = _write_workbook(tmp_path / "c.xlsx", _sample_rows())

    frame = load_company_data(path).frame

    assert frame["Gender"].tolist() == ["1", "0", None]


def test_profile_counts_gender_without_decoding_it(tmp_path: Path) -> None:
    loaded = load_company_data(_write_workbook(tmp_path / "c.xlsx", _sample_rows()))

    profile = profile_company_data(loaded)

    assert profile.gender_counts == {"1": 1, "0": 1, "blank": 1}
    text = render_profile(profile)
    assert "not decoded" in text.lower()


def test_profile_reports_shape_and_dropped_contact_column_names(tmp_path: Path) -> None:
    loaded = load_company_data(_write_workbook(tmp_path / "c.xlsx", _sample_rows()))

    profile = profile_company_data(loaded)
    text = render_profile(profile)

    assert profile.rows == 3
    assert profile.columns_loaded == len(HEADER)
    assert profile.columns_kept == len(HEADER) - 5
    assert "CompanyPhoneNumbers" in text


def test_profile_describes_columns_q_v_z_with_counts_only(tmp_path: Path) -> None:
    loaded = load_company_data(_write_workbook(tmp_path / "c.xlsx", _sample_rows()))

    profile = profile_company_data(loaded)
    by_name = {c.name: c for c in profile.watched}

    assert set(by_name) == {"Q", "V", "Z"}
    assert by_name["Q"].filled == 3 and by_name["Q"].blank == 0
    assert by_name["V"].filled == 2 and by_name["V"].blank == 1
    assert by_name["Q"].percent_formatted == 3
    assert by_name["Z"].negative == 1
    assert by_name["Z"].zero == 1


def test_profile_lists_columns_carrying_k_m_b_suffixes(tmp_path: Path) -> None:
    loaded = load_company_data(_write_workbook(tmp_path / "c.xlsx", _sample_rows()))

    profile = profile_company_data(loaded)
    magnitude = {c.name: c for c in profile.magnitude_columns}

    assert magnitude["RevenueUSD2023"].suffixed == 2
    assert magnitude["RevenueUSD2023"].parsed == 2
    assert "MobileDownloads" not in magnitude


def test_load_drops_a_column_that_is_mostly_email_addresses_whatever_its_name(tmp_path: Path) -> None:
    header = ["CompanyName", "KeyPeopleInfo", "Notes"]
    rows = [
        ["A", "Ann, CEO, ann@example.com", "plain"],
        ["B", "Bo, CFO, bo@example.org", "mail me: cy@example.net"],
        ["C", "no contact here", "also plain"],
    ]
    path = _write_workbook(tmp_path / "c.xlsx", rows, header=header)

    loaded = load_company_data(path)

    assert "KeyPeopleInfo" not in loaded.frame.columns
    assert "KeyPeopleInfo" in loaded.dropped
    assert loaded.dropped_by_content == ("KeyPeopleInfo",)
    assert "Notes" in loaded.frame.columns  # 1 of 3 filled cells is below the share: kept, reported
    cells = {str(v) for v in loaded.frame.to_numpy().ravel() if v is not None}
    assert not any("@" in cell for cell in cells if cell.startswith(("Ann", "Bo")))


def test_render_lists_columns_dropped_by_content(tmp_path: Path) -> None:
    header = ["CompanyName", "KeyPeopleInfo"]
    rows = [["A", "x@y.com"], ["B", "z@y.com"]]
    loaded = load_company_data(_write_workbook(tmp_path / "c.xlsx", rows, header=header))

    text = render_profile(profile_company_data(loaded))

    assert "dropped because their cells are mostly email addresses" in text
    assert "KeyPeopleInfo" in text


def test_profile_counts_contact_like_cells_left_in_kept_columns(tmp_path: Path) -> None:
    rows = [
        _row(CompanyName="Acme", Person_Name="x@y.com", Gender=1),
        _row(CompanyName="Beta", Person_Name="Plain Name", Gender=0),
        _row(CompanyName="Gamma", Person_Name="Other Name", Gender=0),
    ]
    loaded = load_company_data(_write_workbook(tmp_path / "c.xlsx", rows))

    profile = profile_company_data(loaded)

    assert profile.contact_like_cells == {"Person_Name": 1}


def test_render_never_contains_cell_values_from_name_columns(tmp_path: Path) -> None:
    loaded = load_company_data(_write_workbook(tmp_path / "c.xlsx", _sample_rows()))

    text = render_profile(profile_company_data(loaded))

    for value in ("Ann Rao", "Bo Lee", "Cy Dunn", "Acme", "Beta", "Gamma"):
        assert value not in text


def test_with_numeric_columns_adds_parsed_companions_for_suffixed_columns_only(tmp_path: Path) -> None:
    frame = load_company_data(_write_workbook(tmp_path / "c.xlsx", _sample_rows())).frame

    result = with_numeric_columns(frame)

    numbers = result["RevenueUSD2023_num"]
    assert numbers.tolist()[:2] == [186_600_000.0, 2_500_000_000.0]
    assert pd.isna(numbers.iloc[2])  # missing stays missing (pandas stores it as NaN)
    assert "MobileDownloads_num" not in result.columns
    assert "RevenueUSD2023_num" not in frame.columns  # input is not mutated


def test_run_writes_interim_csv_and_report_without_contact_data(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    _write_workbook(raw_dir / "Company_Data.xlsx", _sample_rows())
    verify_raw(raw_dir)  # first run writes the manifest
    interim, report = tmp_path / "interim", tmp_path / "reports" / "profile.md"

    code = run(raw_dir, interim, report)

    assert code == 0
    assert (interim / "company_data.csv").exists()
    text = report.read_text(encoding="utf-8")
    assert "Company_Data profile" in text and "ann@example.com" not in text


def test_run_returns_1_when_the_workbook_is_missing(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    (raw_dir / "other.txt").write_text("x", encoding="utf-8")
    verify_raw(raw_dir)

    assert run(raw_dir, tmp_path / "i", tmp_path / "r.md") == 1


def test_load_rejects_duplicate_headers(tmp_path: Path) -> None:
    header = ["CompanyName", "Gender", "Gender"]
    path = _write_workbook(tmp_path / "c.xlsx", [["A", 1, 0]], header=header)

    with pytest.raises(ValueError, match="duplicate"):
        load_company_data(path)


def test_write_interim_writes_the_cleaned_frame_without_contact_columns(tmp_path: Path) -> None:
    loaded = load_company_data(_write_workbook(tmp_path / "c.xlsx", _sample_rows()))
    out_dir = tmp_path / "interim"

    target = write_interim(loaded.frame, out_dir)

    written = target.read_text(encoding="utf-8")
    assert target.name == "company_data.csv"
    assert "ann@example.com" not in written and "Email" not in written.splitlines()[0]
