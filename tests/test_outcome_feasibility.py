"""Tests for the outcome feasibility report (`make outcome-feasibility`). Every table here is invented."""
from __future__ import annotations

import re
from pathlib import Path

import pandas as pd
import pytest

from src import outcome_feasibility
from src.eda_common import SMALL, EdaSettings
from src.outcome_feasibility import (
    FILL_COLUMNS,
    NO_SECTOR,
    OTHER_GROUPS,
    SECTOR_COLUMN,
    Analysis,
    analyse,
    build_populations,
    filled_flags,
    measure_flags,
    primary_group,
    render_report,
    sector_table,
)
from src.thresholds import load_threshold
from src.verify_raw import ManifestMismatch

MIN_POSTS = int(load_threshold("min_posts_per_leader"))
DISCLOSURE_MIN = int(load_threshold("eda_disclosure_min_leaders"))
SETTINGS = EdaSettings(min_posts=MIN_POSTS, disclosure_min=DISCLOSURE_MIN, model_min=20, size_bands=4)
SENTINEL_VALUE = "98765"  # a cell value that must never appear in any report
LEADER_ID = re.compile(r"\bL[0-9a-f]{10}\b")
PROFIT, EBITDA = "ProfitUSD2024", "EBITDAUSD2024"
REV_2024, REV_2023 = "RevenueUSD2024", "RevenueUSD2023"
HEADERS_WITHOUT_BALANCE_SHEET = (*FILL_COLUMNS, SECTOR_COLUMN, "StockTicker")


def _company(*rows: dict[str, str]) -> pd.DataFrame:
    """One Company_Data-shaped row per dict; every header not given is blank."""
    blank = {column: "" for column in (*FILL_COLUMNS, SECTOR_COLUMN)}
    return pd.DataFrame([{**blank, **row} for row in rows], dtype=str)


def _leaders(*rows: tuple[str, str, int]) -> pd.DataFrame:
    return pd.DataFrame(rows, columns=["leader_id", "company_match", "n_raw_post_cells"])


def _proposal(*rows: tuple[str, str, str]) -> pd.DataFrame:
    return pd.DataFrame(rows, columns=["leader_id", "status", "company"])


# ---- fills ----------------------------------------------------------------------------------


def test_blank_and_marker_cells_are_not_filled() -> None:
    company = _company({PROFIT: "5M"}, {PROFIT: "."}, {PROFIT: "-"}, {PROFIT: ""})

    flags = filled_flags(company)

    assert flags[PROFIT].tolist() == [True, False, False, False]


def test_annual_columns_count_as_filled_even_though_they_are_not_parsed() -> None:
    company = _company({"AnnualNetProfitUSD": "1,234 (USD 2024, Mn)"})

    assert filled_flags(company)["AnnualNetProfitUSD"].tolist() == [True]


def test_a_missing_header_counts_as_nothing_filled() -> None:
    company = _company({PROFIT: "5M"}).drop(columns=[EBITDA])

    assert filled_flags(company)[EBITDA].tolist() == [False]


# ---- measures -------------------------------------------------------------------------------


def test_a_margin_needs_both_cells_read_and_a_positive_revenue() -> None:
    company = _company(
        {PROFIT: "5M", REV_2024: "50M"},  # usable
        {PROFIT: "5M", REV_2024: ""},  # no revenue
        {PROFIT: "", REV_2024: "50M"},  # no profit
        {PROFIT: "5M", REV_2024: "0"},  # zero revenue: a margin is undefined
    )

    flags = measure_flags(company)

    assert flags["Profit margin, 2024"].tolist() == [True, False, False, False]


def test_a_bare_number_cell_blocks_a_ratio_because_its_scale_is_not_stated() -> None:
    company = _company({PROFIT: "1234", REV_2024: "50M"}, {PROFIT: "5M", REV_2024: "5000"})

    assert measure_flags(company)["Profit margin, 2024"].tolist() == [False, False]


def test_revenue_growth_compares_2024_with_a_positive_2023_base() -> None:
    company = _company({REV_2024: "60M", REV_2023: "50M"}, {REV_2024: "60M", REV_2023: "0"}, {REV_2024: "60M"})

    assert measure_flags(company)["Revenue growth, 2023 to 2024"].tolist() == [True, False, False]


def test_given_growth_columns_count_when_the_cell_reads_as_a_number() -> None:
    company = _company({"RevenueCAGR3Year": "12.5%"}, {"RevenueCAGR3Year": "n/a"}, {"RevenueCAGR3Year": ""})

    assert measure_flags(company)["Revenue CAGR, 3 years"].tolist() == [True, False, False]


def test_no_measure_is_built_from_the_annual_columns() -> None:
    company = _company({"AnnualNetProfitUSD": "1,234 (USD 2024, Mn)", "AnnualRevenueUSD": "5,000 (USD 2024, Mn)"})

    assert not measure_flags(company).any().any()


# ---- who is counted -------------------------------------------------------------------------


