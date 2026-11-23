# Leader master table (Step 14A)

Universe: every distinct leader key across the four sources (post sheets, roster, wordcount summaries, Company_Data). The post-based analysis still needs at least 15 raw post cells. Counts only: no names, no ids, no workbook or sheet references. The row-level table is `data/interim/leader_master.csv` (git-ignored).

Information in this report is relayed from `data/interim` files; it was not changed here.

- Universe size (all four sources): **852**
- Keys excluded (shared inside one source, no id assigned): 10

## Source overlap

| Source | Leaders | With at least 15 raw post cells (15+) |
|---|---|---|
| post sheets | 555 | 322 |
| roster | 646 | 239 |
| wordcount summaries | 523 | 317 |
| Company_Data | 842 | 320 |
| universe (union) | 852 | 322 |

## Leaders with posts versus without

| Group | Leaders | With at least 15 raw post cells (15+) |
|---|---|---|
| with at least 1 raw post cell | 554 | 322 |
| with no raw post cell | 298 | 0 |
| all | 852 | 322 |

## Match method (Company_Data matching ladder)

| Match method | Leaders | With at least 15 raw post cells (15+) |
|---|---|---|
| name_exact | 842 | 320 |
| name_loose | <5 | <5 |
| company_name | <5 | <5 |
| domain | <5 | <5 |
| ambiguous | <5 | <5 |
| none | 8 | <5 |

- Leaders with Company_Data columns attached: 844
- Added by company-name or domain step (over name-only): <5

## Completeness

- Leaders with Company_Data columns: 844
- Leaders with both company name and domain blank: 7
- Still ambiguous (not resolved): <5

## Post-analysis denominator (leaders with 15+ raw cells)

| Group | Leaders (15+ raw cells) |
|---|---|
| name_exact | 320 |
| name_loose | <5 |
| company_name | <5 |
| domain | <5 |
| ambiguous | <5 |
| none | <5 |
| all with 15+ | 322 |

The 15-post threshold comes from `configs/thresholds.yaml`. Raw post cells stand in for posts until segmentation is confirmed (G1 unsigned).

