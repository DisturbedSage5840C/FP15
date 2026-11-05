# Company_Data profile

Counts and column headers only: no names, companies or cell values. Contact columns were dropped at load, before anything was written.

## Shape

| Item | Count |
|---|---|
| Data rows | 852 |
| Columns in the file | 129 |
| Contact columns dropped at load | 5 |
| Columns kept | 124 |

## Contact columns dropped (headers)

- Email
- KeyPeopleEmailIds
- CompanyEmails
- CompanyPhoneNumbers

## Columns dropped because their cells are mostly email addresses (headers)

Rule: email addresses in at least 50% of a column's filled cells. The header does not say contact, the content does.

- KeyPeopleInfo

## Gender (counts as coded; not decoded)

Gender is used exactly as coded in the file. What 1 and 0 mean is an open question for the mentors; nothing here decodes it, and no gender is inferred from names.

| Value as coded | Rows |
|---|---|
| 1 | 602 |
| 0 | 58 |
| blank | 192 |

## Columns with the headers Q, V and Z

These are the columns whose header text is the single letter (not the Excel columns lettered Q, V, Z). Counts only; what they measure is not decided here.

| Header | Filled | Blank | Distinct | Ends in % | Negative | Zero | Positive |
|---|---|---|---|---|---|---|---|
| Q | 852 | 0 | 24 | 852 | 4 | 693 | 155 |
| V | 689 | 163 | 115 | 689 | 0 | 0 | 689 |
| Z | 750 | 102 | 151 | 750 | 322 | 37 | 391 |

## Columns carrying K/M/B/T suffixes (parsed by one function)

| Column | Filled | With suffix | Parsed |
|---|---|---|---|
| RevenueUSD2021 | 684 | 684 | 684 |
| RevenueUSD2022 | 683 | 679 | 683 |
| RevenueUSD2023 | 681 | 679 | 681 |
| RevenueUSD2024 | 606 | 604 | 606 |
| ProfitUSD2021 | 681 | 663 | 681 |
| ProfitUSD2022 | 681 | 667 | 681 |
| ProfitUSD2023 | 673 | 667 | 673 |
| ProfitUSD2024 | 597 | 591 | 597 |
| EBITDAUSD2021 | 660 | 653 | 660 |
| EBITDAUSD2022 | 665 | 659 | 665 |
| EBITDAUSD2023 | 684 | 678 | 684 |
| EBITDAUSD2024 | 603 | 597 | 603 |

## Contact-like text left in kept columns (heuristic)

Cells in kept columns that look like an email address or a phone number. Reported, not scrubbed.

| Column | Cells |
|---|---|
| AllAssociatedLegalEntitiesN | 9 |

## Columns with no value at all

- RevenueUSD2025
- ProfitUSD2025
- EBITDAUSD2025
- SoonicornClubStatus
- SoonicornClubEventDate
- DateAdded
- DeadpooledDate
- AppRating
