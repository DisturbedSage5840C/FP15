# Company_Data columns for the leader and firm analysis

Claims here are about the image projected in public posts, not about the person. This report lists column headers, counts and shares only: no names, companies or cell values.
Counts are cell-level: the post minimum is applied to raw post cells, not yet to author blocks.

## Who is counted

| Group | Leaders |
|---|---|
| Leaders with at least one raw post cell | 563 |
| Leaders with 15 or more raw post cells | 301 |
| Matched to exactly one Company_Data row | 295 |
| Left out: ambiguous name match, not resolved | 5 |
| Left out: clear match but no Company_Data row | 1 |
| Left out: not in the leader_id proposal | 0 |

## The 20 columns proposed

Ranked by the share of counted leaders with a value; at most 2 per study variable. 20 columns listed.

| Column | Study variable | Filled | Share | Reads as a number |
|---|---|---|---|---|
| Current_Title | title family | 295 of 295 | 100.0% | n/a |
| CompanyStage | firm stage | 295 of 295 | 100.0% | n/a |
| Country | location | 295 of 295 | 100.0% | n/a |
| IsFunded | funding | 295 of 295 | 100.0% | n/a |
| FoundedYear | firm age | 291 of 295 | 98.6% | 291 of 291 |
| City | location | 291 of 295 | 98.6% | n/a |
| NewsArticlesAllTime | firm visibility | 290 of 295 | 98.3% | 290 of 290 |
| LinkedIn_Connections | audience size | 286 of 295 | 96.9% | 41 of 286 |
| SectorPraticeAreaFeed | sector | 283 of 295 | 95.9% | n/a |
| LinkedIn_Skills | profile richness | 272 of 295 | 92.2% | n/a |
| AnnualRevenueUSD | firm size | 270 of 295 | 91.5% | 0 of 270 |
| LatestRevenueUSD | firm size | 270 of 295 | 91.5% | 270 of 270 |
| TotalEmployeeCount | firm size (employees) | 269 of 295 | 91.2% | 0 of 269 |
| NumberofEmployees | firm size (employees) | 269 of 295 | 91.2% | 269 of 269 |
| AnnualNetProfitUSD | profitability | 269 of 295 | 91.2% | 0 of 269 |
| RevenueCAGR1Year | firm growth | 262 of 295 | 88.8% | 262 of 262 |
| EmployeeCountLatest12monthgr | firm growth | 262 of 295 | 88.8% | 262 of 262 |
| BusinessModels | sector | 258 of 295 | 87.5% | n/a |
| Gender | gender | 237 of 295 | 80.3% | n/a |
| ProfitUSD2024 | profitability | 215 of 295 | 72.9% | 215 of 215 |

## Other candidate columns considered

| Column | Study variable | Filled | Share | Reads as a number |
|---|---|---|---|---|
| LatestEmployeeCount | firm size (employees) | 269 of 295 | 91.2% | 269 of 269 |
| EmployeeCount2024 | firm size (employees) | 240 of 295 | 81.4% | 240 of 240 |
| RevenueUSD2024 | firm size | 217 of 295 | 73.6% | 217 of 217 |
| RevenueUSD2023 | firm size | 247 of 295 | 83.7% | 247 of 247 |
| EBITDAUSD2024 | profitability | 215 of 295 | 72.9% | 215 of 215 |
| RevenueCAGR3Year | firm growth | 245 of 295 | 83.1% | 245 of 245 |
| LatestEmployeeGrowth12month | firm growth | 255 of 295 | 86.4% | 255 of 255 |
| Current_City | location | 288 of 295 | 97.6% | n/a |
| Current_State | location | 282 of 295 | 95.6% | n/a |
| LinkedIn_Followers | audience size | 211 of 295 | 71.5% | 211 of 211 |
| LinkedIn_Recommendations_Count | profile richness | 106 of 295 | 35.9% | 106 of 106 |
| Honors_Awards_Count | profile richness | 28 of 295 | 9.5% | 28 of 28 |
| Languages_Spoken | profile richness | 156 of 295 | 52.9% | n/a |
| LinkedIn_Publications_Count | profile richness | 15 of 295 | 5.1% | 15 of 15 |
| Licenses_Certifications | profile richness | 109 of 295 | 36.9% | n/a |
| TotalFundingUSD | funding | 117 of 295 | 39.7% | 117 of 117 |

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
