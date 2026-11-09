"""Tests for src.segment: split a raw post cell into single posts, and draw the blind 200-cell check sample."""
from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd
import pytest

from src import segment
from src.id_matching import leader_id_for
from src.name_key import name_key
from src.segment import (
    CHECK_COLUMNS,
    SegmentSettings,
    check_frame,
    load_settings,
    raw_cell_frame,
    ref_for,
    segment_cell,
    select_check_cells,
)
from src.verify_raw import ManifestMismatch


def _post(name: str, body: str, marker: str = "• 3rd+") -> str:
    return f"{name}\n{marker}\nHeadline text\n5yr •\n{body}\nFollow"


def test_a_cell_with_one_header_is_one_post() -> None:
    result = segment_cell(_post("Person A", "Body one"))

    assert len(result.segments) == 1
    assert result.found_header is True


def test_a_cell_with_two_headers_is_two_posts_and_each_starts_at_its_name_line() -> None:
    text = _post("Person A", "Body one") + "\n" + _post("Person B", "Body two")

    result = segment_cell(text)

    assert [s.text.split("\n")[0] for s in result.segments] == ["Person A", "Person B"]


def test_a_cell_with_no_marker_is_one_post_and_has_no_header() -> None:
    result = segment_cell("Just some text\nwith no interface lines")

    assert len(result.segments) == 1
    assert result.found_header is False


@pytest.mark.parametrize("text", ["", "   ", "\n\n"])
def test_a_blank_cell_has_no_posts(text: str) -> None:
    result = segment_cell(text)

    assert result.segments == ()
    assert result.found_header is False


@pytest.mark.parametrize("marker", ["• 1st", "• 2nd", "• 3rd", "• 3rd+", "• Following"])
def test_every_known_connection_marker_opens_a_header(marker: str) -> None:
    text = _post("Person A", "x", marker) + "\n" + _post("Person B", "y", marker)

    assert len(segment_cell(text).segments) == 2


def test_a_marker_on_the_first_line_starts_the_first_post_there() -> None:
    result = segment_cell("• 3rd+\nHeadline\nBody")

    assert len(result.segments) == 1
    assert result.segments[0].start_line == 0


def test_back_to_back_marker_lines_are_one_header() -> None:
    result = segment_cell("Person A\n• 3rd+\n• 3rd+\nHeadline\nBody")

    assert len(result.segments) == 1


def test_text_before_the_first_header_stays_with_the_first_post() -> None:
    result = segment_cell("Intro line\nPerson A\n• 3rd+\nBody")

    assert len(result.segments) == 1
    assert result.segments[0].text.startswith("Intro line")


def test_a_marker_shaped_phrase_inside_a_sentence_is_not_a_header() -> None:
    result = segment_cell("Person A\nI finished • 3rd+ in the race\nBody")

    assert result.found_header is False


def test_segments_cover_every_line_exactly_once() -> None:
    text = "Intro\n" + _post("Person A", "one") + "\n\n" + _post("Person B", "two")

    result = segment_cell(text)

    assert "\n".join(s.text for s in result.segments) == text
    assert [s.start_line for s in result.segments] == sorted({s.start_line for s in result.segments})


def _frame(*cells: tuple[str, str]) -> pd.DataFrame:
    """(leader_key, ref) per cell, with synthetic text."""
    return pd.DataFrame([(key, ref, f"text of {ref}") for key, ref in cells], columns=["leader_key", "ref", "text"])


def _leaders_with_cells(n_leaders: int, per_leader: int) -> pd.DataFrame:
    return _frame(*[(f"leader{i:03d}", f"w#1:r{i * 100 + j}") for i in range(n_leaders) for j in range(per_leader)])


def test_the_sample_takes_one_cell_per_leader_when_there_are_enough_leaders() -> None:
    chosen = select_check_cells(_leaders_with_cells(30, 3), n=10, seed=1)

    assert len(chosen) == 10
    assert chosen["leader_key"].is_unique


def test_the_sample_is_the_same_for_the_same_seed_whatever_the_row_order() -> None:
    frame = _leaders_with_cells(30, 3)

    first = select_check_cells(frame, n=10, seed=7)
    second = select_check_cells(frame.sample(frac=1, random_state=3), n=10, seed=7)

    assert first["ref"].to_list() == second["ref"].to_list()


def test_a_different_seed_gives_a_different_sample() -> None:
    frame = _leaders_with_cells(30, 3)

    assert select_check_cells(frame, 10, 1)["ref"].to_list() != select_check_cells(frame, 10, 2)["ref"].to_list()


def test_when_leaders_run_out_extra_cells_fill_the_sample_without_repeats() -> None:
    chosen = select_check_cells(_leaders_with_cells(4, 5), n=10, seed=1)

    assert len(chosen) == 10
    assert chosen["ref"].is_unique
    assert set(chosen["leader_key"]) == {f"leader{i:03d}" for i in range(4)}


def test_when_there_are_fewer_cells_than_asked_all_are_returned() -> None:
    chosen = select_check_cells(_leaders_with_cells(2, 2), n=10, seed=1)

    assert len(chosen) == 4


def test_ref_format_is_workbook_sheet_and_row() -> None:
    assert ref_for("w1.xlsx", "3", "17") == "w1.xlsx#3:r17"


POST_COLUMNS = ["leader", "workbook", "sheet_idx", "source_row", "post_text", "link", "text_kind"]


