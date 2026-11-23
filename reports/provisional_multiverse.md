> PROVISIONAL. G1 unsigned so raw cells stand in for posts; English-only pronoun counts; no gold-set check; exploratory, not pre-registered. Claims are about the image projected in public posts, never personality. The I-rate is one signal, not a narcissism score.

# Provisional robustness multiverse

Exploratory only. This multiverse does not replace the pre-registration and no gate is signed.

- The without-sector Step 14C model is rerun for every combination of the configured post minimum, outcome scale and cell set. Founder-CEO and Professional CEO are the only ceo_type groups in every fit.
- Counts under 5 show as "<5"; fitted-leader counts use the existing secondary-suppression rule.
- Raw p is shown alongside one Benjamini-Hochberg pass across every displayed comparison. The interval is a normal-approximation interval on the estimate; its level is one minus the Benjamini-Hochberg FDR level in configs/thresholds.yaml, so no new cut is introduced. Estimates are in pronoun uses per 100 words.

## Founder-CEO versus Professional CEO

| post minimum | outcome scale | cells | measure | leaders fitted | contrast | estimate | interval | raw p | BH-adjusted p | note |
|---|---|---|---|---|---|---|---|---|---|---|
| 10 | raw rate | all cells | first-person singular (I-rate) | 358 | Professional CEO minus Founder-CEO | -0.18 | -0.51 to +0.15 | 0.289 | 0.652 |  |
| 10 | raw rate | all cells | first-person plural (we-rate) | 358 | Professional CEO minus Founder-CEO | +0.07 | -0.16 to +0.31 | 0.539 | 0.712 |  |
| 10 | raw rate | without possible-Hinglish cells | first-person singular (I-rate) | 358 | Professional CEO minus Founder-CEO | -0.18 | -0.51 to +0.15 | 0.29 | 0.652 |  |
| 10 | raw rate | without possible-Hinglish cells | first-person plural (we-rate) | 358 | Professional CEO minus Founder-CEO | +0.07 | -0.16 to +0.30 | 0.548 | 0.712 |  |
| 10 | raw rate | without repost or embedded-post cells | first-person singular (I-rate) | 337 | Professional CEO minus Founder-CEO | -0.18 | -0.52 to +0.16 | 0.289 | 0.652 |  |
| 10 | raw rate | without repost or embedded-post cells | first-person plural (we-rate) | 337 | Professional CEO minus Founder-CEO | +0.11 | -0.13 to +0.35 | 0.377 | 0.652 |  |
| 10 | log(1 + rate) | all cells | first-person singular (I-rate) | 358 | Professional CEO minus Founder-CEO | -0.06 | -0.16 to +0.05 | 0.301 | 0.652 |  |
| 10 | log(1 + rate) | all cells | first-person plural (we-rate) | 358 | Professional CEO minus Founder-CEO | +0.01 | -0.08 to +0.09 | 0.889 | 0.957 |  |
| 10 | log(1 + rate) | without possible-Hinglish cells | first-person singular (I-rate) | 358 | Professional CEO minus Founder-CEO | -0.06 | -0.16 to +0.05 | 0.301 | 0.652 |  |
| 10 | log(1 + rate) | without possible-Hinglish cells | first-person plural (we-rate) | 358 | Professional CEO minus Founder-CEO | +0.01 | -0.08 to +0.09 | 0.898 | 0.957 |  |
| 10 | log(1 + rate) | without repost or embedded-post cells | first-person singular (I-rate) | 337 | Professional CEO minus Founder-CEO | -0.06 | -0.17 to +0.05 | 0.304 | 0.652 |  |
| 10 | log(1 + rate) | without repost or embedded-post cells | first-person plural (we-rate) | 337 | Professional CEO minus Founder-CEO | +0.02 | -0.07 to +0.11 | 0.657 | 0.776 |  |
| 10 | raw rate, top 1% leader means trimmed | all cells | first-person singular (I-rate) | 354 or more | Professional CEO minus Founder-CEO | -0.03 | -0.25 to +0.19 | 0.79 | 0.873 |  |
| 10 | raw rate, top 1% leader means trimmed | all cells | first-person plural (we-rate) | 354 or more | Professional CEO minus Founder-CEO | +0.07 | -0.15 to +0.29 | 0.539 | 0.712 |  |
| 10 | raw rate, top 1% leader means trimmed | without possible-Hinglish cells | first-person singular (I-rate) | 354 or more | Professional CEO minus Founder-CEO | -0.03 | -0.24 to +0.19 | 0.792 | 0.873 |  |
| 10 | raw rate, top 1% leader means trimmed | without possible-Hinglish cells | first-person plural (we-rate) | 354 or more | Professional CEO minus Founder-CEO | +0.07 | -0.15 to +0.29 | 0.548 | 0.712 |  |
| 10 | raw rate, top 1% leader means trimmed | without repost or embedded-post cells | first-person singular (I-rate) | 333 or more | Professional CEO minus Founder-CEO | -0.04 | -0.27 to +0.19 | 0.741 | 0.839 |  |
| 10 | raw rate, top 1% leader means trimmed | without repost or embedded-post cells | first-person plural (we-rate) | 333 or more | Professional CEO minus Founder-CEO | +0.04 | -0.18 to +0.26 | 0.708 | 0.819 |  |
| 15 | raw rate | all cells | first-person singular (I-rate) | 316 | Professional CEO minus Founder-CEO | -0.16 | -0.51 to +0.19 | 0.379 | 0.652 |  |
| 15 | raw rate | all cells | first-person plural (we-rate) | 316 | Professional CEO minus Founder-CEO | +0.09 | -0.13 to +0.32 | 0.42 | 0.652 |  |
| 15 | raw rate | without possible-Hinglish cells | first-person singular (I-rate) | 316 | Professional CEO minus Founder-CEO | -0.16 | -0.51 to +0.19 | 0.38 | 0.652 |  |
| 15 | raw rate | without possible-Hinglish cells | first-person plural (we-rate) | 316 | Professional CEO minus Founder-CEO | +0.09 | -0.13 to +0.32 | 0.428 | 0.652 |  |
| 15 | raw rate | without repost or embedded-post cells | first-person singular (I-rate) | 294 | Professional CEO minus Founder-CEO | -0.12 | -0.42 to +0.17 | 0.417 | 0.652 |  |
| 15 | raw rate | without repost or embedded-post cells | first-person plural (we-rate) | 294 | Professional CEO minus Founder-CEO | +0.11 | -0.12 to +0.35 | 0.346 | 0.652 |  |
| 15 | log(1 + rate) | all cells | first-person singular (I-rate) | 316 | Professional CEO minus Founder-CEO | -0.05 | -0.16 to +0.06 | 0.392 | 0.652 |  |
| 15 | log(1 + rate) | all cells | first-person plural (we-rate) | 316 | Professional CEO minus Founder-CEO | +0.02 | -0.07 to +0.11 | 0.646 | 0.775 |  |
| 15 | log(1 + rate) | without possible-Hinglish cells | first-person singular (I-rate) | 316 | Professional CEO minus Founder-CEO | -0.05 | -0.16 to +0.06 | 0.391 | 0.652 |  |
| 15 | log(1 + rate) | without possible-Hinglish cells | first-person plural (we-rate) | 316 | Professional CEO minus Founder-CEO | +0.02 | -0.07 to +0.11 | 0.654 | 0.776 |  |
| 15 | log(1 + rate) | without repost or embedded-post cells | first-person singular (I-rate) | 294 | Professional CEO minus Founder-CEO | -0.03 | -0.14 to +0.08 | 0.568 | 0.712 |  |
| 15 | log(1 + rate) | without repost or embedded-post cells | first-person plural (we-rate) | 294 | Professional CEO minus Founder-CEO | +0.03 | -0.06 to +0.12 | 0.498 | 0.702 |  |
| 15 | raw rate, top 1% leader means trimmed | all cells | first-person singular (I-rate) | 312 or more | Professional CEO minus Founder-CEO | -0.01 | -0.24 to +0.21 | 0.919 | 0.969 |  |
| 15 | raw rate, top 1% leader means trimmed | all cells | first-person plural (we-rate) | 312 or more | Professional CEO minus Founder-CEO | +0.04 | -0.17 to +0.25 | 0.713 | 0.819 |  |
| 15 | raw rate, top 1% leader means trimmed | without possible-Hinglish cells | first-person singular (I-rate) | 312 or more | Professional CEO minus Founder-CEO | -0.01 | -0.24 to +0.21 | 0.922 | 0.969 |  |
| 15 | raw rate, top 1% leader means trimmed | without possible-Hinglish cells | first-person plural (we-rate) | 312 or more | Professional CEO minus Founder-CEO | +0.04 | -0.17 to +0.25 | 0.724 | 0.826 |  |
| 15 | raw rate, top 1% leader means trimmed | without repost or embedded-post cells | first-person singular (I-rate) | 290 or more | Professional CEO minus Founder-CEO | +0.02 | -0.22 to +0.25 | 0.898 | 0.957 |  |
| 15 | raw rate, top 1% leader means trimmed | without repost or embedded-post cells | first-person plural (we-rate) | 290 or more | Professional CEO minus Founder-CEO | +0.07 | -0.14 to +0.29 | 0.508 | 0.709 |  |
| 16 | raw rate | all cells | first-person singular (I-rate) | 305 | Professional CEO minus Founder-CEO | -0.19 | -0.47 to +0.10 | 0.196 | 0.602 |  |
| 16 | raw rate | all cells | first-person plural (we-rate) | 305 | Professional CEO minus Founder-CEO | +0.10 | -0.13 to +0.33 | 0.399 | 0.652 |  |
| 16 | raw rate | without possible-Hinglish cells | first-person singular (I-rate) | 305 | Professional CEO minus Founder-CEO | -0.19 | -0.47 to +0.10 | 0.197 | 0.602 |  |
| 16 | raw rate | without possible-Hinglish cells | first-person plural (we-rate) | 305 | Professional CEO minus Founder-CEO | +0.10 | -0.13 to +0.33 | 0.407 | 0.652 |  |
| 16 | raw rate | without repost or embedded-post cells | first-person singular (I-rate) | 284 | Professional CEO minus Founder-CEO | -0.22 | -0.52 to +0.08 | 0.154 | 0.51 |  |
| 16 | raw rate | without repost or embedded-post cells | first-person plural (we-rate) | 284 | Professional CEO minus Founder-CEO | +0.11 | -0.13 to +0.35 | 0.377 | 0.652 |  |
| 16 | log(1 + rate) | all cells | first-person singular (I-rate) | 305 | Professional CEO minus Founder-CEO | -0.06 | -0.16 to +0.05 | 0.3 | 0.652 |  |
| 16 | log(1 + rate) | all cells | first-person plural (we-rate) | 305 | Professional CEO minus Founder-CEO | +0.03 | -0.06 to +0.11 | 0.575 | 0.712 |  |
| 16 | log(1 + rate) | without possible-Hinglish cells | first-person singular (I-rate) | 305 | Professional CEO minus Founder-CEO | -0.06 | -0.16 to +0.05 | 0.3 | 0.652 |  |
| 16 | log(1 + rate) | without possible-Hinglish cells | first-person plural (we-rate) | 305 | Professional CEO minus Founder-CEO | +0.02 | -0.06 to +0.11 | 0.583 | 0.712 |  |
| 16 | log(1 + rate) | without repost or embedded-post cells | first-person singular (I-rate) | 284 | Professional CEO minus Founder-CEO | -0.06 | -0.18 to +0.05 | 0.281 | 0.652 |  |
| 16 | log(1 + rate) | without repost or embedded-post cells | first-person plural (we-rate) | 284 | Professional CEO minus Founder-CEO | +0.03 | -0.06 to +0.12 | 0.518 | 0.712 |  |
| 16 | raw rate, top 1% leader means trimmed | all cells | first-person singular (I-rate) | 301 or more | Professional CEO minus Founder-CEO | -0.03 | -0.24 to +0.18 | 0.774 | 0.868 |  |
| 16 | raw rate, top 1% leader means trimmed | all cells | first-person plural (we-rate) | 301 or more | Professional CEO minus Founder-CEO | +0.04 | -0.17 to +0.26 | 0.693 | 0.814 |  |
| 16 | raw rate, top 1% leader means trimmed | without possible-Hinglish cells | first-person singular (I-rate) | 301 or more | Professional CEO minus Founder-CEO | -0.03 | -0.24 to +0.18 | 0.777 | 0.868 |  |
| 16 | raw rate, top 1% leader means trimmed | without possible-Hinglish cells | first-person plural (we-rate) | 301 or more | Professional CEO minus Founder-CEO | +0.04 | -0.17 to +0.25 | 0.704 | 0.819 |  |
| 16 | raw rate, top 1% leader means trimmed | without repost or embedded-post cells | first-person singular (I-rate) | 280 or more | Professional CEO minus Founder-CEO | -0.06 | -0.30 to +0.18 | 0.62 | 0.75 |  |
| 16 | raw rate, top 1% leader means trimmed | without repost or embedded-post cells | first-person plural (we-rate) | 280 or more | Professional CEO minus Founder-CEO | +0.07 | -0.16 to +0.29 | 0.558 | 0.712 |  |

