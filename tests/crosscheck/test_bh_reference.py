"""Cross-check of src/stats_tools.benjamini_hochberg against statsmodels `multipletests(method="fdr_bh")`.

statsmodels is a dev dependency only. All p-values are invented, from fixed seeds. Vectors mix continuous values, values
rounded to two decimals (so there are many ties), and exact 1s. Both adjusted p-values and reject decisions must match.
q is passed explicitly in every call, so no pass mark is hard-coded here beyond the q values being compared.
"""
from __future__ import annotations

import numpy as np
import pytest

from src.stats_tools import benjamini_hochberg

multitest = pytest.importorskip(
    "statsmodels.stats.multitest", reason="dev dependency: install statsmodels to run the cross-check"
)

TOLERANCE = 1e-12
SEEDS = tuple(range(20))
Q_VALUES = (0.05, 0.10, 0.20)
MIN_LENGTH, MAX_LENGTH = 5, 60
SHARE_OF_EXACT_ONES = 0.15
TIE_DECIMALS = 2


def _random_p_values(seed: int) -> np.ndarray:
    """Even seeds give continuous p-values with a few exact 1s; odd seeds are rounded to force ties as well."""
    rng = np.random.default_rng(seed)
    size = int(rng.integers(MIN_LENGTH, MAX_LENGTH + 1))
    p_values = rng.beta(0.5, 2.0, size=size)  # skewed towards small values, so some are rejected
    p_values[rng.random(size=size) < SHARE_OF_EXACT_ONES] = 1.0
    if seed % 2 == 1:
        p_values = np.round(p_values, TIE_DECIMALS)
    return p_values


def _reference(p_values: np.ndarray, q: float) -> tuple[np.ndarray, np.ndarray]:
    reject, adjusted, _, _ = multitest.multipletests(p_values, alpha=q, method="fdr_bh")
    return adjusted, reject


@pytest.mark.parametrize("seed", SEEDS)
def test_adjusted_p_values_and_decisions_match_reference(seed: int) -> None:
    p_values = _random_p_values(seed)
    q = Q_VALUES[seed % len(Q_VALUES)]

    ours = benjamini_hochberg(p_values.tolist(), q=q)

    reference_adjusted, reference_reject = _reference(p_values, q)
    np.testing.assert_allclose(ours.adjusted, reference_adjusted, rtol=0, atol=TOLERANCE)
    assert list(ours.rejected) == reference_reject.tolist()


def test_vectors_include_ties_exact_ones_and_some_rejections() -> None:
    vectors = [_random_p_values(seed) for seed in SEEDS]

    assert all((vector == 1.0).any() for vector in vectors)
    assert any(len(set(vector.tolist())) < len(vector) for vector in vectors[1::2])
    assert any(benjamini_hochberg(vector.tolist(), q=0.05).rejected.count(True) > 0 for vector in vectors)
    assert any(benjamini_hochberg(vector.tolist(), q=0.05).rejected.count(False) > 0 for vector in vectors)


def test_a_p_value_whose_adjusted_value_equals_q_is_rejected_by_both() -> None:
    p_values = np.array([0.01, 0.02, 0.03, 0.04, 0.05])  # largest adjusted value is 0.05 * 5 / 5 = q

    ours = benjamini_hochberg(p_values.tolist(), q=0.05)

    reference_adjusted, reference_reject = _reference(p_values, 0.05)
    np.testing.assert_allclose(ours.adjusted, reference_adjusted, rtol=0, atol=TOLERANCE)
    assert list(ours.rejected) == reference_reject.tolist()
    assert all(ours.rejected)


def test_all_exact_ones_are_adjusted_to_one_and_never_rejected_by_both() -> None:
    p_values = np.ones(8)

    ours = benjamini_hochberg(p_values.tolist(), q=0.05)

    reference_adjusted, reference_reject = _reference(p_values, 0.05)
    assert list(ours.adjusted) == reference_adjusted.tolist() == [1.0] * 8
    assert list(ours.rejected) == reference_reject.tolist() == [False] * 8
