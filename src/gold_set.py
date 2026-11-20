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

Targets come from the pool itself, or, when a `reference` table is given, from that table (the population the study
covers). With a reference an empty or thin stratum in the pool keeps a non-zero target and shows up as a shortfall;
without one a stratum that is absent from the pool has no target at all and could never be reported. The result carries
a per-stratum table of target, drawn and shortfall. If `raise_on_shortfall` is true (the default in the thresholds file)
a stratum with a non-zero target that draws fewer posts than its target raises an error naming strata and counts only.

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

STRATA_COLUMNS = ("ceo_type", "gender_as_coded", "target", "drawn", "shortfall")

Stratum = tuple[str, str]


@dataclass(frozen=True)
class GoldSettings:
    """Sampling and coder settings, all read from the thresholds file."""

    size: int
    max_posts_per_leader: int
    seed: int
    coders: int
    coders_per_post: int
    raise_on_shortfall: bool = True


@dataclass(frozen=True, eq=False)
class GoldDraw:
    """The gold-set post_ids (sorted) and, per stratum, the target, what was drawn and the shortfall."""

    post_ids: tuple[str, ...]
    strata: pd.DataFrame


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
        raise_on_shortfall=_load_flag("gold_set_raise_on_shortfall", path),
    )
    _validate_settings(settings, path)
    return settings


def _load_flag(key: str, path: Path) -> bool:
    """A true/false setting; anything else (a string such as "yes", a number) is refused rather than coerced."""
    value = load_threshold(key, path)
    if not isinstance(value, bool):
        raise ValueError(f"{path}: {key} must be true or false")
    return value


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


def _groups(rows: pd.DataFrame) -> dict[Stratum, pd.DataFrame]:
    return {
        (str(ceo), str(gender)): group for (ceo, gender), group in rows.groupby(["ceo_label", "gender_label"], sort=True)
    }


def _strata_table(targets: dict[Stratum, int], drawn: dict[Stratum, int]) -> pd.DataFrame:
    rows = [
        (ceo, gender, targets.get((ceo, gender), 0), drawn.get((ceo, gender), 0))
        for ceo, gender in sorted(set(targets) | set(drawn))
    ]
    table = pd.DataFrame(rows, columns=["ceo_type", "gender_as_coded", "target", "drawn"])
    table["shortfall"] = (table["target"] - table["drawn"]).clip(lower=0)
    return table.loc[:, list(STRATA_COLUMNS)].astype({"target": int, "drawn": int, "shortfall": int})


def _raise_on_shortfall(strata: pd.DataFrame) -> None:
    """Refuse a draw in which a stratum with a non-zero target came up short; strata and counts only, no ids."""
    short = strata[(strata["target"] > 0) & (strata["drawn"] < strata["target"])]
    if short.empty:
        return
    detail = "; ".join(
        f"{row.ceo_type} x {row.gender_as_coded}: target {row.target}, drawn {row.drawn}"
        for row in short.itertuples(index=False)
    )
    raise ValueError(
        f"shortfall in {len(short)} stratum/strata, so the gold set cannot be the planned size ({detail}); "
        "set gold_set_raise_on_shortfall to false only to look at the table"
    )


def sample_gold_set(posts: pd.DataFrame, settings: GoldSettings, reference: pd.DataFrame | None = None) -> GoldDraw:
    """The gold-set post_ids, sorted, with a per-stratum table of target, drawn and shortfall.

    Stratified, capped per leader, and the same every time for the same seed. Targets are allocated from `reference`
    (same columns as `posts`) when it is given, otherwise from `posts`; the draw always comes from `posts`.
    """
    pool = _capped_shuffle(_prepare(posts), settings)
    basis = pool if reference is None else _capped_shuffle(_prepare(reference), settings)
    if len(basis) < settings.size:
        raise ValueError(
            f"only {len(basis)} posts remain after the per-leader cap of {settings.max_posts_per_leader}; "
            f"{settings.size} are needed"
        )
    targets = _allocate({stratum: len(rows) for stratum, rows in _groups(basis).items()}, settings.size)
    groups = _groups(pool)
    chosen: list[str] = []
    drawn: dict[Stratum, int] = {}
    for stratum, rows in groups.items():
        picked = list(rows["post_id"].head(targets.get(stratum, 0)))
        chosen.extend(picked)
        drawn[stratum] = len(picked)
    strata = _strata_table(targets, drawn)
    if settings.raise_on_shortfall:
        _raise_on_shortfall(strata)
    return GoldDraw(post_ids=tuple(sorted(chosen)), strata=strata)


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
