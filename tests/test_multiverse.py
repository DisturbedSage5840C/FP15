"""Provisional robustness multiverse (src/multiverse.py). Invented ids and numbers only: no real data.

Everything here is exploratory and about the image projected in public posts. The multiverse does not replace the
pre-registration, and a p-value says nothing about causes.
"""
from __future__ import annotations

import math
import re
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.eda_balance import CEO_TYPE_FACTOR, GENDER_FACTOR, SECTOR_FACTOR, SIZE_FACTOR, TITLE_FACTOR
from src.eda_common import SMALL, load_eda_settings
from src.multiverse import (
    ALL_CELLS,
    CELL_SETS,
    LOG,
    NO_HINGLISH,
    NO_REPOSTS,
    RAW,
    SCALES,
    TRIMMED,
    MultiverseSettings,
    Variant,
    build_variants,
    load_multiverse_settings,
    render_report,
    run_multiverse,
    variant_frame,
)
from src.provisional_common import BANNER, write_banner_csv

EDA = load_eda_settings()
SETTINGS = load_multiverse_settings()
LEADERS = 73
POSTS_EACH = 16
SINGULAR, PLURAL = "singular_per_100", "plural_per_100"
MAIN = Variant(EDA.min_posts, RAW, ALL_CELLS)


def _id(index: int) -> str:
    return f"L{index:03d}"


