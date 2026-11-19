"""Gold-set sampler and coder assignment. Functions only: nothing here reads a file or runs on real data.

Sampler: from a table of post_id, ceo_type, gender_as_coded, leader_id it draws `gold_set_size` posts at random with a
fixed seed, stratified by ceo_type x gender_as_coded, with at most `gold_set_max_posts_per_leader` posts per leader.
gender_as_coded is used exactly as it is coded in the table (a missing value is its own stratum; nothing is inferred).

Method:
  1. Sort by post_id, so the order of the input rows never changes the result, then shuffle once with a seeded generator.
  2. Keep each leader's first `cap` posts in that shuffled order: this is the cap.
  3. Give each stratum a share of `size` in proportion to its posts left after the cap (largest-remainder rounding in
     integers, ties broken by stratum label), and take the first n posts of that stratum in the shuffled order.
A leader whose rows fall in more than one stratum is refused, because the cap could then not be kept.

Coder assignment: every post goes to `coders_per_post` different coders. The coder groups (all pairs when it is two)
are rotated in an order that keeps every prefix of the rotation balanced, so each coder gets about the same number of
posts and each group about the same number of posts (never more than one apart).

Every number comes from configs/thresholds.yaml through `load_gold_settings`; none is written here. The cap value in
that file is a PROPOSAL waiting for mentor approval.
"""
from __future__ import annotations

from collections import Counter
from collections.abc import Hashable, Iterable, Sequence
from dataclasses import dataclass
from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd

from src.thresholds import DEFAULT_THRESHOLDS_PATH, load_threshold

GOLD_SHEET_COLUMNS = ("post_id", "coder", "label", "second_label", "is_reshare", "note")
REQUIRED_COLUMNS = ("post_id", "ceo_type", "gender_as_coded", "leader_id")
MISSING_LABEL = "(missing)"
MIN_CODERS_PER_POST = 2

Stratum = tuple[str, str]


@dataclass(frozen=True)
class GoldSettings:
    """Sampling and coder settings, all read from the thresholds file."""

    size: int
    max_posts_per_leader: int
    seed: int
    coders: int
    coders_per_post: int


@dataclass(frozen=True)
class CoderAssignment:
    """One post given to one coder; a post appears once per coder it goes to."""

    post_id: str
    coder: str


def load_gold_settings(path: Path = DEFAULT_THRESHOLDS_PATH) -> GoldSettings:
    """Settings from the thresholds file; a missing key or an impossible value is named in the error."""
    settings = GoldSettings(
        size=int(load_threshold("gold_set_size", path)),
        max_posts_per_leader=int(load_threshold("gold_set_max_posts_per_leader", path)),
        seed=int(load_threshold("gold_set_seed", path)),
        coders=int(load_threshold("gold_set_coders", path)),
        coders_per_post=int(load_threshold("gold_set_coders_per_post", path)),
    )
    _validate_settings(settings, path)
    return settings


def _validate_settings(settings: GoldSettings, path: Path) -> None:
    if settings.size < 1:
        raise ValueError(f"{path}: gold_set_size must be at least 1")
    if settings.max_posts_per_leader < 1:
        raise ValueError(f"{path}: gold_set_max_posts_per_leader must be at least 1")
    if settings.coders_per_post < MIN_CODERS_PER_POST:
        raise ValueError(f"{path}: gold_set_coders_per_post must be at least two, or agreement cannot be measured")
    if settings.coders_per_post > settings.coders:
        raise ValueError(f"{path}: more coders per post than coders ({settings.coders_per_post} > {settings.coders})")


def _label(value: object) -> str:
    """A stratum label exactly as coded; 1.0 from a column that also holds blanks is shown as 1."""
    if pd.isna(value):  # type: ignore[arg-type]
        return MISSING_LABEL
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def _with_labels(posts: pd.DataFrame) -> pd.DataFrame:
    """A copy with the two stratum labels added; the input table is never modified."""
    missing = [column for column in REQUIRED_COLUMNS if column not in posts.columns]
    if missing:
        raise ValueError(f"missing column(s): {', '.join(missing)}")
    labelled = posts.loc[:, list(REQUIRED_COLUMNS)].copy()
    labelled["ceo_label"] = [_label(value) for value in labelled["ceo_type"]]
    labelled["gender_label"] = [_label(value) for value in labelled["gender_as_coded"]]
    return labelled


def _check_unique(ids: Iterable[Hashable]) -> None:
    """Refuse repeated ids without echoing any of them."""
    counts = Counter(ids)
    repeated = sum(1 for count in counts.values() if count > 1)
    if repeated:
        raise ValueError(f"{repeated} duplicate post_id value(s); every post_id must be unique")


def _prepare(posts: pd.DataFrame) -> pd.DataFrame:
    table = _with_labels(posts)
    if table["post_id"].isna().to_numpy().any():
        raise ValueError("a post has no post_id")
    _check_unique(table["post_id"])
    no_leader = int(table["leader_id"].isna().to_numpy().sum())
    if no_leader:
        verb = "post has" if no_leader == 1 else "posts have"
        raise ValueError(f"{no_leader} {verb} no leader_id, so the per-leader cap cannot be applied")
    strata_per_leader = table[["leader_id", "ceo_label", "gender_label"]].drop_duplicates().groupby("leader_id").size()
    split = int((strata_per_leader > 1).to_numpy().sum())
    if split:
        noun = "leader appears" if split == 1 else "leaders appear"
        raise ValueError(f"{split} {noun} in more than one ceo_type/gender stratum; the cap would not hold")
    return table.sort_values("post_id").reset_index(drop=True)


