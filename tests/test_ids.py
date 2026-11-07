"""End-to-end tests for Step 4 (src.ids): matching tables and the counts-only report. Synthetic data."""
from __future__ import annotations

import io
import logging
import zipfile
from collections.abc import Sequence
from pathlib import Path

import pandas as pd
import pytest

from src.ids import PAIRS, run
from src.verify_raw import MANIFEST_NAME

SUMMARY_HEADER = ["Founder", "Company", "Current title"]
POST_COLUMNS = ["leader", "company", "workbook", "sheet_idx"]
ROSTER_COLUMNS = ["company", "person_name", "title", "profile_url", "person_id"]
COMPANY_COLUMNS = ["CompanyName", "Person_Name"]
NAMES = ("Ann Rao", "Bo Lee", "Cy Dunn", "Di Fox", "Acme")


def _xlsx_bytes(sheets: dict[str, Sequence[Sequence[object]]]) -> bytes:
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer) as writer:
        for name, rows in sheets.items():
            pd.DataFrame(rows).to_excel(writer, sheet_name=name, index=False, header=False)
    return buffer.getvalue()


def _write_interim(interim: Path) -> None:
    interim.mkdir(parents=True)
    pd.DataFrame(
        [["Ann Rao", "Acme", "b/w1.xlsx", "1"], ["Bo Lee", "Beta", "b/w1.xlsx", "2"], ["Cy Dunn", None, "b/w1.xlsx", "3"]],
        columns=POST_COLUMNS,
    ).to_csv(interim / "harmonised_posts.csv", index=False)
    pd.DataFrame(
        [
            ["Acme", "Ann Rao", "CEO", "u1", "1"],
            ["Beta", "Bo Lee", "CEO", "u2", "2"],
            ["Beta2", "Lee Bo", "CTO", "u3", "3"],
            ["Fox", "Di Fox", "CEO", "u4", "4"],
        ],
        columns=ROSTER_COLUMNS,
    ).to_csv(interim / "roster.csv", index=False)
    pd.DataFrame(
        [["Acme", "Ann Rao"], ["Beta", "Bo Lee"], ["Cee", "Cy Dunn"]], columns=COMPANY_COLUMNS
    ).to_csv(interim / "company_data.csv", index=False)


@pytest.fixture
def raw_dir(tmp_path: Path) -> Path:
    raw = tmp_path / "raw"
    raw.mkdir()
    summary = [SUMMARY_HEADER, ["Ann Rao", "Acme", "CEO"], ["Di Fox", "Fox", "CEO"], [None, "Zed", "CEO"]]
    with zipfile.ZipFile(raw / "posts.zip", "w") as archive:
        archive.writestr("batch/wordcount_100.xlsx", _xlsx_bytes({"Summary": summary, "Ann Rao": [["Post"], ["x"]]}))
    return raw


@pytest.fixture
def interim(tmp_path: Path) -> Path:
    _write_interim(tmp_path / "interim")
    return tmp_path / "interim"


def _go(raw: Path, interim: Path, tmp_path: Path) -> tuple[int, Path]:
    report = tmp_path / "reports" / "id_matching.md"
    return run(raw_dir=raw, interim_dir=interim, report_path=report), report


def test_run_writes_the_three_tables_and_the_report(raw_dir: Path, interim: Path, tmp_path: Path) -> None:
    code, report = _go(raw_dir, interim, tmp_path)

    assert code == 0
    for name in ("id_matches.csv", "id_ambiguous.csv", "leader_id_proposal.csv"):
        assert (interim / name).exists()
    assert report.read_text(encoding="utf-8").startswith("# ID matching")


def test_report_carries_no_names_and_no_row_refs(raw_dir: Path, interim: Path, tmp_path: Path) -> None:
    _, report = _go(raw_dir, interim, tmp_path)

    text = report.read_text(encoding="utf-8")
    for name in NAMES:
        assert name not in text
    assert "row:" not in text


def test_report_names_the_summary_workbooks_by_path_and_sheet_index(raw_dir: Path, interim: Path, tmp_path: Path) -> None:
    _, report = _go(raw_dir, interim, tmp_path)

    assert "batch/wordcount_100.xlsx" in report.read_text(encoding="utf-8")


def test_matches_table_covers_every_pair_and_holds_no_names(raw_dir: Path, interim: Path, tmp_path: Path) -> None:
    _go(raw_dir, interim, tmp_path)

    matches = pd.read_csv(interim / "id_matches.csv", dtype=str, keep_default_na=False)

    pairs = set(zip(matches["source_a"], matches["source_b"], strict=True))
    assert pairs == {(a, b) for a, b in PAIRS}
    assert set(matches["match_type"]) <= {"exact", "loose", "ambiguous", "none"}
    assert not any(name in cell for name in NAMES for cell in matches.to_numpy().ravel())


def test_sheets_to_company_matches_three_exact(raw_dir: Path, interim: Path, tmp_path: Path) -> None:
    _go(raw_dir, interim, tmp_path)

    matches = pd.read_csv(interim / "id_matches.csv", dtype=str, keep_default_na=False)
    pair = matches[(matches["source_a"] == "sheets") & (matches["source_b"] == "company")]

    assert pair["match_type"].tolist() == ["exact", "exact", "exact"]


def test_a_roster_key_shared_by_two_rows_is_listed_as_ambiguous_and_gets_no_leader_id(
    raw_dir: Path, interim: Path, tmp_path: Path
) -> None:
    _go(raw_dir, interim, tmp_path)

    ambiguous = pd.read_csv(interim / "id_ambiguous.csv", dtype=str, keep_default_na=False)
    proposal = pd.read_csv(interim / "leader_id_proposal.csv", dtype=str, keep_default_na=False)

    assert "bo lee" in set(ambiguous["key"])
    row = proposal[proposal["key"] == "bo lee"].iloc[0]
    assert row["status"] == "ambiguous" and row["leader_id"] == ""


def test_clear_keys_get_a_prefixed_leader_id(raw_dir: Path, interim: Path, tmp_path: Path) -> None:
    _go(raw_dir, interim, tmp_path)

    proposal = pd.read_csv(interim / "leader_id_proposal.csv", dtype=str, keep_default_na=False)
    row = proposal[proposal["key"] == "ann rao"].iloc[0]

    assert row["status"] == "clear" and row["leader_id"].startswith("L")
    assert {"sheets", "roster", "summaries", "company"} <= set(proposal.columns)


def test_run_returns_1_when_an_interim_input_is_missing(
    raw_dir: Path, interim: Path, tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    (interim / "roster.csv").unlink()

    with caplog.at_level(logging.ERROR):
        code, _ = _go(raw_dir, interim, tmp_path)

    assert code == 1 and "FAILED" in caplog.text


def test_run_refuses_when_the_manifest_no_longer_matches(raw_dir: Path, interim: Path, tmp_path: Path) -> None:
    _go(raw_dir, interim, tmp_path)
    (raw_dir / "posts.zip").write_bytes(b"changed")

    code, _ = _go(raw_dir, interim, tmp_path)

    assert code == 1


def test_run_leaves_the_raw_folder_unchanged(raw_dir: Path, interim: Path, tmp_path: Path) -> None:
    before = {p.name: p.read_bytes() for p in raw_dir.iterdir()}

    _go(raw_dir, interim, tmp_path)

    after = {p.name: p.read_bytes() for p in raw_dir.iterdir() if p.name != MANIFEST_NAME}
    assert after == before
