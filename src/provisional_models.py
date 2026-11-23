"""Random-intercept mixed model for the provisional comparisons (step 14, part 3).

PROVISIONAL. Exploratory only, not pre-registered. Posts are nested in leaders: one random intercept per leader and
categorical fixed effects for the comparison factors. The tests are joint Wald tests per factor from one fit, and the
share of variance at leader level is the intraclass correlation. Nothing here says anything about causes, and the rates
describe the image projected in public posts, not personality.

Factors whose dummy columns repeat an earlier factor (for example the "no usable company match" group, which is the same
set of leaders in gender, sector and size) are pruned in factor order, and the lost degrees of freedom are reported in
the note. The minimum number of leaders to fit anything is the existing "too small to model" rule in
configs/thresholds.yaml; no new cut is introduced here.
"""
from __future__ import annotations

import logging
import warnings
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy.stats import chi2, norm
from statsmodels.tools.sm_exceptions import ConvergenceWarning

from src.eda_common import DEFAULT_THRESHOLDS_PATH, load_eda_settings
from src.stats_tools import FDR_Q_KEY, load_threshold

logger = logging.getLogger(__name__)

RATE_COLUMN = "y"
LEADER_COLUMN = "leader_id"
INTERCEPT = "intercept"
MIN_LEVELS = 2
TOO_FEW_LEADERS_NOTE = "too few leaders to model (below the too-small-to-model minimum in configs/thresholds.yaml)"
ONE_LEVEL_NOTE = "fewer than 2 levels after dropping missing rates"
ALIASED_NOTE = "every column repeats an earlier factor, so no test"
FIT_FAILED_NOTE = "model fit failed"


@dataclass(frozen=True)
class VarianceShare:
    """Share of variance at leader level from the random-intercept model."""

    icc: float
    leaders: int
    posts: int
    note: str


@dataclass(frozen=True)
class FactorTest:
    """Joint Wald test of one factor in the joint model.

    A factor with exactly two levels has 1 degree of freedom and also carries the estimated difference (the second
    level minus the first in sorted order, named in `contrast`) with its interval; otherwise those stay empty / NaN.
    """

    factor: str
    df: int
    p_value: float
    note: str
    contrast: str = ""
    estimate: float = float("nan")
    lower: float = float("nan")
    upper: float = float("nan")


@dataclass(frozen=True)
class _Fit:
    result: Any
    columns_by_factor: dict[str, list[str]]
    dropped_by_factor: dict[str, int]
    levels_by_factor: dict[str, list[str]]
    note: str


def _scored(frame: pd.DataFrame, factors: Sequence[str]) -> pd.DataFrame:
    """Rows with a rate and a leader; a missing rate is never filled."""
    needed = [RATE_COLUMN, LEADER_COLUMN, *factors]
    missing = [column for column in needed if column not in frame.columns]
    if missing:
        raise ValueError(f"model frame is missing columns {missing}")
    return frame.loc[:, needed].dropna(subset=[RATE_COLUMN, LEADER_COLUMN])


def _factor_blocks(data: pd.DataFrame, factors: Sequence[str]) -> dict[str, pd.DataFrame]:
    """Treatment-coded dummy columns for each factor that has at least two levels."""
    blocks: dict[str, pd.DataFrame] = {}
    for factor in factors:
        dummies = pd.get_dummies(data[factor].astype(str), drop_first=True, dtype=float)
        if dummies.shape[1] >= 1:
            blocks[factor] = dummies
    return blocks


def _independent_columns(matrix: np.ndarray) -> list[int]:
    """Indices of columns kept in order: a column stays only if it adds rank to those before it."""
    gram = matrix.T @ matrix
    kept: list[int] = []
    for index in range(gram.shape[0]):
        candidate = [*kept, index]
        if np.linalg.matrix_rank(gram[np.ix_(candidate, candidate)]) == len(candidate):
            kept.append(index)
    return kept


def _design(data: pd.DataFrame, factors: Sequence[str]) -> tuple[pd.DataFrame, dict[str, list[str]], dict[str, int]]:
    """Fixed-effects matrix with positional column names, the columns kept per factor, and the count dropped."""
    blocks = _factor_blocks(data, factors)
    names: list[str] = [INTERCEPT]
    owner: list[str | None] = [None]
    arrays = [np.ones(len(data))]
    for factor, dummies in blocks.items():
        for column in dummies.columns:
            names.append(f"c{len(names)}")
            owner.append(factor)
            arrays.append(dummies[column].to_numpy())
    matrix = np.column_stack(arrays)
    kept = _independent_columns(matrix)
    exog = pd.DataFrame(matrix[:, kept], columns=[names[i] for i in kept], index=data.index)
    columns_by_factor: dict[str, list[str]] = {factor: [] for factor in blocks}
    dropped = dict.fromkeys(blocks, 0)
    for index, factor in enumerate(owner):
        if factor is None:
            continue
        if index in kept:
            columns_by_factor[factor].append(names[index])
        else:
            dropped[factor] += 1
    return exog, columns_by_factor, dropped


