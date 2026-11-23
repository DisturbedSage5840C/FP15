# Gold-set draw: PROVISIONAL (AI-assisted, not a human sign-off). The draw choices below are pending confirmation by the owner. Counts only: no ids, no names, no text.

Command: `make gold-set-draw` (`python -m src.gold_set_draw`). Settings come from configs/thresholds.yaml: gold_set_size 300, per-leader cap 3 (a proposal awaiting mentor approval), seed 20261120.

**Option A (provisional choice):** the pool is every leader with at least one cleaned post, with no minimum number of posts per leader, so no stratum is empty. Option B (only leaders at or above min_posts_per_leader) is not used. The owner confirms or changes this.

Strata are ceo_type as coded in the posts by gender exactly as coded in Company_Data (nothing inferred from names; a missing value is its own stratum). 'available' counts posts before the cap.

## Pool and draw

- Cells in the pool: 26944 (empty cells left out: 1).
- Leaders in the pool: 563.
- Posts drawn: 300. Leaders drawn from: 184.

## Strata

| ceo_type | gender_as_coded | available | target | drawn | shortfall |
|---|---|---|---|---|---|
| Founder-CEO | 0 | 52 | 1 | 1 | 0 |
| Founder-CEO | 1 | 2922 | 23 | 23 | 0 |
| Founder-CEO | no usable company match | 144 | 1 | 1 | 0 |
| Founder-CEO | no value | 2756 | 16 | 16 | 0 |
| Professional CEO | 0 | 2160 | 20 | 20 | 0 |
| Professional CEO | 1 | 14557 | 171 | 171 | 0 |
| Professional CEO | no usable company match | 219 | 4 | 4 | 0 |
| Professional CEO | no value | 3237 | 42 | 42 | 0 |
| no value | 0 | 74 | 1 | 1 | 0 |
| no value | 1 | 576 | 12 | 12 | 0 |
| no value | no usable company match | 110 | 4 | 4 | 0 |
| no value | no value | 130 | 4 | 4 | 0 |
| unrecognised | no usable company match | 7 | 1 | 1 | 0 |

## Posts drawn per leader

| posts drawn from the leader | leaders |
|---|---|
| 1 | 102 |
| 2 | 48 |
| 3 | 34 |

Post ids and post text are in the git-ignored data/derived file only.
