# EDA: limits of the data we already have

Counts and aggregates only: no names, post text, links, emails or leader ids appear here. A count below 5 shows as "<5" instead of its number, and a group with fewer than 20 leaders is flagged as too small to model.

Every statement is about the image projected in public posts, never about personality. Raw post cells stand in for posts until G1 is signed (G1 is the segmentation gate), so every count of leaders at the 15-post cut is a count of raw cells, and the cut once segmented is not computed. Nothing is filled in or guessed: missing stays missing. No gate is signed off by this report. No scraping and no network were used, and scraping_approved stays false.

## 1. Coverage

### Leaders by source list

A leader is one entry in `leader_id_proposal`: a name key matched across the people lists. The lists overlap, so the rows below do not add up to the union.

| List | Leaders | With at least 1 raw cell | At least 15 raw cells |
|---|---|---|---|
| All_500 roster | 652 | 394 | 239 |
| Summaries | 532 | 523 | 317 |
| Company_Data | 852 | 545 | 320 |
| Post workbooks | 564 | 554 | 322 |

### Overlap of the three people lists

Each leader falls in exactly one row. "none of the three lists" are leaders found only in the post workbooks.

| Listed in | Leaders | Share |
|---|---|---|
| All_500 + Summaries + Company_Data | 383 | 44.4% |
| All_500 + Summaries | <5 | <5 |
| All_500 + Company_Data | 269 | 31.2% |
| All_500 only | <5 | <5 |
| Summaries + Company_Data | 145 | 16.8% |
| Summaries only | <5 | <5 |
| Company_Data only | 55 | 6.4% |
| none of the three lists | 6 | 0.7% |
| all | 862 | 100.0% |

### Leaders with posts

| Item | Value |
|---|---|
| Leaders in any list (the union) | 862 |
| of which under an ambiguous name key | 10 |
| Leaders with at least 1 raw cell | 563 |
| Leaders with at least 15 raw cells | 327 |
| Leaders with raw cells but no leader id in the proposal | 9 |
| of which with at least 15 raw cells | 5 |
| Leaders with at least 15 posts once segmented | not computed |
| Raw cells, all leaders (cells, not leaders) | 26,945 |

Cells stand in for posts until G1 is signed. A raw cell can hold more than one post, or none, so the cut on 15 raw cells can differ from the cut on 15 posts in either direction. The count once segmented is not computed: no per-cell segmented table exists and G1 is not signed. Full-cell segmentation was deliberately not run.

## 2. Gaps

Share of leaders missing each variable. Blank, "." and "-" count as missing, and so does a number that cannot be read ("500+" is not guessed at). A post-workbook variable is missing for a leader only when every raw cell of that leader is blank; the blank-cell columns count cells instead. Company_Data variables are read for leaders with a clear match and a company row only: ambiguous and unmatched leaders are counted and left out. "all but <5" means fewer than 5 leaders have the value. Raw cells stand in for posts until G1 is signed. Gender is shown as coded in the file and is not interpreted.

### Leaders with at least 1 raw cell

| Company_Data match | Leaders |
|---|---|
| Clear match with a company row (Company_Data variables read) | 545 |
| Ambiguous name key (left out) | <5 |
| Clear match without a company row (left out) | 9 |
| Not in the leader proposal (left out) | <5 |
| Leaders in this base | 563 |

| Variable | Source | Leaders in base | Leaders missing | Share missing | Blank cells | Share of cells blank |
|---|---|---|---|---|---|---|
| ceo_type | post workbooks | 563 | 45 | 8.0% | 17,517 | 65.0% |
| current_title | post workbooks | 563 | 46 | 8.2% | 17,523 | 65.0% |
| role_start_year | post workbooks | 563 | all but <5 | all but <5 | all but <5 | all but <5 |
| post_date | post workbooks | 563 | 557 | 98.9% | 26,934 | 100.0% |
| post_date_text | post workbooks | 563 | 105 | 18.7% | 22,153 | 82.2% |
| gender (as coded) | Company_Data | 545 | 116 | 21.3% | n/a | n/a |
| sector | Company_Data | 545 | 18 | 3.3% | n/a | n/a |
| firm size (employees) | Company_Data | 545 | 51 | 9.4% | n/a | n/a |
| firm age (founded year) | Company_Data | 545 | 5 | 0.9% | n/a | n/a |
| LinkedIn followers | Company_Data | 545 | 168 | 30.8% | n/a | n/a |
| revenue 2021 | Company_Data | 545 | 109 | 20.0% | n/a | n/a |
| revenue 2022 | Company_Data | 545 | 113 | 20.7% | n/a | n/a |
| revenue 2023 | Company_Data | 545 | 110 | 20.2% | n/a | n/a |
| revenue 2024 | Company_Data | 545 | 158 | 29.0% | n/a | n/a |
| profit 2021 | Company_Data | 545 | 114 | 20.9% | n/a | n/a |
| profit 2022 | Company_Data | 545 | 116 | 21.3% | n/a | n/a |
| profit 2023 | Company_Data | 545 | 115 | 21.1% | n/a | n/a |
| profit 2024 | Company_Data | 545 | 164 | 30.1% | n/a | n/a |

