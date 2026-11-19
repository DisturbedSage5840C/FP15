"""Tests for src/stats_tools.py on invented scores only. Nothing here reads real data."""
from __future__ import annotations

import math
from pathlib import Path

import pandas as pd
import pytest

from src.stats_tools import benjamini_hochberg, shrink_leader_scores
from src.thresholds import load_threshold

MIN_POSTS = int(load_threshold("min_posts_per_leader"))
FDR_Q = float(load_threshold("fdr_q"))


def _leader(leader_id: str, mean: float, posts: int) -> pd.DataFrame:
    """`posts` scores at exactly mean +1, mean -1, mean +1 ... so the leader mean is `mean` (posts must be even)."""
    scores = [mean + (1.0 if index % 2 == 0 else -1.0) for index in range(posts)]
    return pd.DataFrame({"leader_id": leader_id, "score": scores})


def _four_leaders_and_a_small_one() -> pd.DataFrame:
    few, many = MIN_POSTS + 1, 10 * MIN_POSTS
    return pd.concat(
        [
            _leader("A_few_high", 3.0, few),
            _leader("B_many_high", 3.0, many),
            _leader("C_few_low", 0.0, few),
            _leader("D_many_low", 0.0, many),
            _leader("E_too_small", 100.0, MIN_POSTS - 1),
        ],
        ignore_index=True,
    )


# ---------------------------------------------------------------- shrinkage
def test_leaders_with_few_posts_are_pulled_more_toward_the_overall_mean_than_leaders_with_many() -> None:
    posts = _four_leaders_and_a_small_one()

    result = shrink_leader_scores(posts)

    table = result.leaders.set_index("leader_id")
    pull_few = table.loc["A_few_high", "raw_mean"] - table.loc["A_few_high", "shrunk_mean"]
    pull_many = table.loc["B_many_high", "raw_mean"] - table.loc["B_many_high", "shrunk_mean"]
    assert 0 < pull_many < pull_few
    assert table.loc["A_few_high", "weight"] < table.loc["B_many_high", "weight"] < 1


def test_shrunk_means_match_the_hand_computed_normal_normal_formula() -> None:
    # Leader means 3, 3, 0, 0 -> overall mean 1.5, variance of leader means (ddof=1) = 4 * 2.25 / 3 = 3.
    # Scores are +-1 around each mean, so each leader's sum of squares is n; pooled within variance = sum(n) / (sum(n) - 4).
    few, many = MIN_POSTS + 1, 10 * MIN_POSTS
    total = 2 * few + 2 * many
    within = total / (total - 4)
    between = 3.0 - within * (2 / few + 2 / many) / 4
    expected_weight_few = between / (between + within / few)
    expected_shrunk_few = 1.5 + expected_weight_few * (3.0 - 1.5)

    result = shrink_leader_scores(_four_leaders_and_a_small_one())

    row = result.leaders.set_index("leader_id").loc["A_few_high"]
    assert result.grand_mean == pytest.approx(1.5)
    assert result.within_variance == pytest.approx(within)
    assert result.between_variance == pytest.approx(between)
    assert row["weight"] == pytest.approx(expected_weight_few)
    assert row["shrunk_mean"] == pytest.approx(expected_shrunk_few)


def test_shrinkage_is_symmetric_about_the_overall_mean() -> None:
    result = shrink_leader_scores(_four_leaders_and_a_small_one())

    table = result.leaders.set_index("leader_id")
    high = table.loc["A_few_high", "shrunk_mean"] - result.grand_mean
    low = result.grand_mean - table.loc["C_few_low", "shrunk_mean"]
    assert high == pytest.approx(low)


def test_leaders_below_the_minimum_post_count_are_left_out_not_guessed() -> None:
    result = shrink_leader_scores(_four_leaders_and_a_small_one())

    assert set(result.leaders["leader_id"]) == {"A_few_high", "B_many_high", "C_few_low", "D_many_low"}
    assert result.grand_mean == pytest.approx(1.5)  # the 100.0 leader did not leak into it


