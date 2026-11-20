# Outcome feasibility from Company_Data

Claims here are about the image projected in public posts, not about the person. This report holds column headers and counts only: no names, ids, cell values or ratios.

## Who is counted

Leaders are joined to a Company_Data row only on a clear proposal match with a company row. Ambiguous, blank and missing matches are counted as not matched and never guessed. Two leaders at one firm both count.

| Group | 15+ raw post cells | Any raw post cells |
|---|---|---|
| Leaders in the group | 327 | 563 |
| Matched to one Company_Data row | 320 | 545 |
| Distinct firms among those matched | 320 | 545 |
| Not matched; the leader table says: ambiguous | <5 | <5 |
| Not matched; the leader table says: exact | 5 | 9 |
| Not matched; the leader table says: none | <5 | <5 |

## Fill counts

The file has 852 firm rows. The two leader columns count leaders matched to a row. AnnualRevenueUSD and AnnualNetProfitUSD hold a comma-grouped number followed by a bracket whose meaning is unknown, so they are counted as filled and not read. A bare-number cell has no K, M or B suffix, so its scale and unit are not stated; it is left as written, never rescaled, and used in no measure. LatestRevenueUSD and LatestEmployeeGrowth12month are bare numbers throughout, so they give no measure here.

| Column | Filled (file) | Reads as a number (file) | Bare number, scale unstated (file) | Leaders, 15+ posts | Leaders, any posts |
|---|---|---|---|---|---|
| AnnualNetProfitUSD | 760 | not read | not read | 291 | 484 |
| ProfitUSD2024 | 597 | 597 | 6 | 231 | 381 |
| EBITDAUSD2024 | 603 | 603 | 6 | 231 | 382 |
| AnnualRevenueUSD | 768 | not read | not read | 292 | 488 |
| LatestRevenueUSD | 768 | 768 | 768 | 292 | 488 |
| RevenueUSD2024 | 606 | 606 | <5 | 233 | 387 |
| RevenueUSD2023 | 681 | 681 | <5 | 266 | 435 |
| RevenueCAGR1Year | 730 | 730 | <5 | 282 | 468 |
| RevenueCAGR3Year | 673 | 673 | <5 | 263 | 429 |
| RevenueCAGR5Year | 591 | 591 | <5 | 238 | 386 |
| EmployeeCountLatest12monthgr | 750 | 750 | <5 | 283 | 481 |
| LatestEmployeeGrowth12month | 728 | 728 | 728 | 275 | 468 |

## Which measures can be built

A margin or a growth ratio needs both columns of a same-year pair to read as numbers, a positive base, and no bare-number cell. The 2023 and 2024 columns are paired by name; that they share a fiscal year is not verified. The three CAGR columns and the employee growth column are used as given when they read as numbers. No ratio or value is shown here.

| Measure | Firm rows (file) | Leaders, 15+ posts | Leaders, any posts |
|---|---|---|---|
| Profit margin, 2024 | 588 | 228 | 376 |
| EBITDA margin, 2024 | 594 | 228 | 377 |
| Revenue growth, 2023 to 2024 | 570 | 222 | 365 |
| Revenue CAGR, 1 year | 730 | 282 | 468 |
| Revenue CAGR, 3 years | 673 | 263 | 429 |
| Revenue CAGR, 5 years | 591 | 238 | 386 |
| Employee growth, 12 months | 750 | 283 | 481 |

## Measures by sector

Groups with fewer than 5 leaders are pooled and not named. A cell under 5 shows "<5", and a neighbouring cell is also hidden where the total would give a hidden one away. A firm that lists several labels is placed by its first.

### Leaders with 15+ raw post cells

