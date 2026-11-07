"""Tests for Step C (src.company_columns): which Company_Data columns are filled for the leaders who
have enough posts. Synthetic data only. The report holds column headers, counts and shares; it never
holds leader names, company names or cell values.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from src.company_columns import (
    CANDIDATES,
    PER_VARIABLE_CAP,
    Candidate,
    ColumnFill,
    ColumnSettings,
    fill_rows,
    find_eligible,
    leader_post_counts,
    load_settings,
    run,
    select_top,
)
from src.name_key import name_key

POST_COLUMNS = ["leader", "workbook", "sheet_idx", "source_row", "post_text", "text_kind"]
PROPOSAL_COLUMNS = ["leader_id", "key", "status", "sheets", "roster", "summaries", "company"]


# ---- settings ---------------------------------------------------------------------------------


def test_load_settings_reads_both_keys(tmp_path: Path) -> None:
    path = tmp_path / "t.yaml"
    path.write_text("min_posts_per_leader: 7\ncompany_columns_top_n: 3\n", encoding="utf-8")

    assert load_settings(path) == ColumnSettings(min_posts=7, top_n=3)


def test_load_settings_names_the_missing_key(tmp_path: Path) -> None:
    path = tmp_path / "t.yaml"
    path.write_text("min_posts_per_leader: 7\n", encoding="utf-8")

    with pytest.raises(ValueError, match="company_columns_top_n"):
        load_settings(path)


def test_real_thresholds_file_gives_fifteen_posts_and_twenty_columns() -> None:
    assert load_settings(Path("configs/thresholds.yaml")) == ColumnSettings(min_posts=15, top_n=20)


# ---- posts per leader -------------------------------------------------------------------------


def _posts(rows: list[tuple[str, str]]) -> pd.DataFrame:
    return pd.DataFrame(
        [[leader, "b/w.xlsx", 1, n + 1, f"t{n}", kind] for n, (leader, kind) in enumerate(rows)],
        columns=POST_COLUMNS,
    )


def test_post_counts_use_raw_cells_only_and_group_name_variants() -> None:
    posts = _posts([("Ann Rao", "raw"), ("Rao Ann", "raw"), ("Ann Rao", "cleaned"), ("Bo Lee", "raw")])

    counts = leader_post_counts(posts)

    assert counts == {name_key("Ann Rao"): 2, name_key("Bo Lee"): 1}


def test_post_counts_skip_cells_without_a_leader() -> None:
    assert leader_post_counts(_posts([("", "raw"), ("  ", "raw")])) == {}


# ---- eligibility ------------------------------------------------------------------------------


def _proposal(rows: list[tuple[str, str, str]]) -> pd.DataFrame:
    """Rows are (name, status, company ref)."""
    return pd.DataFrame(
        [[f"L{n}", name_key(name), status, "", "", "", company] for n, (name, status, company) in enumerate(rows)],
        columns=PROPOSAL_COLUMNS,
    )


def test_threshold_is_inclusive_and_clear_matches_give_company_positions() -> None:
    counts = {name_key("Ann Rao"): 15, name_key("Bo Lee"): 14}
    proposal = _proposal([("Ann Rao", "clear", "row:3"), ("Bo Lee", "clear", "row:1")])

    result = find_eligible(counts, proposal, min_posts=15)

    assert (result.leaders_with_posts, result.eligible) == (2, 1)
    assert result.matched_positions == (2,)


def test_ambiguous_leaders_are_counted_not_resolved() -> None:
    counts = {name_key("Cy Dunn"): 20}
    proposal = _proposal([("Cy Dunn", "ambiguous", "row:2")])

    result = find_eligible(counts, proposal, min_posts=15)

    assert (result.eligible, result.ambiguous, result.matched_positions) == (1, 1, ())


def test_clear_leader_without_a_company_row_is_counted_apart() -> None:
    counts = {name_key("Di Fox"): 16}

    result = find_eligible(counts, _proposal([("Di Fox", "clear", "")]), min_posts=15)

    assert (result.no_company, result.matched_positions) == (1, ())


def test_leader_missing_from_the_proposal_is_counted_apart() -> None:
    counts = {name_key("Ed Gray"): 30}

    result = find_eligible(counts, _proposal([("Someone Else", "clear", "row:1")]), min_posts=15)

    assert (result.eligible, result.not_in_proposal) == (1, 1)


# ---- fill shares ------------------------------------------------------------------------------


def _company(rows: list[dict[str, str]]) -> pd.DataFrame:
    return pd.DataFrame(rows, dtype=str)


def test_fill_counts_blank_dot_and_dash_as_not_filled() -> None:
    company = _company([{"Gender": "1"}, {"Gender": ""}, {"Gender": "."}, {"Gender": "-"}])

    fill = fill_rows(company, (0, 1, 2, 3), (Candidate("Gender", "gender"),))[0]

    assert (fill.filled, fill.total, fill.present) == (1, 4, True)


def test_fill_only_looks_at_the_given_row_positions() -> None:
    company = _company([{"Gender": "1"}, {"Gender": ""}, {"Gender": "0"}])

    fill = fill_rows(company, (1, 2), (Candidate("Gender", "gender"),))[0]

    assert (fill.filled, fill.total) == (1, 2)


def test_numeric_columns_also_count_cells_that_read_as_numbers() -> None:
    company = _company([{"Rev": "186.6M"}, {"Rev": "2.5B"}, {"Rev": "about a lot"}, {"Rev": ""}])

    fill = fill_rows(company, (0, 1, 2, 3), (Candidate("Rev", "firm size", numeric=True),))[0]

    assert (fill.filled, fill.parsed) == (3, 2)


def test_a_candidate_missing_from_the_file_is_marked_absent() -> None:
    fill = fill_rows(_company([{"Gender": "1"}]), (0,), (Candidate("Nope", "gender"),))[0]

    assert (fill.present, fill.filled) == (False, 0)


def test_share_is_zero_when_no_leader_is_matched() -> None:
    fill = fill_rows(_company([{"Gender": "1"}]), (), (Candidate("Gender", "gender"),))[0]

    assert fill.share == 0.0


# ---- selection --------------------------------------------------------------------------------


def _fill(column: str, variable: str, filled: int, total: int = 10, present: bool = True) -> ColumnFill:
    return ColumnFill(column, variable, False, present, filled, 0, total)


def test_select_top_ranks_by_share_then_keeps_candidate_order_for_ties() -> None:
    fills = [_fill("A", "v1", 5), _fill("B", "v2", 9), _fill("C", "v3", 5)]

    assert [item.column for item in select_top(fills, top_n=3)] == ["B", "A", "C"]


def test_select_top_caps_columns_per_study_variable() -> None:
    fills = [_fill(f"C{n}", "firm size", 10 - n) for n in range(5)] + [_fill("G", "gender", 1)]

    chosen = [item.column for item in select_top(fills, top_n=10)]

    assert chosen == ["C0", "C1", "G"][: PER_VARIABLE_CAP + 1]
    assert sum(1 for item in chosen if item.startswith("C")) == PER_VARIABLE_CAP


def test_select_top_stops_at_top_n_and_skips_absent_columns() -> None:
    fills = [_fill("A", "v1", 9, present=False), _fill("B", "v2", 8), _fill("C", "v3", 7)]

    assert [item.column for item in select_top(fills, top_n=1)] == ["B"]


def test_the_candidate_list_has_no_repeats_and_names_a_study_variable_for_each() -> None:
    columns = [item.column for item in CANDIDATES]

    assert len(columns) == len(set(columns))
    assert all(item.variable for item in CANDIDATES)


# ---- end to end -------------------------------------------------------------------------------

LEADER_CELLS = {"Ann Rao": 15, "Bo Lee": 14, "Cy Dunn": 20, "Di Fox": 16, "Ed Gray": 15}


@pytest.fixture
def workspace(tmp_path: Path) -> dict[str, Path]:
    raw = tmp_path / "raw"
    raw.mkdir()
    (raw / "dummy.bin").write_bytes(b"x")
    interim = tmp_path / "interim"
    interim.mkdir()
    rows = [(leader, "raw") for leader, count in LEADER_CELLS.items() for _ in range(count)]
    _posts(rows).to_csv(interim / "harmonised_posts.csv", index=False)
    _proposal(
        [
            ("Ann Rao", "clear", "row:1"),
            ("Bo Lee", "clear", "row:3"),
            ("Cy Dunn", "ambiguous", "row:3"),
            ("Di Fox", "clear", ""),
            ("Ed Gray", "clear", "row:2"),
        ]
    ).to_csv(interim / "leader_id_proposal.csv", index=False)
    _company(
        [
            {"CompanyName": "Acme Holdings", "Person_Name": "Ann Rao", "Gender": "1", "RevenueUSD2024": "186.6M"},
            {"CompanyName": "Zed Works", "Person_Name": "Ed Gray", "Gender": "", "RevenueUSD2024": "n/a"},
            {"CompanyName": "Other Co", "Person_Name": "Bo Lee", "Gender": "0", "RevenueUSD2024": "2.5B"},
        ]
    ).to_csv(interim / "company_data.csv", index=False)
    return {"raw": raw, "interim": interim, "report": tmp_path / "reports" / "company_columns.md"}


def _go(workspace: dict[str, Path]) -> int:
    return run(
        raw_dir=workspace["raw"],
        interim_dir=workspace["interim"],
        report_path=workspace["report"],
        settings=ColumnSettings(min_posts=15, top_n=20),
    )


def _report(workspace: dict[str, Path]) -> str:
    return workspace["report"].read_text(encoding="utf-8")


def test_run_writes_a_report_with_every_section(workspace: dict[str, Path]) -> None:
    assert _go(workspace) == 0

    report = _report(workspace)
    for heading in (
        "# Company_Data columns for the leader and firm analysis",
        "## Who is counted",
        "## The 20 columns proposed",
        "## Other candidate columns considered",
        "## Needs a human decision",
    ):
        assert heading in report


def test_run_counts_who_is_in_and_who_is_left_out(workspace: dict[str, Path]) -> None:
    _go(workspace)

    report = _report(workspace)
    for line in (
        "| Leaders with at least one raw post cell | 5 |",
        "| Leaders with 15 or more raw post cells | 4 |",
        "| Matched to exactly one Company_Data row | 2 |",
        "| Left out: ambiguous name match, not resolved | 1 |",
        "| Left out: clear match but no Company_Data row | 1 |",
    ):
        assert line in report


def test_run_reports_fill_shares_for_the_matched_leaders(workspace: dict[str, Path]) -> None:
    _go(workspace)

    report = _report(workspace)
    assert "| Gender | gender | 1 of 2 | 50.0% | n/a |" in report
    assert "| RevenueUSD2024 | firm size | 2 of 2 | 100.0% | 1 of 2 |" in report


def test_report_never_holds_names_companies_or_cell_values(workspace: dict[str, Path]) -> None:
    _go(workspace)

    report = _report(workspace)
    for forbidden in ("Ann Rao", "Ed Gray", "Bo Lee", "Acme", "Zed Works", "186.6M", "2.5B"):
        assert forbidden not in report


def test_report_states_the_claim_limit_the_cell_level_caveat_and_the_gender_rule(
    workspace: dict[str, Path],
) -> None:
    _go(workspace)

    report = _report(workspace)
    assert "image projected in public posts" in report
    assert "cell-level" in report
    assert "as coded in the file" in report


def test_run_is_deterministic(workspace: dict[str, Path]) -> None:
    _go(workspace)
    first = _report(workspace)
    workspace["report"].unlink()
    _go(workspace)

    assert _report(workspace) == first


@pytest.mark.parametrize("missing", ["harmonised_posts.csv", "leader_id_proposal.csv", "company_data.csv"])
def test_run_fails_cleanly_when_an_input_table_is_missing(workspace: dict[str, Path], missing: str) -> None:
    (workspace["interim"] / missing).unlink()

    assert _go(workspace) == 1
    assert not workspace["report"].exists()


def test_run_fails_cleanly_when_the_proposal_lacks_a_needed_column(workspace: dict[str, Path]) -> None:
    path = workspace["interim"] / "leader_id_proposal.csv"
    pd.read_csv(path, dtype=str).drop(columns=["company"]).to_csv(path, index=False)

    assert _go(workspace) == 1
    assert not workspace["report"].exists()


def test_run_fails_cleanly_when_the_raw_manifest_does_not_match(workspace: dict[str, Path]) -> None:
    _go(workspace)
    (workspace["raw"] / "dummy.bin").write_bytes(b"changed")
    workspace["report"].unlink()

    assert _go(workspace) == 1
    assert not workspace["report"].exists()