## Title-family joint test

| post minimum | outcome scale | cells | measure | leaders fitted | contrast | estimate | interval | raw p | BH-adjusted p | note |
|---|---|---|---|---|---|---|---|---|---|---|
| 10 | raw rate | all cells | first-person singular (I-rate) | 358 | n/a | n/a | n/a | 0.551 | 0.712 |  |
| 10 | raw rate | all cells | first-person plural (we-rate) | 358 | n/a | n/a | n/a | 0.00117 | 0.0127 |  |
| 10 | raw rate | without possible-Hinglish cells | first-person singular (I-rate) | 358 | n/a | n/a | n/a | 0.552 | 0.712 |  |
| 10 | raw rate | without possible-Hinglish cells | first-person plural (we-rate) | 358 | n/a | n/a | n/a | 0.00117 | 0.0127 |  |
| 10 | raw rate | without repost or embedded-post cells | first-person singular (I-rate) | 337 | n/a | n/a | n/a | 0.977 | 0.996 |  |
| 10 | raw rate | without repost or embedded-post cells | first-person plural (we-rate) | 337 | n/a | n/a | n/a | 0.000322 | 0.00522 |  |
| 10 | log(1 + rate) | all cells | first-person singular (I-rate) | 358 | n/a | n/a | n/a | 0.336 | 0.652 |  |
| 10 | log(1 + rate) | all cells | first-person plural (we-rate) | 358 | n/a | n/a | n/a | 0.00303 | 0.0213 |  |
| 10 | log(1 + rate) | without possible-Hinglish cells | first-person singular (I-rate) | 358 | n/a | n/a | n/a | 0.337 | 0.652 |  |
| 10 | log(1 + rate) | without possible-Hinglish cells | first-person plural (we-rate) | 358 | n/a | n/a | n/a | 0.003 | 0.0213 |  |
| 10 | log(1 + rate) | without repost or embedded-post cells | first-person singular (I-rate) | 337 | n/a | n/a | n/a | 0.977 | 0.996 |  |
| 10 | log(1 + rate) | without repost or embedded-post cells | first-person plural (we-rate) | 337 | n/a | n/a | n/a | 0.000538 | 0.00792 |  |
| 10 | raw rate, top 1% leader means trimmed | all cells | first-person singular (I-rate) | 354 or more | n/a | n/a | n/a | 0.0744 | 0.289 |  |
| 10 | raw rate, top 1% leader means trimmed | all cells | first-person plural (we-rate) | 354 or more | n/a | n/a | n/a | 0.00395 | 0.0256 |  |
| 10 | raw rate, top 1% leader means trimmed | without possible-Hinglish cells | first-person singular (I-rate) | 354 or more | n/a | n/a | n/a | 0.0748 | 0.289 |  |
| 10 | raw rate, top 1% leader means trimmed | without possible-Hinglish cells | first-person plural (we-rate) | 354 or more | n/a | n/a | n/a | 0.00394 | 0.0256 |  |
| 10 | raw rate, top 1% leader means trimmed | without repost or embedded-post cells | first-person singular (I-rate) | 333 or more | n/a | n/a | n/a | 0.99 | 0.996 |  |
| 10 | raw rate, top 1% leader means trimmed | without repost or embedded-post cells | first-person plural (we-rate) | 333 or more | n/a | n/a | n/a | 9.76e-05 | 0.00522 |  |
| 15 | raw rate | all cells | first-person singular (I-rate) | 316 | n/a | n/a | n/a | 0.584 | 0.712 |  |
| 15 | raw rate | all cells | first-person plural (we-rate) | 316 | n/a | n/a | n/a | 0.00302 | 0.0213 |  |
| 15 | raw rate | without possible-Hinglish cells | first-person singular (I-rate) | 316 | n/a | n/a | n/a | 0.585 | 0.712 |  |
| 15 | raw rate | without possible-Hinglish cells | first-person plural (we-rate) | 316 | n/a | n/a | n/a | 0.00301 | 0.0213 |  |
| 15 | raw rate | without repost or embedded-post cells | first-person singular (I-rate) | 294 | n/a | n/a | n/a | 0.934 | 0.976 |  |
| 15 | raw rate | without repost or embedded-post cells | first-person plural (we-rate) | 294 | n/a | n/a | n/a | 0.000768 | 0.0104 |  |
| 15 | log(1 + rate) | all cells | first-person singular (I-rate) | 316 | n/a | n/a | n/a | 0.385 | 0.652 |  |
| 15 | log(1 + rate) | all cells | first-person plural (we-rate) | 316 | n/a | n/a | n/a | 0.00536 | 0.0321 |  |
| 15 | log(1 + rate) | without possible-Hinglish cells | first-person singular (I-rate) | 316 | n/a | n/a | n/a | 0.386 | 0.652 |  |
| 15 | log(1 + rate) | without possible-Hinglish cells | first-person plural (we-rate) | 316 | n/a | n/a | n/a | 0.00531 | 0.0321 |  |
| 15 | log(1 + rate) | without repost or embedded-post cells | first-person singular (I-rate) | 294 | n/a | n/a | n/a | 0.893 | 0.957 |  |
| 15 | log(1 + rate) | without repost or embedded-post cells | first-person plural (we-rate) | 294 | n/a | n/a | n/a | 0.00117 | 0.0127 |  |
| 15 | raw rate, top 1% leader means trimmed | all cells | first-person singular (I-rate) | 312 or more | n/a | n/a | n/a | 0.087 | 0.314 |  |
| 15 | raw rate, top 1% leader means trimmed | all cells | first-person plural (we-rate) | 312 or more | n/a | n/a | n/a | 0.000315 | 0.00522 |  |
| 15 | raw rate, top 1% leader means trimmed | without possible-Hinglish cells | first-person singular (I-rate) | 312 or more | n/a | n/a | n/a | 0.0874 | 0.314 |  |
| 15 | raw rate, top 1% leader means trimmed | without possible-Hinglish cells | first-person plural (we-rate) | 312 or more | n/a | n/a | n/a | 0.000315 | 0.00522 |  |
| 15 | raw rate, top 1% leader means trimmed | without repost or embedded-post cells | first-person singular (I-rate) | 290 or more | n/a | n/a | n/a | 0.989 | 0.996 |  |
| 15 | raw rate, top 1% leader means trimmed | without repost or embedded-post cells | first-person plural (we-rate) | 290 or more | n/a | n/a | n/a | 5.64e-05 | 0.00457 |  |
| 16 | raw rate | all cells | first-person singular (I-rate) | 305 | n/a | n/a | n/a | 0.401 | 0.652 |  |
| 16 | raw rate | all cells | first-person plural (we-rate) | 305 | n/a | n/a | n/a | 0.00184 | 0.0175 |  |
| 16 | raw rate | without possible-Hinglish cells | first-person singular (I-rate) | 305 | n/a | n/a | n/a | 0.402 | 0.652 |  |
| 16 | raw rate | without possible-Hinglish cells | first-person plural (we-rate) | 305 | n/a | n/a | n/a | 0.00183 | 0.0175 |  |
| 16 | raw rate | without repost or embedded-post cells | first-person singular (I-rate) | 284 | n/a | n/a | n/a | 0.99 | 0.996 |  |
| 16 | raw rate | without repost or embedded-post cells | first-person plural (we-rate) | 284 | n/a | n/a | n/a | 0.000223 | 0.00522 |  |
| 16 | log(1 + rate) | all cells | first-person singular (I-rate) | 305 | n/a | n/a | n/a | 0.305 | 0.652 |  |
| 16 | log(1 + rate) | all cells | first-person plural (we-rate) | 305 | n/a | n/a | n/a | 0.00272 | 0.0213 |  |
| 16 | log(1 + rate) | without possible-Hinglish cells | first-person singular (I-rate) | 305 | n/a | n/a | n/a | 0.305 | 0.652 |  |
| 16 | log(1 + rate) | without possible-Hinglish cells | first-person plural (we-rate) | 305 | n/a | n/a | n/a | 0.0027 | 0.0213 |  |
| 16 | log(1 + rate) | without repost or embedded-post cells | first-person singular (I-rate) | 284 | n/a | n/a | n/a | 0.951 | 0.988 |  |
| 16 | log(1 + rate) | without repost or embedded-post cells | first-person plural (we-rate) | 284 | n/a | n/a | n/a | 0.000269 | 0.00522 |  |
| 16 | raw rate, top 1% leader means trimmed | all cells | first-person singular (I-rate) | 301 or more | n/a | n/a | n/a | 0.036 | 0.201 |  |
| 16 | raw rate, top 1% leader means trimmed | all cells | first-person plural (we-rate) | 301 or more | n/a | n/a | n/a | 0.000168 | 0.00522 |  |
| 16 | raw rate, top 1% leader means trimmed | without possible-Hinglish cells | first-person singular (I-rate) | 301 or more | n/a | n/a | n/a | 0.0361 | 0.201 |  |
| 16 | raw rate, top 1% leader means trimmed | without possible-Hinglish cells | first-person plural (we-rate) | 301 or more | n/a | n/a | n/a | 0.000168 | 0.00522 |  |
| 16 | raw rate, top 1% leader means trimmed | without repost or embedded-post cells | first-person singular (I-rate) | 280 or more | n/a | n/a | n/a | 0.997 | 0.997 |  |
| 16 | raw rate, top 1% leader means trimmed | without repost or embedded-post cells | first-person plural (we-rate) | 280 or more | n/a | n/a | n/a | 1.2e-05 | 0.00195 |  |