| Sector (first listed label's group) | Leaders | Profit margin, 2024 | EBITDA margin, 2024 | Revenue growth, 2023 to 2024 | Revenue CAGR, 1 year | Revenue CAGR, 3 years | Revenue CAGR, 5 years | Employee growth, 12 months |
|---|---|---|---|---|---|---|---|---|
| Financial Services | 51 | 39 | 37 | 36 | 44 | 40 | 39 | 47 |
| Business Services | 33 | 24 | 24 | 23 | 28 | 25 | 24 | 29 |
| FinTech | 25 | 20 | 20 | 20 | 25 | 25 | 21 | 19 |
| Healthcare | 23 | 11 | 12 | 11 | 19 | 19 | 17 | 20 |
| Consumer Goods | 22 | 21 | 21 | 21 | 21 | 20 | 18 | 21 |
| Food and Agriculture | 16 | 10 | 10 | 12 | 14 | 11 | 11 | 16 |
| Energy | 14 | 12 | 12 | 12 | 14 | 12 | 11 | 13 |
| Retail | 13 | 9 | 9 | 9 | 10 | 9 | 8 | 11 |
| Real Estate and Construction | 12 | 9 | 9 | 8 | 10 | 9 | 7 | 10 |
| Chemicals and Materials | 10 | 8 | 8 | 7 | 9 | 8 | 5 | 9 |
| Consumer | 10 | 10 | 10 | 10 | 10 | 10 | 10 | 10 |
| HealthTech | 8 | 6 | 6 | 6 | 8 | 8 | 8 | <5 |
| Industrial Goods and Manufacturing | 8 | <5 | <5 | <5 | <5 | <5 | <5 | 7 |
| Conglomerates | 7 | 5 | 5 | 5 | 7 | 7 | <5 | 7 |
| Investment Industry | 7 | <5 | <5 | <5 | 6 | 5 | <5 | <5 |
| Enterprise Applications | 6 | <5 | <5 | <5 | <5 | <5 | <5 | 6 |
| Environment | 5 | 5 | 5 | 5 | 5 | 5 | 5 | 5 |
| (other groups, each under the disclosure minimum) | 38 | 23 | 24 | 24 | 33 | 32 | 31 | 37 |
| (no sector listed) | 12 | 5 | 5 | 5 | 10 | 10 | 7 | 10 |
| All leaders in this group | 320 | 228 | 228 | 222 | 282 | 263 | 238 | 283 |

### Leaders with any raw post cell

| Sector (first listed label's group) | Leaders | Profit margin, 2024 | EBITDA margin, 2024 | Revenue growth, 2023 to 2024 | Revenue CAGR, 1 year | Revenue CAGR, 3 years | Revenue CAGR, 5 years | Employee growth, 12 months |
|---|---|---|---|---|---|---|---|---|
| Financial Services | 81 | 63 | 58 | 57 | 72 | 66 | 65 | 74 |
| Healthcare | 50 | 27 | 29 | 28 | 40 | 38 | 35 | 45 |
| Business Services | 47 | 33 | 34 | 33 | 41 | 36 | 34 | 39 |
| Consumer Goods | 39 | 32 | 33 | 32 | 35 | 34 | 31 | 36 |
| FinTech | 32 | 27 | 27 | 27 | 32 | 32 | 27 | 25 |
| Food and Agriculture | 31 | 19 | 19 | 23 | 29 | 24 | 20 | 30 |
| Chemicals and Materials | 24 | 16 | 16 | 14 | 19 | 15 | 10 | 21 |
| Retail | 24 | 15 | 15 | 15 | 18 | 15 | 13 | 22 |
| Real Estate and Construction | 22 | 16 | 16 | 14 | 18 | 17 | 14 | 18 |
| Energy | 21 | 18 | 18 | 16 | 18 | 13 | 11 | 19 |
| Industrial Goods and Manufacturing | 21 | 9 | 9 | 8 | 12 | 9 | 8 | 16 |
| Consumer | 15 | 13 | 13 | 13 | 15 | 14 | 14 | 15 |
| Enterprise Applications | 15 | 12 | 12 | 9 | 12 | 12 | 12 | 15 |
| Conglomerates | 11 | 9 | 9 | 9 | 11 | 11 | 7 | 11 |
| Investment Industry | 11 | 5 | 5 | 5 | 10 | 9 | 8 | 7 |
| Travel and Hospitality | 11 | <5 | <5 | <5 | <5 | <5 | <5 | 9 |
| Auto | 10 | 6 | 6 | 6 | 9 | 9 | 8 | 9 |
| Environment | 10 | 9 | 9 | 9 | 9 | 9 | 8 | 10 |
| HealthTech | 10 | 8 | 8 | 8 | 10 | 10 | 10 | <5 |
| Education | 5 | <5 | <5 | <5 | <5 | <5 | 5 | <5 |
| Telecom | 5 | <5 | <5 | <5 | 5 | 5 | <5 | 5 |
| (other groups, each under the disclosure minimum) | 32 | 22 | 24 | 24 | 31 | 29 | 29 | 31 |
| (no sector listed) | 18 | 8 | 8 | 7 | 14 | 14 | 10 | 16 |
| All leaders in this group | 545 | 376 | 377 | 365 | 468 | 429 | 386 | 481 |

## Not in the file

ROA and Tobin's q need the columns below. None has a header in Company_Data. Nothing is guessed or filled.

- **Total assets**: the denominator of ROA (profit over assets) and the book value of assets in Tobin's q.
- **Market value of equity (current)**: the main part of the numerator of Tobin's q; the file has no current market value.
- **Total debt**: added to the market value of equity in the numerator of Tobin's q, and a leverage control.
- **Book equity**: gives return on equity as an alternative to ROA and a cross-check on total assets and debt.

Headers with a similar look were found and are not accepted as substitutes:

- LatestValuationUSD: not accepted; its meaning is not verified (it could be a private-round valuation).
- StockPriceatIPOUSD: not accepted; a price at the IPO date only, with no share count.
- MarketCapitalatIPOUSD: not accepted; market value at the IPO date only, not current.

## Caveats

- **Firm performance is not leader success.** A firm's margin or growth reflects its market, history and capital as much as one leader.
- **No tenure.** role_start_year is filled for fewer than 5 leaders in the workbooks seen so far, so a leader's time in the role cannot be matched to a performance year.
- **No movers.** Each leader is seen at one firm, so leader and firm cannot be told apart by who moved where.
- **Reverse causation.** Performance may shape how and whether a leader posts, as much as the reverse. Any link is descriptive.
- **Fiscal years.** Whether the Latest columns and the 2023 and 2024 columns share a fiscal year is unverified.
- **Sector.** The sector label is the first listed one; a firm can list several.

## Open for the team and the mentors

- Which outcome measure (ROA, Tobin's q, or the margins and growth above), which year window, and whether to adjust for sector. Recorded as open in docs/decisions.md; nothing is decided here.
- The meeting with the data owners about specific columns is planned for 2026-11-23.