### Leaders with at least 15 raw cells

| Company_Data match | Leaders |
|---|---|
| Clear match with a company row (Company_Data variables read) | 320 |
| Ambiguous name key (left out) | 5 |
| Clear match without a company row (left out) | <5 |
| Not in the leader proposal (left out) | <5 |
| Leaders in this base | 327 |

| Variable | Source | Leaders in base | Leaders missing | Share missing | Blank cells | Share of cells blank |
|---|---|---|---|---|---|---|
| ceo_type | post workbooks | 327 | 11 | 3.4% | 17,099 | 66.7% |
| current_title | post workbooks | 327 | 11 | 3.4% | 17,099 | 66.7% |
| role_start_year | post workbooks | 327 | all but <5 | all but <5 | all but <5 | all but <5 |
| post_date | post workbooks | 327 | all but <5 | all but <5 | all but <5 | all but <5 |
| post_date_text | post workbooks | 327 | 21 | 6.4% | 21,266 | 82.9% |
| gender (as coded) | Company_Data | 320 | 65 | 20.3% | n/a | n/a |
| sector | Company_Data | 320 | 12 | 3.8% | n/a | n/a |
| firm size (employees) | Company_Data | 320 | 28 | 8.8% | n/a | n/a |
| firm age (founded year) | Company_Data | 320 | <5 | <5 | n/a | n/a |
| LinkedIn followers | Company_Data | 320 | 93 | 29.1% | n/a | n/a |
| revenue 2021 | Company_Data | 320 | 52 | 16.2% | n/a | n/a |
| revenue 2022 | Company_Data | 320 | 57 | 17.8% | n/a | n/a |
| revenue 2023 | Company_Data | 320 | 54 | 16.9% | n/a | n/a |
| revenue 2024 | Company_Data | 320 | 87 | 27.2% | n/a | n/a |
| profit 2021 | Company_Data | 320 | 54 | 16.9% | n/a | n/a |
| profit 2022 | Company_Data | 320 | 57 | 17.8% | n/a | n/a |
| profit 2023 | Company_Data | 320 | 56 | 17.5% | n/a | n/a |
| profit 2024 | Company_Data | 320 | 89 | 27.8% | n/a | n/a |

## 3. Balance for the planned comparisons

Each factor is crossed with the post cut: leaders with at least 1 raw cell, and leaders with at least 15 raw cells. Raw cells stand in for posts until G1 is signed. A group with fewer than 20 leaders at the cut is flagged "too small to model"; that is a working flag for the EDA, not the modelling rule (that belongs in the pre-registration, gate G3). Founder vs professional uses ceo_type pooled per leader (conflicting and unrecognised kept apart). Gender is shown as coded in the file and is not interpreted. Title family, sector (first segment of the coded sector path) and size bands are a proposal for the mentors, not a decision. A leader with no usable value or no clear Company_Data match is shown in its own group, never filled in.

Firm size is cut into 4 quantile bands of the readable employee counts over all of Company_Data (cut points, employees: 105, 546, 2,333). A size that cannot be read ("500+") is not guessed at.

### Founder vs professional CEO

| Group | Leaders with 1+ raw cell | Share | Leaders with 15+ raw cells | Share | Flag at the cut |
|---|---|---|---|---|---|
| Professional CEO | 442 | 78.5% | 263 | 80.4% |  |
| Founder-CEO | 74 | 13.1% | 53 | 16.2% |  |
| unrecognised | <5 | <5 | <5 | <5 | too small to model |
| no value | <5 | <5 | <5 | <5 | too small to model |
| all | 563 | 100.0% | 327 | 100.0% |  |

