# Harmonise summary

Counts, file paths and sheet indexes only; no names and no post text.

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

Roster loaded once from seventh_100_leaders/All_500.xlsx: 653 people.

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

## Skipped sheets and why (workbook: sheet index)

**header only, no data rows** (160 sheets)

- Linkdln_posts_data/Fifth_100_Leaders/500_file1.xlsx: 1, 2, 3, 9, 12, 19, 20, 22, 32, 33, 35, 36, 37, 39, 44, 46
- Linkdln_posts_data/Fifth_100_Leaders/500_file2.xlsx: 1, 7, 9, 21, 22, 31, 36, 46, 49, 50
- Linkdln_posts_data/First_100_leaders/First_file1_updated.xlsx: 4, 6, 13, 22, 23, 27, 29, 30, 34, 37
- Linkdln_posts_data/First_100_leaders/First_file2_updated.xlsx: 4, 17, 19, 20, 22, 28, 34
- Linkdln_posts_data/First_100_leaders/First_file3_updated.xlsx: 5, 9, 16, 17
- Linkdln_posts_data/Fourth_100_leaders/400_file1_updated_final.xlsx: 10, 45, 49, 50
- Linkdln_posts_data/Fourth_100_leaders/400_file2_updated_Final.xlsx: 1, 9, 10, 16, 21, 34, 36, 37, 38, 45
- Linkdln_posts_data/Fourth_100_leaders/wordcount_400.xlsx: 44
- Linkdln_posts_data/Second_200_leaders/Second_file1_updated.xlsx: 7, 8, 12, 21, 26, 33, 34, 40, 41, 45, 48, 53, 55
- Linkdln_posts_data/Second_200_leaders/Second_file2_updated.xlsx: 4, 6, 16, 18, 30, 31, 32, 34, 35, 36, 37
- Linkdln_posts_data/Sixth_100/600_file1.xlsx: 4, 6, 12, 18, 22, 24, 30, 36, 45, 48
- Linkdln_posts_data/Sixth_100/600_file2.xlsx: 2, 10, 13, 16, 18, 22, 38, 44, 45
- Linkdln_posts_data/Third_100_leaders/300_file1_updated_final.xlsx: 1, 3, 5, 8, 20, 22, 26, 28, 35, 41, 44, 50, 51, 52, 56, 58, 59
- Linkdln_posts_data/Third_100_leaders/300_file2_updated_final.xlsx: 5, 7, 9, 13, 14, 20, 24
- Linkdln_posts_data/Third_100_leaders/300_file3_updated_final.xlsx: 10, 12
- Linkdln_posts_data/seventh_100_leaders/700_file1.xlsx: 5, 7, 8, 9, 12, 14, 17, 18, 26, 28, 32, 34, 40, 42, 44
- Linkdln_posts_data/seventh_100_leaders/700_file2.xlsx: 1, 3, 6, 7, 8, 14, 19, 21, 25, 29, 31, 32, 34, 44

**no post-text column** (1 sheets)

- Linkdln_posts_data/Fifth_100_Leaders/wordcount_500.xlsx: 0

**roster sheet (the roster is loaded once from seventh_100_leaders/All_500.xlsx)** (7 sheets)

- Linkdln_posts_data/Fifth_100_Leaders/All_500.xlsx: 0
- Linkdln_posts_data/First_100_leaders/First_100 posts.xlsx: 0
- Linkdln_posts_data/Fourth_100_leaders/All_500.xlsx: 0
- Linkdln_posts_data/Second_200_leaders/Second_100 posts.xlsx: 0
- Linkdln_posts_data/Sixth_100/All_500.xlsx: 0
- Linkdln_posts_data/Third_100_leaders/All_500.xlsx: 0
- Linkdln_posts_data/seventh_100_leaders/All_500.xlsx: 0

**summary sheet (no post text)** (6 sheets)

- Linkdln_posts_data/First_100_leaders/wordcount_100.xlsx: 0
- Linkdln_posts_data/Fourth_100_leaders/wordcount_400.xlsx: 0
- Linkdln_posts_data/Second_200_leaders/wordcount_200.xlsx: 0
- Linkdln_posts_data/Sixth_100/wordcount_600.xlsx: 0
- Linkdln_posts_data/Third_100_leaders/wordcount_300.xlsx: 0
- Linkdln_posts_data/seventh_100_leaders/wordcount_700.xlsx: 0

**word-frequency sheet (no post text)** (14 sheets)

- Linkdln_posts_data/Fifth_100_Leaders/wordcount_500.xlsx: 1, 2
- Linkdln_posts_data/First_100_leaders/wordcount_100.xlsx: 1, 2
- Linkdln_posts_data/Fourth_100_leaders/wordcount_400.xlsx: 1, 2
- Linkdln_posts_data/Second_200_leaders/wordcount_200.xlsx: 1, 2
- Linkdln_posts_data/Sixth_100/wordcount_600.xlsx: 1, 2
- Linkdln_posts_data/Third_100_leaders/wordcount_300.xlsx: 1, 2
- Linkdln_posts_data/seventh_100_leaders/wordcount_700.xlsx: 1, 2


## Leader assignment

