"""Tests for Step 1 (src.leader_table): the base list of leaders who have posts. Synthetic data only."""
from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd
import pytest

from src import leader_table
from src.id_matching import AMBIGUOUS, EXACT, LOOSE, NONE, Entity, leader_id_for, make_entity
from src.id_sources import SOURCE_COMPANY, SOURCE_ROSTER, SOURCE_SUMMARIES
from src.leader_table import LeaderRow, build_leader_table, render_report
from src.name_key import name_key
from src.verify_raw import ManifestMismatch

POST_COLUMNS = ["leader", "company", "workbook", "sheet_idx", "text_kind"]
NAMES = ("Ann Rao", "Bo Lee", "Cy Dunn", "Di Fox", "Ed Ng")


def _posts() -> pd.DataFrame:
    rows = [
        ["Ann Rao", "Acme", "w1.xlsx", "1", "raw"],
        ["Ann Rao", "Acme", "w1.xlsx", "1", "raw"],
        ["Bo Lee", "Beta", "w1.xlsx", "2", "raw"],
        ["Cy Dunn", "Cee", "w1.xlsx", "3", "raw"],
        ["Di Fox", "Fox", "w1.xlsx", "4", "raw"],
        ["Ed Ng", "Eden", "w1.xlsx", "5", "cleaned"],
    ]
    return pd.DataFrame(rows, columns=POST_COLUMNS)


def _entities(source: str, names: list[str]) -> tuple[Entity, ...]:
    made = [make_entity(source, f"row:{i + 1}", name) for i, name in enumerate(names)]
    return tuple(entity for entity in made if entity is not None)


def _enrichment() -> dict[str, tuple[Entity, ...]]:
    return {
        SOURCE_COMPANY: _entities(SOURCE_COMPANY, ["Ann Rao", "Cy Dunn Smith", "Di Fox", "Fox Di", "Zed Kay"]),
        SOURCE_ROSTER: _entities(SOURCE_ROSTER, ["Ann Rao", "Bo Lee", "Gil Tan"]),
        SOURCE_SUMMARIES: _entities(SOURCE_SUMMARIES, ["Bo Lee", "Hal Poe"]),
    }


def _by_key(rows: tuple[LeaderRow, ...]) -> dict[str, LeaderRow]:
    return {row.leader_id: row for row in rows}


def _row(name: str) -> LeaderRow:
    return _by_key(build_leader_table(_posts(), _enrichment()).rows)[leader_id_for(name_key(name))]


def test_base_list_is_every_distinct_leader_with_posts() -> None:
    table = build_leader_table(_posts(), _enrichment())

    assert len(table.rows) == len(NAMES)
    assert {row.leader_id for row in table.rows} == {leader_id_for(name_key(n)) for n in NAMES}


@pytest.mark.parametrize(
    ("name", "expected"),
    [("Ann Rao", EXACT), ("Cy Dunn", LOOSE), ("Di Fox", AMBIGUOUS), ("Bo Lee", NONE)],
)
def test_company_match_has_the_four_types(name: str, expected: str) -> None:
    assert _row(name).company_match == expected


def test_roster_and_summary_flags_follow_the_matches() -> None:
    assert (_row("Ann Rao").in_roster, _row("Ann Rao").in_summaries) == (True, False)
    assert (_row("Bo Lee").in_roster, _row("Bo Lee").in_summaries) == (True, True)
    assert (_row("Cy Dunn").in_roster, _row("Cy Dunn").in_summaries) == (False, False)


def test_leaders_sharing_one_sheet_reference_keep_their_own_match_types() -> None:
    shared = _posts().assign(workbook="w1.xlsx", sheet_idx="1")

    table = build_leader_table(shared, _enrichment())
    kinds = {row.leader_id: row.company_match for row in table.rows}

    assert kinds[leader_id_for(name_key("Ann Rao"))] == EXACT
    assert kinds[leader_id_for(name_key("Cy Dunn"))] == LOOSE
    assert kinds[leader_id_for(name_key("Di Fox"))] == AMBIGUOUS
    assert kinds[leader_id_for(name_key("Bo Lee"))] == NONE
    flags = {row.leader_id: row.in_roster for row in table.rows}
    assert flags[leader_id_for(name_key("Ann Rao"))] and not flags[leader_id_for(name_key("Cy Dunn"))]


