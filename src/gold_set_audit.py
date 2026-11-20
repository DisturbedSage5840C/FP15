"""Audit of the gold-set sampler on SYNTHETIC tables shaped like ours. No real data is read or written.

`python -m src.gold_set_audit` (make gold-set-audit) builds invented leader/post tables, runs src/gold_set.py on them
with the settings in configs/thresholds.yaml, and writes reports/gold_set_sampler_audit.md: counts only, labelled
SYNTHETIC. It never alters the sampler. It only reports how the sampler behaves, so a human can decide.

The table shape (number of leaders, share of founder-CEOs, share coded 0, the heavy-tailed posts per leader) is an
ASSUMPTION written down in the constants below. It is not estimated from the real posts, because this step must not
touch them. Each leader is in exactly one stratum, as the sampler requires.
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd

# Private helpers of the sampler are imported on purpose: the audit must use the very quotas and labels the sampler
# uses, and copying them here would let the two drift apart. Nothing in src/gold_set.py is changed.
from src.gold_set import GoldSettings, _with_labels, load_gold_settings, sample_gold_set
from src.thresholds import load_threshold

DEFAULT_REPORT_PATH = Path("reports/gold_set_sampler_audit.md")

LEADERS = 560
FOUNDER_SHARE = 0.15
GENDER_ZERO_SHARE = 0.07
FOUNDER_LABEL = "Founder-CEO"
PROFESSIONAL_LABEL = "Professional CEO"
GENDER_ZERO, GENDER_ONE = 0, 1
POSTS_MEDIAN = 6.0  # median of the lognormal draw before adding one post, so every leader has at least one
POSTS_SIGMA = 1.1  # spread of the lognormal draw: large enough for a heavy right tail
AUDIT_SEEDS = tuple(range(20))

AUDIT_COLUMNS = (
    "ceo_type", "gender_as_coded", "leaders", "leaders_used", "posts", "posts_after_cap", "quota", "drawn", "unfilled",
)
COUNT_COLUMNS = AUDIT_COLUMNS[2:]
SUMMARY_COLUMNS = (
    "ceo_type", "gender_as_coded", "leaders_median", "leaders_used_median", "posts_after_cap_median", "quota_median",
    "drawn_min", "drawn_median", "drawn_max", "seeds_unfilled", "seeds_empty",
)
STRATUM_KEYS = ["ceo_type", "gender_as_coded"]


def synthetic_posts(seed: int, leaders: int = LEADERS) -> pd.DataFrame:
    """Invented post table: one row per post, each leader in one ceo_type x gender stratum, heavy-tailed post counts."""
    rng = np.random.default_rng(seed)
    founders = round(FOUNDER_SHARE * leaders)
    gender_zero = round(GENDER_ZERO_SHARE * leaders)
    ceo_types = np.array([FOUNDER_LABEL] * founders + [PROFESSIONAL_LABEL] * (leaders - founders))
    genders = np.array([GENDER_ZERO] * gender_zero + [GENDER_ONE] * (leaders - gender_zero))
    rng.shuffle(ceo_types)
    rng.shuffle(genders)
    counts = 1 + np.floor(rng.lognormal(np.log(POSTS_MEDIAN), POSTS_SIGMA, size=leaders)).astype(int)
    leader_index = np.repeat(np.arange(leaders), counts)
    return pd.DataFrame(
        {
            "post_id": [f"P{number:06d}" for number in range(len(leader_index))],
            "ceo_type": ceo_types[leader_index],
            "gender_as_coded": genders[leader_index],
            "leader_id": [f"S{index:04d}" for index in leader_index],
        }
    )


def restrict_to_min_posts(posts: pd.DataFrame, minimum: int) -> pd.DataFrame:
    """A new table with only the leaders who have at least `minimum` posts; the input is not changed."""
    posts_per_leader = posts.groupby("leader_id")["post_id"].transform("size")
    return posts[posts_per_leader >= minimum].reset_index(drop=True)


def capped_pool_size(posts: pd.DataFrame, cap: int) -> int:
    """Posts left after keeping at most `cap` per leader (the count the sampler compares with the gold-set size)."""
    return int(posts.groupby("leader_id")["post_id"].size().clip(upper=cap).sum())


def _per_leader(posts: pd.DataFrame, chosen: Sequence[str], cap: int) -> pd.DataFrame:
    labelled = _with_labels(posts)
    labelled["drawn"] = labelled["post_id"].isin(list(chosen)).astype(int)
    per_leader = labelled.groupby("leader_id").agg(
        ceo_type=("ceo_label", "first"),
        gender_as_coded=("gender_label", "first"),
        posts=("post_id", "size"),
        drawn=("drawn", "sum"),
    )
    per_leader["posts_after_cap"] = per_leader["posts"].clip(upper=cap)
    per_leader["used"] = (per_leader["drawn"] > 0).astype(int)
    return per_leader


def _quota_by_stratum(strata: pd.DataFrame) -> dict[tuple[str, str], int]:
    """Targets from the sampler's own per-stratum table, keyed by (ceo_type, gender_as_coded)."""
    return {(row.ceo_type, row.gender_as_coded): int(row.target) for row in strata.itertuples(index=False)}


