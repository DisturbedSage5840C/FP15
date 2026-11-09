# Dedupe characterisation: groups whose texts differ in content

Counts only; no names, ids, links or text. These are the groups the looser harmonise key collapsed although the
raw texts are not the same after ignoring spacing, case and punctuation (see `reports/dedup_check.md`).

| Measure | Count |
|---|---|
| Content-different groups | 3608 |
| Rows those groups held | 15954 |

## Group size (rows per group)

| Rows in group | Groups |
|---|---|
| 2 | 1589 |
| 3 | 89 |
| 4 | 1739 |
| 5 or more | 191 |

## Link type

From the domain and path pattern only; no link is opened. No link means the group was keyed on the first 200
characters of text.

| Link type | Groups |
|---|---|
| linkedin_post | 2991 |
| linkedin_profile_or_company | 0 |
| linkedin_other_path | 0 |
| other_domain | 2 |
| no_link | 615 |

## How the texts differ

Tried in this order, first match wins: only the trailing number or age line differs (trailing_only); the
shortest text is the start of every other (prefix); identical after removing the first N lines, N up to 5
(first_lines); anything else (other).

| Difference | Groups |
|---|---|
| trailing_only | 23 |
| prefix | 182 |
| first_lines | 0 |
| other | 3403 |
