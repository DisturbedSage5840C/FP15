"""Cross-check of src/stats_tools.shrink_leader_scores against the written formula, recomputed here in plain Python.

Synthetic scores only. Nothing is imported from src except the function under test and the threshold loader, so the
second computation below shares no code with the first.

The formula (normal-normal empirical Bayes, method of moments), for the K leaders with n_i >= m posts, where m is
`min_posts_per_leader` from configs/thresholds.yaml, y_ij is post j of leader i, N = sum n_i, and ybar_i = mean_j y_ij:

    grand         = (1 / K) * sum_i ybar_i                                    (unweighted mean of the leader means)
    sigma_w2      = sum_i sum_j (y_ij - ybar_i)^2 / (N - K)                    (pooled within-leader variance)
    s2            = sum_i (ybar_i - grand)^2 / (K - 1)                         (spread of the leader means)
    tau2          = max(0, s2 - sigma_w2 * (1 / K) * sum_i 1 / n_i)            (between-leader variance, floored at 0)
    w_i           = tau2 / (tau2 + sigma_w2 / n_i)        (0 when the denominator is 0)
    shrunk_i      = grand + w_i * (ybar_i - grand)

A leader with few posts has a larger sigma_w2 / n_i, so a smaller w_i, so it is pulled further toward `grand`.
Pooled variances mean the weight depends on a leader's post count only, not on that leader's own spread.
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest

from src.stats_tools import shrink_leader_scores
from src.thresholds import load_threshold

MIN_POSTS = int(load_threshold("min_posts_per_leader"))
SEEDS = tuple(range(10))
TOLERANCE = 1e-10
MIN_LEADERS, MAX_LEADERS = 4, 14
SHORT_COUNT_FLOOR = 3  # leaders below MIN_POSTS are drawn too, so the filter is exercised
EXTRA_POSTS_MAX = 40
LEADER_SD_CHOICES = (0.0, 0.5, 1.0, 2.0)  # 0.0 gives a dataset where the between-variance is about zero
NOISE_SD_CHOICES = (0.5, 1.0, 3.0)


def _reference_shrinkage(rows: list[tuple[str, float]], minimum: int) -> dict[str, dict[str, float]]:
    """The formula in the module docstring, with explicit loops and no pandas."""
    by_leader: dict[str, list[float]] = {}
    for leader, score in rows:
        by_leader.setdefault(leader, []).append(score)
    kept = {leader: scores for leader, scores in by_leader.items() if len(scores) >= minimum}
    k = len(kept)
    means = {leader: sum(scores) / len(scores) for leader, scores in kept.items()}
    grand = sum(means.values()) / k
    n_total = sum(len(scores) for scores in kept.values())
    squares = sum((y - means[leader]) ** 2 for leader, scores in kept.items() for y in scores)
    sigma_w2 = squares / (n_total - k)
    s2 = sum((mean - grand) ** 2 for mean in means.values()) / (k - 1)
    mean_inverse_n = sum(1 / len(scores) for scores in kept.values()) / k
    tau2 = max(0.0, s2 - sigma_w2 * mean_inverse_n)
    out: dict[str, dict[str, float]] = {}
    for leader, scores in kept.items():
        denominator = tau2 + sigma_w2 / len(scores)
        weight = tau2 / denominator if denominator > 0 else 0.0
        out[leader] = {
            "n_posts": float(len(scores)),
            "raw_mean": means[leader],
            "weight": weight,
            "shrunk_mean": grand + weight * (means[leader] - grand),
            "grand": grand,
            "within": sigma_w2,
            "between": tau2,
        }
    return out


def _synthetic_posts(seed: int) -> list[tuple[str, float]]:
    """Posts for 4 to 14 leaders with uneven counts (some below the minimum) and a leader effect plus noise."""
    rng = np.random.default_rng(seed)
    leaders = int(rng.integers(MIN_LEADERS, MAX_LEADERS + 1))
    leader_sd = LEADER_SD_CHOICES[seed % len(LEADER_SD_CHOICES)]  # cycled, so no-leader-effect datasets are certain
    noise_sd = float(rng.choice(NOISE_SD_CHOICES))
    rows: list[tuple[str, float]] = []
    for index in range(leaders):
        count = int(rng.integers(SHORT_COUNT_FLOOR, MIN_POSTS + EXTRA_POSTS_MAX + 1))
        effect = rng.normal(0.0, leader_sd) if leader_sd else 0.0
        rows.extend((f"L{index:02d}", float(effect + rng.normal(0.0, noise_sd))) for _ in range(count))
    return rows


def _frame(rows: list[tuple[str, float]]) -> pd.DataFrame:
    return pd.DataFrame(rows, columns=["leader_id", "score"])


def _enough_leaders(rows: list[tuple[str, float]]) -> bool:
    counts: dict[str, int] = {}
    for leader, _ in rows:
        counts[leader] = counts.get(leader, 0) + 1
    return sum(1 for count in counts.values() if count >= MIN_POSTS) >= 2


@pytest.mark.parametrize("seed", SEEDS)
def test_shrinkage_matches_the_written_formula(seed: int) -> None:
    rows = _synthetic_posts(seed)
    if not _enough_leaders(rows):
        pytest.skip("fewer than two leaders at the minimum for this seed (the function refuses these by design)")

    result = shrink_leader_scores(_frame(rows))

    expected = _reference_shrinkage(rows, MIN_POSTS)
    table = result.leaders.set_index("leader_id")
    assert set(table.index) == set(expected)
    for leader, values in expected.items():
        assert table.loc[leader, "n_posts"] == values["n_posts"]
        for column in ("raw_mean", "weight", "shrunk_mean"):
            assert table.loc[leader, column] == pytest.approx(values[column], abs=TOLERANCE, rel=0)
    first = next(iter(expected.values()))
    assert result.grand_mean == pytest.approx(first["grand"], abs=TOLERANCE, rel=0)
    assert result.within_variance == pytest.approx(first["within"], abs=TOLERANCE, rel=0)
    assert result.between_variance == pytest.approx(first["between"], abs=TOLERANCE, rel=0)


def test_ten_datasets_are_tested_and_include_a_floored_between_variance() -> None:
    usable = [seed for seed in SEEDS if _enough_leaders(_synthetic_posts(seed))]
    floored = [
        seed for seed in usable if _reference_shrinkage(_synthetic_posts(seed), MIN_POSTS).popitem()[1]["between"] == 0.0
    ]

    assert len(usable) == len(SEEDS)  # none of the ten is skipped, so ten datasets really are compared
    assert floored  # at least one dataset exercises the "floored at zero" branch


def _leaders_with_counts(counts: dict[str, int], leader_sd: float = 2.0, noise_sd: float = 1.0) -> pd.DataFrame:
    rng = np.random.default_rng(sum(counts.values()))
    rows = []
    for leader, count in counts.items():
        effect = rng.normal(0.0, leader_sd)
        rows.extend((leader, float(effect + rng.normal(0.0, noise_sd))) for _ in range(count))
    return _frame(rows)


def test_weight_on_own_mean_rises_with_post_count() -> None:
    counts = {"A": MIN_POSTS, "B": MIN_POSTS + 5, "C": MIN_POSTS + 15, "D": MIN_POSTS + 40, "E": MIN_POSTS + 100}

    result = shrink_leader_scores(_leaders_with_counts(counts))

    by_count = result.leaders.sort_values("n_posts")
    assert result.between_variance > 0  # otherwise every weight is 0 and the property would hold for nothing
    weights = by_count["weight"].to_numpy()
    assert all(later > earlier for earlier, later in zip(weights, weights[1:]))
    assert all(0 < weight < 1 for weight in weights)


def _same_variance_pair(count: int) -> pd.DataFrame:
    """Two leaders with identical spread (the same pattern shifted by 3), plus filler leaders so the pooling is real."""
    pattern = [math.sin(index) for index in range(count)]
    rows = [("P1", value) for value in pattern] + [("P2", value + 3.0) for value in pattern]
    filler = _leaders_with_counts({"F1": MIN_POSTS + 10, "F2": MIN_POSTS + 30})
    return pd.concat([_frame(rows), filler], ignore_index=True)


def test_two_leaders_with_the_same_count_and_variance_get_the_same_weight() -> None:
    result = shrink_leader_scores(_same_variance_pair(MIN_POSTS + 5))

    weights = result.leaders.set_index("leader_id")["weight"]
    assert weights["P1"] == pytest.approx(weights["P2"], abs=TOLERANCE, rel=0)
    assert weights["P1"] > 0


def test_weight_depends_on_count_only_not_on_the_leaders_own_spread() -> None:
    count = MIN_POSTS + 5
    calm = [("C1", math.sin(index) * 0.1) for index in range(count)]
    wild = [("C2", math.sin(index) * 5.0 + 3.0) for index in range(count)]
    filler = _leaders_with_counts({"F1": MIN_POSTS + 10, "F2": MIN_POSTS + 30})

    result = shrink_leader_scores(pd.concat([_frame(calm + wild), filler], ignore_index=True))

    weights = result.leaders.set_index("leader_id")["weight"]
    assert weights["C1"] == pytest.approx(weights["C2"], abs=TOLERANCE, rel=0)
