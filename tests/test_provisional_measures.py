"""Provisional per-post measures (src/provisional_measures.py). Invented cells only: no real post text, no real data.

The rates tested here are one signal of the image projected in public posts. They are not a narcissism score.
"""
from __future__ import annotations

import math
from pathlib import Path

import pandas as pd
import pytest

from src.provisional_common import BANNER, read_banner_csv, write_banner_csv
from src.provisional_measures import MEASURE_COLUMNS, measure_cells, repost_refs, run
from src.segment import ref_for

HAND_COUNTED = "I built this with my team and we shipped it for our clients while I'm learning from all of them"


def cells(rows: list[tuple[str, str, str, str, str]]) -> pd.DataFrame:
    """(leader_id, workbook, sheet_idx, source_row, text) -> the columns of posts_clean that the step reads."""
    return pd.DataFrame(
        [
            {"leader_id": leader, "workbook": wb, "sheet_idx": sheet, "source_row": row, "post_text_clean": text,
             "language": "English"}
            for leader, wb, sheet, row, text in rows
        ]
    )


def test_rates_match_the_hand_count() -> None:
    frame = measure_cells(cells([("L1", "a", "0", "2", HAND_COUNTED)]))

    row = frame.iloc[0]
    assert row["word_count"] == 20
    assert row["singular_per_100"] == pytest.approx(15.0)
    assert row["plural_per_100"] == pytest.approx(10.0)


def test_zero_word_cell_stays_missing_not_zero() -> None:
    frame = measure_cells(cells([("L1", "a", "0", "2", "   "), ("L1", "a", "0", "3", "\U0001F680 \U0001F680")]))

    assert frame["singular_per_100"].isna().all()
    assert frame["plural_per_100"].isna().all()
    assert (frame["word_count"] == 0).all()


def test_empty_text_cell_read_as_nan_stays_missing() -> None:
    raw = cells([("L1", "a", "0", "2", "x")])
    raw["post_text_clean"] = [float("nan")]

    frame = measure_cells(raw)

    assert math.isnan(frame.iloc[0]["singular_per_100"])
    assert frame.iloc[0]["word_count"] == 0


def test_hinglish_cells_are_kept_and_marked() -> None:
    raw = cells([("L1", "a", "0", "2", "I like it"), ("L1", "a", "0", "3", "I like it")])
    raw["language"] = ["English", "Hinglish"]

    frame = measure_cells(raw)

    assert len(frame) == 2
    assert frame["hinglish_flag"].tolist() == [0, 1]


def test_post_id_is_deterministic_unique_and_carries_no_raw_names() -> None:
    raw = cells([("L2", "secret_book.xlsx", "0", "5", "we won"), ("L1", "secret_book.xlsx", "1", "3", "I won")])

    first = measure_cells(raw)
    second = measure_cells(raw.iloc[::-1].reset_index(drop=True))

    assert first["post_id"].is_unique
    assert dict(zip(first["leader_id"], first["post_id"], strict=True)) == dict(
        zip(second["leader_id"], second["post_id"], strict=True)
    )
    assert not first["post_id"].str.contains("secret|xlsx").any()


def test_output_carries_only_the_agreed_columns_and_no_text() -> None:
    frame = measure_cells(cells([("L1", "a", "0", "2", HAND_COUNTED)]))

    assert tuple(frame.columns) == MEASURE_COLUMNS
    assert "post_text_clean" not in frame.columns


def test_banner_csv_round_trips_and_starts_with_the_banner(tmp_path: Path) -> None:
    path = tmp_path / "out.csv"
    frame = pd.DataFrame({"leader_id": ["L1"], "x": [1.5]})

    write_banner_csv(frame, path)

    first_line = path.read_text(encoding="utf-8").splitlines()[0]
    assert first_line.startswith("# PROVISIONAL")
    assert first_line == "# " + BANNER
    pd.testing.assert_frame_equal(read_banner_csv(path), frame)


def test_banner_names_every_limit_the_user_listed() -> None:
    for phrase in ("G1 unsigned", "English-only", "no gold-set check", "not pre-registered", "never personality"):
        assert phrase in BANNER


def test_run_refuses_when_the_raw_manifest_does_not_match(tmp_path: Path) -> None:
    raw = tmp_path / "raw"
    raw.mkdir()
    (raw / "MANIFEST.sha256").write_text("deadbeef  missing.xlsx\n", encoding="utf-8")

    code = run(raw_dir=raw, clean_path=tmp_path / "none.csv", out_path=tmp_path / "out.csv")

    assert code == 1
    assert not (tmp_path / "out.csv").exists()


FEED_HEADER = "Ann Sentinel\n• 3rd+\nmy own words here"
EMBEDDED = "Ann Sentinel\n• 3rd+\nmy words\nBob Sentinel\n• 3rd+\ntheir words"
NOTICE = "Ann Sentinel\n• 3rd+\nBob Sentinel reposted this\nsome shared words"


def _raw_posts(rows: list[tuple[str, str, str, str, str]]) -> pd.DataFrame:
    """(leader name, workbook, sheet_idx, source_row, text) as harmonised raw cells."""
    return pd.DataFrame(
        [
            {"leader": name, "workbook": wb, "sheet_idx": sheet, "source_row": row, "post_text": text, "text_kind": "raw"}
            for name, wb, sheet, row, text in rows
        ]
    )


def test_repost_refs_flag_cells_with_an_embedded_post_or_a_repost_notice_and_no_others() -> None:
    posts = _raw_posts(
        [
            ("Ann Sentinel", "a", "0", "2", FEED_HEADER),
            ("Ann Sentinel", "a", "0", "3", EMBEDDED),
            ("Ann Sentinel", "a", "0", "4", NOTICE),
            ("Ann Sentinel", "a", "0", "5", "no header at all"),
        ]
    )

    flagged = repost_refs(posts)

    assert flagged == {ref_for("a", "0", "3"), ref_for("a", "0", "4")}


def test_repost_refs_ignore_cleaned_rows() -> None:
    posts = _raw_posts([("Ann Sentinel", "a", "0", "3", EMBEDDED)]).assign(text_kind="cleaned")

    assert repost_refs(posts) == set()


def test_measure_cells_marks_flagged_cells_and_keeps_the_rest_zero() -> None:
    raw = cells([("L1", "a", "0", "2", "I like it"), ("L1", "a", "0", "3", "I like it")])

    frame = measure_cells(raw, {ref_for("a", "0", "3")})

    assert frame["repost_flag"].tolist() == [0, 1]


def test_without_a_repost_marker_the_flag_is_missing_not_zero() -> None:
    frame = measure_cells(cells([("L1", "a", "0", "2", "I like it")]))

    assert frame["repost_flag"].isna().all()


def test_the_flag_column_holds_no_name_or_ref() -> None:
    raw = cells([("L1", "secret_book.xlsx", "0", "3", "I like it")])

    text = measure_cells(raw, {ref_for("secret_book.xlsx", "0", "3")}).to_csv(index=False)

    assert "secret" not in text and "Sentinel" not in text