def _labels(count: int = LEADERS) -> pd.DataFrame:
    rows = [
        {
            "leader_id": _id(i),
            CEO_TYPE_FACTOR: "Founder-CEO" if i % 2 == 0 else "Professional CEO",
            TITLE_FACTOR: ("CEO", "Managing director", "Chair")[(i * 7 + i // 3) % 3],
            GENDER_FACTOR: "man" if (i // 2) % 2 == 0 else "woman",
            SECTOR_FACTOR: "Sector",
            SIZE_FACTOR: f"size band {(i // 5) % 3 + 1}",
        }
        for i in range(count)
    ]
    return pd.DataFrame(rows)


def _measures(count: int = LEADERS, posts_each: int = POSTS_EACH, seed: int = 5) -> pd.DataFrame:
    """Even leaders (Founder-CEO) say 'I' about 3 more per 100 words; the plural rate has no group shift."""
    rng = np.random.default_rng(seed)
    rows = []
    for i in range(count):
        shift = rng.normal(0, 1.0)
        for post in range(posts_each):
            rows.append(
                {
                    "leader_id": _id(i),
                    "post_id": f"p{len(rows):06d}",
                    "word_count": 60,
                    SINGULAR: max(0.0, 5.0 + (3.0 if i % 2 == 0 else 0.0) + shift + rng.normal(0, 1.0)),
                    PLURAL: max(0.0, 4.0 + rng.normal(0, 1.5)),
                    "hinglish_flag": int(i < 4 and post < 4),
                    "repost_flag": float(i in (5, 6) and post < 3),
                }
            )
    return pd.DataFrame(rows)


def _frame(measures: pd.DataFrame, variant: Variant, measure: str = SINGULAR, labels: pd.DataFrame | None = None):
    return variant_frame(measures, _labels() if labels is None else labels, measure, variant, SETTINGS, EDA)


# --- settings and the variant grid -------------------------------------------------------------------------------


def test_the_settings_come_from_the_config_with_the_main_minimum_between_the_lower_and_higher() -> None:
    assert SETTINGS.min_posts_lower < EDA.min_posts < SETTINGS.min_posts_higher
    assert 0 < SETTINGS.trim_share < 1
    assert SETTINGS.log_offset > 0


def _config(tmp_path: Path, body: str) -> Path:
    path = tmp_path / "thresholds.yaml"
    path.write_text("min_posts_per_leader: 15\neda_disclosure_min_leaders: 5\n" + body, encoding="utf-8")
    return path


@pytest.mark.parametrize(
    "body",
    [
        "multiverse:\n  min_posts_lower: 15\n  min_posts_higher: 20\n  trim_share: 0.01\n  log_offset: 1\n",
        "multiverse:\n  min_posts_lower: 10\n  min_posts_higher: 15\n  trim_share: 0.01\n  log_offset: 1\n",
        "multiverse:\n  min_posts_lower: 10\n  min_posts_higher: 20\n  trim_share: 0\n  log_offset: 1\n",
        "multiverse:\n  min_posts_lower: 10\n  min_posts_higher: 20\n  trim_share: 0.01\n  log_offset: 0\n",
        "multiverse:\n  min_posts_lower: 10\n  min_posts_higher: 20\n  trim_share: 0.01\n",
        "other: 1\n",
    ],
)
def test_a_bad_or_missing_multiverse_setting_is_an_error_not_a_default(tmp_path: Path, body: str) -> None:
    with pytest.raises(ValueError):
        load_multiverse_settings(_config(tmp_path, body))


def test_variants_are_every_combination_of_minimum_scale_and_cell_set() -> None:
    variants = build_variants(EDA.min_posts, SETTINGS)

    assert len(variants) == 3 * 3 * 3
    assert len(set(variants)) == len(variants)
    assert {v.min_posts for v in variants} == {SETTINGS.min_posts_lower, EDA.min_posts, SETTINGS.min_posts_higher}
    assert {v.scale for v in variants} == set(SCALES) == {RAW, LOG, TRIMMED}
    assert {v.cells for v in variants} == {name for name, _ in CELL_SETS} == {ALL_CELLS, NO_HINGLISH, NO_REPOSTS}
    assert MAIN in variants


def test_the_number_of_variants_follows_the_settings_not_a_fixed_number() -> None:
    wider = MultiverseSettings(8, 25, SETTINGS.trim_share, SETTINGS.log_offset)

    assert len(build_variants(EDA.min_posts, wider)) == 27
    assert {v.min_posts for v in build_variants(EDA.min_posts, wider)} == {8, EDA.min_posts, 25}


# --- one variant's frame -----------------------------------------------------------------------------------------


def test_a_variant_frame_has_the_rate_as_y_the_leader_and_one_column_per_factor() -> None:
    frame = _frame(_measures(), MAIN)

    assert {"y", "leader_id", CEO_TYPE_FACTOR, TITLE_FACTOR, GENDER_FACTOR, SIZE_FACTOR} <= set(frame.columns)
    assert frame["leader_id"].nunique() == LEADERS
    assert len(frame) == LEADERS * POSTS_EACH


def test_the_post_minimum_is_applied_to_the_cells_of_that_variant() -> None:
    measures = _measures()
    position = measures.groupby("leader_id").cumcount()
    short = measures[~((measures["leader_id"] == _id(1)) & (position >= 12))]
    assert (short["leader_id"] == _id(1)).sum() == 12

    low = _frame(short, Variant(SETTINGS.min_posts_lower, RAW, ALL_CELLS))
    main = _frame(short, MAIN)

    assert _id(1) in set(low["leader_id"])
    assert _id(1) not in set(main["leader_id"])


def test_the_hinglish_set_drops_flagged_cells_and_the_repost_set_drops_repost_cells() -> None:
    measures = _measures()
    lower = SETTINGS.min_posts_lower

    everything = _frame(measures, Variant(lower, RAW, ALL_CELLS))
    no_hinglish = _frame(measures, Variant(lower, RAW, NO_HINGLISH))
    no_reposts = _frame(measures, Variant(lower, RAW, NO_REPOSTS))

    assert len(everything) - len(no_hinglish) == int(measures["hinglish_flag"].sum())
    assert len(everything) - len(no_reposts) == int(measures["repost_flag"].sum())


def test_a_cell_with_no_repost_flag_is_not_counted_as_a_non_repost() -> None:
    measures = _measures().assign(repost_flag=np.nan)

    frame = _frame(measures, Variant(SETTINGS.min_posts_lower, RAW, NO_REPOSTS))

    assert frame.empty


def test_log_scale_is_used_only_in_the_log_variant() -> None:
    measures = _measures()
    raw = _frame(measures, MAIN)
    logged = _frame(measures, Variant(EDA.min_posts, LOG, ALL_CELLS))
    trimmed = _frame(measures, Variant(EDA.min_posts, TRIMMED, ALL_CELLS))

    assert np.allclose(np.log(SETTINGS.log_offset + raw["y"].to_numpy()), logged["y"].to_numpy())
    assert np.allclose(raw["y"].to_numpy(), measures[SINGULAR].to_numpy())
    assert set(trimmed["y"]) <= set(raw["y"])  # trimmed rows are raw values, only fewer of them
    assert not np.allclose(raw["y"].to_numpy(), logged["y"].to_numpy())


def _graded_measures(count: int) -> pd.DataFrame:
    """Leader i has every post equal to i + 1, so the leader means are exactly 1..count."""
    rows = [
        {
            "leader_id": _id(i), "post_id": f"p{i:03d}{post:02d}", "word_count": 60,
            SINGULAR: float(i + 1), PLURAL: float(i + 1), "hinglish_flag": 0, "repost_flag": 0.0,
        }
        for i in range(count)
        for post in range(POSTS_EACH)
    ]
    return pd.DataFrame(rows)


def test_trimming_removes_the_top_share_of_leader_means_and_nothing_else() -> None:
    count = 200
    measures = _graded_measures(count)
    labels = _labels(count)

    trimmed = _frame(measures, Variant(EDA.min_posts, TRIMMED, ALL_CELLS), labels=labels)
    raw = _frame(measures, MAIN, labels=labels)

    removed = set(raw["leader_id"]) - set(trimmed["leader_id"])
    assert removed == {_id(count - 1), _id(count - 2)}  # 1 percent of 200 leaders, the two highest means
    assert len(trimmed) == (count - 2) * POSTS_EACH
    assert trimmed["y"].max() == count - 2


def test_trimming_follows_the_configured_share() -> None:
    count = 200
    settings = MultiverseSettings(SETTINGS.min_posts_lower, SETTINGS.min_posts_higher, 0.05, SETTINGS.log_offset)

    trimmed = variant_frame(
        _graded_measures(count), _labels(count), SINGULAR, Variant(EDA.min_posts, TRIMMED, ALL_CELLS), settings, EDA
    )

    assert trimmed["leader_id"].nunique() == count - 10


def test_a_frame_with_no_qualifying_leader_is_empty_not_an_error() -> None:
    frame = _frame(_measures(count=3, posts_each=4), MAIN)

    assert frame.empty
    assert "y" in frame.columns


# --- the fits ----------------------------------------------------------------------------------------------------


@pytest.fixture(scope="module")
def tests_run() -> list:
    return run_multiverse(_measures(), _labels(), EDA, SETTINGS)


def test_every_variant_of_both_measures_is_fitted_with_three_tested_terms(tests_run: list) -> None:
    assert len(tests_run) == 2 * 27 * 3
    assert {t.measure for t in tests_run} == {SINGULAR, PLURAL}
    assert {t.factor for t in tests_run} == {CEO_TYPE_FACTOR, TITLE_FACTOR, SIZE_FACTOR}
    assert len({(t.measure, t.variant) for t in tests_run}) == 2 * 27


def test_only_the_founder_vs_professional_row_carries_an_estimate_with_an_interval(tests_run: list) -> None:
    two_group = [t for t in tests_run if t.factor == CEO_TYPE_FACTOR]
    joint = [t for t in tests_run if t.factor != CEO_TYPE_FACTOR]

    assert all(t.df == 1 and not math.isnan(t.estimate) and t.lower < t.estimate < t.upper for t in two_group)
    assert all(math.isnan(t.estimate) for t in joint)


def test_benjamini_hochberg_runs_once_across_every_comparison_and_never_lowers_a_p(tests_run: list) -> None:
    assert all(t.adjusted_p >= t.p_value for t in tests_run if not math.isnan(t.p_value))
    ordered = sorted((t for t in tests_run if not math.isnan(t.p_value)), key=lambda t: t.p_value)
    adjusted = [t.adjusted_p for t in ordered]
    assert adjusted == sorted(adjusted)
    assert max(adjusted) <= 1.0


def test_an_invented_group_shift_keeps_its_direction_in_every_i_rate_variant(tests_run: list) -> None:
    estimates = [t.estimate for t in tests_run if t.measure == SINGULAR and t.factor == CEO_TYPE_FACTOR]

    assert all(value < 0 for value in estimates)  # Professional minus Founder, and Founder leaders say 'I' more


def test_the_main_variant_is_among_the_fits_with_every_invented_leader(tests_run: list) -> None:
    main_rows = [t for t in tests_run if t.measure == SINGULAR and t.variant == MAIN]

    assert len(main_rows) == 3
    assert {t.leaders for t in main_rows} == {LEADERS}


def test_a_variant_with_too_few_leaders_reports_no_numbers_and_does_not_fail() -> None:
    results = run_multiverse(_measures(count=3), _labels(3), EDA, SETTINGS)

    assert len(results) == 2 * 27 * 3
    assert all(math.isnan(t.p_value) and math.isnan(t.estimate) for t in results)
    assert all(t.note for t in results)


# --- the report --------------------------------------------------------------------------------------------------


@pytest.fixture(scope="module")
def report(tests_run: list) -> str:
    return render_report(tests_run, EDA, SETTINGS)


def test_report_starts_with_the_banner_and_says_it_does_not_replace_the_pre_registration(report: str) -> None:
    assert report.startswith(f"> {BANNER}")
    assert "does not replace the pre-registration" in report
    assert "exploratory" in report.lower()


def test_report_shows_every_variant_for_both_measures_in_each_table(report: str) -> None:
    assert report.count(f"| {SETTINGS.min_posts_lower} |") >= 2 * 9 * 2
    assert report.count(f"| {SETTINGS.min_posts_higher} |") >= 2 * 9 * 2
    assert report.count(f"| {EDA.min_posts} |") >= 2 * 9 * 2
    for name in (ALL_CELLS, NO_HINGLISH, NO_REPOSTS):
        assert name in report


def test_report_counts_variants_in_the_same_direction_and_with_raw_p_below_the_fdr_level(report: str) -> None:
    lines = [line for line in report.splitlines() if "same direction" in line]

    assert len(lines) == 2  # one per measure
    assert all(re.search(r"\d+ of \d+", line) for line in lines)
    assert all("raw p below 0.05" in line for line in lines)


def test_report_has_no_leader_id_no_causal_and_no_personality_wording(report: str) -> None:
    body = report.split("\n", 1)[1].lower()

    assert not re.search(r"\bL\d{3}\b", report)
    for word in ("personality", "narcissis", "because", "causes", "caused", "effect of", "leads to"):
        assert word not in body


def test_a_variant_with_too_few_leaders_shows_the_disclosure_mark_in_the_report() -> None:
    results = run_multiverse(_measures(count=3), _labels(3), EDA, SETTINGS)

    text = render_report(results, EDA, SETTINGS)

    assert SMALL in text
    assert "n/a" in text
    assert not re.search(r"\|\s3\s\|", text)  # the true count of 3 leaders is never printed


def test_fitted_leader_counts_in_the_report_use_the_disclosure_rules(report: str) -> None:
    assert "leaders fitted" in report
    assert f"{LEADERS:,}" in report


def test_run_refuses_when_the_manifest_is_bad_and_writes_nothing(tmp_path: Path) -> None:
    from src.multiverse import run

    measures_path = tmp_path / "measures.csv"
    write_banner_csv(_measures(), measures_path)

    failed = run(raw_dir=tmp_path / "no_such_raw", measures_path=measures_path, report_path=tmp_path / "r.md")

    assert failed == 1
    assert not (tmp_path / "r.md").exists()
