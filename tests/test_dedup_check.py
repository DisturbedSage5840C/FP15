"""Tests for src.dedup_check: what the looser dedupe key collapsed, as counts (synthetic text)."""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from src import dedup_check
from src.dedup_check import classify_texts, count_collapsed, render_report
from src.verify_raw import ManifestMismatch

COLUMNS = ["leader", "link", "post_text"]


def _rows(*rows: tuple[str, str, str]) -> pd.DataFrame:
    return pd.DataFrame(list(rows), columns=COLUMNS)


@pytest.mark.parametrize(
    ("texts", "label"),
    [
        (["Same", "Same"], "identical"),
        (["Same text", "Same  text\n"], "spacing"),
        (["Same text", "same TEXT"], "case"),
        (["Same text!", "Same, text"], "punctuation"),
        (["Same text", "Other words"], "content"),
    ],
)
def test_a_group_is_labelled_by_its_largest_difference(texts: list[str], label: str) -> None:
    assert classify_texts(texts) == label


def test_counts_split_identical_from_different_text() -> None:
    posts = _rows(
        ("Ann", "", "Alpha"), ("Ann", "", "Alpha"),
        ("Ann", "http://x/2", "Beta text"), ("Ann", "http://x/2", "beta  TEXT"),
        ("Bo", "", "Solo"),
    )

    counts = count_collapsed(posts)

    assert counts.groups == 2
    assert counts.rows_collapsed == 2
    assert counts.by_label == {"identical": 1, "spacing": 0, "case": 1, "punctuation": 0, "content": 0}
    assert counts.rows_by_label["identical"] == 1


def test_link_keyed_groups_with_different_text_are_content_differences() -> None:
    posts = _rows(("Ann", "http://x/1", "First version"), ("Ann", "http://x/1", "Second, longer version"))

    counts = count_collapsed(posts)

    assert counts.by_label["content"] == 1
    assert counts.content_by_key == {"link": 1, "text_head": 0}


def test_content_groups_where_one_text_extends_the_other_are_counted() -> None:
    posts = _rows(("Ann", "http://x/1", "Start of post"), ("Ann", "http://x/1", "Start of post and more words"))

    assert count_collapsed(posts).content_extends == 1


def test_the_report_has_counts_and_no_text() -> None:
    posts = _rows(("Ann", "", "Alpha secret"), ("Ann", "", "Alpha secret"))

    text = render_report(count_collapsed(posts), rows_before=2)

    assert "| Rows collapsed by the looser key | 1 |" in text
    assert "Ann" not in text and "secret" not in text


@pytest.fixture
def workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, Path]:
    monkeypatch.setattr(dedup_check, "verify_raw", lambda directory: "abc123")
    monkeypatch.setattr(dedup_check, "_load_all", lambda directory: [])
    stacked = _rows(("Ann", "", "Alpha"), ("Ann", "", "Alpha"))
    monkeypatch.setattr(dedup_check, "stack_records", lambda records: (stacked, pd.DataFrame()))
    return {"raw": tmp_path / "raw", "report": tmp_path / "reports" / "dedup_check.md"}


def test_run_writes_the_report(workspace: dict[str, Path]) -> None:
    assert dedup_check.run(workspace["raw"], workspace["report"]) == 0
    assert "| identical | 1 | 1 |" in workspace["report"].read_text(encoding="utf-8")


def test_run_fails_cleanly_when_the_raw_manifest_does_not_match(
    workspace: dict[str, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    def _fail(directory: Path) -> str:
        raise ManifestMismatch("changed")

    monkeypatch.setattr(dedup_check, "verify_raw", _fail)

    assert dedup_check.run(workspace["raw"], workspace["report"]) == 1
    assert not workspace["report"].exists()


def test_main_returns_the_exit_code_of_run(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(dedup_check, "run", lambda: 0)

    assert dedup_check.main([]) == 0
