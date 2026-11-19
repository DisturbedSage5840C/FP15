"""Tests for the synthetic gold-set sampler audit. Every table here is invented; nothing reads real data."""
from __future__ import annotations

import re

import pandas as pd
import pytest

from src.gold_set import load_gold_settings
from src.gold_set_audit import (
    AUDIT_SEEDS,
    FOUNDER_SHARE,
    GENDER_ZERO_SHARE,
    LEADERS,
    audit_pool,
    empty_strata,
    render_report,
    restrict_to_min_posts,
    summarise_seeds,
    synthetic_posts,
)
from src.thresholds import load_threshold

SETTINGS = load_gold_settings()
MIN_POSTS = int(load_threshold("min_posts_per_leader"))
STRATUM_COUNT = 4
HEAVY_TAIL_RATIO = 5  # the longest leader has at least this many times the median leader's posts
TINY_LEADERS = 20  # too few leaders to leave `gold_set_size` posts after the cap


def _per_leader(posts: pd.DataFrame) -> pd.DataFrame:
    return posts.groupby("leader_id").agg(
        posts=("post_id", "size"),
        ceo_types=("ceo_type", "nunique"),
        genders=("gender_as_coded", "nunique"),
        ceo_type=("ceo_type", "first"),
        gender=("gender_as_coded", "first"),
    )


def test_synthetic_table_is_identical_for_the_same_seed() -> None:
    first = synthetic_posts(3)

    second = synthetic_posts(3)

    pd.testing.assert_frame_equal(first, second)


def test_synthetic_table_differs_between_seeds() -> None:
    assert not synthetic_posts(1).equals(synthetic_posts(2))


def test_synthetic_table_has_about_560_leaders_with_the_requested_group_sizes() -> None:
    leaders = _per_leader(synthetic_posts(0))

    assert len(leaders) == LEADERS
    assert (leaders["ceo_type"] == "Founder-CEO").sum() == round(FOUNDER_SHARE * LEADERS)
    assert (leaders["gender"] == 0).sum() == round(GENDER_ZERO_SHARE * LEADERS)


def test_posts_per_leader_are_heavy_tailed() -> None:
    posts_per_leader = _per_leader(synthetic_posts(0))["posts"]

    assert posts_per_leader.max() >= HEAVY_TAIL_RATIO * posts_per_leader.median()
    assert posts_per_leader.min() >= 1


def test_every_leader_sits_in_exactly_one_stratum() -> None:
    leaders = _per_leader(synthetic_posts(0))

    assert (leaders["ceo_types"] == 1).all()
    assert (leaders["genders"] == 1).all()


def test_post_ids_are_unique() -> None:
    posts = synthetic_posts(0)

    assert posts["post_id"].is_unique


def test_restricting_to_the_minimum_keeps_only_leaders_at_or_above_it() -> None:
    posts = synthetic_posts(0)

    restricted = restrict_to_min_posts(posts, MIN_POSTS)

    kept = _per_leader(restricted)["posts"]
    assert kept.min() >= MIN_POSTS
    assert 0 < len(kept) < posts["leader_id"].nunique()
    assert set(restricted["leader_id"]) <= set(posts["leader_id"])


def test_restricting_does_not_change_the_input_table() -> None:
    posts = synthetic_posts(0)
    before = posts.copy()

    restrict_to_min_posts(posts, MIN_POSTS)

    pd.testing.assert_frame_equal(posts, before)


@pytest.mark.parametrize("minimum", [None, MIN_POSTS])
def test_audit_draws_exactly_the_gold_set_size(minimum: int | None) -> None:
    posts = synthetic_posts(0) if minimum is None else restrict_to_min_posts(synthetic_posts(0), minimum)

    audit = audit_pool(posts, SETTINGS)

    assert audit["drawn"].sum() == SETTINGS.size
    assert audit["quota"].sum() == SETTINGS.size


def test_audit_counts_are_nested_posts_then_cap_then_drawn() -> None:
    audit = audit_pool(synthetic_posts(0), SETTINGS)

    assert (audit["drawn"] <= audit["posts_after_cap"]).all()
    assert (audit["posts_after_cap"] <= audit["posts"]).all()
    assert (audit["leaders_used"] <= audit["leaders"]).all()