## Firm-size joint test

| post minimum | outcome scale | cells | measure | leaders fitted | contrast | estimate | interval | raw p | BH-adjusted p | note |
|---|---|---|---|---|---|---|---|---|---|---|
| 10 | raw rate | all cells | first-person singular (I-rate) | 358 | n/a | n/a | n/a | 0.0761 | 0.289 |  |
| 10 | raw rate | all cells | first-person plural (we-rate) | 358 | n/a | n/a | n/a | 0.427 | 0.652 |  |
| 10 | raw rate | without possible-Hinglish cells | first-person singular (I-rate) | 358 | n/a | n/a | n/a | 0.0768 | 0.289 |  |
| 10 | raw rate | without possible-Hinglish cells | first-person plural (we-rate) | 358 | n/a | n/a | n/a | 0.431 | 0.652 |  |
| 10 | raw rate | without repost or embedded-post cells | first-person singular (I-rate) | 337 | n/a | n/a | n/a | 0.233 | 0.652 |  |
| 10 | raw rate | without repost or embedded-post cells | first-person plural (we-rate) | 337 | n/a | n/a | n/a | 0.451 | 0.676 |  |
| 10 | log(1 + rate) | all cells | first-person singular (I-rate) | 358 | n/a | n/a | n/a | 0.0551 | 0.258 |  |
| 10 | log(1 + rate) | all cells | first-person plural (we-rate) | 358 | n/a | n/a | n/a | 0.361 | 0.652 |  |
| 10 | log(1 + rate) | without possible-Hinglish cells | first-person singular (I-rate) | 358 | n/a | n/a | n/a | 0.0558 | 0.258 |  |
| 10 | log(1 + rate) | without possible-Hinglish cells | first-person plural (we-rate) | 358 | n/a | n/a | n/a | 0.368 | 0.652 |  |
| 10 | log(1 + rate) | without repost or embedded-post cells | first-person singular (I-rate) | 337 | n/a | n/a | n/a | 0.21 | 0.63 |  |
| 10 | log(1 + rate) | without repost or embedded-post cells | first-person plural (we-rate) | 337 | n/a | n/a | n/a | 0.424 | 0.652 |  |
| 10 | raw rate, top 1% leader means trimmed | all cells | first-person singular (I-rate) | 354 or more | n/a | n/a | n/a | 0.413 | 0.652 |  |
| 10 | raw rate, top 1% leader means trimmed | all cells | first-person plural (we-rate) | 354 or more | n/a | n/a | n/a | 0.527 | 0.712 |  |
| 10 | raw rate, top 1% leader means trimmed | without possible-Hinglish cells | first-person singular (I-rate) | 354 or more | n/a | n/a | n/a | 0.417 | 0.652 |  |
| 10 | raw rate, top 1% leader means trimmed | without possible-Hinglish cells | first-person plural (we-rate) | 354 or more | n/a | n/a | n/a | 0.533 | 0.712 |  |
| 10 | raw rate, top 1% leader means trimmed | without repost or embedded-post cells | first-person singular (I-rate) | 333 or more | n/a | n/a | n/a | 0.814 | 0.891 |  |
| 10 | raw rate, top 1% leader means trimmed | without repost or embedded-post cells | first-person plural (we-rate) | 333 or more | n/a | n/a | n/a | 0.334 | 0.652 |  |
| 15 | raw rate | all cells | first-person singular (I-rate) | 316 | n/a | n/a | n/a | 0.0467 | 0.232 |  |
| 15 | raw rate | all cells | first-person plural (we-rate) | 316 | n/a | n/a | n/a | 0.48 | 0.7 |  |
| 15 | raw rate | without possible-Hinglish cells | first-person singular (I-rate) | 316 | n/a | n/a | n/a | 0.0473 | 0.232 |  |
| 15 | raw rate | without possible-Hinglish cells | first-person plural (we-rate) | 316 | n/a | n/a | n/a | 0.487 | 0.7 |  |
| 15 | raw rate | without repost or embedded-post cells | first-person singular (I-rate) | 294 | n/a | n/a | n/a | 0.269 | 0.652 |  |
| 15 | raw rate | without repost or embedded-post cells | first-person plural (we-rate) | 294 | n/a | n/a | n/a | 0.57 | 0.712 |  |
| 15 | log(1 + rate) | all cells | first-person singular (I-rate) | 316 | n/a | n/a | n/a | 0.0403 | 0.214 |  |
| 15 | log(1 + rate) | all cells | first-person plural (we-rate) | 316 | n/a | n/a | n/a | 0.387 | 0.652 |  |
| 15 | log(1 + rate) | without possible-Hinglish cells | first-person singular (I-rate) | 316 | n/a | n/a | n/a | 0.0409 | 0.214 |  |
| 15 | log(1 + rate) | without possible-Hinglish cells | first-person plural (we-rate) | 316 | n/a | n/a | n/a | 0.398 | 0.652 |  |
| 15 | log(1 + rate) | without repost or embedded-post cells | first-person singular (I-rate) | 294 | n/a | n/a | n/a | 0.169 | 0.549 |  |
| 15 | log(1 + rate) | without repost or embedded-post cells | first-person plural (we-rate) | 294 | n/a | n/a | n/a | 0.478 | 0.7 |  |
| 15 | raw rate, top 1% leader means trimmed | all cells | first-person singular (I-rate) | 312 or more | n/a | n/a | n/a | 0.296 | 0.652 |  |
| 15 | raw rate, top 1% leader means trimmed | all cells | first-person plural (we-rate) | 312 or more | n/a | n/a | n/a | 0.263 | 0.652 |  |
| 15 | raw rate, top 1% leader means trimmed | without possible-Hinglish cells | first-person singular (I-rate) | 312 or more | n/a | n/a | n/a | 0.3 | 0.652 |  |
| 15 | raw rate, top 1% leader means trimmed | without possible-Hinglish cells | first-person plural (we-rate) | 312 or more | n/a | n/a | n/a | 0.267 | 0.652 |  |
| 15 | raw rate, top 1% leader means trimmed | without repost or embedded-post cells | first-person singular (I-rate) | 290 or more | n/a | n/a | n/a | 0.557 | 0.712 |  |
| 15 | raw rate, top 1% leader means trimmed | without repost or embedded-post cells | first-person plural (we-rate) | 290 or more | n/a | n/a | n/a | 0.318 | 0.652 |  |
| 16 | raw rate | all cells | first-person singular (I-rate) | 305 | n/a | n/a | n/a | 0.0977 | 0.342 |  |
| 16 | raw rate | all cells | first-person plural (we-rate) | 305 | n/a | n/a | n/a | 0.488 | 0.7 |  |
| 16 | raw rate | without possible-Hinglish cells | first-person singular (I-rate) | 305 | n/a | n/a | n/a | 0.0991 | 0.342 |  |
| 16 | raw rate | without possible-Hinglish cells | first-person plural (we-rate) | 305 | n/a | n/a | n/a | 0.495 | 0.702 |  |
| 16 | raw rate | without repost or embedded-post cells | first-person singular (I-rate) | 284 | n/a | n/a | n/a | 0.19 | 0.602 |  |
| 16 | raw rate | without repost or embedded-post cells | first-person plural (we-rate) | 284 | n/a | n/a | n/a | 0.488 | 0.7 |  |
| 16 | log(1 + rate) | all cells | first-person singular (I-rate) | 305 | n/a | n/a | n/a | 0.0734 | 0.289 |  |
| 16 | log(1 + rate) | all cells | first-person plural (we-rate) | 305 | n/a | n/a | n/a | 0.415 | 0.652 |  |
| 16 | log(1 + rate) | without possible-Hinglish cells | first-person singular (I-rate) | 305 | n/a | n/a | n/a | 0.0745 | 0.289 |  |
| 16 | log(1 + rate) | without possible-Hinglish cells | first-person plural (we-rate) | 305 | n/a | n/a | n/a | 0.426 | 0.652 |  |
| 16 | log(1 + rate) | without repost or embedded-post cells | first-person singular (I-rate) | 284 | n/a | n/a | n/a | 0.131 | 0.443 |  |
| 16 | log(1 + rate) | without repost or embedded-post cells | first-person plural (we-rate) | 284 | n/a | n/a | n/a | 0.409 | 0.652 |  |
| 16 | raw rate, top 1% leader means trimmed | all cells | first-person singular (I-rate) | 301 or more | n/a | n/a | n/a | 0.0716 | 0.289 |  |
| 16 | raw rate, top 1% leader means trimmed | all cells | first-person plural (we-rate) | 301 or more | n/a | n/a | n/a | 0.259 | 0.652 |  |
| 16 | raw rate, top 1% leader means trimmed | without possible-Hinglish cells | first-person singular (I-rate) | 301 or more | n/a | n/a | n/a | 0.0732 | 0.289 |  |
| 16 | raw rate, top 1% leader means trimmed | without possible-Hinglish cells | first-person plural (we-rate) | 301 or more | n/a | n/a | n/a | 0.263 | 0.652 |  |
| 16 | raw rate, top 1% leader means trimmed | without repost or embedded-post cells | first-person singular (I-rate) | 280 or more | n/a | n/a | n/a | 0.4 | 0.652 |  |
| 16 | raw rate, top 1% leader means trimmed | without repost or embedded-post cells | first-person plural (we-rate) | 280 or more | n/a | n/a | n/a | 0.257 | 0.652 |  |

## Direction and raw-p count

- first-person singular (I-rate): 26 of 27 fitted variants have the same direction as the main variant; 0 of 27 raw p below 0.05.
- first-person plural (we-rate): 27 of 27 fitted variants have the same direction as the main variant; 0 of 27 raw p below 0.05.
