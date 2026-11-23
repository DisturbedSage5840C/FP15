> PROVISIONAL. G1 unsigned so raw cells stand in for posts; English-only pronoun counts; no gold-set check; exploratory, not pre-registered. Claims are about the image projected in public posts, never personality. The I-rate is one signal, not a narcissism score.

# Provisional leader-level measures

Exploratory only. Nothing here is pre-registered and no gate is signed.

- Leaders are kept when they have at least 15 scored cells (the minimum in configs/thresholds.yaml).
- A cell with no words stays missing and is not scored.
- Rates are per 100 words from the English-only word lists in the dictionary layer.
- Shrunk means use the existing empirical Bayes shrinkage from cell to leader, run separately for each measure and each cell set.
- Counts under 5 are shown as "<5", and a lone hidden count hides its next smallest too.

## Cells

|  | count |
|---|---|
| cleaned cells | 26,945 |
| cells with at least one word (scored) | 26,944 |
| cells marked possible Hinglish | 29 |

## Leader-level rates per 100 words

| measure | cell set | value | leaders | min | q1 | median | q3 | max |
|---|---|---|---|---|---|---|---|---|
| first-person singular (I-rate) | all cells | raw leader mean | 327 | 0.00 | 0.31 | 0.62 | 1.14 | 13.22 |
| first-person singular (I-rate) | all cells | shrunk leader mean | 327 | 0.03 | 0.34 | 0.63 | 1.13 | 11.90 |
| first-person singular (I-rate) | without possible-Hinglish cells | raw leader mean | 327 | 0.00 | 0.31 | 0.62 | 1.14 | 13.22 |
| first-person singular (I-rate) | without possible-Hinglish cells | shrunk leader mean | 327 | 0.03 | 0.34 | 0.63 | 1.13 | 11.90 |
| first-person plural (we-rate) | all cells | raw leader mean | 327 | 0.00 | 0.67 | 1.15 | 1.70 | 6.04 |
| first-person plural (we-rate) | all cells | shrunk leader mean | 327 | 0.23 | 0.74 | 1.16 | 1.66 | 5.43 |
| first-person plural (we-rate) | without possible-Hinglish cells | raw leader mean | 327 | 0.00 | 0.67 | 1.15 | 1.70 | 6.04 |
| first-person plural (we-rate) | without possible-Hinglish cells | shrunk leader mean | 327 | 0.23 | 0.74 | 1.17 | 1.66 | 5.43 |

## Leaders by possible-Hinglish status (all-cells set)

| status | leaders | share of leaders |
|---|---|---|
| leaders with at least one flagged cell | 18 | 5.5% |
| leaders with no flagged cell | 309 | 94.5% |

A leader counts as having a flagged cell when at least one of their cells carries the possible-Hinglish mark. The mark comes from the language flag in post cleaning, whose precision check is still pending a human.

