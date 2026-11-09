# ID matching

Sorted-token name keys, matched across four lists. Loose = all tokens of the shorter name sit inside the longer one (at least 2 tokens), with one unclaimed candidate. Company agreement is shown for a human and never changes a match. Row-level tables are in data/interim (git-ignored); this file holds counts, file paths and sheet indexes only.

## Sources

| source | file | entities | distinct keys | keys held by 2+ entities |
|---|---|---|---|---|
| sheets | harmonised posts table (git-ignored, data/interim) | 564 | 564 | 0 |
| roster | roster table (git-ignored, data/interim; the roster workbook is loaded once) | 653 | 652 | 1 |
| summaries | the summary sheet of every wordcount workbook (counted below) | 541 | 532 | 9 |
| company | company table (git-ignored, data/interim; contact columns dropped at load) | 852 | 852 | 0 |

## Summary sheets read

7 summary sheets read. Workbook names and sheet indexes are not listed. Total name cells filled: 541.

## Pair outcomes

| pair (a -> b) | a entities | b entities | exact | loose | ambiguous | none | b never named | exact: company agrees / differs / unknown |
|---|---|---|---|---|---|---|---|---|
| sheets -> company | 564 | 852 | 554 | 0 | 2 | 8 | 298 | 515 / 1 / 38 |
| sheets -> roster | 564 | 653 | 399 | 1 | 1 | 163 | 253 | 370 / 0 / 29 |
| sheets -> summaries | 564 | 541 | 523 | 0 | 11 | 30 | 0 | 482 / 0 / 41 |
| roster -> summaries | 653 | 541 | 378 | 1 | 9 | 265 | 152 | 376 / 1 / 1 |
| roster -> company | 653 | 852 | 651 | 0 | 2 | 0 | 200 | 650 / 1 / 0 |
| summaries -> company | 541 | 852 | 519 | 0 | 18 | 4 | 324 | 514 / 2 / 3 |

Outcomes are counted per entity of side a. Ambiguous names are listed in data/interim/id_ambiguous.csv and are not resolved.

## Distinct-key overlap

| pair | in both | only in first | only in second |
|---|---|---|---|
| sheets / company | 554 | 10 | 298 |
| sheets / roster | 399 | 165 | 253 |
| sheets / summaries | 532 | 32 | 0 |
| roster / summaries | 383 | 269 | 149 |
| roster / company | 652 | 0 | 200 |
| summaries / company | 528 | 4 | 324 |

## Owner figures versus ours

| measure | owner | ours | difference |
|---|---|---|---|
| sheet leaders (distinct keys) | 544 | 564 | +20 |
| sheets -> company exact | 541 | 554 | +13 |
| sheets -> company ambiguous | 5 | 2 | -3 |
| sheets -> company exact + loose | 543 | 554 | +11 |
| roster and summaries both | 383 | 383 | +0 |
| roster only | 265 | 269 | +4 |
| summaries only | 148 | 149 | +1 |
| Company_Data rows | 852 | 852 | +0 |
| summary names (distinct keys) | 532 | 532 | +0 |

The owner's leader figure of 544 is superseded, see Findings in docs/decisions.md (the owner's corrected count is 567 and is not comparable with ours until posts are segmented).

A non-zero difference is a finding to explain with the owner, not something fixed by this step.

## leader_id proposal

Keys: 862. Clear (proposed id): 852. Ambiguous (no id, left for a human): 10.

| clear keys present in | keys | share of clear |
|---|---|---|
| 1 source(s) | 51 | 6.0% |
| 2 source(s) | 266 | 31.2% |
| 3 source(s) | 157 | 18.4% |
| 4 source(s) | 378 | 44.4% |