### Gender (as coded)

| Group | Leaders with 1+ raw cell | Share | Leaders with 15+ raw cells | Share | Flag at the cut |
|---|---|---|---|---|---|
| coded 1 | 389 | 69.1% | 226 | 69.1% |  |
| coded 0 | 40 | 7.1% | 29 | 8.9% |  |
| no value | 116 | 20.6% | 65 | 19.9% |  |
| no usable company match | 18 | 3.2% | 7 | 2.1% | too small to model |
| all | 563 | 100.0% | 327 | 100.0% |  |

### Title family

| Group | Leaders with 1+ raw cell | Share | Leaders with 15+ raw cells | Share | Flag at the cut |
|---|---|---|---|---|---|
| CEO | 188 | 33.4% | 122 | 37.3% |  |
| Other chief officer | 186 | 33.0% | 112 | 34.3% |  |
| Managing director | 105 | 18.7% | 60 | 18.3% |  |
| no title | 46 | 8.2% | 11 | 3.4% | too small to model |
| Other title | 31 | 5.5% | 17 | 5.2% | too small to model |
| President | 5 | 0.9% | <5 | <5 | too small to model |
| Chair | <5 | <5 | <5 | <5 | too small to model |
| Founder | <5 | <5 | <5 | <5 | too small to model |
| all | 563 | 100.0% | 327 | 100.0% |  |

### Sector

| Group | Leaders with 1+ raw cell | Share | Leaders with 15+ raw cells | Share | Flag at the cut |
|---|---|---|---|---|---|
| Financial Services | 81 | 14.4% | 51 | 15.6% |  |
| Healthcare | 50 | 8.9% | 23 | 7.0% |  |
| Business Services | 47 | 8.3% | 33 | 10.1% |  |
| Consumer Goods | 39 | 6.9% | 22 | 6.7% |  |
| FinTech | 32 | 5.7% | 25 | 7.6% |  |
| Food and Agriculture | 31 | 5.5% | 16 | 4.9% | too small to model |
| Chemicals and Materials | 24 | 4.3% | 10 | 3.1% | too small to model |
| Retail | 24 | 4.3% | 13 | 4.0% | too small to model |
| Real Estate and Construction | 22 | 3.9% | 12 | 3.7% | too small to model |
| Energy | 21 | 3.7% | 14 | 4.3% | too small to model |
| Industrial Goods and Manufacturing | 21 | 3.7% | 8 | 2.4% | too small to model |
| Consumer | 15 | 2.7% | 10 | 3.1% | too small to model |
| Enterprise Applications | 15 | 2.7% | 6 | 1.8% | too small to model |
| Conglomerates | 11 | 2.0% | 7 | 2.1% | too small to model |
| Investment Industry | 11 | 2.0% | 7 | 2.1% | too small to model |
| Travel and Hospitality | 11 | 2.0% | <5 | <5 | too small to model |
| Auto | 10 | 1.8% | <5 | <5 | too small to model |
| Environment | 10 | 1.8% | 5 | 1.5% | too small to model |
| HealthTech | 10 | 1.8% | 8 | 2.4% | too small to model |
| Education | 5 | 0.9% | <5 | <5 | too small to model |
| Telecom | 5 | 0.9% | <5 | <5 | too small to model |
| Energy Tech | <5 | <5 | <5 | <5 | too small to model |
| Real Estate and Construction Tech | <5 | <5 | <5 | <5 | too small to model |
| Auto Tech | <5 | <5 | <5 | <5 | too small to model |
| High Tech | <5 | <5 | <5 | <5 | too small to model |
| Mobile | <5 | <5 | <5 | <5 | too small to model |
| Transportation and Logistics | <5 | <5 | <5 | <5 | too small to model |
| Travel and Hospitality Tech | <5 | <5 | <5 | <5 | too small to model |
| Aerospace, Maritime and Defense | <5 | <5 | <5 | <5 | too small to model |
| Aerospace, Maritime and Defense Tech | <5 | <5 | <5 | <5 | too small to model |
| Media & Entertainment | <5 | <5 | <5 | <5 | too small to model |
| Chemicals and Materials Tech | <5 | <5 | <5 | <5 | too small to model |
| EdTech | <5 | <5 | <5 | <5 | too small to model |
| Life Sciences | <5 | <5 | <5 | <5 | too small to model |
| no usable company match | 18 | 3.2% | 7 | 2.1% | too small to model |
| no value | 18 | 3.2% | 12 | 3.7% | too small to model |
| all | 563 | 100.0% | 327 | 100.0% |  |

