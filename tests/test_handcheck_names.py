"""Tests for Step 2 (src.handcheck_names): hand-check file for ambiguous, unmatched and mismatched leaders."""
from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd
import pytest

from src import handcheck_names
from src.handcheck_names import (
    CASE_AMBIGUOUS,
    CASE_COMPANY_DIFFERS,
    CASE_NO_MATCH,
    MAX_NEAR_CANDIDATES,
    HandcheckRow,
    build_handcheck,
    handcheck_frame,
)
from src.id_matching import leader_id_for
from src.name_key import name_key
from src.verify_raw import ManifestMismatch

POST_COLUMNS = ["leader", "company", "workbook", "sheet_idx", "text_kind"]
COMPANY_COLUMNS = ["Person_Name", "CompanyName", "Current_Title"]


def _posts(*leaders: tuple[str, str]) -> pd.DataFrame:
    """One raw cell per leader, all on one shared sheet reference (as in the real workbooks)."""
    rows = [[name, firm, "w1.xlsx", "1", "raw"] for name, firm in leaders]
    return pd.DataFrame(rows, columns=POST_COLUMNS)


def _company(*people: tuple[str, str, str]) -> pd.DataFrame:
    return pd.DataFrame(list(people), columns=COMPANY_COLUMNS)


def _rows_for(rows: tuple[HandcheckRow, ...], name: str) -> list[HandcheckRow]:
    return [row for row in rows if row.sheet_name == name]


def test_an_ambiguous_leader_lists_every_candidate_row() -> None:
    posts = _posts(("Di Fox", "Fox Ltd"))
    company = _company(("Di Fox", "Fox Ltd", "CEO"), ("Fox Di", "Other Co", "Chair"))

    rows = _rows_for(build_handcheck(posts, company), "Di Fox")

    assert {row.case for row in rows} == {CASE_AMBIGUOUS}
    assert sorted(row.company_row for row in rows) == ["row:1", "row:2"]
    assert {row.n_candidates for row in rows} == {2}
    assert {row.candidate_basis for row in rows} == {"ambiguous_match"}


def test_an_unmatched_leader_gets_near_candidates_ranked_by_shared_tokens() -> None:
    posts = _posts(("Ann Rao Lee", "Acme"))
    company = _company(
        ("Zed Kay", "Other", "CEO"),
        ("Rao Kay", "Other", "CEO"),
        ("Lee Rao Pat", "Other", "CEO"),
    )

    rows = _rows_for(build_handcheck(posts, company), "Ann Rao Lee")

    assert {row.case for row in rows} == {CASE_NO_MATCH}
    assert [row.company_row for row in rows] == ["row:3", "row:2"]
    assert [row.candidate_rank for row in rows] == [1, 2]
    assert rows[0].candidate_basis == "shared_name_tokens"


def test_a_company_row_with_the_same_firm_is_a_candidate_even_without_a_shared_name() -> None:
    posts = _posts(("Ann Rao", "Acme Ltd"))
    company = _company(("Zed Kay", "ACME  Ltd.", "CEO"))

    rows = build_handcheck(posts, company)

    assert [(row.company_row, row.candidate_basis) for row in rows] == [("row:1", "same_company")]


def test_an_unmatched_leader_with_no_candidate_still_gets_one_row() -> None:
    posts = _posts(("Ann Rao", "Acme"))
    company = _company(("Zed Kay", "Other", "CEO"))

    rows = build_handcheck(posts, company)

    assert len(rows) == 1
    assert (rows[0].case, rows[0].company_row, rows[0].n_candidates) == (CASE_NO_MATCH, "", 0)


def test_near_candidates_are_capped() -> None:
    posts = _posts(("Ann Rao", "Acme"))
    company = _company(*[(f"Ann P{i}", f"F{i}", "CEO") for i in range(MAX_NEAR_CANDIDATES + 4)])

    rows = build_handcheck(posts, company)

    assert len(rows) == MAX_NEAR_CANDIDATES


