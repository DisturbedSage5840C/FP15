"""Empirical Bayes shrinkage from post-level scores to leader-level scores, and Benjamini-Hochberg FDR.

Functions only. This module is tested on invented scores in this step; it has not been run on real data.

Shrinkage (normal-normal model). Posts are nested in leaders. For the leaders with at least `min_posts_per_leader`
scored posts:
    raw_mean_i     mean of leader i's post scores, n_i the number of scored posts
    grand_mean     plain mean of the leaders' raw means (every leader counts once, not once per post)
    within_var     pooled variance of posts around their own leader mean, sum of squares / (posts - leaders)
    between_var    method of moments: var(raw means, ddof=1) - within_var * mean(1 / n_i), floored at zero
    weight_i       between_var / (between_var + within_var / n_i)
    shrunk_i       grand_mean + weight_i * (raw_mean_i - grand_mean)
A leader with fewer posts has a smaller weight, so is pulled further toward the grand mean. A leader below the
minimum is left out of the output (missing stays missing; nothing is guessed). A missing score is not a post.
When both variances are zero every leader has the same mean already, and the weight is set to zero.

Benjamini-Hochberg: adjusted p = running minimum from the largest rank down of p * m / rank, capped at one; a test is
rejected when its adjusted p is at or below q. Missing p-values stay missing and are not counted in m.

The pass marks (`min_posts_per_leader`, `fdr_q`) are read from configs/thresholds.yaml, never written here.
"""
from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from src.thresholds import DEFAULT_THRESHOLDS_PATH, load_threshold

MIN_POSTS_KEY = "min_posts_per_leader"
FDR_Q_KEY = "fdr_q"
MIN_ELIGIBLE_LEADERS = 2
LEADER_COLUMNS = ("leader_id", "n_posts", "raw_mean", "weight", "shrunk_mean")
REQUIRED_COLUMNS = ("leader_id", "score")


@dataclass(frozen=True, eq=False)
class ShrinkageResult:
    """One row per leader at or above the minimum, plus the estimates the shrinkage rests on."""

    leaders: pd.DataFrame
    grand_mean: float
    within_variance: float
    between_variance: float
    min_posts: int


@dataclass(frozen=True)
class BenjaminiHochbergResult:
    """Adjusted p-values and rejections, in the order the p-values were given."""

    adjusted: tuple[float, ...]
    rejected: tuple[bool, ...]
    q: float


def _scored_posts(posts: pd.DataFrame) -> pd.DataFrame:
    """A copy with only leader_id and a numeric score, posts without a score removed; the input is not modified."""
    missing = [column for column in REQUIRED_COLUMNS if column not in posts.columns]
    if missing:
        raise ValueError(f"missing column(s): {', '.join(missing)}")
    table = posts.loc[:, list(REQUIRED_COLUMNS)].copy()
    no_leader = int(table["leader_id"].isna().to_numpy().sum())
    if no_leader:
        raise ValueError(f"{no_leader} row(s) have no leader_id, so posts cannot be grouped by leader")
    table["score"] = table["score"].astype(float)
    return table.dropna(subset=["score"]).reset_index(drop=True)


def _eligible_posts(table: pd.DataFrame, min_posts: int) -> pd.DataFrame:
    """Only the posts of leaders with at least `min_posts` scored posts."""
    counts = table.groupby("leader_id")["score"].transform("size").to_numpy()
    eligible = table.loc[counts >= min_posts].reset_index(drop=True)
    qualifying = len(set(eligible["leader_id"]))
    if qualifying < MIN_ELIGIBLE_LEADERS:
        raise ValueError(
            f"shrinkage needs at least two leaders with {min_posts} or more scored posts; {qualifying} qualify"
        )
    return eligible


