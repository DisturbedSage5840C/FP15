"""Tests for src.segment_score: compare the human post counts with the segmenter. It never signs off a gate."""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from src import segment_score
from src.segment_score import (
    HumanCount,
    ScoreResult,
    load_human_counts,
    load_threshold,
    render_report,
    score_cells,
)
from src.verify_raw import ManifestMismatch

ONE_POST = "Person A\n• 3rd+\nBody"
TWO_POSTS = ONE_POST + "\nPerson B\n• 3rd+\nBody two"
THREE_POSTS = TWO_POSTS + "\nPerson C\n• 3rd+\nBody three"
TEXTS = {"r1": ONE_POST, "r2": TWO_POSTS, "r3": THREE_POSTS, "r4": ONE_POST}


def _write_sample(path: Path, counts: list[str]) -> None:
    rows = [(str(i + 1), f"leader{i}", f"r{i + 1}", "text", count, "") for i, count in enumerate(counts)]
    columns = ["n", "leader_id", "ref", "post_text", "human_post_count", "human_note"]
    pd.DataFrame(rows, columns=columns).to_csv(path, index=False)


def test_human_counts_are_read_with_blank_cells_left_unscored(tmp_path: Path) -> None:
    path = tmp_path / "s.csv"
    _write_sample(path, ["1", " 2 ", ""])

    rows = load_human_counts(path)

    assert [(r.n, r.ref, r.count) for r in rows] == [(1, "r1", 1), (2, "r2", 2), (3, "r3", None)]


@pytest.mark.parametrize("bad", ["two", "2.5", "-1", "1e3"])
def test_a_count_that_is_not_a_whole_number_is_rejected_by_row(tmp_path: Path, bad: str) -> None:
    path = tmp_path / "s.csv"
    _write_sample(path, ["1", bad])

    with pytest.raises(ValueError, match="row 2"):
        load_human_counts(path)


def test_a_sample_without_the_needed_columns_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "s.csv"
    pd.DataFrame({"n": ["1"]}).to_csv(path, index=False)

    with pytest.raises(ValueError, match="missing columns"):
        load_human_counts(path)


def test_exact_matches_give_the_accuracy() -> None:
    rows = [HumanCount(1, "r1", 1), HumanCount(2, "r2", 2), HumanCount(3, "r3", 2), HumanCount(4, "r4", 1)]

    result = score_cells(rows, TEXTS, threshold=0.95)

    assert (result.scored, result.exact) == (4, 3)
    assert result.accuracy == pytest.approx(0.75)
    assert result.at_or_above_threshold is False


def test_accuracy_equal_to_the_threshold_counts_as_at_or_above() -> None:
    result = score_cells([HumanCount(1, "r1", 1), HumanCount(2, "r2", 2)], TEXTS, threshold=1.0)

    assert result.accuracy == 1.0
    assert result.at_or_above_threshold is True


def test_unscored_rows_are_counted_but_do_not_affect_accuracy() -> None:
    result = score_cells([HumanCount(1, "r1", 1), HumanCount(2, "r2", None)], TEXTS, threshold=0.95)

    assert (result.n_rows, result.scored, result.unscored) == (2, 1, 1)
    assert result.accuracy == 1.0


def test_nothing_scored_gives_no_accuracy_and_no_verdict() -> None:
    result = score_cells([HumanCount(1, "r1", None)], TEXTS, threshold=0.95)

    assert result.accuracy is None
    assert result.at_or_above_threshold is None


def test_misses_are_split_by_direction() -> None:
    rows = [HumanCount(1, "r1", 2), HumanCount(2, "r3", 1), HumanCount(3, "r2", 2)]

    result = score_cells(rows, TEXTS, threshold=0.95)

    assert (result.machine_fewer, result.machine_more) == (1, 1)


def test_breakdown_by_the_machine_post_count() -> None:
    rows = [HumanCount(1, "r1", 1), HumanCount(2, "r2", 3), HumanCount(3, "r3", 3), HumanCount(4, "r4", 2)]

    result = score_cells(rows, TEXTS, threshold=0.95)

    assert result.by_machine_count == (("1", 2, 1), ("2", 1, 0), ("3 or more", 1, 1))


def test_detail_rows_carry_the_row_number_and_both_counts_but_no_text() -> None:
    result = score_cells([HumanCount(2, "r2", 3)], TEXTS, threshold=0.95)

    assert [(d.n, d.human, d.machine) for d in result.details] == [(2, 3, 2)]


def test_a_ref_that_is_not_in_the_data_is_an_error_naming_the_row() -> None:
    with pytest.raises(ValueError, match="row 7"):
        score_cells([HumanCount(7, "gone", 1)], TEXTS, threshold=0.95)


def test_threshold_is_read_from_the_thresholds_file(tmp_path: Path) -> None:
    path = tmp_path / "t.yaml"
    path.write_text("segmentation_accuracy: 0.9\n", encoding="utf-8")

    assert load_threshold(path) == 0.9


