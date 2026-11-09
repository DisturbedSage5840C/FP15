"""Tests for src.dedup_characterise: counts describing the content-different groups (synthetic text and links)."""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from src import dedup_characterise
from src.dedup_characterise import characterise, render_report, size_bucket
from src.verify_raw import ManifestMismatch

COLUMNS = ["leader", "link", "post_text"]
POST = "https://www.linkedin.com/posts/x_1"
HEAD = "word " * 45  # longer than the 200-character text key


def _rows(*rows: tuple[str, str, str]) -> pd.DataFrame:
    return pd.DataFrame(list(rows), columns=COLUMNS)


@pytest.mark.parametrize(("size", "bucket"), [(2, "2"), (3, "3"), (4, "4"), (5, "5 or more"), (40, "5 or more")])
def test_size_buckets(size: int, bucket: str) -> None:
    assert size_bucket(size) == bucket


def test_only_content_different_groups_are_counted() -> None:
    posts = _rows(
        ("Ann", POST, "Same"), ("Ann", POST, "Same"),
        ("Ann", "http://x/2", "One thing"), ("Ann", "http://x/2", "Another thing"),
    )

    result = characterise(posts)

    assert result.groups == 1
    assert result.by_link_type == {"other_domain": 1}


def test_group_sizes_link_types_and_relations_are_tallied() -> None:
    posts = _rows(
        ("Ann", POST, "Body\n12"), ("Ann", POST, "Body\n15"), ("Ann", POST, "Body\n19"),
        ("Bo", "http://x/1", "Start of post"), ("Bo", "http://x/1", "Start of post and more"),
        ("Cy", "", HEAD + " version A"),
        ("Cy", "", HEAD + " version B"),
    )

    result = characterise(posts)

    assert result.groups == 3
    assert result.by_size == {"3": 1, "2": 2}
    assert result.by_link_type == {"linkedin_post": 1, "other_domain": 1, "no_link": 1}
    assert result.by_relation == {"trailing_only": 1, "prefix": 1, "other": 1}


def test_the_report_has_counts_only() -> None:
    posts = _rows(("Ann", POST, "Body\n12"), ("Ann", POST, "Body\n15"))

    text = render_report(characterise(posts))

    assert "| trailing_only | 1 |" in text
    assert "Ann" not in text and "linkedin.com" not in text and "Body" not in text


@pytest.fixture
def workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    stacked = _rows(("Ann", POST, "Body\n12"), ("Ann", POST, "Body\n15"))
    monkeypatch.setattr(dedup_characterise, "verify_raw", lambda directory: "abc123")
    monkeypatch.setattr(dedup_characterise, "stack_records", lambda records: (stacked, []))
    monkeypatch.setattr(dedup_characterise, "_load_all", lambda directory: [])
    return tmp_path


def test_run_writes_the_report(workspace: Path) -> None:
    report = workspace / "reports" / "c.md"

    assert dedup_characterise.run(workspace / "raw", report) == 0
    assert "| Content-different groups | 1 |" in report.read_text(encoding="utf-8")


def test_run_fails_cleanly_when_the_manifest_does_not_match(workspace: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def _fail(directory: Path) -> str:
        raise ManifestMismatch("changed")

    monkeypatch.setattr(dedup_characterise, "verify_raw", _fail)
    report = workspace / "c.md"

    assert dedup_characterise.run(workspace / "raw", report) == 1
    assert not report.exists()


def test_main_returns_the_exit_code_of_run(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(dedup_characterise, "run", lambda: 0)

    assert dedup_characterise.main([]) == 0
