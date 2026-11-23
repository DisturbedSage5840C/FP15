# Leader master table (Step 14A)

Universe: every distinct leader key across the four sources (post sheets, roster, wordcount summaries, Company_Data). The post-based analysis still needs at least 15 raw post cells. Counts only: no names, no ids, no workbook or sheet references. The row-level table is `data/interim/leader_master.csv` (git-ignored).

Information in this report is relayed from `data/interim` files; it was not changed here.

- Universe size (all four sources): **862**
- Keys excluded due to internal source sharing: <5

## Post-sheet base versus master

| Measure | Old post-sheet base | Master |
|---|---|---|
| leaders represented in post sheets | 564 | 564 |
| leaders with at least 15 raw post cells (15+) | 327 | 327 |

## Source overlap

| Source | Leaders | With at least 15 raw post cells (15+) |
|---|---|---|
| post sheets | 564 | 327 |
| roster | 652 | 241 |
| wordcount summaries | 532 | 322 |
| Company_Data | 852 | 325 |
| universe (union) | 862 | 327 |

## Leaders with posts versus without

| Group | Leaders | With at least 15 raw post cells (15+) |
|---|---|---|
| with at least 1 raw post cell | 563 | 327 |
| with no raw post cell | 299 | 0 |
| all | 862 | 327 |

## Match method (Company_Data matching ladder)

| Match method | Leaders | With at least 15 raw post cells (15+) |
|---|---|---|
| name_exact | 852 | 325 |
| name_loose | <5 | <5 |
| company_name | <5 | <5 |
| domain | <5 | <5 |
| ambiguous | <5 | <5 |
| none | 8 | <5 |

- Leaders with Company_Data columns attached: 852
- Added by company-name or domain step (over name-only): <5

## Completeness

- Leaders with Company_Data columns: 852
- Leaders with both company name and domain blank: 8
- Still ambiguous (not resolved): <5

## Post-analysis denominator (leaders with 15+ raw cells)

| Group | Leaders (15+ raw cells) |
|---|---|
| name_exact | 325 |
| name_loose | <5 |
| company_name | <5 |
| domain | <5 |
| ambiguous | <5 |
| none | <5 |
| all with 15+ | 327 |

The 15-post threshold comes from `configs/thresholds.yaml`. Raw post cells stand in for posts until segmentation is confirmed (G1 unsigned).

