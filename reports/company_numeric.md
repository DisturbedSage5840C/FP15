# Company_Data numbers (Step 3)

Numeric versions of three named columns, read with the one `parse_quantity` function. Blank markers (empty, `.`, `-`) stay missing. Unreadable cells stay missing and are not guessed. The row-level table is `data/interim/company_numeric.csv` (git-ignored, keyed by `row:<n>`, no names).

## Counts per column

| Source column | Numeric column | Rows | Blank | Filled | Parsed | Unparsed | Scale unverified |
|---|---|---|---|---|---|---|---|
| LatestRevenueUSD | revenue_usd_latest | 852 | 84 | 768 | 768 | 0 | 0 |
| NumberofEmployees | employees | 852 | 79 | 773 | 773 | 0 | 0 |
| ProfitUSD2024 | profit_usd_2024 | 852 | 255 | 597 | 597 | 0 | 6 |

Scale unverified: a ProfitUSD2024 cell written as a bare number, without a K, M, B or T suffix. The file does not state its scale, so it is flagged and kept as written, never rescaled.

## Do the three columns share a fiscal year? (headers only)

| Column header | Year named in the header | Says latest |
|---|---|---|
| LatestRevenueUSD | none | Latest |
| NumberofEmployees | none | - |
| ProfitUSD2024 | 2024 | - |

Only ProfitUSD2024 names a year (2024). LatestRevenueUSD says latest without a year, and NumberofEmployees names no year. The headers therefore do not show that the three refer to the same fiscal year. This is not established and needs the owner or the mentors. The bracketed columns (AnnualRevenueUSD, AnnualNetProfitUSD, TotalEmployeeCount) were not parsed and are not used to answer this.