def test_populations_keep_leaders_with_a_clear_company_row_and_enough_posts() -> None:
    leaders = _leaders(
        ("La", "exact", MIN_POSTS),
        ("Lb", "exact", MIN_POSTS - 1),
        ("Lc", "exact", 1),
        ("Ld", "exact", 0),
    )
    proposal = _proposal(("La", "clear", "row:3"), ("Lb", "clear", "row:1"), ("Lc", "clear", "row:2"))

    at_minimum, with_posts = build_populations(leaders, proposal, MIN_POSTS)

    assert at_minimum.positions == (2,)  # row:3 is the third row, position 2
    assert with_posts.positions == (2, 0, 1)
    assert (at_minimum.leaders, with_posts.leaders) == (1, 3)


def test_a_leader_without_a_clear_company_row_is_counted_as_unmatched_not_guessed() -> None:
    leaders = _leaders(
        ("La", "exact", MIN_POSTS),
        ("Lb", "ambiguous", MIN_POSTS),
        ("Lc", "none", MIN_POSTS),
        ("Ld", "exact", MIN_POSTS),
    )
    proposal = _proposal(("La", "clear", ""), ("Lb", "ambiguous", "row:2"), ("Ld", "clear", "row:4"))

    at_minimum, _ = build_populations(leaders, proposal, MIN_POSTS)

    assert at_minimum.positions == (3,)
    assert at_minimum.leaders == 4
    assert at_minimum.unmatched == 3
    assert at_minimum.unmatched_by_match == {"ambiguous": 1, "exact": 1, "none": 1}


def test_two_leaders_at_one_firm_are_both_counted() -> None:
    leaders = _leaders(("La", "exact", MIN_POSTS), ("Lb", "exact", MIN_POSTS))
    proposal = _proposal(("La", "clear", "row:1"), ("Lb", "clear", "row:1"))

    at_minimum, _ = build_populations(leaders, proposal, MIN_POSTS)

    assert at_minimum.positions == (0, 0)


def test_several_blank_ids_in_the_proposal_are_ignored_because_a_blank_id_never_joins() -> None:
    leaders = _leaders(("La", "exact", MIN_POSTS), ("Lb", "none", MIN_POSTS))
    proposal = _proposal(("La", "clear", "row:1"), ("", "ambiguous", ""), ("", "ambiguous", ""))

    at_minimum, _ = build_populations(leaders, proposal, MIN_POSTS)

    assert at_minimum.positions == (0,)
    assert at_minimum.unmatched == 1


def test_a_repeated_non_blank_id_in_the_proposal_is_refused() -> None:
    leaders = _leaders(("La", "exact", MIN_POSTS))
    proposal = _proposal(("La", "clear", "row:1"), ("La", "clear", "row:2"))

    with pytest.raises(ValueError, match="more than once"):
        build_populations(leaders, proposal, MIN_POSTS)


# ---- sector ---------------------------------------------------------------------------------


def test_primary_sector_is_the_group_of_the_first_listed_label() -> None:
    cell = "Financial Services > Banks,\nFinTech > Payments"

    assert primary_group(cell) == "Financial Services"


def test_a_comma_inside_a_group_name_is_not_a_separator() -> None:
    assert primary_group("Aerospace, Maritime and Defense > Defense Primes") == "Aerospace, Maritime and Defense"


@pytest.mark.parametrize("cell", ["", ".", "-"])
def test_blank_sector_cells_have_no_group(cell: str) -> None:
    assert primary_group(cell) is None


def _sector_inputs(sizes: dict[str, int]) -> tuple[pd.Series, pd.DataFrame, tuple[int, ...]]:
    """One company row per leader: `sizes` leaders per group, every leader with a usable profit margin."""
    cells = [f"{group} > Sub" for group, count in sizes.items() for _ in range(count)]
    company = _company(*({SECTOR_COLUMN: cell, PROFIT: "5M", REV_2024: "50M"} for cell in cells))
    groups = company[SECTOR_COLUMN].map(primary_group)
    return groups, measure_flags(company), tuple(range(len(cells)))


def test_groups_under_the_disclosure_minimum_are_pooled_and_never_named() -> None:
    groups, flags, positions = _sector_inputs({"Big": 12, "Small": 2, "Tiny": 1})

    table = sector_table(groups, flags, positions, SETTINGS)

    labels = [row[0] for row in table]
    assert "Big" in labels
    assert "Small" not in labels and "Tiny" not in labels
    assert OTHER_GROUPS in labels


def test_a_measure_cell_under_the_disclosure_minimum_is_hidden() -> None:
    company = _company(
        *({SECTOR_COLUMN: "Big > Sub", PROFIT: "5M" if index < 2 else "", REV_2024: "50M"} for index in range(12))
    )
    groups = company[SECTOR_COLUMN].map(primary_group)

    table = sector_table(groups, measure_flags(company), tuple(range(12)), SETTINGS)

    big = next(row for row in table if row[0] == "Big")
    assert big[1] == "12"
    assert SMALL in big[2:]  # only two leaders have a profit margin