def _posts(*rows: tuple[str, str, str, str, str, str, str]) -> pd.DataFrame:
    return pd.DataFrame(list(rows), columns=POST_COLUMNS)


def test_raw_cell_frame_keeps_raw_cells_with_a_leader_and_some_text() -> None:
    posts = _posts(
        ("Ann Rao", "w.xlsx", "1", "2", "Body", "", "raw"),
        ("Ann Rao", "w.xlsx", "1", "3", "Cleaned", "", "cleaned"),
        ("Bo Lee", "w.xlsx", "1", "4", "   ", "", "raw"),
        ("", "w.xlsx", "1", "5", "No leader", "", "raw"),
    )

    frame = raw_cell_frame(posts)

    assert frame["ref"].to_list() == ["w.xlsx#1:r2"]
    assert frame["leader_key"].to_list() == [name_key("Ann Rao")]


def test_check_frame_is_blind_and_has_empty_human_columns() -> None:
    chosen = pd.DataFrame([("k1", "w#1:r2", "Body")], columns=["leader_key", "ref", "text"])

    out = check_frame(chosen)

    assert list(out.columns) == CHECK_COLUMNS
    assert out["leader_id"].to_list() == [leader_id_for("k1")]
    assert out["human_post_count"].to_list() == [""]
    assert out["human_note"].to_list() == [""]
    assert not any("machine" in column for column in out.columns)


def test_check_frame_defuses_text_a_spreadsheet_would_run_as_a_formula() -> None:
    chosen = pd.DataFrame([("k1", "w#1:r2", "=1+1")], columns=["leader_key", "ref", "text"])

    assert check_frame(chosen)["post_text"].to_list() == ["'=1+1"]


def test_settings_load_from_the_thresholds_file(tmp_path: Path) -> None:
    path = tmp_path / "t.yaml"
    path.write_text("segmentation_check_cells: 50\nsegmentation_check_seed: 9\n", encoding="utf-8")

    assert load_settings(path) == SegmentSettings(check_cells=50, seed=9)


def test_a_missing_settings_key_is_named_in_the_error(tmp_path: Path) -> None:
    path = tmp_path / "t.yaml"
    path.write_text("segmentation_check_cells: 50\n", encoding="utf-8")

    with pytest.raises(ValueError, match="segmentation_check_seed"):
        load_settings(path)


@pytest.fixture
def workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, Path]:
    raw, interim = tmp_path / "raw", tmp_path / "interim"
    raw.mkdir()
    interim.mkdir()
    rows = [(f"Leader {i}", "w.xlsx", "1", str(i), _post(f"Leader {i}", "body"), "", "raw") for i in range(6)]
    _posts(*rows).to_csv(interim / "harmonised_posts.csv", index=False)
    monkeypatch.setattr(segment, "verify_raw", lambda directory: "abc123")
    return {"raw": raw, "interim": interim, "sample": tmp_path / "derived" / "check.csv"}


def _go(workspace: dict[str, Path]) -> int:
    return segment.run(workspace["raw"], workspace["interim"], workspace["sample"], SegmentSettings(check_cells=4, seed=5))


def test_run_writes_the_sample_with_the_requested_number_of_rows(workspace: dict[str, Path]) -> None:
    assert _go(workspace) == 0

    written = pd.read_csv(workspace["sample"], dtype=str, keep_default_na=False)
    assert len(written) == 4
    assert list(written.columns) == CHECK_COLUMNS


def test_run_keeps_an_existing_sample_so_human_counts_are_never_overwritten(
    workspace: dict[str, Path], caplog: pytest.LogCaptureFixture
) -> None:
    workspace["sample"].parent.mkdir(parents=True)
    workspace["sample"].write_text("n,human_post_count\n1,2\n", encoding="utf-8")

    with caplog.at_level(logging.INFO):
        code = _go(workspace)

    assert code == 0
    assert workspace["sample"].read_text(encoding="utf-8") == "n,human_post_count\n1,2\n"
    assert "already exists" in caplog.text


def test_run_fails_cleanly_when_the_harmonised_posts_are_missing(workspace: dict[str, Path]) -> None:
    (workspace["interim"] / "harmonised_posts.csv").unlink()

    assert _go(workspace) == 1
    assert not workspace["sample"].exists()


def test_run_fails_cleanly_when_a_needed_column_is_missing(workspace: dict[str, Path]) -> None:
    path = workspace["interim"] / "harmonised_posts.csv"
    pd.read_csv(path, dtype=str).drop(columns=["link"]).to_csv(path, index=False)

    assert _go(workspace) == 1


def test_run_fails_cleanly_and_names_the_key_when_the_id_key_is_missing(
    workspace: dict[str, Path], tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.delenv("FP15_ID_KEY", raising=False)
    monkeypatch.chdir(tmp_path)

    with caplog.at_level("ERROR"):
        code = _go(workspace)

    assert code == 1
    assert "FP15_ID_KEY" in caplog.text
    assert not workspace["sample"].exists()


def test_run_fails_cleanly_when_the_raw_manifest_does_not_match(
    workspace: dict[str, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    def _fail(directory: Path) -> str:
        raise ManifestMismatch("changed")

    monkeypatch.setattr(segment, "verify_raw", _fail)

    assert _go(workspace) == 1
    assert not workspace["sample"].exists()


def test_main_returns_the_exit_code_of_run(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(segment, "run", lambda: 0)

    assert segment.main([]) == 0