### Firm size band

| Group | Leaders with 1+ raw cell | Share | Leaders with 15+ raw cells | Share | Flag at the cut |
|---|---|---|---|---|---|
| size band 1 (smallest) | 127 | 22.6% | 76 | 23.2% |  |
| size band 2 | 113 | 20.1% | 59 | 18.0% |  |
| size band 3 | 118 | 21.0% | 76 | 23.2% |  |
| size band 4 (largest) | 136 | 24.2% | 81 | 24.8% |  |
| no usable company match | 18 | 3.2% | 7 | 2.1% | too small to model |
| no value | 51 | 9.1% | 28 | 8.6% |  |
| all | 563 | 100.0% | 327 | 100.0% |  |

## 4. Distribution of cells per leader

Raw cells per leader, for leaders with at least 1 raw cell and for those at the post cut (15). Raw cells stand in for posts until G1 is signed. Quartiles use linear interpolation between neighbouring leaders. The top 10% is the top 10% of leaders by cell count, rounded up to a whole leader. A group with fewer than 5 leaders is hidden across the row, because its min and max would be single leaders' counts.

| Group | Leaders | Raw cells | Min | Q1 | Median | Q3 | Max | Leaders in the top 10% | Share of cells from the top 10% |
|---|---|---|---|---|---|---|---|---|---|
| 1 or more raw cells | 563 | 26,945 | 1 | 6.0 | 21.0 | 66.0 | 257 | 57 | 40.6% |
| 15 or more raw cells | 327 | 25,639 | 15 | 28.0 | 56.0 | 112.0 | 257 | 33 | 26.6% |

## 5. Quality issues already found

Counts only: no names, values, ids or references. Nothing here was corrected, filled in or dropped; the issues are listed so later stages can handle them on purpose. A count below 5 (zero included) shows as "<5". ceo_type counts are over every row of the harmonised table (raw and cleaned text rows), as in reports/ceo_type_gender_counts.md; a value that is neither label is counted, not inspected.

### ceo_type

| Issue | Leaders | Rows |
|---|---|---|
| ceo_type blank | 46 | 34,476 |
| ceo_type neither label (shifted) | <5 | <5 |

### Repeated names

Keys (a normalised name) held by two or more entities in one source list, and keys the id proposal flagged ambiguous.

| Check | Keys |
|---|---|
| sheets | <5 |
| roster | <5 |
| summaries | 9 |
| company | <5 |
| keys flagged ambiguous | 10 |

### Company mismatches

Match kind of each leader against Company_Data (one row per leader), then match rows where the company named in one source differs from the other, per source pair (a leader can appear in more than one row).

| Company_Data match kind | Leaders |
|---|---|
| exact | 554 |
| none | 8 |
| ambiguous | <5 |

| Source pair | Match rows where the company differs |
|---|---|
| sheets to company | <5 |
| sheets to roster | <5 |
| sheets to summaries | <5 |
| roster to summaries | 6 |
| roster to company | <5 |
| summaries to company | <5 |

### Language (Hinglish rows)

Language tag of each cleaned post. Hinglish and other non-English rows are only counted here; nothing is translated or dropped in this section.

| Language | Cleaned posts |
|---|---|
| English | 26,837 |
| mixed | 69 |
| Hinglish | 29 |
| other | 9 |
| Hindi | <5 |
| all | 26,945 |

## 6. Possible selection bias

Who is in the sample compared with Company_Data overall, sector and size mix only. Selection bias is described, not corrected: nothing is reweighted, filled in or dropped here. The study here means leaders with at least one raw post cell and a clear Company_Data match (raw cells stand in for posts until G1 is signed): 545 leaders, against 852 Company_Data firms. 18 further leaders with raw cells have no clear Company_Data match, so they have no sector or size and are in neither table. Firm size bands are cut once over all Company_Data rows, so both sides use the same bands. Every firm in Company_Data is listed, so listed vs unlisted cannot be compared. The differences say who is in the sample, nothing about how leaders present themselves. A count below 5 (zero included) shows as "<5", with its share and difference.

