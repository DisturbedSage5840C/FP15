# Data inventory

Counts and header labels only: no sheet names, file names, sheet indexes, cell values or post text appear here. Read straight from data/raw after the manifest check; nothing is harmonised, filled in or guessed.

## Raw files

| File | Bytes | SHA-256 (from MANIFEST.sha256) |
|---|---|---|
| raw-file-01 | 1,024,931 | adfdacb35abde4398d66e2744f53fb35c839b38b09a2aa26f20647a0c43d524f |
| raw-file-02 | 50,365,360 | 3cbf832862dd85f19a9f8728a60ea31b4e9c97c55c8321de5675afeab758c6fb |

## Zip members

35 members (4 pdf, 1 script, 30 workbook). Member names are not listed.

## Workbooks

| Workbook | Sheets | Data rows |
|---|---|---|
| workbook-01 | 51 | 1,856 |
| workbook-02 | 51 | 1,643 |
| workbook-03 | 1 | 653 |
| workbook-04 | 79 | 54,506 |
| workbook-05 | 1 | 100 |
| workbook-06 | 39 | 1,393 |
| workbook-07 | 39 | 1,173 |
| workbook-08 | 22 | 815 |
| workbook-09 | 80 | 52,077 |
| workbook-10 | 51 | 3,047 |
| workbook-11 | 51 | 2,832 |
| workbook-12 | 1 | 653 |
| workbook-13 | 91 | 92,113 |
| workbook-14 | 1 | 99 |
| workbook-15 | 62 | 2,879 |
| workbook-16 | 39 | 1,836 |
| workbook-17 | 79 | 69,319 |
| workbook-18 | 50 | 3,067 |
| workbook-19 | 51 | 3,062 |
| workbook-20 | 1 | 653 |
| workbook-21 | 86 | 105,725 |
| workbook-22 | 61 | 3,213 |
| workbook-23 | 27 | 1,556 |
| workbook-24 | 14 | 784 |
| workbook-25 | 1 | 653 |
| workbook-26 | 79 | 82,125 |
| workbook-27 | 50 | 1,821 |
| workbook-28 | 51 | 1,766 |
| workbook-29 | 1 | 653 |
| workbook-30 | 75 | 75,686 |

## Header layouts

| Layout | Sheets | Data rows | Header cells |
|---|---|---|---|
| leader_posts_14 | 701 | 32,266 | 14 |
| wordcount_leader_12 | 541 | 30,994 | 12 |
| off-layout | 14 | 845 | 5, 9, 11, 13, 14, 18, 16382 |
| word_frequency_9 | 14 | 499,625 | 9 |
| roster_5 | 7 | 3,464 | 5 |
| summary_8 | 6 | 465 | 8 |
| no-header | 2 | 99 | - |

## Odd sheets

25 of 1,285 sheets have at least one oddity. docs/FIRST_PROMPT.md names 4 odd sheets; the tables below count every sheet with any oddity. Which four were meant is for the project owner to pick out; the per-sheet list is in the git-ignored data/interim files.

| Kind of oddity | Sheets |
|---|---|
| off-layout | 14 |
| known layout, with stray cells or blank rows | 9 |
| no-header | 2 |

| Reason | Sheets |
|---|---|
| off-layout (nearest: leader_posts_14; missing: selected_order, excel_data_row_number, excel_file_row_number, leader_name, company_name, current_title, role_start_year, ceo_type, link_to_post_url, linkedin_profile_url; extra: link_to_the_post_(if_available)) | 3 |
| off-layout (nearest: wordcount_leader_12; missing: leader_name, company_name, current_title, role_start_year, ceo_type, link_to_post_url, linkedin_profile_url; extra: link_to_the_post_(if_available)) | 3 |
| 2 non-empty cell(s) beyond the header | 3 |
| off-layout (nearest: leader_posts_14; missing: post_date_text; extra: -) | 2 |
| no header row (first row is data) | 2 |
| off-layout (nearest: wordcount_leader_12; missing: post_date_text; extra: -) | 2 |
| 6 non-empty cell(s) beyond the header | 2 |
| 5 non-empty cell(s) beyond the header | 1 |
| off-layout (nearest: summary_8; missing: -; extra: scraped_date) | 1 |
| off-layout (nearest: leader_posts_14; missing: post_text; extra: -) | 1 |
| 1 non-empty cell(s) beyond the header | 1 |
| 5 blank column(s) beyond the header | 1 |
| 16370 non-empty cell(s) beyond the header | 1 |
| off-layout (nearest: wordcount_leader_12; missing: -; extra: 6 unnamed column(s)) | 1 |
| off-layout (nearest: wordcount_leader_12; missing: -; extra: 16370 unnamed column(s)) | 1 |
| 46 blank row(s) above the header | 1 |

## Study variables

### leader_posts_14

| Variable | Raw header | Sheets | Non-empty / rows |
|---|---|---|---|
| leader_name | leader_name | 701 | 14,474 / 32,266 |
| company_name | company_name | 701 | 14,474 / 32,266 |
| current_title | current_title | 701 | 14,474 / 32,266 |
| role_start_year | role_start_year | 701 | 1 / 32,266 |
| ceo_type | ceo_type | 701 | 14,474 / 32,266 |
| platform | platform | 701 | 14,474 / 32,266 |
| post_date | post_date | 701 | 9 / 32,266 |
| post_date_text | post_date_text | 701 | 8,031 / 32,266 |

### off-layout

