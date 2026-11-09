# Dedupe check: what the looser key collapsed

Counts only; no names, ids or text. The harmonise step keeps the first row of each group that shares
(leader, link) or, with no link, (leader, first 200 characters of text). This compares the full raw texts inside
each group of two or more rows. Nothing is changed by this check.

| Measure | Count |
|---|---|
| Rows before the looser key | 63773 |
| Groups with more than one row | 6737 |
| Rows collapsed by the looser key | 15662 |

Groups are labelled by their largest difference: identical (same raw text), spacing (same after collapsing
whitespace), case (same after also ignoring case), punctuation (same after also ignoring punctuation), content
(anything else).

| Label | Groups | Rows collapsed |
|---|---|---|
| identical | 3128 | 3315 |
| spacing | 0 | 0 |
| case | 0 | 0 |
| punctuation | 1 | 1 |
| content | 3608 | 12346 |

Groups labelled content, by key type: link 2993, text head 615.
Of the content groups, 184 are cases where the shorter text is the start of the longer one.