def test_a_missing_threshold_key_is_named(tmp_path: Path) -> None:
    path = tmp_path / "t.yaml"
    path.write_text("other: 1\n", encoding="utf-8")

    with pytest.raises(ValueError, match="segmentation_accuracy"):
        load_threshold(path)


def _result(**overrides: object) -> ScoreResult:
    base = score_cells([HumanCount(1, "r1", 1), HumanCount(2, "r2", 3)], TEXTS, threshold=0.95)
    return ScoreResult(**{**base.__dict__, **overrides})


def test_the_report_gives_counts_and_says_it_does_not_sign_off_g1() -> None:
    text = render_report(_result(), required_cells=200)

    assert text.startswith("# Segmentation check")
    assert "| Cells with a human count | 2 |" in text
    assert "| Exact matches | 1 |" in text
    assert "does not sign off G1" in text
    assert "docs/decisions.md" in text


def test_the_report_warns_when_fewer_cells_were_scored_than_required() -> None:
    assert "fewer than the 200" in render_report(_result(), required_cells=200)


def test_the_report_does_not_warn_when_enough_cells_were_scored() -> None:
    assert "fewer than" not in render_report(_result(), required_cells=2)


@pytest.fixture
def workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, Path]:
    interim = tmp_path / "interim"
    interim.mkdir()
    rows = [(f"Leader {i}", "w.xlsx", "1", str(i), TWO_POSTS, "", "raw") for i in range(3)]
    columns = ["leader", "workbook", "sheet_idx", "source_row", "post_text", "link", "text_kind"]
    pd.DataFrame(rows, columns=columns).to_csv(interim / "harmonised_posts.csv", index=False)
    sample = tmp_path / "check.csv"
    pd.DataFrame(
        [(str(i + 1), f"leader{i}", f"w.xlsx#1:r{i}", "text", "2" if i < 2 else "1", "") for i in range(3)],
        columns=["n", "leader_id", "ref", "post_text", "human_post_count", "human_note"],
    ).to_csv(sample, index=False)
    monkeypatch.setattr(segment_score, "verify_raw", lambda directory: "abc123")
    return {
        "raw": tmp_path / "raw",
        "interim": interim,
        "sample": sample,
        "report": tmp_path / "reports" / "score.md",
        "detail": tmp_path / "derived" / "detail.csv",
    }


def _go(workspace: dict[str, Path], threshold: float = 0.95) -> int:
    return segment_score.run(
        workspace["raw"], workspace["interim"], workspace["sample"], workspace["report"], workspace["detail"], threshold
    )


def test_run_writes_the_report_and_the_detail_file(workspace: dict[str, Path]) -> None:
    assert _go(workspace) == 0

    assert "| Exact matches | 2 |" in workspace["report"].read_text(encoding="utf-8")
    detail = pd.read_csv(workspace["detail"], dtype=str)
    assert list(detail.columns) == ["n", "human", "machine", "match"]
    assert detail["match"].to_list() == ["yes", "yes", "no"]


def test_run_fails_cleanly_when_no_human_count_is_filled_in(workspace: dict[str, Path]) -> None:
    sample = pd.read_csv(workspace["sample"], dtype=str, keep_default_na=False)
    sample["human_post_count"] = ""
    sample.to_csv(workspace["sample"], index=False)

    assert _go(workspace) == 1
    assert not workspace["report"].exists()


def test_run_fails_cleanly_when_the_sample_is_missing(workspace: dict[str, Path]) -> None:
    workspace["sample"].unlink()

    assert _go(workspace) == 1


def test_run_fails_cleanly_when_the_raw_manifest_does_not_match(
    workspace: dict[str, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    def _fail(directory: Path) -> str:
        raise ManifestMismatch("changed")

    monkeypatch.setattr(segment_score, "verify_raw", _fail)

    assert _go(workspace) == 1
    assert not workspace["report"].exists()


def test_main_returns_the_exit_code_of_run(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(segment_score, "run", lambda: 0)

    assert segment_score.main([]) == 0


def test_required_cells_are_read_from_the_thresholds_file(tmp_path: Path) -> None:
    path = tmp_path / "t.yaml"
    path.write_text("segmentation_check_cells: 120\n", encoding="utf-8")

    assert segment_score.load_required_cells(path) == 120


def test_a_missing_required_cells_key_is_named(tmp_path: Path) -> None:
    path = tmp_path / "t.yaml"
    path.write_text("other: 1\n", encoding="utf-8")

    with pytest.raises(ValueError, match="segmentation_check_cells"):
        segment_score.load_required_cells(path)


def test_the_report_says_not_scored_when_no_cell_has_a_human_count() -> None:
    result = score_cells([HumanCount(1, "r1", None)], TEXTS, threshold=0.95)

    text = render_report(result, required_cells=200)

    assert "| At or above threshold | not scored |" in text
    assert "| Accuracy (exact matches / cells with a human count) | n/a |" in text