def audit_pool(posts: pd.DataFrame, settings: GoldSettings, reference: pd.DataFrame | None = None) -> pd.DataFrame:
    """Run the sampler on `posts` and count, per stratum, leaders, posts, the quota and what was drawn.

    Quotas are the sampler's targets: allocated from `reference` when given (the population the study covers), else
    from `posts`. The audit always runs the sampler with raising switched off, so a stratum that falls short is a row
    with `unfilled` above zero (the sampler's shortfall) instead of an error; the real settings still raise. Every
    ceo_type x gender stratum that could exist from the labels present is listed, empty ones as zeros. The sampler's
    other error (a capped pool smaller than the gold-set size) is not caught here.
    """
    draw = sample_gold_set(posts, replace(settings, raise_on_shortfall=False), reference=reference)
    per_leader = _per_leader(posts, draw.post_ids, settings.max_posts_per_leader)
    counts = per_leader.groupby(STRATUM_KEYS).agg(
        leaders=("posts", "size"),
        leaders_used=("used", "sum"),
        posts=("posts", "sum"),
        posts_after_cap=("posts_after_cap", "sum"),
        drawn=("drawn", "sum"),
    )
    ceo_types = sorted(set(per_leader["ceo_type"]) | set(draw.strata["ceo_type"]))
    genders = sorted(set(per_leader["gender_as_coded"]) | set(draw.strata["gender_as_coded"]))
    counts = counts.reindex(pd.MultiIndex.from_product([ceo_types, genders], names=STRATUM_KEYS), fill_value=0)
    quota = _quota_by_stratum(draw.strata)
    counts["quota"] = [quota.get(stratum, 0) for stratum in counts.index]
    counts["unfilled"] = counts["quota"] - counts["drawn"]
    typed = counts.reset_index().loc[:, list(AUDIT_COLUMNS)]
    return typed.astype({column: int for column in COUNT_COLUMNS})


def empty_strata(audit: pd.DataFrame) -> int:
    """Strata with no posts left to draw from. Given a reference, such a stratum still has a quota and shows as unfilled."""
    return int((audit["posts_after_cap"] == 0).sum())


def _pool(seed: int, minimum: int | None, leaders: int) -> pd.DataFrame:
    posts = synthetic_posts(seed, leaders)
    return posts if minimum is None else restrict_to_min_posts(posts, minimum)


def _reference(seed: int, minimum: int | None, leaders: int) -> pd.DataFrame | None:
    """The population the quotas are set from: everyone, when the pool is restricted; the pool itself otherwise."""
    return None if minimum is None else synthetic_posts(seed, leaders)


