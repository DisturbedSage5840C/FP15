# Harmonise summary

Counts only: no names, no file names, no sheet indexes and no post text. The per-sheet log is a git-ignored file.

## Headline figures against the owner's figures

| Measure | Owner's figure | Raw post_text workbooks | Difference | Cleaned workbooks | All |
|---|---|---|---|---|---|
| Non-empty post_text rows | 32,448 | 32,656 | +208 | 31,385 | 64,041 |
| Sheets with post text | 705 | 550 | -155 | 547 | 1,097 |
| Unique posts after dedupe | 22,083 | 26,945 | +4,862 | 31,009 | 57,954 |
| Leaders | 544 | 563 | +19 | 564 | 564 |

The owner's leader figure of 544 is superseded, see Findings in docs/decisions.md (the owner's corrected count is 567 and is not comparable with ours until posts are segmented).

The wordcount workbooks carry `cleaned_post_text`, a cleaned copy of posts that also sit in the raw `post_text` workbooks. The owner's figures are compared with the raw post_text workbooks only. Raw and cleaned rows are kept apart by `text_kind` and are not deduplicated against each other, so the All column counts the same post twice.

Rows lost at the leader step: 268. Rows collapsed as certain duplicates: 5,819. Differences are reported, not forced: they come from sheets skipped with a reason (below), rows dropped on the combined sheet for lack of a leader, and the dedupe rule.

Roster loaded once from the roster workbook: 653 people.

## Sheets

| Item | Count |
|---|---|
| Sheets loaded | 1,285 |
| Sheets used | 1,097 |
| Sheets skipped | 188 |
| Combined sheets (first post sheet of a workbook) | 23 |
| Sheets mapped by header | 1,094 |
| Sheets mapped by header+positional | 1 |
| Sheets mapped by positional | 2 |
| Sheets with cleaned text | 547 |
| Sheets with raw text | 550 |

## Skipped sheets and why

- **header only, no data rows**: 160 sheets in 17 workbooks
- **no post-text column**: 1 sheets in 1 workbooks
- **roster sheet (the roster is loaded once from the roster workbook)**: 7 sheets in 7 workbooks
- **summary sheet (no post text)**: 6 sheets in 6 workbooks
- **word-frequency sheet (no post text)**: 14 sheets in 7 workbooks

## Leader assignment

Rule (ASSUMPTION in docs/decisions.md): on the combined sheet rows with no leader are dropped; on every other sheet a blank leader cell takes the sheet name; nothing is forward-filled. Conflicts are flagged `sheet_name_conflict`, never auto-resolved. Excel truncates sheet names at 31 characters, so some conflicts may be truncation, not a real disagreement.

| Item | Rows |
|---|---|
| Rows dropped (combined sheet, no leader) | 268 |
| Rows with a leader filled from the sheet name | 34,956 |
|   of which the sheet name disagrees with the other leader cells | 206 |

## Spot check: is the sheet name the leader? (20 random sheets)

Agreement in the sample: 332/332 rows (100.0%). Agreement on all 940 comparable sheets: 11,050/11,244 rows (98.3%). A human still has to judge whether this supports the assumption.

## Date and tenure columns in the unique posts

`age_text` is a relative age ('3mo'), not a date. Absolute dates stay missing; none are inferred.

| Column | Filled | Share |
|---|---|---|
| age_text | 29,301 | 50.6% |
| post_date | 25 | 0.0% |
| post_date holds post text | 14 | 0.0% |
| post_date_text | 12,664 | 21.9% |
| role_start_year | 14 | 0.0% |

## Sheets the profiler flagged as odd

25 sheets in 20 workbooks