### Sector

| Group | Study leaders | Study share | Company_Data firms | Company_Data share | Difference (points) |
|---|---|---|---|---|---|
| Financial Services | 81 | 14.9% | 115 | 13.5% | +1.4 |
| Business Services | 47 | 8.6% | 73 | 8.6% | +0.1 |
| Healthcare | 50 | 9.2% | 68 | 8.0% | +1.2 |
| Consumer Goods | 39 | 7.2% | 55 | 6.5% | +0.7 |
| Food and Agriculture | 31 | 5.7% | 54 | 6.3% | -0.6 |
| FinTech | 32 | 5.9% | 48 | 5.6% | +0.2 |
| Chemicals and Materials | 24 | 4.4% | 44 | 5.2% | -0.8 |
| Industrial Goods and Manufacturing | 21 | 3.9% | 39 | 4.6% | -0.7 |
| Energy | 21 | 3.9% | 37 | 4.3% | -0.5 |
| Retail | 24 | 4.4% | 35 | 4.1% | +0.3 |
| Real Estate and Construction | 22 | 4.0% | 33 | 3.9% | +0.2 |
| Consumer | 15 | 2.8% | 31 | 3.6% | -0.9 |
| Auto | 10 | 1.8% | 21 | 2.5% | -0.6 |
| Enterprise Applications | 15 | 2.8% | 21 | 2.5% | +0.3 |
| Conglomerates | 11 | 2.0% | 14 | 1.6% | +0.4 |
| Environment | 10 | 1.8% | 14 | 1.6% | +0.2 |
| Investment Industry | 11 | 2.0% | 14 | 1.6% | +0.4 |
| Travel and Hospitality | 11 | 2.0% | 14 | 1.6% | +0.4 |
| HealthTech | 10 | 1.8% | 13 | 1.5% | +0.3 |
| Telecom | 5 | 0.9% | 11 | 1.3% | -0.4 |
| Real Estate and Construction Tech | <5 | <5 | 7 | 0.8% | <5 |
| Transportation and Logistics | <5 | <5 | 7 | 0.8% | <5 |
| EdTech | <5 | <5 | 6 | 0.7% | <5 |
| Education | 5 | 0.9% | 6 | 0.7% | +0.2 |
| High Tech | <5 | <5 | 6 | 0.7% | <5 |
| Energy Tech | <5 | <5 | 5 | 0.6% | <5 |
| Semiconductors | <5 | <5 | 5 | 0.6% | <5 |
| Aerospace, Maritime and Defense | <5 | <5 | <5 | <5 | <5 |
| Food and Agriculture Tech | <5 | <5 | <5 | <5 | <5 |
| Media & Entertainment | <5 | <5 | <5 | <5 | <5 |
| Mobile | <5 | <5 | <5 | <5 | <5 |
| Aerospace, Maritime and Defense Tech | <5 | <5 | <5 | <5 | <5 |
| Auto Tech | <5 | <5 | <5 | <5 | <5 |
| Travel and Hospitality Tech | <5 | <5 | <5 | <5 | <5 |
| Chemicals and Materials Tech | <5 | <5 | <5 | <5 | <5 |
| Mining | <5 | <5 | <5 | <5 | <5 |
| Environment Tech | <5 | <5 | <5 | <5 | <5 |
| Life Sciences | <5 | <5 | <5 | <5 | <5 |
| no value | 18 | 3.3% | 25 | 2.9% | +0.4 |
| all | 545 | 100.0% | 852 | 100.0% |  |

### Firm size (employees)

| Group | Study leaders | Study share | Company_Data firms | Company_Data share | Difference (points) |
|---|---|---|---|---|---|
| size band 1 (smallest) | 127 | 23.3% | 194 | 22.8% | +0.5 |
| size band 2 | 113 | 20.7% | 193 | 22.7% | -1.9 |
| size band 3 | 118 | 21.7% | 195 | 22.9% | -1.2 |
| size band 4 (largest) | 136 | 25.0% | 191 | 22.4% | +2.5 |
| no value | 51 | 9.4% | 79 | 9.3% | +0.1 |
| all | 545 | 100.0% | 852 | 100.0% |  |