def summarise_seeds(
    seeds: Sequence[int], settings: GoldSettings, minimum: int | None, leaders: int = LEADERS
) -> tuple[pd.DataFrame, int]:
    """Per-stratum counts over many seeds, and the number of seeds on which the sampler cannot draw at all.

    A seed is counted as "cannot draw" when the capped pool is smaller than the gold-set size, the exact condition
    on which the sampler raises; any other error is not hidden.
    """
    audits: list[pd.DataFrame] = []
    cannot_draw = 0
    for seed in seeds:
        posts = _pool(seed, minimum, leaders)
        reference = _reference(seed, minimum, leaders)
        basis = posts if reference is None else reference
        if capped_pool_size(basis, settings.max_posts_per_leader) < settings.size:
            cannot_draw += 1
            continue
        audits.append(audit_pool(posts, settings, reference=reference).assign(seed=seed))
    if not audits:
        return pd.DataFrame(columns=list(SUMMARY_COLUMNS)), cannot_draw
    stacked = pd.concat(audits, ignore_index=True)
    stacked["is_unfilled"] = (stacked["unfilled"] > 0).astype(int)
    stacked["is_empty"] = (stacked["posts_after_cap"] == 0).astype(int)
    summary = stacked.groupby(STRATUM_KEYS).agg(
        leaders_median=("leaders", "median"),
        leaders_used_median=("leaders_used", "median"),
        posts_after_cap_median=("posts_after_cap", "median"),
        quota_median=("quota", "median"),
        drawn_min=("drawn", "min"),
        drawn_median=("drawn", "median"),
        drawn_max=("drawn", "max"),
        seeds_unfilled=("is_unfilled", "sum"),
        seeds_empty=("is_empty", "sum"),
    )
    return summary.reset_index().loc[:, list(SUMMARY_COLUMNS)], cannot_draw


def _markdown_table(frame: pd.DataFrame) -> str:
    header = "| " + " | ".join(frame.columns) + " |"
    divider = "|" + "|".join("---" for _ in frame.columns) + "|"
    rows = [
        "| " + " | ".join(f"{value:g}" if isinstance(value, float) else str(value) for value in row) + " |"
        for row in frame.itertuples(index=False)
    ]
    return "\n".join([header, divider, *rows])


def _single_seed_section(seed: int, settings: GoldSettings, minimum: int | None) -> str:
    posts = _pool(seed, minimum, LEADERS)
    reference = _reference(seed, minimum, LEADERS)
    pool_size = capped_pool_size(posts if reference is None else reference, settings.max_posts_per_leader)
    if pool_size < settings.size:
        return (
            f"Seed {seed}: the sampler cannot draw. {pool_size} posts remain after the cap of "
            f"{settings.max_posts_per_leader}; {settings.size} are needed.\n"
        )
    audit = audit_pool(posts, settings, reference=reference)
    cannot_fill = int((audit["unfilled"] > 0).sum())
    nothing_to_draw = empty_strata(audit)
    short_posts = int(audit['unfilled'].sum())
    return (
        f"Seed {seed}: {posts['leader_id'].nunique()} leaders in the pool, {len(posts)} posts, {pool_size} after the "
        f"cap. Strata with a shortfall (quota above what was drawn): {cannot_fill} of {len(audit)}, {short_posts} posts short in all. Strata with no posts in the pool (nothing to draw): {nothing_to_draw} of {len(audit)}.\n\n{_markdown_table(audit)}\n"
    )


def _option_section(title: str, settings: GoldSettings, minimum: int | None) -> str:
    first_seed = AUDIT_SEEDS[0]
    summary, cannot_draw = summarise_seeds(AUDIT_SEEDS, settings, minimum)
    table = _markdown_table(summary) if len(summary) else "No seed could be drawn, so there is no table."
    return (
        f"## {title}\n\n### One table (seed {first_seed})\n\n{_single_seed_section(first_seed, settings, minimum)}\n"
        f"### Across {len(AUDIT_SEEDS)} seeds\n\n"
        f"Seeds on which the sampler could draw {settings.size} posts: {len(AUDIT_SEEDS) - cannot_draw} of "
        f"{len(AUDIT_SEEDS)}. Seeds on which it refused (capped pool below {settings.size}): {cannot_draw}.\n\n"
        f"{table}\n"
    )