| Variable | Raw header | Sheets | Non-empty / rows |
|---|---|---|---|
| leader_name | leader_name | 7 | 82 / 325 |
| company_name | company_name | 7 | 82 / 325 |
| current_title | Current title | 1 | 76 / 76 |
| current_title | current_title | 7 | 70 / 325 |
| role_start_year | role_start_year | 7 | 13 / 325 |
| ceo_type | ceo_type | 7 | 82 / 325 |
| platform | Platform | 6 | 96 / 444 |
| platform | platform | 7 | 70 / 325 |
| post_date | Post date | 10 | 390 / 617 |
| post_date | post_date | 7 | 13 / 325 |
| post_date_text | Post date text | 6 | 68 / 444 |
| post_date_text | post_date_text | 3 | 14 / 242 |

### roster_5

| Variable | Raw header | Sheets | Non-empty / rows |
|---|---|---|---|
| current_title | Current_Title | 7 | 3,464 / 3,464 |

Not present in this layout: leader_name, company_name, role_start_year, ceo_type, platform, post_date, post_date_text.

### summary_8

| Variable | Raw header | Sheets | Non-empty / rows |
|---|---|---|---|
| current_title | Current title | 6 | 461 / 465 |

Not present in this layout: leader_name, company_name, role_start_year, ceo_type, platform, post_date, post_date_text.

### wordcount_leader_12

| Variable | Raw header | Sheets | Non-empty / rows |
|---|---|---|---|
| leader_name | leader_name | 541 | 14,236 / 30,994 |
| company_name | company_name | 541 | 14,236 / 30,994 |
| current_title | current_title | 541 | 14,236 / 30,994 |
| role_start_year | role_start_year | 541 | 0 / 30,994 |
| ceo_type | ceo_type | 541 | 14,236 / 30,994 |
| platform | platform | 541 | 14,236 / 30,994 |
| post_date | Post date | 541 | 29,256 / 30,994 |
| post_date | post_date | 541 | 7 / 30,994 |
| post_date_text | post_date_text | 541 | 7,957 / 30,994 |

### Where role_start_year or post_date holds values

| Workbook | Column | Non-empty / rows |
|---|---|---|
| workbook-04 | Post date | 3,048 / 3,231 |
| workbook-06 | post_date | 6 / 14 |
| workbook-06 | role_start_year | 6 / 14 |
| workbook-08 | post_date | 2 / 353 |
| workbook-09 | Post date | 2,986 / 3,193 |
| workbook-09 | post_date | 8 / 362 |
| workbook-09 | role_start_year | 6 / 14 |
| workbook-10 | post_date | 6 / 1,224 |
| workbook-13 | Post date | 5,203 / 5,648 |
| workbook-13 | post_date | 5 / 1,169 |
| workbook-17 | Post date | 4,164 / 4,477 |
| workbook-19 | post_date | 1 / 127 |
| workbook-19 | role_start_year | 1 / 127 |
| workbook-21 | Post date | 5,779 / 5,991 |
| workbook-21 | post_date | 1 / 126 |
| workbook-21 | role_start_year | 1 / 126 |
| workbook-26 | Post date | 4,990 / 5,343 |
| workbook-30 | Post date | 3,476 / 3,502 |

## Author blocks

1,277 sheets have a leader/founder column. A block is a run of consecutive rows by the same leader key; the key is the exact text of the cell, so near-duplicate spellings count as different leaders until the ID matching step.

| Author blocks in a sheet | Sheets |
|---|---|
| 0 | 275 |
| 1 | 940 |
| 2 | 4 |
| 17 | 2 |
| 18 | 2 |
| 22 | 2 |
| 27 | 2 |
| 29 | 2 |
| 30 | 2 |
| 32 | 2 |
| 35 | 2 |
| 37 | 4 |
| 40 | 2 |
| 42 | 5 |
| 43 | 1 |
| 46 | 1 |
| 47 | 1 |
| 65 | 1 |
| 69 | 2 |
| 70 | 2 |
| 73 | 2 |
| 74 | 2 |
| 75 | 2 |
| 76 | 3 |
| 77 | 1 |
| 78 | 1 |
| 80 | 1 |
| 81 | 2 |
| 86 | 1 |
| 87 | 1 |
| 99 | 1 |
| 100 | 1 |
| 653 | 5 |

| Distinct leader keys in a sheet | Sheets |
|---|---|
| 0 | 275 |
| 1 | 940 |
| 2 | 4 |
| 17 | 2 |
| 18 | 2 |
| 22 | 2 |
| 27 | 2 |
| 29 | 2 |
| 30 | 2 |
| 32 | 2 |
| 35 | 2 |
| 37 | 4 |
| 40 | 2 |
| 42 | 5 |
| 43 | 1 |
| 46 | 1 |
| 47 | 1 |
| 65 | 1 |
| 69 | 2 |
| 70 | 2 |
| 73 | 4 |
| 74 | 3 |
| 75 | 1 |
| 76 | 2 |
| 78 | 1 |
| 80 | 1 |
| 81 | 2 |
| 85 | 1 |
| 86 | 1 |
| 99 | 1 |
| 100 | 1 |
| 652 | 5 |

11 sheets have more blocks than distinct leaders (a leader's rows are split into separate runs).

859 distinct leader keys in total; 813 of them appear in more than one sheet.

## Company_Data

- Data rows: 852; columns: 129 (one sheet).
- Contact columns found by header name (to be dropped at load in Step 3): Email, KeyPeopleEmailIds, CompanyEmails, CompanyPhoneNumbers.
- Single-letter headers (meaning unknown, logged under Findings): Q, V, Z.
