"""Provisional leader-level measures (src/provisional_leaders.py). Invented numbers only: no real data.

Everything here is about the image projected in public posts. The I-rate is one signal, not a narcissism score.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from src.provisional_common import BANNER, read_banner_csv, write_banner_csv
from src.provisional_leaders import (
    LEADER_COLUMNS,
    build_leader_frame,
    hinglish_status_counts,
    render_report,
    run,
    summarise,
)

MIN_POSTS = 15
DISCLOSURE_MIN = 5
ALL_CELLS = "all cells"
NO_HINGLISH = "without possible-Hinglish cells"


def invented_measures(n_leaders: int = 8, posts_each: int = 16, hinglish_leaders: int = 0) -> pd.DataFrame:
    """Invented per-post table: leader i has a singular rate near i, a plural rate near 10 - i, plus noise."""
    rng = np.random.default_rng(7)
    rows = []
    for leader in range(n_leaders):
        for post in range(posts_each):
            rows.append(
                {
                    "leader_id": f"L{leader:02d}",
                    "post_id": f"p{len(rows):06d}",
                    "word_count": 50,
                    "singular_per_100": float(leader) + rng.normal(0, 1),
                    "plural_per_100": float(10 - leader) + rng.normal(0, 1),
                    "hinglish_flag": int(leader < hinglish_leaders and post < 3),
                }
            )
    return pd.DataFrame(rows)


def empty_manifest_dir(tmp_path: Path) -> Path:
    raw = tmp_path / "raw"
    raw.mkdir()
    (raw / "MANIFEST.sha256").write_text("", encoding="utf-8")
    return raw


def test_leader_frame_keeps_only_leaders_at_or_above_the_minimum() -> None:
    short = pd.DataFrame(
        {"leader_id": ["LSHORT"] * 3, "post_id": ["x1", "x2", "x3"], "word_count": 50,
         "singular_per_100": 1.0, "plural_per_100": 1.0, "hinglish_flag": 0}
    )

    leaders = build_leader_frame(pd.concat([invented_measures(), short]), MIN_POSTS)

    assert "LSHORT" not in set(leaders["leader_id"])
    assert tuple(leaders.columns) == LEADER_COLUMNS


def test_leader_frame_has_both_measures_and_both_cell_sets() -> None:
    leaders = build_leader_frame(invented_measures(hinglish_leaders=3), MIN_POSTS)

    assert set(leaders["measure"]) == {"singular_per_100", "plural_per_100"}
    assert set(leaders["cell_set"]) == {ALL_CELLS, NO_HINGLISH}


def test_all_cells_set_counts_every_scored_post_of_a_leader() -> None:
    leaders = build_leader_frame(invented_measures(hinglish_leaders=3), MIN_POSTS)

    flagged = leaders[(leaders["leader_id"] == "L00") & (leaders["measure"] == "singular_per_100")]
    counts = dict(zip(flagged["cell_set"], flagged["n_posts"], strict=True))
    assert counts[ALL_CELLS] == 16


def test_leader_falling_under_the_minimum_without_hinglish_leaves_that_set_only() -> None:
    frame = invented_measures(posts_each=16, hinglish_leaders=2)  # L00 and L01 lose 3 cells: 13 < 15

    leaders = build_leader_frame(frame, MIN_POSTS)

    by_set = leaders[leaders["measure"] == "singular_per_100"].groupby("cell_set")["leader_id"].apply(set)
    assert "L00" in by_set[ALL_CELLS]
    assert "L00" not in by_set[NO_HINGLISH]


def test_missing_rates_are_not_counted_as_posts() -> None:
    frame = invented_measures()
    frame.loc[frame["leader_id"] == "L03", "singular_per_100"] = np.nan  # no scored post at all

    leaders = build_leader_frame(frame, MIN_POSTS)

    singular = leaders[leaders["measure"] == "singular_per_100"]
    assert "L03" not in set(singular["leader_id"])


def test_too_few_qualifying_leaders_gives_an_empty_frame_not_a_crash() -> None:
    leaders = build_leader_frame(invented_measures(n_leaders=1), MIN_POSTS)

    assert leaders.empty
    assert tuple(leaders.columns) == LEADER_COLUMNS


def test_shrinkage_pulls_every_leader_toward_the_mean() -> None:
    leaders = build_leader_frame(invented_measures(), MIN_POSTS)
    sub = leaders[(leaders["measure"] == "singular_per_100") & (leaders["cell_set"] == ALL_CELLS)]
    grand = sub["raw_mean"].mean()

    assert ((sub["shrunk_mean"] - grand).abs() <= (sub["raw_mean"] - grand).abs() + 1e-9).all()


def test_summarise_gives_count_and_quartiles_when_big_enough() -> None:
    row = summarise(pd.Series([1.0, 2.0, 3.0, 4.0, 5.0, 6.0]), DISCLOSURE_MIN)

    assert row["leaders"] == "6"
    assert row["min"] == "1.00"
    assert row["median"] == "3.50"
    assert row["max"] == "6.00"


def test_summarise_hides_everything_under_the_disclosure_minimum() -> None:
    row = summarise(pd.Series([1.0, 2.0, 3.0]), DISCLOSURE_MIN)

    assert row == {"leaders": "<5", "min": "<5", "q1": "<5", "median": "<5", "q3": "<5", "max": "<5"}


def test_summarise_of_nothing_shows_the_count_as_suppressed() -> None:
    assert summarise(pd.Series([], dtype=float), DISCLOSURE_MIN)["leaders"] == "<5"


def test_hinglish_status_counts_split_leaders_and_suppress_small_cells() -> None:
    frame = invented_measures(n_leaders=8, hinglish_leaders=2)
    leaders = build_leader_frame(frame, MIN_POSTS)
    ids = set(leaders[leaders["cell_set"] == ALL_CELLS]["leader_id"])

    shown = hinglish_status_counts(frame, ids, DISCLOSURE_MIN)

    assert shown["leaders with no flagged cell"] == "<5"
    assert shown["leaders with at least one flagged cell"] == "<5"


def test_hinglish_status_counts_show_big_cells() -> None:
    frame = invented_measures(n_leaders=14, hinglish_leaders=6)
    leaders = build_leader_frame(frame, MIN_POSTS)
    ids = set(leaders[leaders["cell_set"] == ALL_CELLS]["leader_id"])

    shown = hinglish_status_counts(frame, ids, DISCLOSURE_MIN)

    assert shown["leaders with at least one flagged cell"] == "6"
    assert shown["leaders with no flagged cell"] == "8"


def test_render_report_starts_with_the_banner_and_leaks_no_ids_or_personality_words() -> None:
    frame = invented_measures(n_leaders=14, hinglish_leaders=6)
    leaders = build_leader_frame(frame, MIN_POSTS)

    text = render_report(frame, leaders, MIN_POSTS, DISCLOSURE_MIN)

    assert text.splitlines()[0] == f"> {BANNER}"
    assert "L00" not in text and "p0000" not in text
    assert "personality" not in text.replace("never personality", "")
    assert "narcissis" not in text.replace("not a narcissism score", "")
    assert "exploratory" in text.lower()


def test_run_refuses_on_manifest_mismatch_and_writes_nothing(tmp_path: Path) -> None:
    raw = tmp_path / "raw"
    raw.mkdir()
    (raw / "MANIFEST.sha256").write_text("deadbeef  missing.xlsx\n", encoding="utf-8")

    code = run(raw_dir=raw, measures_path=tmp_path / "m.csv", out_path=tmp_path / "l.csv",
               report_path=tmp_path / "r.md")

    assert code == 1
    assert not (tmp_path / "r.md").exists()


def test_run_fails_clearly_when_the_measures_file_is_missing(tmp_path: Path) -> None:
    code = run(raw_dir=empty_manifest_dir(tmp_path), measures_path=tmp_path / "none.csv",
               out_path=tmp_path / "l.csv", report_path=tmp_path / "r.md")

    assert code == 1
    assert not (tmp_path / "r.md").exists()


def test_run_end_to_end_on_invented_files(tmp_path: Path) -> None:
    measures_path = tmp_path / "m.csv"
    write_banner_csv(invented_measures(n_leaders=14, hinglish_leaders=6), measures_path)

    code = run(raw_dir=empty_manifest_dir(tmp_path), measures_path=measures_path, out_path=tmp_path / "l.csv",
               report_path=tmp_path / "r.md")

    assert code == 0
    assert (tmp_path / "r.md").read_text(encoding="utf-8").startswith("> PROVISIONAL")
    leaders = read_banner_csv(tmp_path / "l.csv")
    assert tuple(leaders.columns) == LEADER_COLUMNS
    assert leaders["shrunk_mean"].notna().all()