def render_report(settings: GoldSettings, min_posts: int) -> str:
    """Markdown for reports/gold_set_sampler_audit.md: synthetic counts only, no ids and no text."""
    option_a = _option_section("Option A: draw from all leaders with posts", settings, None)
    option_b = _option_section(
        f"Option B: draw only from leaders with at least {min_posts} posts (min_posts_per_leader)", settings, min_posts
    )
    return (
        "# Gold-set sampler audit (SYNTHETIC)\n\n"
        "**SYNTHETIC DATA. Every table below is invented. No real leader, post or id was read. Counts only.**\n\n"
        "Command: `make gold-set-audit` (`python -m src.gold_set_audit`). Settings come from configs/thresholds.yaml: "
        f"gold_set_size {settings.size}, per-leader cap {settings.max_posts_per_leader} (a proposal awaiting mentor "
        f"approval), seed {settings.seed}, min_posts_per_leader {min_posts}.\n\n"
        "## Assumed shape of the synthetic table\n\n"
        f"- {LEADERS} leaders, each in exactly one ceo_type x gender stratum. {FOUNDER_SHARE:.0%} are "
        f"{FOUNDER_LABEL}; {GENDER_ZERO_SHARE:.0%} are coded gender {GENDER_ZERO} (the other leaders are coded "
        f"{GENDER_ONE}; the audit uses the codes as they are and attaches no meaning to them).\n"
        f"- Posts per leader: 1 plus a lognormal draw (median {POSTS_MEDIAN:g}, sigma {POSTS_SIGMA:g}), so counts are "
        "heavy-tailed and some leaders have a single post. These two numbers are assumptions, not estimates from the "
        f"real data. Table seeds {AUDIT_SEEDS[0]} to {AUDIT_SEEDS[-1]}.\n\n"
        "## How to read the columns\n\n"
        "- leaders / posts: in the pool before the cap. posts_after_cap: each leader counted at most the cap.\n"
        "- quota: the stratum's share of the gold-set size, proportional to posts_after_cap (largest remainder).\n"
        "- drawn: posts the sampler actually picked. leaders_used: leaders with at least one drawn post.\n"
        "- unfilled: the sampler's shortfall, quota minus drawn. A stratum that falls short has unfilled above zero.\n"
        "- seeds_empty: seeds on which the stratum has no posts in the pool.\n\n"
        "## Shortfalls\n\n"
        "The sampler returns a per-stratum table of target, drawn and shortfall with the post_ids. With "
        "`gold_set_raise_on_shortfall: true` (the default in configs/thresholds.yaml) it raises an error if any stratum "
        "with a non-zero target draws fewer posts than its target. This audit runs it with that flag off, so a "
        "shortfall is a row below instead of a stop. A stratum with no posts in the pool can only have a non-zero "
        "target if the targets are set from a larger population, so Option B sets its quotas from all leaders "
        "(the Option A pool) and draws only from leaders at the minimum. Option A sets its quotas from its own pool, "
        "so an empty stratum there has no target and is shown only by seeds_empty.\n\n"
        f"{option_a}\n{option_b}\n"
        "## What this does and does not show\n\n"
        "The counts describe the sampler on invented tables. They say nothing about the real leaders, and the shape "
        "assumptions above change them. Which pool to draw from is an open question for the team and the mentors "
        "(see docs/decisions.md, a proposal, not a decision). The sampler was changed only to report shortfalls; its draw is the same.\n"
    )


def main() -> int:
    settings = load_gold_settings()
    report = render_report(settings, int(load_threshold("min_posts_per_leader")))
    DEFAULT_REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    DEFAULT_REPORT_PATH.write_text(report, encoding="utf-8")
    print(f"wrote {DEFAULT_REPORT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
