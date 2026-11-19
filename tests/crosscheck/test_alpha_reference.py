"""Cross-check of src/agreement.py against the independent `krippendorff` package (dev dependency only).

Synthetic ratings only; every table comes from a fixed seed. The reference takes a coders x units array with NaN for a
missing rating; src/agreement.py takes one row per unit. The pass mark is not used here: this file compares alpha
values, not gate decisions.

Where the two implementations differ on purpose or by accident, the test pins what each one does, so a change in either
shows up here:
  * every rating uses one label        -> both raise ValueError (reference: "more than one value in the domain").
  * a label occurs only in a unit that has a single rating (so it never enters a pair)
                                       -> reference returns nan with a divide warning; src/agreement.py raises ValueError.
"""
from __future__ import annotations

import warnings

import numpy as np
import pytest

from src.agreement import krippendorff_alpha_nominal

reference = pytest.importorskip("krippendorff", reason="dev dependency: install the dev extra to run the cross-check")

TOLERANCE = 1e-9
SEEDS = tuple(range(25))
MIN_CODERS, MAX_CODERS = 2, 4
MIN_LABELS, MAX_LABELS = 2, 5
MIN_UNITS, MAX_UNITS = 20, 60
MISSING_RATE = 0.2


def _random_table(seed: int) -> np.ndarray:
    """A coders x units float table with NaN for missing; redrawn until alpha is defined (>= 2 labels in pairs)."""
    rng = np.random.default_rng(seed)
    for _ in range(100):
        coders = int(rng.integers(MIN_CODERS, MAX_CODERS + 1))
        labels = int(rng.integers(MIN_LABELS, MAX_LABELS + 1))
        units = int(rng.integers(MIN_UNITS, MAX_UNITS + 1))
        table = rng.integers(1, labels + 1, size=(coders, units)).astype(float)
        table[rng.random(size=table.shape) < MISSING_RATE] = np.nan
        if _is_defined(table):
            return table
    raise AssertionError(f"seed {seed}: no defined table in 100 draws")


def _is_defined(table: np.ndarray) -> bool:
    """True when at least two different labels sit in units that have two or more ratings."""
    pairable = table[:, (~np.isnan(table)).sum(axis=0) >= 2]
    return len(set(pairable[~np.isnan(pairable)].tolist())) >= 2


def _as_units(table: np.ndarray) -> list[list[float | None]]:
    """Rows are units, as src/agreement.py expects; NaN becomes None."""
    return [[None if np.isnan(value) else float(value) for value in column] for column in table.T]


def _reference_alpha(table: np.ndarray) -> float:
    return float(reference.alpha(reliability_data=table, level_of_measurement="nominal"))


@pytest.mark.parametrize("seed", SEEDS)
def test_alpha_matches_reference_on_random_tables(seed: int) -> None:
    table = _random_table(seed)

    ours = krippendorff_alpha_nominal(_as_units(table))

    assert ours == pytest.approx(_reference_alpha(table), abs=TOLERANCE, rel=0)


def test_random_tables_cover_the_requested_shapes() -> None:
    tables = [_random_table(seed) for seed in SEEDS]
    labels = [len(set(table[~np.isnan(table)].tolist())) for table in tables]

    assert {table.shape[0] for table in tables} == {2, 3, 4}
    assert min(labels) >= MIN_LABELS and max(labels) <= MAX_LABELS
    assert len(set(labels)) > 1
    assert all(np.isnan(table).any() for table in tables)


def test_all_raters_using_one_label_is_undefined_in_both() -> None:
    table = np.ones((3, 10))

    with pytest.raises(ValueError, match="more than one value"):
        _reference_alpha(table)
    with pytest.raises(ValueError, match="only one label"):
        krippendorff_alpha_nominal(_as_units(table))


def test_one_label_with_missing_ratings_is_undefined_in_both() -> None:
    table = np.array([[1.0, 1.0, np.nan, 1.0], [1.0, 1.0, 1.0, 1.0]])

    with pytest.raises(ValueError, match="more than one value"):
        _reference_alpha(table)
    with pytest.raises(ValueError, match="only one label"):
        krippendorff_alpha_nominal(_as_units(table))


def test_label_seen_only_in_an_unpairable_unit_differs_between_the_two() -> None:
    table = np.array([[1.0, 1.0, 1.0, 2.0], [1.0, 1.0, 1.0, np.nan]])  # the only 2 is alone in its unit

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        reference_alpha = _reference_alpha(table)

    assert np.isnan(reference_alpha)
    with pytest.raises(ValueError, match="only one label"):
        krippendorff_alpha_nominal(_as_units(table))


def test_a_unit_with_one_rating_is_ignored_the_same_way_by_both() -> None:
    table = np.array([[1.0, 2.0, 1.0, np.nan], [1.0, 2.0, np.nan, 2.0], [1.0, 1.0, np.nan, np.nan]])

    assert krippendorff_alpha_nominal(_as_units(table)) == pytest.approx(_reference_alpha(table), abs=TOLERANCE, rel=0)
