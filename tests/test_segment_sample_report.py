"""Tests for src.segment_sample_report: a counts-only report on the G1 sample, with no machine count in it."""
from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd
import pytest

from src import segment_sample_report
from src.segment import SegmentSettings, check_frame, raw_cell_frame, select_check_cells
from src.segment_sample_report import SampleCounts, render_report, sample_counts
from src.verify_raw import ManifestMismatch

TEXT_SENTINEL = "ZZ-post-text-that-must-never-be-reported"
POST_COLUMNS = ["leader", "workbook", "sheet_idx", "source_row", "post_text", "link", "text_kind"]
SETTINGS = SegmentSettings(check_cells=3, seed=5)


def _cells(n_leaders: int, per_leader: int) -> pd.DataFrame:
    rows = [(f"leader{i:03d}", f"w#1:r{i * 100 + j}", f"text {i} {j}") for i in range(n_leaders) for j in range(per_leader)]
    return pd.DataFrame(rows, columns=["leader_key", "ref", "text"])


def _sample_for(frame: pd.DataFrame, settings: SegmentSettings = SETTINGS) -> pd.DataFrame:
    drawn = check_frame(select_check_cells(frame, settings.check_cells, settings.seed))
    return drawn[["ref", "leader_id", "human_post_count"]]


# ---- counts -----------------------------------------------------------------------------------


def test_counts_describe_the_frame_the_sample_and_the_settings() -> None:
    frame = _cells(4, 3)

    counts = sample_counts(frame, _sample_for(frame), SETTINGS)

    assert counts == SampleCounts(
        raw_cells=12, leaders=4, required=3, seed=5,
        sample_cells=3, sample_leaders=3, human_counts_filled=0, matches_fresh_draw=True,
    )


def test_human_counts_filled_ignores_blank_and_whitespace_entries() -> None:
    frame = _cells(4, 3)
    sample = _sample_for(frame).assign(human_post_count=["2", " ", ""])

    assert sample_counts(frame, sample, SETTINGS).human_counts_filled == 1


def test_a_sample_that_differs_from_a_fresh_draw_is_flagged() -> None:
    frame = _cells(4, 3)
    sample = _sample_for(frame).assign(ref=["w#9:r1", "w#9:r2", "w#9:r3"])

    assert sample_counts(frame, sample, SETTINGS).matches_fresh_draw is False


def test_sample_leaders_counts_distinct_leader_ids() -> None:
    frame = _cells(4, 3)
    sample = _sample_for(frame).assign(leader_id=["Lsame", "Lsame", "Lother"])

    assert sample_counts(frame, sample, SETTINGS).sample_leaders == 2


def test_missing_sample_column_raises_a_clear_error() -> None:
    frame = _cells(4, 3)

    with pytest.raises(ValueError, match="human_post_count"):
        sample_counts(frame, _sample_for(frame).drop(columns=["human_post_count"]), SETTINGS)


# ---- report -----------------------------------------------------------------------------------


def _report() -> str:
    frame = _cells(4, 3)
    return render_report(sample_counts(frame, _sample_for(frame), SETTINGS))


def test_report_holds_the_counts_and_the_seed() -> None:
    text = _report()

    assert "| Raw cells with a leader and some text | 12 |" in text
    assert "| Cells in the sample file | 3 |" in text
    assert "| Cells with a human count filled in | 0 |" in text
    assert "| Seed | 5 |" in text


def test_report_has_no_refs_ids_or_cell_text() -> None:
    text = _report()

    for forbidden in ("w#1", "leader000", "text 0 0", "Lsame"):
        assert forbidden not in text


def test_report_says_there_is_no_machine_count_and_g1_is_not_signed() -> None:
    lowered = _report().lower()

    assert "no machine count" in lowered
    assert "not signed" in lowered
    assert "passed" not in lowered


# ---- entry points -----------------------------------------------------------------------------


@pytest.fixture
def workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, Path]:
    raw, interim = tmp_path / "raw", tmp_path / "interim"
    raw.mkdir()
    interim.mkdir()
    rows = [
        (f"Leader {i}", "w.xlsx", "1", str(i), f"Leader {i}\n• 3rd+\nHead\n5yr •\nbody\nFollow", "", "raw") for i in range(6)
    ]
    posts = pd.DataFrame(rows, columns=POST_COLUMNS)
    posts.to_csv(interim / "harmonised_posts.csv", index=False)
    sample = check_frame(select_check_cells(raw_cell_frame(posts), SETTINGS.check_cells, SETTINGS.seed))
    sample_path = tmp_path / "derived" / "check.csv"
    sample_path.parent.mkdir()
    sample.assign(post_text=TEXT_SENTINEL).to_csv(sample_path, index=False)
    monkeypatch.setattr(segment_sample_report, "verify_raw", lambda directory: "abc123")
    return {"raw": raw, "interim": interim, "sample": sample_path, "report": tmp_path / "reports" / "s.md"}


def _go(workspace: dict[str, Path]) -> int:
    return segment_sample_report.run(
        workspace["raw"], workspace["interim"], workspace["sample"], workspace["report"], SETTINGS
    )


def test_run_writes_a_counts_only_report_and_leaves_the_sample_untouched(workspace: dict[str, Path]) -> None:
    before = workspace["sample"].read_bytes()

    code = _go(workspace)

    assert code == 0
    text = workspace["report"].read_text(encoding="utf-8")
    assert "| Cells in the sample file | 3 |" in text
    assert "| Sample matches a fresh draw from the seed | yes |" in text
    assert TEXT_SENTINEL not in text
    assert workspace["sample"].read_bytes() == before


def test_run_fails_cleanly_and_names_the_make_target_when_the_sample_is_missing(
    workspace: dict[str, Path], caplog: pytest.LogCaptureFixture
) -> None:
    workspace["sample"].unlink()

    with caplog.at_level(logging.ERROR):
        code = _go(workspace)

    assert code == 1
    assert "segmentation-sample" in caplog.text
    assert not workspace["report"].exists()


def test_run_fails_cleanly_when_the_harmonised_posts_are_missing(workspace: dict[str, Path]) -> None:
    (workspace["interim"] / "harmonised_posts.csv").unlink()

    assert _go(workspace) == 1
    assert not workspace["report"].exists()


def test_run_fails_cleanly_when_the_raw_manifest_does_not_match(
    workspace: dict[str, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    def _fail(directory: Path) -> str:
        raise ManifestMismatch("changed")

    monkeypatch.setattr(segment_sample_report, "verify_raw", _fail)

    assert _go(workspace) == 1
    assert not workspace["report"].exists()


def test_main_returns_the_exit_code_of_run(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(segment_sample_report, "run", lambda: 0)

    assert segment_sample_report.main() == 0
