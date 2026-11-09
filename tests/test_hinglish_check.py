"""Tests for src.hinglish_check: a seeded random draw of flagged cells for a human precision check (synthetic text)."""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from src import hinglish_check
from src.verify_raw import ManifestMismatch

COLUMNS = ["leader_id", "workbook", "sheet_idx", "source_row", "post_text_clean", "age_months",
           "reaction_status", "reaction_count", "language"]


def _clean(n_flagged: int) -> pd.DataFrame:
    rows = [(f"L{i}", "w.xlsx", "1", str(i), f"text {i}", "", "unverified", "", "Hinglish") for i in range(n_flagged)]
    rows.append(("Lx", "w.xlsx", "1", "99", "plain", "", "unverified", "", "English"))
    return pd.DataFrame(rows, columns=COLUMNS)


def test_only_flagged_cells_are_drawn_and_the_draw_is_repeatable() -> None:
    first = hinglish_check.draw_cells(_clean(10), n=4, seed=7)
    second = hinglish_check.draw_cells(_clean(10).iloc[::-1], n=4, seed=7)

    assert len(first) == 4
    assert "Lx" not in first["leader_id"].to_list()
    assert first["leader_id"].to_list() == second["leader_id"].to_list()


def test_fewer_flagged_cells_than_requested_gives_all_of_them() -> None:
    assert len(hinglish_check.draw_cells(_clean(2), n=5, seed=1)) == 2


def test_the_check_file_has_a_blank_column_for_the_human_and_defuses_formulas() -> None:
    clean = _clean(1).assign(post_text_clean="=1+1")

    drawn = hinglish_check.draw_cells(clean, n=1, seed=1)

    assert list(drawn.columns) == hinglish_check.CHECK_COLUMNS
    assert drawn["human_right"].iloc[0] == ""
    assert drawn["post_text"].iloc[0].startswith("'")


@pytest.fixture
def workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, Path]:
    clean = tmp_path / "posts_clean.csv"
    _clean(6).to_csv(clean, index=False)
    thresholds = tmp_path / "t.yaml"
    thresholds.write_text("hinglish_check_cells: 3\nhinglish_check_seed: 5\n", encoding="utf-8")
    monkeypatch.setattr(hinglish_check, "verify_raw", lambda directory: "abc123")
    return {"raw": tmp_path / "raw", "clean": clean, "out": tmp_path / "d" / "check.csv", "thresholds": thresholds}


def _go(ws: dict[str, Path]) -> int:
    return hinglish_check.run(ws["raw"], ws["clean"], ws["out"], ws["thresholds"])


def test_run_writes_the_file_and_never_overwrites_a_filled_one(workspace: dict[str, Path]) -> None:
    assert _go(workspace) == 0
    assert len(pd.read_csv(workspace["out"], dtype=str)) == 3
    workspace["out"].write_text("human work", encoding="utf-8")

    assert _go(workspace) == 1
    assert workspace["out"].read_text(encoding="utf-8") == "human work"


def test_run_fails_cleanly_when_the_clean_table_is_missing(workspace: dict[str, Path]) -> None:
    workspace["clean"].unlink()

    assert _go(workspace) == 1


def test_run_fails_cleanly_when_a_setting_is_missing(workspace: dict[str, Path]) -> None:
    workspace["thresholds"].write_text("hinglish_check_cells: 3\n", encoding="utf-8")

    assert _go(workspace) == 1


def test_run_fails_cleanly_when_the_raw_manifest_does_not_match(
    workspace: dict[str, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    def _fail(directory: Path) -> str:
        raise ManifestMismatch("changed")

    monkeypatch.setattr(hinglish_check, "verify_raw", _fail)

    assert _go(workspace) == 1
    assert not workspace["out"].exists()


def test_main_returns_the_exit_code_of_run(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(hinglish_check, "run", lambda: 0)

    assert hinglish_check.main([]) == 0