Rule (ASSUMPTION in docs/decisions.md): on the combined sheet rows with no leader are dropped; on every other sheet a blank leader cell takes the sheet name; nothing is forward-filled. Conflicts are flagged `sheet_name_conflict`, never auto-resolved. Excel truncates sheet names at 31 characters, so some conflicts may be truncation, not a real disagreement.

| Item | Rows |
|---|---|
| Rows dropped (combined sheet, no leader) | 268 |
| Rows with a leader filled from the sheet name | 34,956 |
|   of which the sheet name disagrees with the other leader cells | 206 |

## Spot check: is the sheet name the leader? (20 random sheets)

- Linkdln_posts_data/Fifth_100_Leaders/500_file1.xlsx: 18 (23/23 leader cells agree with the sheet name)
- Linkdln_posts_data/Fifth_100_Leaders/500_file1.xlsx: 27 (1/1 leader cells agree with the sheet name)
- Linkdln_posts_data/Fifth_100_Leaders/500_file2.xlsx: 11 (3/3 leader cells agree with the sheet name)
- Linkdln_posts_data/Fifth_100_Leaders/500_file2.xlsx: 35 (4/4 leader cells agree with the sheet name)
- Linkdln_posts_data/Fifth_100_Leaders/wordcount_500.xlsx: 60 (5/5 leader cells agree with the sheet name)
- Linkdln_posts_data/First_100_leaders/First_file1_updated.xlsx: 24 (53/53 leader cells agree with the sheet name)
- Linkdln_posts_data/First_100_leaders/First_file2_updated.xlsx: 5 (26/26 leader cells agree with the sheet name)
- Linkdln_posts_data/First_100_leaders/wordcount_100.xlsx: 21 (4/4 leader cells agree with the sheet name)
- Linkdln_posts_data/First_100_leaders/wordcount_100.xlsx: 58 (3/3 leader cells agree with the sheet name)
- Linkdln_posts_data/First_100_leaders/wordcount_100.xlsx: 59 (1/1 leader cells agree with the sheet name)
- Linkdln_posts_data/Fourth_100_leaders/wordcount_400.xlsx: 10 (46/46 leader cells agree with the sheet name)
- Linkdln_posts_data/Fourth_100_leaders/wordcount_400.xlsx: 41 (15/15 leader cells agree with the sheet name)
- Linkdln_posts_data/Second_200_leaders/wordcount_200.xlsx: 55 (51/51 leader cells agree with the sheet name)
- Linkdln_posts_data/Sixth_100/wordcount_600.xlsx: 83 (1/1 leader cells agree with the sheet name)
- Linkdln_posts_data/Third_100_leaders/300_file1_updated_final.xlsx: 17 (40/40 leader cells agree with the sheet name)
- Linkdln_posts_data/Third_100_leaders/300_file2_updated_final.xlsx: 25 (10/10 leader cells agree with the sheet name)
- Linkdln_posts_data/Third_100_leaders/wordcount_300.xlsx: 71 (39/39 leader cells agree with the sheet name)
- Linkdln_posts_data/seventh_100_leaders/700_file2.xlsx: 36 (1/1 leader cells agree with the sheet name)
- Linkdln_posts_data/seventh_100_leaders/wordcount_700.xlsx: 21 (3/3 leader cells agree with the sheet name)
- Linkdln_posts_data/seventh_100_leaders/wordcount_700.xlsx: 65 (3/3 leader cells agree with the sheet name)

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

## Sheets the profiler flagged as odd (workbook: sheet index)

- Linkdln_posts_data/Fifth_100_Leaders/All_500.xlsx: 0
- Linkdln_posts_data/Fifth_100_Leaders/wordcount_500.xlsx: 0
- Linkdln_posts_data/First_100_leaders/First_file1_updated.xlsx: 0, 1
- Linkdln_posts_data/First_100_leaders/First_file2_updated.xlsx: 10, 25
- Linkdln_posts_data/First_100_leaders/First_file3_updated.xlsx: 4
- Linkdln_posts_data/First_100_leaders/wordcount_100.xlsx: 3, 4, 51
- Linkdln_posts_data/Fourth_100_leaders/400_file1_updated_final.xlsx: 11
- Linkdln_posts_data/Fourth_100_leaders/All_500.xlsx: 0
- Linkdln_posts_data/Fourth_100_leaders/wordcount_400.xlsx: 13
- Linkdln_posts_data/Second_200_leaders/Second_100 posts.xlsx: 0
- Linkdln_posts_data/Second_200_leaders/Second_file1_updated.xlsx: 50
- Linkdln_posts_data/Sixth_100/600_file1.xlsx: 38
- Linkdln_posts_data/Sixth_100/600_file2.xlsx: 11
- Linkdln_posts_data/Sixth_100/All_500.xlsx: 0
- Linkdln_posts_data/Sixth_100/wordcount_600.xlsx: 33, 53
- Linkdln_posts_data/Third_100_leaders/300_file1_updated_final.xlsx: 1
- Linkdln_posts_data/Third_100_leaders/300_file2_updated_final.xlsx: 17
- Linkdln_posts_data/Third_100_leaders/All_500.xlsx: 0
- Linkdln_posts_data/Third_100_leaders/wordcount_300.xlsx: 59
- Linkdln_posts_data/seventh_100_leaders/All_500.xlsx: 0