def _fit(data: pd.DataFrame, factors: Sequence[str]) -> _Fit:
    """REML fit of rate ~ factors with a random intercept per leader; convergence warnings become the note."""
    exog, columns_by_factor, dropped = _design(data, factors)
    model = sm.MixedLM(data[RATE_COLUMN].to_numpy(), exog, groups=data[LEADER_COLUMN].to_numpy())
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        result = model.fit(reml=True)
    for item in caught:
        if not issubclass(item.category, ConvergenceWarning):
            warnings.warn(item.message, item.category, stacklevel=2)
    messages = sorted({str(item.message) for item in caught if issubclass(item.category, ConvergenceWarning)})
    note = "convergence warning: " + "; ".join(messages) if messages else ""
    levels = {factor: sorted(data[factor].astype(str).unique()) for factor in columns_by_factor}
    return _Fit(result, columns_by_factor, dropped, levels, note)


def _min_leaders(thresholds_path: Path) -> int:
    return load_eda_settings(thresholds_path).model_min


def _enough_leaders(data: pd.DataFrame, thresholds_path: Path) -> bool:
    return data[LEADER_COLUMN].nunique() >= _min_leaders(thresholds_path)


def _failed_share(data: pd.DataFrame, note: str) -> VarianceShare:
    return VarianceShare(float("nan"), int(data[LEADER_COLUMN].nunique()), len(data), note)


def variance_share(
    frame: pd.DataFrame,
    factors: Sequence[str] = (),
    thresholds_path: Path = DEFAULT_THRESHOLDS_PATH,
) -> VarianceShare:
    """Leader-level share of the variance: leader variance over leader plus post variance, given the factors."""
    data = _scored(frame, factors)
    if not _enough_leaders(data, thresholds_path):
        return _failed_share(data, TOO_FEW_LEADERS_NOTE)
    try:
        fit = _fit(data, factors)
    except (np.linalg.LinAlgError, ValueError) as error:
        logger.warning("variance share: %s (%s)", FIT_FAILED_NOTE, error)
        return _failed_share(data, FIT_FAILED_NOTE)
    result = fit.result
    leader_variance = float(result.cov_re.iloc[0, 0])
    icc = leader_variance / (leader_variance + float(result.scale))
    return VarianceShare(icc, int(data[LEADER_COLUMN].nunique()), len(data), fit.note)


def _interval_level(thresholds_path: Path) -> float:
    """Confidence level of the reported intervals: one minus the existing fdr_q, so no new cut is introduced."""
    return 1.0 - float(load_threshold(FDR_Q_KEY, thresholds_path))


def _difference(fit: _Fit, factor: str, column: str, thresholds_path: Path) -> dict[str, Any]:
    """Estimate and interval of the second level minus the first, for a two-level factor with one kept column."""
    first, second = fit.levels_by_factor[factor]
    estimate = float(fit.result.fe_params[column])
    half_width = float(norm.ppf(0.5 + _interval_level(thresholds_path) / 2)) * float(fit.result.bse_fe[column])
    return {
        "contrast": f"{second} minus {first}",
        "estimate": estimate,
        "lower": estimate - half_width,
        "upper": estimate + half_width,
    }


def _wald(fit: _Fit, factor: str, thresholds_path: Path = DEFAULT_THRESHOLDS_PATH) -> FactorTest:
    columns = fit.columns_by_factor[factor]
    if not columns:
        return FactorTest(factor, 0, float("nan"), ALIASED_NOTE)
    coefficients = fit.result.fe_params[columns].to_numpy()
    covariance = fit.result.cov_params().loc[columns, columns].to_numpy()
    statistic = float(coefficients @ np.linalg.solve(covariance, coefficients))
    p_value = float(chi2.sf(statistic, len(columns)))
    dropped = fit.dropped_by_factor[factor]
    notes = [fit.note] if fit.note else []
    if dropped:
        notes.append(f"{dropped} column(s) repeat an earlier factor and were dropped")
    two_levels = len(fit.levels_by_factor[factor]) == MIN_LEVELS and len(columns) == 1
    difference = _difference(fit, factor, columns[0], thresholds_path) if two_levels else {}
    return FactorTest(factor, len(columns), p_value, "; ".join(notes), **difference)


def _untested(factor: str, note: str) -> FactorTest:
    return FactorTest(factor, 0, float("nan"), note)


def factor_tests(
    frame: pd.DataFrame,
    factors: Sequence[str],
    thresholds_path: Path = DEFAULT_THRESHOLDS_PATH,
) -> list[FactorTest]:
    """One joint Wald test per factor from a single joint model, in the order given; failures carry a note."""
    data = _scored(frame, factors)
    if not _enough_leaders(data, thresholds_path):
        return [_untested(factor, TOO_FEW_LEADERS_NOTE) for factor in factors]
    usable = [factor for factor in factors if data[factor].astype(str).nunique() >= MIN_LEVELS]
    try:
        fit = _fit(data, usable)
        tests = {factor: _wald(fit, factor, thresholds_path) for factor in usable}
    except (np.linalg.LinAlgError, ValueError) as error:
        logger.warning("factor tests: %s (%s)", FIT_FAILED_NOTE, error)
        return [_untested(factor, FIT_FAILED_NOTE) for factor in factors]
    return [tests.get(factor, _untested(factor, ONE_LEVEL_NOTE)) for factor in factors]