def _capped_shuffle(table: pd.DataFrame, settings: GoldSettings) -> pd.DataFrame:
    """Posts in random order with each leader's later posts beyond the cap dropped."""
    rng = np.random.default_rng(settings.seed)
    shuffled = table.iloc[rng.permutation(len(table))]
    position_within_leader = shuffled.groupby("leader_id").cumcount()
    return shuffled[position_within_leader < settings.max_posts_per_leader]


def _allocate(available: dict[Stratum, int], size: int) -> dict[Stratum, int]:
    """Proportional quotas that add up to `size`, by largest remainder in whole numbers."""
    total = sum(available.values())
    shares = {stratum: divmod(size * count, total) for stratum, count in available.items()}
    quotas = {stratum: base for stratum, (base, _) in shares.items()}
    leftover = size - sum(quotas.values())
    by_remainder = sorted(shares, key=lambda stratum: (-shares[stratum][1], stratum))
    return {stratum: quota + (1 if stratum in by_remainder[:leftover] else 0) for stratum, quota in quotas.items()}


def sample_gold_set(posts: pd.DataFrame, settings: GoldSettings) -> tuple[str, ...]:
    """The gold-set post_ids, sorted: stratified, capped per leader, and the same every time for the same seed."""
    eligible = _capped_shuffle(_prepare(posts), settings)
    if len(eligible) < settings.size:
        raise ValueError(
            f"only {len(eligible)} posts remain after the per-leader cap of {settings.max_posts_per_leader}; "
            f"{settings.size} are needed"
        )
    groups: dict[Stratum, pd.DataFrame] = {
        (str(ceo), str(gender)): rows
        for (ceo, gender), rows in eligible.groupby(["ceo_label", "gender_label"], sort=True)
    }
    quotas = _allocate({stratum: len(rows) for stratum, rows in groups.items()}, settings.size)
    chosen: list[str] = []
    for stratum, rows in groups.items():
        chosen.extend(rows["post_id"].head(quotas[stratum]))
    return tuple(sorted(chosen))


def stratum_report(posts: pd.DataFrame, chosen: Sequence[str]) -> pd.DataFrame:
    """Posts available and posts drawn in every ceo_type x gender_as_coded stratum, empty strata included."""
    labelled = _with_labels(posts)
    labelled["drawn"] = labelled["post_id"].isin(list(chosen)).astype(int)
    grouped = labelled.groupby(["ceo_label", "gender_label"], sort=True)
    report = grouped.agg(available=("post_id", "size"), drawn=("drawn", "sum")).reset_index()
    return report.rename(columns={"ceo_label": "ceo_type", "gender_label": "gender_as_coded"})


def _balanced_group_order(coder_names: Sequence[str], per_post: int) -> list[tuple[str, ...]]:
    """Every coder group, ordered so that each prefix of the list leaves the coders' loads as even as possible."""
    remaining = list(combinations(coder_names, per_post))
    load = dict.fromkeys(coder_names, 0)
    ordered: list[tuple[str, ...]] = []
    while remaining:
        best = min(remaining, key=lambda group: (_squared_load_after(load, group), group))
        ordered.append(best)
        remaining.remove(best)
        load = {name: load[name] + (name in best) for name in coder_names}
    return ordered


def _squared_load_after(load: dict[str, int], group: tuple[str, ...]) -> int:
    return sum((count + (name in group)) ** 2 for name, count in load.items())


def assign_coders(post_ids: Iterable[str], settings: GoldSettings) -> tuple[CoderAssignment, ...]:
    """Give every post to `coders_per_post` different coders, balanced across coders and across coder groups."""
    ids = sorted(post_ids)
    _check_unique(ids)
    coder_names = [f"coder_{number}" for number in range(1, settings.coders + 1)]
    order = _balanced_group_order(coder_names, settings.coders_per_post)
    shuffled = np.random.default_rng(settings.seed).permutation(len(ids))
    rows = [
        CoderAssignment(post_id=ids[index], coder=coder)
        for turn, index in enumerate(shuffled)
        for coder in order[turn % len(order)]
    ]
    return tuple(sorted(rows, key=lambda row: (row.post_id, row.coder)))


def assignment_balance(assignments: Iterable[CoderAssignment]) -> tuple[Counter[str], Counter[tuple[str, ...]]]:
    """Posts per coder, and posts per coder group (the pair when two coders read each post)."""
    rows = list(assignments)
    by_post: dict[str, list[str]] = {}
    for row in rows:
        by_post.setdefault(row.post_id, []).append(row.coder)
    coder_counts = Counter(row.coder for row in rows)
    group_counts = Counter(tuple(sorted(coders)) for coders in by_post.values())
    return coder_counts, group_counts