def test_raw_cells_are_counted_and_cleaned_only_leader_has_zero() -> None:
    assert _row("Ann Rao").n_raw_post_cells == 2
    assert _row("Bo Lee").n_raw_post_cells == 1
    assert _row("Ed Ng").n_raw_post_cells == 0


def test_enrichment_only_names_are_counted_not_resolved() -> None:
    table = build_leader_table(_posts(), _enrichment())

    assert table.enrichment_only == {SOURCE_COMPANY: 1, SOURCE_ROSTER: 1, SOURCE_SUMMARIES: 1}


def test_a_missing_enrichment_source_means_none_and_no() -> None:
    table = build_leader_table(_posts(), {})

    assert {row.company_match for row in table.rows} == {NONE}
    assert not any(row.in_roster or row.in_summaries for row in table.rows)


def test_report_holds_counts_only() -> None:
    table = build_leader_table(_posts(), _enrichment())

    text = render_report(table, min_posts=2)

    assert "5" in text
    for name in (*NAMES, "Acme", "Zed Kay", "Gil Tan"):
        assert name not in text
    assert not any(row.leader_id in text for row in table.rows)
    assert "w1.xlsx" not in text


def test_report_counts_leaders_at_the_post_minimum_by_match_type() -> None:
    table = build_leader_table(_posts(), _enrichment())

    text = render_report(table, min_posts=1)

    assert "at least 1 raw post cell" in text


@pytest.fixture
def interim(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    folder = tmp_path / "interim"
    folder.mkdir()
    _posts().to_csv(folder / "harmonised_posts.csv", index=False)
    monkeypatch.setattr(leader_table, "verify_raw", lambda raw_dir: "ok")
    monkeypatch.setattr(leader_table, "_build_enrichment", lambda raw_dir, interim_dir: _enrichment())
    return folder


def test_run_writes_the_csv_and_the_report(interim: Path, tmp_path: Path) -> None:
    report = tmp_path / "reports" / "leader_table.md"

    code = leader_table.run(tmp_path / "raw", interim, report, min_posts=2)

    frame = pd.read_csv(interim / "leader_table.csv", dtype=str, keep_default_na=False)
    assert code == 0
    assert list(frame.columns) == ["leader_id", "company_match", "in_roster", "in_summaries", "n_raw_post_cells"]
    assert len(frame) == len(NAMES)
    assert set(frame["in_roster"]) <= {"yes", "no"}
    assert report.exists()
    csv_text = (interim / "leader_table.csv").read_text(encoding="utf-8")
    assert not any(name in csv_text for name in NAMES)


def test_run_fails_clearly_when_the_id_key_is_missing(
    interim: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.delenv("FP15_ID_KEY", raising=False)
    monkeypatch.chdir(tmp_path)

    with caplog.at_level(logging.ERROR):
        code = leader_table.run(tmp_path / "raw", interim, tmp_path / "r.md", min_posts=2)

    assert code == 1
    assert "leader-table FAILED" in caplog.text
    assert not (interim / "leader_table.csv").exists()


def test_run_fails_when_the_manifest_does_not_match(
    interim: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def _bad(raw_dir: Path) -> str:
        raise ManifestMismatch("changed")

    monkeypatch.setattr(leader_table, "verify_raw", _bad)

    assert leader_table.run(tmp_path / "raw", interim, tmp_path / "r.md", min_posts=2) == 1


def test_build_enrichment_keeps_only_the_three_enrichment_sources(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import src.ids

    everything = {"sheets": (), **_enrichment()}
    monkeypatch.setattr(src.ids, "_build_sources", lambda raw_dir, interim_dir: (everything, ()))

    found = leader_table._build_enrichment(tmp_path, tmp_path)

    assert set(found) == {SOURCE_COMPANY, SOURCE_ROSTER, SOURCE_SUMMARIES}


def test_main_returns_the_exit_code_of_run(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(leader_table, "run", lambda: 0)

    assert leader_table.main() == 0


def test_run_fails_when_the_posts_table_is_missing(interim: Path, tmp_path: Path) -> None:
    (interim / "harmonised_posts.csv").unlink()

    assert leader_table.run(tmp_path / "raw", interim, tmp_path / "r.md", min_posts=2) == 1
