"""Nominal-level Krippendorff alpha for two or more coders, with missing ratings allowed.

Input is a table with one row per unit (a post) and one entry per coder; a missing rating is None or NaN. Blank
strings are NOT treated as missing: convert them before calling, so a typo cannot hide as a skipped rating.

Method: every unit with m >= 2 ratings adds 1/(m-1) to the coincidence matrix o[c][k] for each ordered pair of its
ratings from different coders. With n_c the row totals and n their sum,
    alpha = 1 - (n - 1) * sum_{c != k} o[c][k] / sum_{c != k} n_c * n_k.
A unit with fewer than two ratings cannot be compared and is left out.

The pass mark (`krippendorff_alpha_min`) is read from configs/thresholds.yaml, never written here. This module is
tested on invented ratings only; it is not run on real coding in this step.
"""
from __future__ import annotations

import math
from collections import defaultdict
from collections.abc import Hashable, Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path

from src.thresholds import DEFAULT_THRESHOLDS_PATH, load_threshold

ALPHA_THRESHOLD_KEY = "krippendorff_alpha_min"
MIN_RATINGS_PER_UNIT = 2

Rating = Hashable | None
Unit = Sequence[Rating]


@dataclass(frozen=True)
class AlphaResult:
    """Alpha with the pass mark it was judged against and how much of the table it rests on."""

    alpha: float
    threshold: float
    passed: bool
    units_used: int
    coders: int


def _is_missing(rating: Rating) -> bool:
    return rating is None or (isinstance(rating, float) and math.isnan(rating))


def _present(unit: Unit) -> list[Hashable]:
    return [rating for rating in unit if rating is not None and not _is_missing(rating)]


def _alpha_and_units(units: Iterable[Unit]) -> tuple[float, int]:
    """Alpha and the number of units that had two or more ratings."""
    coincidence: defaultdict[tuple[Hashable, Hashable], float] = defaultdict(float)
    pairable = 0
    for unit in units:
        ratings = _present(unit)
        if len(ratings) < MIN_RATINGS_PER_UNIT:
            continue
        pairable += 1
        weight = 1 / (len(ratings) - 1)
        for i, first in enumerate(ratings):
            for j, second in enumerate(ratings):
                if i != j:
                    coincidence[(first, second)] += weight
    if pairable == 0:
        raise ValueError("alpha is undefined: no unit has two or more ratings")

    label_totals: defaultdict[Hashable, float] = defaultdict(float)
    for (first, _), count in coincidence.items():
        label_totals[first] += count
    if len(label_totals) < 2:
        raise ValueError("alpha is undefined: only one label was used")

    total = sum(label_totals.values())
    observed = sum(count for (first, second), count in coincidence.items() if first != second)
    expected = total * total - sum(count * count for count in label_totals.values())
    return float(1 - (total - 1) * observed / expected), pairable


def krippendorff_alpha_nominal(units: Iterable[Unit]) -> float:
    """Nominal Krippendorff alpha; ValueError when it is undefined (no comparable unit, or a single label)."""
    return _alpha_and_units(units)[0]


def alpha_gate(units: Iterable[Unit], thresholds_path: Path = DEFAULT_THRESHOLDS_PATH) -> AlphaResult:
    """Alpha plus pass or fail against `krippendorff_alpha_min` in the thresholds file (at or above passes)."""
    table = [tuple(unit) for unit in units]
    threshold = float(load_threshold(ALPHA_THRESHOLD_KEY, thresholds_path))
    alpha, pairable = _alpha_and_units(table)
    coders = max((len(unit) for unit in table), default=0)
    return AlphaResult(alpha=alpha, threshold=threshold, passed=alpha >= threshold, units_used=pairable, coders=coders)