def test_a_leader_exactly_at_the_minimum_is_included_and_one_post_short_is_not() -> None:
    at_minimum = MIN_POSTS + MIN_POSTS % 2  # _leader needs an even number of posts
    posts = pd.concat(
        [
            _leader("at_min", 2.0, at_minimum),
            _leader("big_one", 0.0, 2 * at_minimum),
            _leader("big_two", 1.0, 2 * at_minimum),
        ],
        ignore_index=True,
    )

    at_threshold = shrink_leader_scores(posts, min_posts=at_minimum)
    one_above = shrink_leader_scores(posts, min_posts=at_minimum + 1)

    assert "at_min" in set(at_threshold.leaders["leader_id"])
    assert "at_min" not in set(one_above.leaders["leader_id"])


def test_default_minimum_comes_from_the_thresholds_file(tmp_path: Path) -> None:
    thresholds = tmp_path / "thresholds.yaml"
    thresholds.write_text("min_posts_per_leader: 4\n", encoding="utf-8")
    posts = pd.concat([_leader("p", 1.0, 4), _leader("q", 0.0, 6), _leader("r", 0.0, 2)], ignore_index=True)

    result = shrink_leader_scores(posts, thresholds_path=thresholds)

    assert set(result.leaders["leader_id"]) == {"p", "q"}
    assert result.min_posts == 4


def test_missing_scores_are_not_counted_as_posts() -> None:
    posts = _four_leaders_and_a_small_one()
    blanks = pd.DataFrame({"leader_id": ["C_few_low"] * 20, "score": [math.nan] * 20})
    padded = pd.concat([posts, blanks], ignore_index=True)

    base = shrink_leader_scores(posts).leaders.set_index("leader_id")
    with_blanks = shrink_leader_scores(padded).leaders.set_index("leader_id")

    assert with_blanks.loc["C_few_low", "n_posts"] == base.loc["C_few_low", "n_posts"]
    assert with_blanks.loc["C_few_low", "shrunk_mean"] == pytest.approx(base.loc["C_few_low", "shrunk_mean"])


def test_when_leaders_do_not_differ_everyone_is_shrunk_all_the_way_to_the_overall_mean() -> None:
    posts = pd.concat([_leader(name, 5.0, 2 * MIN_POSTS) for name in ("a", "b", "c")], ignore_index=True)

    result = shrink_leader_scores(posts)

    assert result.between_variance == 0.0  # floored at zero, never negative
    assert result.leaders["weight"].tolist() == [0.0, 0.0, 0.0]
    assert result.leaders["shrunk_mean"].tolist() == pytest.approx([5.0, 5.0, 5.0])


def test_when_posts_within_a_leader_never_vary_nothing_is_shrunk() -> None:
    posts = pd.concat(
        [pd.DataFrame({"leader_id": name, "score": [value] * MIN_POSTS}) for name, value in (("a", 1.0), ("b", 4.0))],
        ignore_index=True,
    )

    result = shrink_leader_scores(posts)

    assert result.within_variance == 0.0
    assert result.leaders["weight"].tolist() == [1.0, 1.0]
    assert result.leaders["shrunk_mean"].tolist() == result.leaders["raw_mean"].tolist()


def test_shrinkage_does_not_modify_the_input_table() -> None:
    posts = _four_leaders_and_a_small_one()
    before = posts.copy(deep=True)

    shrink_leader_scores(posts)

    pd.testing.assert_frame_equal(posts, before)


def test_output_has_one_row_per_leader_sorted_by_leader_id_with_documented_columns() -> None:
    result = shrink_leader_scores(_four_leaders_and_a_small_one())

    assert list(result.leaders.columns) == ["leader_id", "n_posts", "raw_mean", "weight", "shrunk_mean"]
    assert result.leaders["leader_id"].tolist() == sorted(result.leaders["leader_id"])
    assert result.leaders["leader_id"].is_unique


def test_fewer_than_two_eligible_leaders_is_refused() -> None:
    posts = pd.concat([_leader("only", 1.0, 2 * MIN_POSTS), _leader("small", 0.0, MIN_POSTS - 1)], ignore_index=True)

    with pytest.raises(ValueError, match="at least two leaders"):
        shrink_leader_scores(posts)


def test_missing_column_and_missing_leader_id_are_refused() -> None:
    posts = _four_leaders_and_a_small_one()

    with pytest.raises(ValueError, match="missing column"):
        shrink_leader_scores(posts.drop(columns=["score"]))
    with pytest.raises(ValueError, match="no leader_id"):
        shrink_leader_scores(posts.assign(leader_id=posts["leader_id"].where(posts.index != 0)))


