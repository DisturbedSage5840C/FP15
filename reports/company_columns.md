# Company_Data columns for the leader and firm analysis

Claims here are about the image projected in public posts, not about the person. This report lists column headers, counts and shares only: no names, companies or cell values.
Counts are cell-level: the post minimum is applied to raw post cells, not yet to author blocks.

## Who is counted

| Group | Leaders |
|---|---|
| Leaders with at least one raw post cell | 563 |
| Leaders with 15 or more raw post cells | 327 |
| Matched to exactly one Company_Data row | 320 |
| Left out: ambiguous name match, not resolved | 5 |
| Left out: clear match but no Company_Data row | 2 |
| Left out: not in the leader_id proposal | 0 |

## The 20 columns proposed

Ranked by the share of counted leaders with a value; at most 2 per study variable. 20 columns listed.

| Column | Study variable | Filled | Share | Reads as a number |
|---|---|---|---|---|
| Current_Title | title family | 320 of 320 | 100.0% | n/a |
| CompanyStage | firm stage | 320 of 320 | 100.0% | n/a |
| Country | location | 320 of 320 | 100.0% | n/a |
| IsFunded | funding | 320 of 320 | 100.0% | n/a |
| FoundedYear | firm age | 316 of 320 | 98.8% | 316 of 316 |
| City | location | 316 of 320 | 98.8% | n/a |
| NewsArticlesAllTime | firm visibility | 315 of 320 | 98.4% | 315 of 315 |
| LinkedIn_Connections | audience size | 309 of 320 | 96.6% | 45 of 309 |
| SectorPraticeAreaFeed | sector | 308 of 320 | 96.2% | n/a |
| LinkedIn_Skills | profile richness | 295 of 320 | 92.2% | n/a |
| TotalEmployeeCount | firm size (employees) | 292 of 320 | 91.2% | 0 of 292 |
| NumberofEmployees | firm size (employees) | 292 of 320 | 91.2% | 292 of 292 |
| AnnualRevenueUSD | firm size | 292 of 320 | 91.2% | 0 of 292 |
| LatestRevenueUSD | firm size | 292 of 320 | 91.2% | 292 of 292 |
| AnnualNetProfitUSD | profitability | 291 of 320 | 90.9% | 0 of 291 |
| EmployeeCountLatest12monthgr | firm growth | 283 of 320 | 88.4% | 283 of 283 |
| BusinessModels | sector | 282 of 320 | 88.1% | n/a |
| RevenueCAGR1Year | firm growth | 282 of 320 | 88.1% | 282 of 282 |
| Gender | gender | 255 of 320 | 79.7% | n/a |
| ProfitUSD2024 | profitability | 231 of 320 | 72.2% | 231 of 231 |

## Other candidate columns considered

| Column | Study variable | Filled | Share | Reads as a number |
|---|---|---|---|---|
| LatestEmployeeCount | firm size (employees) | 292 of 320 | 91.2% | 292 of 292 |
| EmployeeCount2024 | firm size (employees) | 260 of 320 | 81.2% | 260 of 260 |
| RevenueUSD2024 | firm size | 233 of 320 | 72.8% | 233 of 233 |
| RevenueUSD2023 | firm size | 266 of 320 | 83.1% | 266 of 266 |
| EBITDAUSD2024 | profitability | 231 of 320 | 72.2% | 231 of 231 |
| RevenueCAGR3Year | firm growth | 263 of 320 | 82.2% | 263 of 263 |
| LatestEmployeeGrowth12month | firm growth | 275 of 320 | 85.9% | 275 of 275 |
| Current_City | location | 313 of 320 | 97.8% | n/a |
| Current_State | location | 307 of 320 | 95.9% | n/a |
| LinkedIn_Followers | audience size | 227 of 320 | 70.9% | 227 of 227 |
| LinkedIn_Recommendations_Count | profile richness | 118 of 320 | 36.9% | 118 of 118 |
| Honors_Awards_Count | profile richness | 30 of 320 | 9.4% | 30 of 30 |
| Languages_Spoken | profile richness | 172 of 320 | 53.8% | n/a |
| LinkedIn_Publications_Count | profile richness | 16 of 320 | 5.0% | 16 of 16 |
| Licenses_Certifications | profile richness | 118 of 320 | 36.9% | n/a |
| TotalFundingUSD | funding | 127 of 320 | 39.7% | 127 of 127 |

Columns left out on purpose:

- CompanyName, Person_Name: identifiers; analysis files carry leader_id only.
- Website, LinkedIn, LinkedIn_Profile_Link, Twitter, Facebook, BlogUrl, TracxnURL, DomainName: links and identifiers, not analysis variables.
- Overview, Description, AdditionalComment, TeamBackground: free text, not a structured variable.
- IsIPO, StockTicker, Exchange, IPODate and the other IPO columns: every firm in the file is listed, so listed versus unlisted cannot be tested.
- Q, V, Z: unnamed columns with no known meaning; not used until the owner says what they hold.
- the *_num columns: derived by this project from the columns above; not a source column.
- email and phone columns: dropped when the file is loaded, before anything is written to disk.

## Needs a human decision

- The choice of columns and the study variable each one serves is a proposal for the mentors, not a decision.
- Gender is used as coded in the file; what 1 and 0 mean is not confirmed, and gender is never inferred from a name.
- Tenure is not in Company_Data (it has no role start year), and role_start_year is empty in the post workbooks, so tenure cannot be filled from here.
- LinkedIn_Followers and LinkedIn_Connections already exist in the file. Scraping new reaction or follower counts is not approved, so these file values are the only source.
- The 15-post rule is applied to raw post cells, a cell-level proxy. It will change once author blocks are segmented.
- Ambiguous name matches are left out, not resolved. Resolving them is a human job.
