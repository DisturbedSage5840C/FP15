# Leader table (Step 1)

The base list is the leaders who have posts. The roster, the summaries and Company_Data only enrich it.
Counts only: no names, no ids, no workbook or sheet references. The row-level table is `data/interim/leader_table.csv` (git-ignored).

- Leaders in the base list: 564
- With at least 1 raw post cell: 563
- With no raw post cell (cleaned text only): 1
- Raw post cells, all leaders: 26,945

## Company_Data match

| Company_Data match | Leaders | With at least 15 raw post cells |
|---|---|---|
| exact | 554 | 325 |
| loose | 0 | 0 |
| ambiguous | 2 | 0 |
| none | 8 | 2 |

The post minimum is read from `configs/thresholds.yaml`. Raw post cells are a cell-level proxy until author blocks are segmented.

## Roster and summaries

| Enrichment source | Yes | No | Share yes |
|---|---|---|---|
| In the roster | 401 | 163 | 71.1% |
| In the summaries | 534 | 30 | 94.7% |

Yes means at least one candidate was found (exact, loose or ambiguous). Ambiguous matches are never resolved by hand.

## Names in an enrichment source with no leader in the base list

| Source | Names counted, not resolved |
|---|---|
| company | 293 |
| roster | 249 |
| summaries | 0 |