def _within_variance(eligible: pd.DataFrame) -> float:
    """Pooled variance of posts around their own leader's mean."""
    leader_means = eligible.groupby("leader_id")["score"].transform("mean").to_numpy(dtype=float)
    squares = float(np.sum((eligible["score"].to_numpy(dtype=float) - leader_means) ** 2))
    degrees_of_freedom = len(eligible) - len(set(eligible["leader_id"]))
    if degrees_of_freedom < 1:
        raise ValueError("within-leader variance cannot be estimated: no leader has two scored posts")
    return squares / degrees_of_freedom


def _weights(between: float, within: float, n_posts: np.ndarray) -> np.ndarray:
    """Shrinkage weight per leader; zero where there is no variance at all."""
    denominator = between + within / n_posts
    safe = np.where(denominator > 0, denominator, 1.0)
    return np.where(denominator > 0, between / safe, 0.0)


def shrink_leader_scores(
    posts: pd.DataFrame,
    min_posts: int | None = None,
    thresholds_path: Path = DEFAULT_THRESHOLDS_PATH,
) -> ShrinkageResult:
    """Leader-level scores shrunk toward the grand mean; `min_posts` defaults to the thresholds file."""
    minimum = int(load_threshold(MIN_POSTS_KEY, thresholds_path)) if min_posts is None else int(min_posts)
    eligible = _eligible_posts(_scored_posts(posts), minimum)
    per_leader = eligible.groupby("leader_id")["score"].agg(n_posts="size", raw_mean="mean").reset_index()
    per_leader = per_leader.sort_values("leader_id").reset_index(drop=True)

    raw_means = per_leader["raw_mean"].to_numpy(dtype=float)
    n_posts = per_leader["n_posts"].to_numpy(dtype=float)
    grand_mean = float(np.mean(raw_means))
    within = _within_variance(eligible)
    noise_in_means = within * float(np.mean(1 / n_posts))
    between = max(0.0, float(np.var(raw_means, ddof=1)) - noise_in_means)

    weight = _weights(between, within, n_posts)
    shrunk = grand_mean + weight * (raw_means - grand_mean)
    leaders = per_leader.assign(weight=weight, shrunk_mean=shrunk).loc[:, list(LEADER_COLUMNS)]
    return ShrinkageResult(leaders, grand_mean, within, between, minimum)


def _check_q(q: float) -> None:
    if not (0 < q <= 1):
        raise ValueError(f"q must be greater than 0 and at most 1, got {q}")


def _check_p_values(p_values: np.ndarray) -> None:
    present = ~np.isnan(p_values)
    outside = present & ((p_values < 0) | (p_values > 1))
    if outside.any():
        raise ValueError(f"{int(outside.sum())} p-value(s) are not between 0 and 1")


def _adjust(p_values: np.ndarray) -> np.ndarray:
    """BH-adjusted p-values in input order; NaN stays NaN and is not counted."""
    adjusted = np.full(len(p_values), np.nan)
    present = np.flatnonzero(~np.isnan(p_values))
    order = present[np.argsort(p_values[present], kind="stable")]
    if order.size == 0:
        return adjusted
    ranks = np.arange(1, order.size + 1)
    scaled = p_values[order] * order.size / ranks
    running_minimum = np.minimum.accumulate(scaled[::-1])[::-1]
    adjusted[order] = np.minimum(running_minimum, 1.0)
    return adjusted


def benjamini_hochberg(
    p_values: Sequence[float],
    q: float | None = None,
    thresholds_path: Path = DEFAULT_THRESHOLDS_PATH,
) -> BenjaminiHochbergResult:
    """Benjamini-Hochberg step-up FDR; `q` defaults to `fdr_q` in the thresholds file."""
    level = float(load_threshold(FDR_Q_KEY, thresholds_path)) if q is None else float(q)
    _check_q(level)
    values = np.asarray(list(p_values), dtype=float)
    _check_p_values(values)
    adjusted = _adjust(values)
    rejected = tuple(bool(value <= level) for value in adjusted)  # NaN <= q is False
    return BenjaminiHochbergResult(
        adjusted=tuple(float(value) if not math.isnan(value) else math.nan for value in adjusted),
        rejected=rejected,
        q=level,
    )
