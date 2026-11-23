# ceo_type and Gender counts

Counts only: no names, no ids, no cell values. Inputs are `data/interim/harmonised_posts.csv` and `data/interim/company_data.csv` (both git-ignored).

## ceo_type, per leader

A leader is one `name_key` in the post workbooks. The column is blank on many rows, so a leader with a label on some rows counts once under that label. A leader with both labels is counted as conflicting, not assigned.

| ceo_type | Leaders |
|---|---|
| Professional CEO | 442 |
| Founder-CEO | 74 |
| blank on every row | 46 |
| only a value that is neither label | 2 |
| both labels (conflicting) | 0 |
| all leaders | 564 |

## ceo_type, per post cell

| ceo_type | Cells |
|---|---|
| Professional CEO | 19,230 |
| Founder-CEO | 4,234 |
| blank | 34,476 |
| a value that is neither label | 14 |
| rows with no leader name (not counted above) | 0 |

## Company_Data Gender, exactly as coded

Counted as the strings 1 and 0, with '.', '-' and empty cells treated as blank. Gender coding is read from `configs/gender_coding.yaml` (confirmed 2026-11-23 by the project team from the data owner and mentors: 1 = man, 0 = woman). Gender is never inferred from names.

| Value as coded | Rows |
|---|---|
| coded 1 (man) | 602 |
| coded 0 (woman) | 58 |
| blank | 192 |
| any other value | 0 |
| all rows | 852 |
