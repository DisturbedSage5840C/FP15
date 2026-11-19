"""Tests for src.agreement: nominal Krippendorff alpha. Synthetic ratings only; every expected value is worked by hand.

Method (nominal): for each unit with m >= 2 ratings, every ordered pair of its ratings from different coders adds
1/(m-1) to the coincidence matrix o[c][k]. With n_c the row sums and n their total,
alpha = 1 - (n - 1) * sum_{c != k} o[c][k] / sum_{c != k} n_c * n_k.
"""
from __future__ import annotations

import math
from pathlib import Path

import pytest

from src.agreement import AlphaResult, alpha_gate, krippendorff_alpha_nominal

MISSING = None


def test_perfect_agreement_gives_one() -> None:
    units = [("a", "a"), ("b", "b"), ("a", "a"), ("c", "c")]

    assert krippendorff_alpha_nominal(units) == 1.0


def test_a_known_disagreement_table_matches_the_hand_value() -> None:
    # Units (a,a) (a,b) (b,b) (b,b), two coders.
    # o_aa = 2, o_ab = o_ba = 1, o_bb = 4  ->  n_a = 3, n_b = 5, n = 8.
    # observed disagreement sum = 2; expected sum = 2 * 3 * 5 = 30.
    # alpha = 1 - (8 - 1) * 2 / 30 = 16 / 30.
    units = [("a", "a"), ("a", "b"), ("b", "b"), ("b", "b")]

    assert krippendorff_alpha_nominal(units) == pytest.approx(16 / 30)


def test_missing_ratings_are_allowed_and_a_lone_rating_is_ignored() -> None:
    # Three coders. u1 (a,a,-) u2 (a,b,b) u3 (-,b,b) u4 (a,-,b) u5 (b,-,-)  (u5 has one rating: not pairable).
    # u1: o_aa += 2.  u2 (m=3, weight 1/2): o_ab += 1, o_ba += 1, o_bb += 1.  u3: o_bb += 2.  u4: o_ab += 1, o_ba += 1.
    # o_aa = 2, o_ab = o_ba = 2, o_bb = 3  ->  n_a = 4, n_b = 5, n = 9.
    # observed disagreement sum = 4; expected sum = 2 * 4 * 5 = 40.  alpha = 1 - 8 * 4 / 40 = 0.2.
    units = [
        ("a", "a", MISSING),
        ("a", "b", "b"),
        (MISSING, "b", "b"),
        ("a", MISSING, "b"),
        ("b", MISSING, MISSING),
    ]

    assert krippendorff_alpha_nominal(units) == pytest.approx(0.2)


def test_nan_counts_as_a_missing_rating() -> None:
    nan = float("nan")
    units = [("a", "a", nan), ("a", "b", "b"), (nan, "b", "b"), ("a", nan, "b"), ("b", nan, nan)]

    assert krippendorff_alpha_nominal(units) == pytest.approx(0.2)


def test_coder_order_inside_a_unit_does_not_matter() -> None:
    forward = [("a", "b"), ("b", "b"), ("a", "a")]
    swapped = [("b", "a"), ("b", "b"), ("a", "a")]

    assert krippendorff_alpha_nominal(forward) == pytest.approx(krippendorff_alpha_nominal(swapped))


def test_systematic_disagreement_gives_a_negative_alpha() -> None:
    # Two coders who always pick opposite labels: o_ab = o_ba = 2, n_a = n_b = 2, n = 4.
    # alpha = 1 - 3 * 4 / (2 * 2 * 2) = -0.5.
    units = [("a", "b"), ("b", "a")]

    assert krippendorff_alpha_nominal(units) == pytest.approx(-0.5)


def test_labels_may_be_integers_or_strings() -> None:
    assert krippendorff_alpha_nominal([(1, 1), (2, 2), (1, 2)]) == pytest.approx(
        krippendorff_alpha_nominal([("x", "x"), ("y", "y"), ("x", "y")])
    )


def test_no_unit_with_two_ratings_is_an_error() -> None:
    with pytest.raises(ValueError, match="no unit has two or more ratings"):
        krippendorff_alpha_nominal([("a", MISSING), (MISSING, "b")])


def test_an_empty_table_is_an_error() -> None:
    with pytest.raises(ValueError, match="no unit has two or more ratings"):
        krippendorff_alpha_nominal([])


def test_only_one_label_used_is_an_error_not_a_free_pass() -> None:
    with pytest.raises(ValueError, match="only one label"):
        krippendorff_alpha_nominal([("a", "a"), ("a", "a")])


def test_the_result_is_a_plain_float() -> None:
    value = krippendorff_alpha_nominal([("a", "a"), ("a", "b"), ("b", "b")])

    assert isinstance(value, float)
    assert not math.isnan(value)


# ---- pass or fail against the threshold in thresholds.yaml ----------------------------------------------------


def _config(tmp_path: Path, minimum: str = "0.5") -> Path:
    path = tmp_path / "thresholds.yaml"
    path.write_text(f"krippendorff_alpha_min: {minimum}\n", encoding="utf-8")
    return path


def test_the_gate_passes_when_alpha_reaches_the_threshold(tmp_path: Path) -> None:
    units = [("a", "a"), ("a", "b"), ("b", "b"), ("b", "b")]  # alpha = 16/30 = 0.5333

    result = alpha_gate(units, _config(tmp_path, "0.5"))

    assert isinstance(result, AlphaResult)
    assert result.passed is True
    assert result.threshold == 0.5
    assert result.alpha == pytest.approx(16 / 30)


def test_the_gate_fails_when_alpha_is_below_the_threshold(tmp_path: Path) -> None:
    units = [("a", "a"), ("a", "b"), ("b", "b"), ("b", "b")]

    assert alpha_gate(units, _config(tmp_path, "0.6")).passed is False


def test_alpha_exactly_at_the_threshold_passes(tmp_path: Path) -> None:
    assert alpha_gate([("a", "a"), ("b", "b")], _config(tmp_path, "1.0")).passed is True


def test_the_gate_reports_how_many_units_and_coders_it_used(tmp_path: Path) -> None:
    units = [("a", "a", MISSING), ("a", "b", "b"), ("b", MISSING, MISSING)]

    result = alpha_gate(units, _config(tmp_path, "0.0"))

    assert result.units_used == 2
    assert result.coders == 3


def test_the_gate_reads_its_threshold_only_from_the_config(tmp_path: Path) -> None:
    path = tmp_path / "thresholds.yaml"
    path.write_text("min_posts_per_leader: 15\n", encoding="utf-8")

    with pytest.raises(ValueError, match="missing key krippendorff_alpha_min"):
        alpha_gate([("a", "b")], path)