def test_a_leader_whose_firm_lists_no_sector_has_its_own_row() -> None:
    company = _company({SECTOR_COLUMN: "", PROFIT: "5M", REV_2024: "50M"})
    groups = company[SECTOR_COLUMN].map(primary_group)

    table = sector_table(groups, measure_flags(company), (0,), SETTINGS)

    assert NO_SECTOR in [row[0] for row in table]


# ---- the report -----------------------------------------------------------------------------


def _analysis() -> Analysis:
    company = _company(
        *({SECTOR_COLUMN: "Retail > Stores", PROFIT: SENTINEL_VALUE + "M", REV_2024: "50M"} for _ in range(8))
    )
    leaders = _leaders(*((f"L{index:010x}", "exact", MIN_POSTS + 1) for index in range(8)))
    proposal = _proposal(*((f"L{index:010x}", "clear", f"row:{index + 1}") for index in range(8)))
    return analyse(company, leaders, proposal, SETTINGS, HEADERS_WITHOUT_BALANCE_SHEET)


def test_report_lists_the_columns_roa_and_tobins_q_need_and_says_they_are_not_in_the_file() -> None:
    report = render_report(_analysis())

    for need in ("Total assets", "Book equity", "Total debt", "Market value of equity"):
        assert need in report
    assert "Not in the file" in report


def test_report_flags_a_similarly_named_header_without_accepting_it() -> None:
    headers = (*HEADERS_WITHOUT_BALANCE_SHEET, "MarketCapitalatIPOUSD", "LatestValuationUSD")
    analysis = analyse(_company({PROFIT: "5M"}), _leaders(), _proposal(), SETTINGS, headers)

    report = render_report(analysis)

    assert "MarketCapitalatIPOUSD" in report and "LatestValuationUSD" in report
    assert "not accepted" in report.lower()


def test_report_has_the_four_caveats() -> None:
    report = render_report(_analysis()).lower()

    assert "firm performance is not leader success" in report
    assert "role_start_year" in report
    assert "movers" in report
    assert "reverse causation" in report


def test_report_holds_counts_only_no_values_or_ids_and_never_says_personality() -> None:
    report = render_report(_analysis())

    assert SENTINEL_VALUE not in report
    assert not LEADER_ID.search(report)
    assert "personality" not in report.lower()
    assert "http" not in report


def test_report_shows_no_hidden_small_cell_number() -> None:
    company = _company(*({SECTOR_COLUMN: "Tiny > Sub", PROFIT: "5M", REV_2024: "50M"} for _ in range(2)))
    leaders = _leaders(("La", "exact", MIN_POSTS), ("Lb", "exact", MIN_POSTS))
    proposal = _proposal(("La", "clear", "row:1"), ("Lb", "clear", "row:2"))

    report = render_report(analyse(company, leaders, proposal, SETTINGS, HEADERS_WITHOUT_BALANCE_SHEET))

    assert "Tiny" not in report


# ---- entry points ---------------------------------------------------------------------------


@pytest.fixture
def interim(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    folder = tmp_path / "interim"
    folder.mkdir()
    _company({SECTOR_COLUMN: "Retail > Stores", PROFIT: "5M", REV_2024: "50M"}).to_csv(
        folder / "company_data.csv", index=False
    )
    _leaders(("La", "exact", MIN_POSTS)).to_csv(folder / "leader_table.csv", index=False)
    _proposal(("La", "clear", "row:1")).to_csv(folder / "leader_id_proposal.csv", index=False)
    monkeypatch.setattr(outcome_feasibility, "verify_raw", lambda _raw_dir: "ok")
    return folder


def test_run_writes_a_counts_only_report(interim: Path, tmp_path: Path) -> None:
    report = tmp_path / "reports" / "outcome_feasibility.md"

    code = outcome_feasibility.run(tmp_path / "raw", interim, report)

    assert code == 0
    assert report.read_text(encoding="utf-8").startswith("# ")


def test_run_fails_when_the_manifest_does_not_match(
    interim: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def _bad(_raw_dir: Path) -> str:
        raise ManifestMismatch("changed")

    monkeypatch.setattr(outcome_feasibility, "verify_raw", _bad)

    assert outcome_feasibility.run(tmp_path / "raw", interim, tmp_path / "r.md") == 1


def test_run_fails_when_an_input_file_is_missing(interim: Path, tmp_path: Path) -> None:
    (interim / "leader_id_proposal.csv").unlink()

    assert outcome_feasibility.run(tmp_path / "raw", interim, tmp_path / "r.md") == 1


def test_run_fails_when_a_proposal_row_points_past_the_end_of_company_data(interim: Path, tmp_path: Path) -> None:
    _proposal(("La", "clear", "row:99")).to_csv(interim / "leader_id_proposal.csv", index=False)

    assert outcome_feasibility.run(tmp_path / "raw", interim, tmp_path / "r.md") == 1


def test_main_returns_the_exit_code_of_run(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(outcome_feasibility, "run", lambda: 0)

    assert outcome_feasibility.main() == 0