def test_an_exact_match_whose_company_differs_is_listed_with_its_one_candidate() -> None:
    posts = _posts(("Ann Rao", "Acme"), ("Bo Lee", "Beta"), ("Cy Dunn", "Cee"))
    company = _company(
        ("Ann Rao", "Different Co", "CEO"),  # company differs
        ("Bo Lee", "Beta", "CEO"),  # company agrees
        ("Cy Dunn", "", "CEO"),  # company unknown
    )

    rows = build_handcheck(posts, company)

    assert [(row.sheet_name, row.case, row.company_row) for row in rows] == [
        ("Ann Rao", CASE_COMPANY_DIFFERS, "row:1")
    ]
    assert rows[0].company_firm == "Different Co"
    assert rows[0].sheet_company == "Acme"


def test_leaders_sharing_a_sheet_reference_each_get_their_own_case() -> None:
    posts = _posts(("Di Fox", "Fox"), ("Bo Lee", "Beta"), ("Ann Rao", "Acme"))
    company = _company(("Di Fox", "Fox", "x"), ("Fox Di", "Fox", "x"), ("Ann Rao", "Acme", "x"))

    cases = {row.sheet_name: row.case for row in build_handcheck(posts, company)}

    assert cases == {"Di Fox": CASE_AMBIGUOUS, "Bo Lee": CASE_NO_MATCH}


def test_every_row_carries_the_keyed_leader_id_and_empty_human_columns() -> None:
    posts = _posts(("Di Fox", "Fox"))
    company = _company(("Di Fox", "Fox", "x"), ("Fox Di", "Fox", "x"))

    frame = handcheck_frame(build_handcheck(posts, company))

    assert set(frame["leader_id"]) == {leader_id_for(name_key("Di Fox"))}
    assert set(frame["human_decision"]) == {""}
    assert set(frame["human_note"]) == {""}


def test_the_frame_defuses_spreadsheet_formulas() -> None:
    posts = _posts(("=cmd Fox", "Fox"))
    company = _company(("=cmd Fox", "Fox", "x"), ("Fox cmd", "+Firm", "x"))

    frame = handcheck_frame(build_handcheck(posts, company))

    assert not any(str(value).startswith(("=", "+", "-", "@")) for value in frame.to_numpy().ravel())


@pytest.fixture
def interim(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    folder = tmp_path / "interim"
    folder.mkdir()
    _posts(("Di Fox", "Fox"), ("Bo Lee", "Beta")).to_csv(folder / "harmonised_posts.csv", index=False)
    _company(("Di Fox", "Fox", "x"), ("Fox Di", "Fox", "x")).to_csv(folder / "company_data.csv", index=False)
    monkeypatch.setattr(handcheck_names, "verify_raw", lambda raw_dir: "ok")
    return folder


def test_run_writes_the_file_and_logs_counts_only(
    interim: Path, tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    out = tmp_path / "derived"

    with caplog.at_level(logging.INFO):
        code = handcheck_names.run(tmp_path / "raw", interim, out)

    frame = pd.read_csv(out / "handcheck_names.csv", dtype=str, keep_default_na=False)
    assert code == 0
    assert set(frame["case"]) == {CASE_AMBIGUOUS, CASE_NO_MATCH}
    assert "Di Fox" not in caplog.text and "Bo Lee" not in caplog.text


def test_run_fails_when_the_manifest_does_not_match(
    interim: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def _bad(raw_dir: Path) -> str:
        raise ManifestMismatch("changed")

    monkeypatch.setattr(handcheck_names, "verify_raw", _bad)

    assert handcheck_names.run(tmp_path / "raw", interim, tmp_path / "derived") == 1


def test_run_fails_clearly_when_the_id_key_is_missing(
    interim: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("FP15_ID_KEY", raising=False)
    monkeypatch.chdir(tmp_path)

    assert handcheck_names.run(tmp_path / "raw", interim, tmp_path / "derived") == 1
    assert not (tmp_path / "derived" / "handcheck_names.csv").exists()


def test_run_fails_when_company_data_is_missing(interim: Path, tmp_path: Path) -> None:
    (interim / "company_data.csv").unlink()

    assert handcheck_names.run(tmp_path / "raw", interim, tmp_path / "derived") == 1


def test_main_returns_the_exit_code_of_run(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(handcheck_names, "run", lambda: 0)

    assert handcheck_names.main() == 0