def test_the_pass_marks_are_not_written_in_the_module_source() -> None:
    source = Path("src/stats_tools.py").read_text(encoding="utf-8")

    assert "min_posts_per_leader" in source and "fdr_q" in source
    assert "0.05" not in source
    assert " 15" not in source


# ---------------------------------------------------------------- Benjamini-Hochberg
TEN_P_VALUES = [0.001, 0.008, 0.039, 0.041, 0.042, 0.06, 0.074, 0.205, 0.212, 0.216]


def test_bh_adjusted_p_values_match_a_hand_computed_table() -> None:
    # p * m / rank = 0.01, 0.04, 0.13, 0.1025, 0.084, 0.1, 0.105714..., 0.25625, 0.235555..., 0.216
    # then a running minimum from the largest rank down gives the adjusted values below.
    expected = [0.01, 0.04, 0.084, 0.084, 0.084, 0.1, 0.074 * 10 / 7, 0.216, 0.216, 0.216]

    result = benjamini_hochberg(TEN_P_VALUES, q=FDR_Q)

    assert result.adjusted == pytest.approx(expected)


def test_bh_rejects_exactly_those_with_adjusted_p_at_or_below_q() -> None:
    result = benjamini_hochberg(TEN_P_VALUES, q=FDR_Q)

    assert result.rejected == (True, True, False, False, False, False, False, False, False, False)
    assert result.q == FDR_Q


def test_bh_threshold_is_inclusive() -> None:
    # m=2: p * m / rank = 0.04 and 0.04, so both sit exactly on q=0.04.
    result = benjamini_hochberg([0.02, 0.04], q=0.04)

    assert result.adjusted == pytest.approx([0.04, 0.04])
    assert result.rejected == (True, True)


def test_bh_keeps_the_input_order() -> None:
    shuffled = [0.216, 0.001, 0.074, 0.008]
    # m=4, sorted 0.001 (r1), 0.008 (r2), 0.074 (r3), 0.216 (r4):
    # p*m/r = 0.004, 0.016, 0.098666..., 0.216 -> the running minimum from the top changes nothing.
    expected = {0.216: 0.216, 0.001: 0.004, 0.074: 0.074 * 4 / 3, 0.008: 0.016}

    result = benjamini_hochberg(shuffled, q=FDR_Q)

    assert result.adjusted == pytest.approx([expected[p] for p in shuffled])
    assert result.rejected == (False, True, False, True)


def test_bh_adjusted_values_never_exceed_one() -> None:
    result = benjamini_hochberg([0.9, 0.95, 1.0], q=FDR_Q)

    assert max(result.adjusted) <= 1.0
    assert result.adjusted == pytest.approx([1.0, 1.0, 1.0])


def test_bh_leaves_missing_p_values_missing_and_does_not_count_them() -> None:
    # Without the NaN this is the m=2 example [0.02, 0.04] -> 0.04, 0.04.
    result = benjamini_hochberg([0.02, math.nan, 0.04], q=FDR_Q)

    assert result.adjusted[0] == pytest.approx(0.04)
    assert math.isnan(result.adjusted[1])
    assert result.adjusted[2] == pytest.approx(0.04)
    assert result.rejected == (True, False, True)


def test_bh_with_nothing_to_test_returns_nothing() -> None:
    result = benjamini_hochberg([], q=FDR_Q)

    assert result.adjusted == ()
    assert result.rejected == ()


def test_bh_q_defaults_to_the_thresholds_file(tmp_path: Path) -> None:
    thresholds = tmp_path / "thresholds.yaml"
    thresholds.write_text("fdr_q: 0.01\n", encoding="utf-8")

    result = benjamini_hochberg([0.001, 0.008, 0.039], thresholds_path=thresholds)

    assert result.q == 0.01
    assert result.rejected == (True, False, False)


@pytest.mark.parametrize("bad", [-0.1, 1.1, math.inf])
def test_bh_refuses_p_values_outside_zero_to_one(bad: float) -> None:
    with pytest.raises(ValueError, match="between 0 and 1"):
        benjamini_hochberg([0.01, bad], q=FDR_Q)


@pytest.mark.parametrize("bad_q", [0.0, -0.05, 1.5])
def test_bh_refuses_an_impossible_q(bad_q: float) -> None:
    with pytest.raises(ValueError, match="q must be"):
        benjamini_hochberg([0.01], q=bad_q)
