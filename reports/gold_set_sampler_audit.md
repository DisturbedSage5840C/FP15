# Gold-set sampler audit (SYNTHETIC)

**SYNTHETIC DATA. Every table below is invented. No real leader, post or id was read. Counts only.**

Command: `make gold-set-audit` (`python -m src.gold_set_audit`). Settings come from configs/thresholds.yaml: gold_set_size 300, per-leader cap 3 (a proposal awaiting mentor approval), seed 20261120, min_posts_per_leader 15.

## Assumed shape of the synthetic table

- 560 leaders, each in exactly one ceo_type x gender stratum. 15% are Founder-CEO; 7% are coded gender 0 (the other leaders are coded 1; the audit uses the codes as they are and attaches no meaning to them).
- Posts per leader: 1 plus a lognormal draw (median 6, sigma 1.1), so counts are heavy-tailed and some leaders have a single post. These two numbers are assumptions, not estimates from the real data. Table seeds 0 to 19.

## How to read the columns

- leaders / posts: in the pool before the cap. posts_after_cap: each leader counted at most the cap.
- quota: the stratum's share of the gold-set size, proportional to posts_after_cap (largest remainder).
- drawn: posts the sampler actually picked. leaders_used: leaders with at least one drawn post.
- unfilled: quota minus drawn. A stratum that cannot be filled has unfilled above zero.
- seeds_empty: seeds on which the stratum has no posts in the pool. The sampler gives such a stratum no quota and does not report it, so it shows unfilled 0; read it together with seeds_empty.

## Option A: draw from all leaders with posts

### One table (seed 0)

Seed 0: 560 leaders in the pool, 6057 posts, 1569 after the cap. Strata that cannot be filled (quota above what was drawn): 0 of 4. Strata with no posts in the pool (nothing to draw): 0 of 4.

| ceo_type | gender_as_coded | leaders | leaders_used | posts | posts_after_cap | quota | drawn | unfilled |
|---|---|---|---|---|---|---|---|---|
| Founder-CEO | 0 | 7 | 4 | 54 | 21 | 4 | 4 | 0 |
| Founder-CEO | 1 | 77 | 28 | 925 | 222 | 43 | 43 | 0 |
| Professional CEO | 0 | 32 | 12 | 301 | 91 | 17 | 17 | 0 |
| Professional CEO | 1 | 444 | 160 | 4777 | 1235 | 236 | 236 | 0 |

### Across 20 seeds

Seeds on which the sampler could draw 300 posts: 20 of 20. Seeds on which it refused (capped pool below 300): 0.

| ceo_type | gender_as_coded | leaders_median | leaders_used_median | posts_after_cap_median | quota_median | drawn_min | drawn_median | drawn_max | seeds_unfilled | seeds_empty |
|---|---|---|---|---|---|---|---|---|---|---|
| Founder-CEO | 0 | 5 | 2 | 15 | 3 | 2 | 3 | 5 | 0 | 0 |
| Founder-CEO | 1 | 79 | 28 | 221 | 42.5 | 40 | 42.5 | 44 | 0 | 0 |
| Professional CEO | 0 | 34 | 12 | 94 | 18 | 16 | 18 | 20 | 0 | 0 |
| Professional CEO | 1 | 442 | 159.5 | 1234.5 | 236.5 | 236 | 236.5 | 240 | 0 | 0 |

## Option B: draw only from leaders with at least 15 posts (min_posts_per_leader)

### One table (seed 0)

Seed 0: 107 leaders in the pool, 3441 posts, 321 after the cap. Strata that cannot be filled (quota above what was drawn): 0 of 4. Strata with no posts in the pool (nothing to draw): 1 of 4.

| ceo_type | gender_as_coded | leaders | leaders_used | posts | posts_after_cap | quota | drawn | unfilled |
|---|---|---|---|---|---|---|---|---|
| Founder-CEO | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| Founder-CEO | 1 | 19 | 19 | 600 | 57 | 53 | 53 | 0 |
| Professional CEO | 0 | 6 | 6 | 135 | 18 | 17 | 17 | 0 |
| Professional CEO | 1 | 82 | 82 | 2706 | 246 | 230 | 230 | 0 |

### Across 20 seeds

Seeds on which the sampler could draw 300 posts: 20 of 20. Seeds on which it refused (capped pool below 300): 0.

| ceo_type | gender_as_coded | leaders_median | leaders_used_median | posts_after_cap_median | quota_median | drawn_min | drawn_median | drawn_max | seeds_unfilled | seeds_empty |
|---|---|---|---|---|---|---|---|---|---|---|
| Founder-CEO | 0 | 1 | 1 | 3 | 3 | 0 | 3 | 7 | 0 | 4 |
| Founder-CEO | 1 | 16.5 | 16.5 | 49.5 | 40.5 | 26 | 40.5 | 55 | 0 | 0 |
| Professional CEO | 0 | 7 | 6 | 21 | 16.5 | 8 | 16.5 | 27 | 0 | 0 |
| Professional CEO | 1 | 101.5 | 95 | 304.5 | 239.5 | 216 | 239.5 | 252 | 0 | 0 |

## What this does and does not show

The counts describe the sampler on invented tables. They say nothing about the real leaders, and the shape assumptions above change them. Which pool to draw from is an open question for the team and the mentors (see docs/decisions.md, a proposal, not a decision). The sampler was not changed.
