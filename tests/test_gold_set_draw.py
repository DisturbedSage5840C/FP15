"""Gold-set draw stage (src/gold_set_draw.py). Invented names, ids, texts and numbers only: no real data.

The draw is PROVISIONAL (AI-assisted, owner to confirm). It uses Option A: every leader with a post is in the pool,
with no minimum number of posts per leader.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

import pandas as pd
import pytest

from src.eda_balance import CEO_TYPE_FACTOR, GENDER_FACTOR
from src.gold_set import GoldSettings, load_gold_settings
from src.gold_set_draw import (
    build_pool,
    draw_gold_set,
    read_gold_file,
    render_report,
    run,
    write_gold_file,
)
from src.name_key import name_key
from src.provisional_measures import measure_cells

LEADERS = 40
POSTS_EACH = 6
SENTINEL_TEXT = "Sentinel post text"
SETTINGS = GoldSettings(size=30, max_posts_per_leader=3, seed=7, coders=4, coders_per_post=2)


def _id(index: int) -> str:
    return f"L{index:03d}"


def invented_cells(empty_first: bool = False) -> pd.DataFrame:
    rows = []
    for leader in range(LEADERS):
        for post in range(POSTS_EACH):
            text = "" if empty_first and leader == 0 and post == 0 else f"{SENTINEL_TEXT} {leader}-{post}"
            rows.append(
                {
                    "leader_id": _id(leader),
                    "workbook": "wb.xlsx",
                    "sheet_idx": "0",
                    "source_row": str(post + 2),
                    "post_text_clean": text,
                    "language": "English",
                }
            )
    return pd.DataFrame(rows)


def invented_labels(skip_last: bool = False) -> pd.DataFrame:
    rows = [
        {
            "leader_id": _id(i),
            CEO_TYPE_FACTOR: "Founder-CEO" if i % 2 == 0 else "Professional CEO",
            GENDER_FACTOR: "coded 1" if (i // 2) % 2 == 0 else "coded 0",
        }
        for i in range(LEADERS - (1 if skip_last else 0))
    ]
    return pd.DataFrame(rows)


def test_post_ids_are_the_same_ids_the_provisional_measures_use() -> None:
    cells = invented_cells().sample(frac=1, random_state=3)

    pool = build_pool(cells, invented_labels())

    measured = measure_cells(cells)
    assert list(pool["post_id"]) == list(measured["post_id"])
    assert list(pool["leader_id"]) == list(measured["leader_id"])


def test_an_empty_cell_cannot_be_drawn_but_keeps_the_numbering_of_the_others() -> None:
    pool = build_pool(invented_cells(empty_first=True), invented_labels())

    assert len(pool) == LEADERS * POSTS_EACH - 1
    assert "p000001" not in set(pool["post_id"])
    assert "p000002" in set(pool["post_id"])


def test_strata_labels_are_the_codes_as_given_without_the_word_coded() -> None:
    pool = build_pool(invented_cells(), invented_labels())

    assert set(pool["gender_as_coded"]) == {"0", "1"}
    assert set(pool["ceo_type"]) == {"Founder-CEO", "Professional CEO"}


def test_a_leader_with_posts_but_no_label_row_is_refused_not_dropped() -> None:
    with pytest.raises(ValueError, match="no group label"):
        build_pool(invented_cells(), invented_labels(skip_last=True))


def test_draw_respects_the_size_the_cap_and_fills_every_stratum() -> None:
    pool = build_pool(invented_cells(), invented_labels())

    draw = draw_gold_set(pool, SETTINGS)

    chosen = pool[pool["post_id"].isin(draw.post_ids)]
    assert len(draw.post_ids) == SETTINGS.size
    assert chosen.groupby("leader_id").size().max() <= SETTINGS.max_posts_per_leader
    assert (draw.strata["drawn"] > 0).all()
    assert draw.strata["shortfall"].sum() == 0


def test_report_holds_counts_only_and_says_the_choice_is_provisional() -> None:
    pool = build_pool(invented_cells(), invented_labels())
    draw = draw_gold_set(pool, SETTINGS)

    report = render_report(pool, draw, SETTINGS)

    assert "PROVISIONAL" in report.splitlines()[0]
    assert "Option A" in report
    assert "not a human sign-off" in report
    assert "L000" not in report
    assert "p0000" not in report
    assert SENTINEL_TEXT not in report
    assert "personality" not in report.lower()


def test_gold_file_keeps_text_with_hash_lines_and_newlines_and_starts_with_the_provisional_marker(
    tmp_path: Path,
) -> None:
    frame = pd.DataFrame(
        {
            "post_id": ["p000001", "p000002"],
            "leader_id": ["Lx", "Ly"],
            "post_text": ["first line\n# looks like a comment\nlast line", "plain, with a comma"],
        }
    )
    path = tmp_path / "derived" / "gold.csv"

    write_gold_file(frame, path)

    back = read_gold_file(path)
    first_line = path.read_text(encoding="utf-8").splitlines()[0]
    assert list(back["post_text"]) == list(frame["post_text"])
    assert list(back["post_id"]) == list(frame["post_id"])
    assert first_line.startswith("# PROVISIONAL")
    assert "AI-assisted" in first_line


# --- run(): files in, one derived file and one report out ---------------------------------------------------------


def fake_id(key: str) -> str:
    return "L" + hashlib.sha256(key.encode("utf-8")).hexdigest()[:10]


NAMES = [f"Sentinel Person{i:02d}" for i in range(LEADERS)]


def _write_inputs(root: Path) -> None:
    interim = root / "interim"
    interim.mkdir()
    labels = invented_labels()
    pd.DataFrame(
        [
            {"leader": name, "text_kind": "raw", "title": "CEO", "ceo_type": labels.loc[i, CEO_TYPE_FACTOR]}
            for i, name in enumerate(NAMES)
        ]
    ).to_csv(interim / "harmonised_posts.csv", index=False)
    pd.DataFrame(
        {
            "Gender": ["1" if (i // 2) % 2 == 0 else "0" for i in range(LEADERS)],
            "SectorPraticeAreaFeed": [f"Sector {i // 20}" for i in range(LEADERS)],
            "NumberofEmployees": [str(100 * (i + 1)) for i in range(LEADERS)],
        }
    ).to_csv(interim / "company_data.csv", index=False)
    pd.DataFrame(
        {"key": [name_key(n) for n in NAMES], "status": "clear", "company": [f"row:{i + 1}" for i in range(LEADERS)]}
    ).to_csv(interim / "leader_id_proposal.csv", index=False)
    cells = invented_cells()
    cells["leader_id"] = [fake_id(name_key(NAMES[int(v[1:])])) for v in cells["leader_id"]]
    cells.to_csv(interim / "posts_clean.csv", index=False)
    raw = root / "raw"
    raw.mkdir()
    (raw / "MANIFEST.sha256").write_text("", encoding="utf-8")
    (root / "thresholds.yaml").write_text(
        "gold_set_size: 30\ngold_set_max_posts_per_leader: 3\ngold_set_seed: 7\ngold_set_coders: 4\n"
        "gold_set_coders_per_post: 2\ngold_set_raise_on_shortfall: true\n"
        "min_posts_per_leader: 15\neda_disclosure_min_leaders: 5\neda_model_min_leaders: 20\neda_size_bands: 4\n",
        encoding="utf-8",
    )


def _paths(root: Path) -> dict[str, Path]:
    return {
        "raw_dir": root / "raw",
        "interim_dir": root / "interim",
        "clean_path": root / "interim" / "posts_clean.csv",
        "out_path": root / "derived" / "gold_set.csv",
        "report_path": root / "reports" / "gold_set_draw.md",
        "thresholds_path": root / "thresholds.yaml",
    }


def test_run_writes_the_text_file_and_a_report_with_no_name_or_text(tmp_path: Path) -> None:
    _write_inputs(tmp_path)

    code = run(**_paths(tmp_path), id_of=fake_id)

    drawn = read_gold_file(tmp_path / "derived" / "gold_set.csv")
    report = (tmp_path / "reports" / "gold_set_draw.md").read_text(encoding="utf-8")
    assert code == 0
    assert len(drawn) == load_gold_settings(tmp_path / "thresholds.yaml").size
    assert drawn["post_text"].str.startswith(SENTINEL_TEXT).all()
    assert list(drawn.columns) == ["post_id", "leader_id", "post_text"]
    assert "Sentinel" not in report
    assert name_key(NAMES[0]) not in report


def test_run_fails_without_writing_when_the_cleaned_posts_are_missing(tmp_path: Path) -> None:
    _write_inputs(tmp_path)
    (tmp_path / "interim" / "posts_clean.csv").unlink()

    code = run(**_paths(tmp_path), id_of=fake_id)

    assert code == 1
    assert not (tmp_path / "derived" / "gold_set.csv").exists()
    assert not (tmp_path / "reports" / "gold_set_draw.md").exists()


def test_run_fails_clearly_when_the_id_key_is_missing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("FP15_ID_KEY", raising=False)
    monkeypatch.chdir(tmp_path)
    _write_inputs(tmp_path)

    code = run(**_paths(tmp_path))

    assert code == 1
    assert not (tmp_path / "derived" / "gold_set.csv").exists()
