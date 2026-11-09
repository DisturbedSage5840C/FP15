"""Tests for Step B (src.extra_features): prevalence of text features and badly handled examples.

Synthetic data only. The report holds rules, counts, cell refs and leader ids; it never holds post
text, leader names, company names or links.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from src.extra_features import (
    FAILURE_CLASSES,
    FeatureSettings,
    load_settings,
    pick_examples,
    prevalence_rows,
    run,
)
from src.id_matching import leader_id_for
from src.name_key import name_key
from src.text_features import TextFeatures

POST_COLUMNS = ["leader", "company", "workbook", "sheet_idx", "source_row", "post_text", "link", "text_kind"]
CLASS_NAMES = (
    "length_several_blocks",
    "hashtag_numeric_only",
    "mention_stray_at",
    "url_bare_domain",
    "question_runs",
    "emoji_symbol_only",
    "hinglish_borderline",
    "repost_word_in_running_text",
)


def _class(name: str):
    return next(item for item in FAILURE_CLASSES if item.name == name)


# ---- settings ---------------------------------------------------------------------------------


def test_load_settings_reads_the_keys_from_the_yaml(tmp_path: Path) -> None:
    path = tmp_path / "t.yaml"
    path.write_text("extra_features_examples_per_class: 4\nextra_features_seed: 9\n", encoding="utf-8")

    assert load_settings(path) == FeatureSettings(examples_per_class=4, seed=9)


def test_load_settings_names_the_missing_key(tmp_path: Path) -> None:
    path = tmp_path / "t.yaml"
    path.write_text("extra_features_seed: 9\n", encoding="utf-8")

    with pytest.raises(ValueError, match="extra_features_examples_per_class"):
        load_settings(path)


def test_real_thresholds_file_asks_for_ten_examples_with_the_owner_seed() -> None:
    settings = load_settings(Path("configs/thresholds.yaml"))

    assert (settings.examples_per_class, settings.seed) == (10, 20261107)


# ---- prevalence -------------------------------------------------------------------------------


def test_prevalence_counts_cells_with_at_least_one_and_the_median_among_them() -> None:
    features = [TextFeatures(hashtags=3), TextFeatures(hashtags=1), TextFeatures(), TextFeatures()]

    rows = {row.feature: row for row in prevalence_rows(features)}

    assert (rows["hashtags"].cells, rows["hashtags"].share, rows["hashtags"].median) == (2, 0.5, 2.0)


def test_prevalence_reports_flags_as_cells_with_the_flag() -> None:
    features = [TextFeatures(repost_line=True), TextFeatures(), TextFeatures(repost_line=True)]

    rows = {row.feature: row for row in prevalence_rows(features)}

    assert (rows["repost_line"].cells, rows["repost_line"].median) == (2, None)


def test_prevalence_of_an_empty_corpus_is_zero_not_an_error() -> None:
    rows = {row.feature: row for row in prevalence_rows([])}

    assert (rows["emoji"].cells, rows["emoji"].share, rows["emoji"].median) == (0, 0.0, None)


# ---- badly handled classes --------------------------------------------------------------------


def test_every_failure_class_has_a_name_and_a_stated_problem() -> None:
    assert tuple(item.name for item in FAILURE_CLASSES) == CLASS_NAMES
    assert all(item.problem for item in FAILURE_CLASSES)


@pytest.mark.parametrize(
    ("name", "hit", "miss"),
    [
        ("length_several_blocks", TextFeatures(follow_lines=2), TextFeatures(follow_lines=1)),
        ("hashtag_numeric_only", TextFeatures(numeric_hashtags=1), TextFeatures(hashtags=2)),
        ("mention_stray_at", TextFeatures(stray_at=1), TextFeatures(mentions=2)),
        ("url_bare_domain", TextFeatures(bare_domains=1), TextFeatures(urls=2)),
        ("question_runs", TextFeatures(question_runs=1), TextFeatures(question_marks=3)),
        ("emoji_symbol_only", TextFeatures(symbols=1), TextFeatures(symbols=1, emoji=1)),
        ("hinglish_borderline", TextFeatures(roman_markers=2), TextFeatures(roman_markers=3)),
        ("hinglish_borderline", TextFeatures(roman_markers=1), TextFeatures(roman_markers=0)),
        (
            "repost_word_in_running_text",
            TextFeatures(repost_word_in_text=True),
            TextFeatures(repost_word_in_text=True, repost_line=True),
        ),
    ],
)
def test_failure_class_predicates(name: str, hit: TextFeatures, miss: TextFeatures) -> None:
    predicate = _class(name).matches

    assert predicate(hit) is True
    assert predicate(miss) is False


def test_hinglish_borderline_excludes_cells_that_have_devanagari() -> None:
    assert _class("hinglish_borderline").matches(TextFeatures(roman_markers=1, devanagari_tokens=2)) is False


# ---- examples ---------------------------------------------------------------------------------


def test_pick_examples_is_deterministic_and_capped() -> None:
    refs = [f"b/w.xlsx#1:r{n}" for n in range(30)]

    first = pick_examples(refs, 10, seed=5, label="x")
    second = pick_examples(list(reversed(refs)), 10, seed=5, label="x")

    assert first == second
    assert len(first) == 10
    assert set(first) <= set(refs)


def test_pick_examples_returns_everything_when_fewer_than_the_cap() -> None:
    assert pick_examples(["b#1:r2", "b#1:r1"], 10, seed=5, label="x") == ["b#1:r1", "b#1:r2"]


def test_pick_examples_differs_between_labels() -> None:
    refs = [f"b/w.xlsx#1:r{n}" for n in range(60)]

    assert pick_examples(refs, 10, seed=5, label="a") != pick_examples(refs, 10, seed=5, label="b")


# ---- end to end -------------------------------------------------------------------------------


def _post(leader: str, row: int, text: str, kind: str = "raw") -> list[object]:
    return [leader, "Acme Holdings", "batch/w1.xlsx", 1, row, text, "https://www.linkedin.com/posts/zz", kind]


ROWS = [
    _post("Ann Rao", 1, "Name\nFollow\nQuarterly update shipped\n+ Follow\nMore words here"),
    _post("Ann Rao", 2, "Top #1 priority and #Growth next"),
    _post("Bo Lee", 1, "Meet @ 5pm at the office"),
    _post("Bo Lee", 2, "Visit firm.com today"),
    _post("Cy Dunn", 1, "Really?? Yes!"),
    _post("Cy Dunn", 2, "Done ✔ next step"),
    _post("Di Fox", 1, "Hum sab milkar celebrate"),
    _post("Di Fox", 2, "I reposted my note because it holds"),
    _post("Ed Gray", 1, "Plain sentence about hiring"),
    _post("Ed Gray", 2, "cleaned version of a hiring sentence", "cleaned"),
]


@pytest.fixture
def workspace(tmp_path: Path) -> dict[str, Path]:
    raw = tmp_path / "raw"
    raw.mkdir()
    (raw / "dummy.bin").write_bytes(b"x")
    interim = tmp_path / "interim"
    interim.mkdir()
    pd.DataFrame(ROWS, columns=POST_COLUMNS).to_csv(interim / "harmonised_posts.csv", index=False)
    return {
        "raw": raw,
        "interim": interim,
        "report": tmp_path / "reports" / "extra_features.md",
        "examples": tmp_path / "derived" / "extra_features_examples.csv",
    }


def _go(workspace: dict[str, Path], per_class: int = 10) -> int:
    return run(
        raw_dir=workspace["raw"],
        interim_dir=workspace["interim"],
        report_path=workspace["report"],
        settings=FeatureSettings(examples_per_class=per_class, seed=1),
        examples_path=workspace["examples"],
    )


def _examples(workspace: dict[str, Path]) -> pd.DataFrame:
    return pd.read_csv(workspace["examples"], dtype=str, keep_default_na=False)


def _report(workspace: dict[str, Path]) -> str:
    return workspace["report"].read_text(encoding="utf-8")


def test_run_writes_a_report_with_every_section(workspace: dict[str, Path]) -> None:
    assert _go(workspace) == 0

    report = _report(workspace)
    for heading in (
        "# Extra text features",
        "## Rules",
        "## How common each feature is",
        "## Where the rules handle text badly",
        "## Needs a human decision",
    ):
        assert heading in report


def test_run_counts_only_raw_cells(workspace: dict[str, Path]) -> None:
    _go(workspace)

    assert "| Raw cells analysed | 9 |" in _report(workspace)


def test_report_lists_a_count_for_each_class_and_no_example_rows(workspace: dict[str, Path]) -> None:
    _go(workspace)

    report = _report(workspace)
    for name in CLASS_NAMES:
        assert f"### {name}" in report
    assert "| Cells matching |" in report
    assert "Leader ID" not in report
    assert "batch/w1.xlsx#1:r1" not in report


def test_report_holds_no_leader_id_of_any_leader_in_the_data(workspace: dict[str, Path]) -> None:
    _go(workspace)

    report = _report(workspace)
    for name in ("Ann Rao", "Bo Lee", "Cy Dunn", "Di Fox", "Ed Gray"):
        assert leader_id_for(name_key(name)) not in report


def test_run_writes_example_refs_with_leader_ids_to_the_derived_file(workspace: dict[str, Path]) -> None:
    _go(workspace)

    examples = _examples(workspace)
    assert list(examples.columns) == ["class", "cell", "leader_id"]
    assert set(examples["class"]) <= set(CLASS_NAMES)
    ann = leader_id_for(name_key("Ann Rao"))
    assert ((examples["cell"] == "batch/w1.xlsx#1:r1") & (examples["leader_id"] == ann)).any()


def test_run_caps_the_examples_per_class(workspace: dict[str, Path]) -> None:
    rows = [_post(f"Leader {n}", 1, "Meet @ 5pm") for n in range(8)]
    pd.DataFrame(rows, columns=POST_COLUMNS).to_csv(workspace["interim"] / "harmonised_posts.csv", index=False)

    assert _go(workspace, per_class=3) == 0

    examples = _examples(workspace)
    assert (examples["class"] == "mention_stray_at").sum() == 3
    section = _report(workspace).split("### mention_stray_at", 1)[1].split("###", 1)[0]
    assert "| Cells matching | 8 |" in section
    assert "| Examples written | 3 |" in section


def test_report_never_holds_names_post_text_companies_or_links(workspace: dict[str, Path]) -> None:
    _go(workspace)

    report = _report(workspace)
    for forbidden in ("Ann Rao", "Bo Lee", "Cy Dunn", "Di Fox", "Ed Gray", "Acme", "linkedin.com/", "firm.com",
                      "priority", "Quarterly", "hiring", "celebrate"):
        assert forbidden not in report


def test_run_is_deterministic(workspace: dict[str, Path]) -> None:
    _go(workspace)
    first = _report(workspace)
    workspace["report"].unlink()
    _go(workspace)

    assert _report(workspace) == first


def test_the_report_states_the_claim_limit_and_the_cell_level_caveat(workspace: dict[str, Path]) -> None:
    _go(workspace)

    report = _report(workspace)
    assert "image projected in public posts" in report
    assert "cell-level" in report


def test_run_fails_cleanly_when_the_harmonised_posts_are_missing(workspace: dict[str, Path]) -> None:
    (workspace["interim"] / "harmonised_posts.csv").unlink()

    assert _go(workspace) == 1
    assert not workspace["report"].exists()


def test_run_fails_cleanly_when_a_needed_column_is_missing(workspace: dict[str, Path]) -> None:
    path = workspace["interim"] / "harmonised_posts.csv"
    pd.read_csv(path, dtype=str).drop(columns=["post_text"]).to_csv(path, index=False)

    assert _go(workspace) == 1
    assert not workspace["report"].exists()


def test_run_fails_cleanly_when_the_raw_manifest_does_not_match(workspace: dict[str, Path]) -> None:
    _go(workspace)
    (workspace["raw"] / "dummy.bin").write_bytes(b"changed")
    workspace["report"].unlink()

    assert _go(workspace) == 1
    assert not workspace["report"].exists()