def test_no_leader_gives_more_than_the_cap_so_drawn_is_bounded_by_leaders_used() -> None:
    audit = audit_pool(synthetic_posts(0), SETTINGS)

    assert (audit["drawn"] <= audit["leaders_used"] * SETTINGS.max_posts_per_leader).all()


def test_audit_lists_all_four_strata_even_when_one_has_no_leaders() -> None:
    posts = synthetic_posts(0)
    without_small_cell = posts[~((posts["ceo_type"] == "Founder-CEO") & (posts["gender_as_coded"] == 0))]

    audit = audit_pool(without_small_cell, SETTINGS)

    assert len(audit) == STRATUM_COUNT
    empty = audit[(audit["ceo_type"] == "Founder-CEO") & (audit["gender_as_coded"] == "0")].iloc[0]
    assert (empty["leaders"], empty["posts"], empty["quota"], empty["drawn"], empty["unfilled"]) == (0, 0, 0, 0, 0)


@pytest.mark.parametrize("minimum", [None, MIN_POSTS])
def test_no_stratum_is_unfilled_on_any_audit_seed(minimum: int | None) -> None:
    for seed in AUDIT_SEEDS:
        posts = synthetic_posts(seed) if minimum is None else restrict_to_min_posts(synthetic_posts(seed), minimum)

        audit = audit_pool(posts, SETTINGS)

        assert (audit["unfilled"] == 0).all(), f"seed {seed}: a stratum could not be filled"


def test_audit_refuses_a_pool_too_small_for_the_gold_set() -> None:
    posts = synthetic_posts(0, leaders=TINY_LEADERS)

    with pytest.raises(ValueError, match="remain after the per-leader cap"):
        audit_pool(posts, SETTINGS)


def test_seed_summary_has_one_row_per_stratum_and_counts_no_failures_on_a_normal_pool() -> None:
    summary, cannot_draw = summarise_seeds(AUDIT_SEEDS, SETTINGS, minimum=None)

    assert len(summary) == STRATUM_COUNT
    assert cannot_draw == 0
    assert (summary["drawn_min"] <= summary["drawn_median"]).all()
    assert (summary["drawn_median"] <= summary["drawn_max"]).all()
    assert (summary["seeds_unfilled"] == 0).all()


def test_seed_summary_counts_the_seeds_on_which_the_sampler_refuses() -> None:
    _, cannot_draw = summarise_seeds((0, 1), SETTINGS, minimum=None, leaders=TINY_LEADERS)

    assert cannot_draw == 2


def test_report_is_labelled_synthetic_and_names_both_pool_options() -> None:
    report = render_report(SETTINGS, MIN_POSTS)

    assert "SYNTHETIC" in report
    assert "Option A" in report and "Option B" in report
    assert str(SETTINGS.max_posts_per_leader) in report
    assert "proposal" in report.lower()


def test_report_holds_counts_only_no_ids_or_text() -> None:
    report = render_report(SETTINGS, MIN_POSTS)

    assert not re.search(r"\bS\d{4}\b", report)  # synthetic leader ids
    assert not re.search(r"\bP\d{6}\b", report)  # synthetic post ids
    assert "http" not in report


def test_a_stratum_with_no_posts_in_the_pool_is_counted_as_empty_not_as_filled() -> None:
    posts = synthetic_posts(0)
    without_small_cell = posts[~((posts["ceo_type"] == "Founder-CEO") & (posts["gender_as_coded"] == 0))]

    audit = audit_pool(without_small_cell, SETTINGS)

    assert empty_strata(audit) == 1
    assert empty_strata(audit_pool(posts, SETTINGS)) == 0


def test_seed_summary_counts_seeds_on_which_each_stratum_is_empty() -> None:
    summary, _ = summarise_seeds(AUDIT_SEEDS, SETTINGS, minimum=MIN_POSTS)

    assert "seeds_empty" in summary.columns
    assert (summary["seeds_empty"] >= 0).all()
    assert (summary["seeds_empty"] <= len(AUDIT_SEEDS)).all()


def test_report_states_how_many_strata_have_nothing_to_draw() -> None:
    report = render_report(SETTINGS, MIN_POSTS)

    assert "no posts in the pool" in report
