"""Mixed-model helpers for the provisional comparisons (src/provisional_models.py). Invented numbers only.

Exploratory. A p-value here says nothing about causes and nothing about personality: the data are rates in public posts.
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

from src.provisional_models import FactorTest, VarianceShare, factor_tests, variance_share

POSTS_EACH = 12
LEADERS = 60


def invented_posts(effect: float = 3.0, leader_sd: float = 2.0, seed: int = 11) -> pd.DataFrame:
    """Leaders alternate between group 'x' and 'y' of factor A (a real shift of `effect`); factor B is unrelated noise."""
    rng = np.random.default_rng(seed)
    rows = []
    for leader in range(LEADERS):
        level_a = "x" if leader % 2 == 0 else "y"
        level_b = ("p", "q", "r")[(leader * 7 + leader // 3) % 3]
        leader_shift = rng.normal(0, leader_sd)
        for _ in range(POSTS_EACH):
            value = 5.0 + leader_shift + (effect if level_a == "x" else 0.0) + rng.normal(0, 1.0)
            rows.append({"leader_id": f"L{leader:03d}", "y": value, "A": level_a, "B": level_b})
    return pd.DataFrame(rows)


def test_variance_share_is_high_when_leaders_differ_much_more_than_posts() -> None:
    share = variance_share(invented_posts(effect=0.0, leader_sd=3.0))

    assert isinstance(share, VarianceShare)
    assert 0.7 < share.icc < 0.98
    assert share.leaders == LEADERS
    assert share.posts == LEADERS * POSTS_EACH
    assert share.note == ""


def test_variance_share_is_near_zero_when_only_posts_vary() -> None:
    share = variance_share(invented_posts(effect=0.0, leader_sd=0.0))

    assert 0.0 <= share.icc < 0.1


def test_a_real_group_shift_gives_a_small_p_and_noise_does_not() -> None:
    tests = {test.factor: test for test in factor_tests(invented_posts(), ("A", "B"))}

    assert isinstance(tests["A"], FactorTest)
    assert tests["A"].p_value < 0.01
    assert tests["A"].df == 1
    assert tests["B"].df == 2
    assert tests["B"].p_value > 0.05


def test_a_factor_with_one_level_is_reported_not_crashed() -> None:
    frame = invented_posts().assign(C="same")

    tests = {test.factor: test for test in factor_tests(frame, ("A", "C"))}

    assert math.isnan(tests["C"].p_value)
    assert "fewer than 2 levels" in tests["C"].note
    assert tests["A"].p_value < 0.01


def test_rows_with_a_missing_rate_are_ignored() -> None:
    frame = invented_posts()
    frame.loc[frame.index[:5], "y"] = np.nan

    share = variance_share(frame)

    assert share.posts == LEADERS * POSTS_EACH - 5


def test_too_few_leaders_is_reported_with_a_note() -> None:
    frame = invented_posts()
    frame = frame[frame["leader_id"].isin({"L000", "L001"})]

    share = variance_share(frame)

    assert math.isnan(share.icc)
    assert share.note != ""


def test_a_two_level_factor_reports_its_difference_with_an_interval_and_the_direction() -> None:
    tests = {test.factor: test for test in factor_tests(invented_posts(), ("A", "B"))}

    test = tests["A"]
    assert test.contrast == "y minus x"
    assert -4.0 < test.estimate < -2.0
    assert test.lower < test.estimate < test.upper
    assert test.lower < -3.0 < test.upper


def test_the_interval_and_the_p_value_agree_about_zero() -> None:
    tests = {test.factor: test for test in factor_tests(invented_posts(effect=0.0), ("A", "B"))}

    test = tests["A"]
    assert (test.lower < 0.0 < test.upper) == (test.p_value > 0.05)


def test_a_factor_with_three_levels_has_no_single_difference() -> None:
    tests = {test.factor: test for test in factor_tests(invented_posts(), ("A", "B"))}

    assert tests["B"].contrast == ""
    assert math.isnan(tests["B"].estimate)
    assert math.isnan(tests["B"].lower)
    assert math.isnan(tests["B"].upper)


def test_a_one_degree_test_equals_the_two_sided_normal_test_of_the_difference() -> None:
    from scipy.stats import norm

    test = {t.factor: t for t in factor_tests(invented_posts(effect=0.4), ("A",))}["A"]

    half_width = (test.upper - test.lower) / 2
    z = abs(test.estimate) / (half_width / norm.ppf(0.975))
    assert math.isclose(2 * norm.sf(z), test.p_value, rel_tol=1e-6)
