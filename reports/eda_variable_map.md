# EDA: variable map and fill rates

Counts only: no names, post text, links, emails, company names or leader ids appear here. A count below 5 shows as "<5" instead of its number, and a share is hidden when either the filled or the missing side is below that minimum. Every statement is about the image projected in public posts, never about personality. Nothing is filled in or guessed: missing stays missing. No gate is signed off by this report. No scraping and no network were used, and scraping_approved stays false.

## Variable map

| Variable | Source | Study role | Filled n of N | Share missing | Usable? |
|---|---|---|---|---|---|
| ceo_type | post workbooks | X leader block | 518 of 563 | 8.0% | yes |
| current_title | post workbooks | X leader block | 517 of 563 | 8.2% | yes |
| role_start_year | post workbooks | X leader block | <5 of 563 | <5 | yes |
| post_date | post workbooks | control | 6 of 563 | 98.9% | yes |
| post_date_text | post workbooks | control | 458 of 563 | 18.7% | yes |
| gender (as coded) | Company_Data | X leader block | 429 of 545 | 21.3% | yes |
| gender coded 1 (man) | Company_Data | X leader block | 389 of 545 | 28.6% | yes |
| gender coded 0 (woman) | Company_Data | X leader block | 40 of 545 | 92.7% | yes |
| gender coded as another value | Company_Data | X leader block | <5 of 545 | <5 | no |
| gender with no value | Company_Data | X leader block | 116 of 545 | 78.7% | yes |
| sector | Company_Data | X firm block | 527 of 545 | 3.3% | yes |
| firm size (employees) | Company_Data | X firm block | 494 of 545 | 9.4% | yes |
| firm age (founded year) | Company_Data | X firm block | 540 of 545 | 0.9% | yes |
| LinkedIn followers | Company_Data | control | 377 of 545 | 30.8% | yes |
| revenue 2021 | Company_Data | X firm block | 436 of 545 | 20.0% | yes |
| revenue 2022 | Company_Data | X firm block | 432 of 545 | 20.7% | yes |
| revenue 2023 | Company_Data | X firm block | 435 of 545 | 20.2% | yes |
| revenue 2024 | Company_Data | X firm block | 387 of 545 | 29.0% | yes |
| profit 2021 | Company_Data | X firm block | 431 of 545 | 20.9% | yes |
| profit 2022 | Company_Data | X firm block | 429 of 545 | 21.3% | yes |
| profit 2023 | Company_Data | X firm block | 430 of 545 | 21.1% | yes |
| profit 2024 | Company_Data | X firm block | 381 of 545 | 30.1% | yes |
| cells with a parsed relative age | derived | control | 25,157 of 26,945 | 6.6% | yes |
| cells ending in a number (unverified) | derived | outcome | 7,733 of 26,945 | 71.3% | no |
| IPO columns | Company_Data | not usable | 545 of 545 | <5 | no |
| unnamed column Q | Company_Data | not usable | 545 of 545 | <5 | no |
| unnamed column V | Company_Data | not usable | 453 of 545 | 16.9% | no |
| unnamed column Z | Company_Data | not usable | 481 of 545 | 11.7% | no |
| email and phone columns | Company_Data | not usable | n/a | n/a | no |

## Reading the table

- N is the leaders with at least 1 raw post cell (post-workbook variables), the leaders with a clear Company_Data match (company variables), or the cells (derived variables).
- "." and "-" count as blank. A number that cannot be read (for example "500+") counts as missing.
- Gender is shown as coded in Company_Data, with labels from configs/gender_coding.yaml (confirmed 2026-11-23 by the project team from the data owner and mentors: 1 = man, 0 = woman). Gender is never inferred from names.
- Study role is a proposal for the humans to confirm. Usable yes means at least one value is filled; it is not a judgment that the variable is adequate for a model.
- Cells ending in a number are unverified: they may be reaction counts, years or ages.

## Why a variable is not usable

- gender coded as another value: No cell is filled.
- cells ending in a number (unverified): Unverified: what these trailing numbers are (reaction counts, years, ages) has not been hand-checked.
- IPO columns: Every firm in Company_Data is listed, so listed versus unlisted cannot be tested.
- unnamed column Q: The column has no header and its meaning is unknown.
- unnamed column V: The column has no header and its meaning is unknown.
- unnamed column Z: The column has no header and its meaning is unknown.
- email and phone columns: Email and phone columns are dropped at load, before anything is written to disk, so they have no fill rate.

## Checks

Numbers quoted in the write-up (configs/writeup_numbers.yaml) against the data.

No difference from the write-up numbers (12 compared).
