# Scraping and expansion: specification for discussion (NOT approved)

**Status: nothing in this file is approved and nothing has been built.** No scraper exists in this repo, no
network call is made, and `scraping_approved` in `configs/thresholds.yaml` is `false`. The team asked the course mentors for
three things. Until they approve in writing, the study covers the Indian corporate leaders already in the data
(CLAUDE.md, "Data rules"). This file says what each request would add, how it would be checked, and what he has to
answer first.

## What is in the code today

| Guard | Where | What it does |
|---|---|---|
| Flag `scraping_approved: false` | `configs/thresholds.yaml` | A human switch. Only a person changes it, after written approval. |
| Static scan | `tests/test_no_network.py` | Fails if any module in `src/` imports a network library or calls `urlopen`, `create_connection`, `getaddrinfo` or `gethostbyname` while the flag is false. |
| Runtime guard | `tests/conftest.py` | While the flag is false, any test that resolves a host or opens a socket fails with a message naming the flag. |

Setting the flag to `true` turns both guards off. That is a decision for the course mentors, recorded in
`docs/decisions.md` with a date, not a code change.

## The three requests

### 1. Likes, reposts and followers

**Would add.** Engagement per post, and audience size per leader.

| Table | Column | Type | Note |
|---|---|---|---|
| `post_engagement` | `leader_id` | text | Keyed id only, never a name. |
| | `post_ref` | text | Workbook, sheet index and row of the existing cell, plus the position within the cell once segmentation is signed off. |
| | `scrape_date` | date | Required. Without it a relative age cannot be turned into a date. |
| | `likes`, `reposts`, `comments` | integer or blank | Blank when not shown. Never zero-filled. |
| | `reactions_total` | integer or blank | Only if the route reports it. |
| | `source_route` | text | Which collection route produced the row (see open questions). |
| `leader_audience` | `leader_id`, `scrape_date` | | One row per leader per date. |
| | `followers` | integer or blank | Parsed by the same function as other counts (`1.2K`, `3M`). |

**How it would be checked against the existing data.**
- Re-collect a random sample of posts that already carry a trailing count in the workbooks. Compare the new count
  with the old one. Report the exact-agreement rate and the size of the gaps; counts grow over time, so a gap is
  expected and its direction is itself a check.
- This is also the first real test of the reaction-count shape rule. The human comparison from Step A is still
  outstanding (`reaction_check_confirmed: false`).
- Followers: no existing column to compare with. Check for plausibility (non-negative integer, orders of magnitude
  by title family) and re-collect a sample on a second day.

### 2. Foreign leaders

**Would add.** Leaders outside the Indian corporate set, as new rows with the same original variables.

| Column | Note |
|---|---|
| `leader_name`, `company_name`, `current_title`, `role_start_year`, `ceo_type`, `platform`, `post_date`, `post_date_text` | The original variables, per the data owner. |
| `country` | New. Needed to keep the Indian and foreign groups apart in every table. |
| Company fields | `Company_Data.xlsx` covers Indian firms only. Foreign firms need a new, documented source for sector, size and listing. Currency and fiscal year must be recorded, not assumed. |

**How it would be checked.**
- The same `leader_id` keying and the same manifest hash for any new raw files.
- No overlap with existing leaders: match on the name key and report the count.
- Coding rules for `ceo_type`, title family and gender written down before any row is coded. Gender stays as coded
  by the source, never inferred from names.
- Compare distributions with the Indian set (posts per leader, post length, language flag) and report the gaps
  rather than pooling silently.

**Scope effect.** The research question is about Indian corporate leaders. Adding a foreign group changes the
question to a comparison and, if G3 (pre-registration) is already locked, needs a dated amendment.

### 3. The empty original columns

`role_start_year`, `post_date` and `post_date_text` are empty in the workbooks seen so far
(CLAUDE.md, "Data rules"). Check which are filled in each workbook and report; never fill by guessing.

**Would add.** Values for those columns, from a named source.

| Column | Possible source (for the course mentors to choose) | Check |
|---|---|---|
| `role_start_year` | Company filings or a profile the team is allowed to read | Second coder on a random sample; report agreement. |
| `post_date`, `post_date_text` | Collection with a recorded `scrape_date` | Compare with the parsed relative age in months. The label rounds, so the allowed gap has to be measured, not assumed. |

Until then the study uses the relative age in months and does not turn it into a date.

## Open questions the course mentors must answer

1. **Collection route.** An official API, a platform data export the leaders or firms consent to, a licensed
   vendor, a manual copy by team members, or automated scraping? Each has different legal and ethical weight.
2. **LinkedIn terms of use.** What do the current terms say about automated collection and research use? Who at
   Plaksha reviews that, and in writing?
3. **Consent and ethics.** Does the study need ethics-committee approval for this data? The posts are public, but
   the people are named individuals and the finding is about how they present themselves. Is any notification or
   opt-out expected? Which data-protection rules apply to Indian and to foreign leaders?
4. **Storage.** Where may collected data live, who may access it, and does the public-repo rule stay as it is:
   no names, post text, links or reversible ids ever committed?
5. **Retention.** How long is collected data kept, and when is it deleted? What happens to derived tables?
6. **Scope and timing.** Is the expansion before or after the pre-registration lock (G3)? Who signs off?
7. **Budget and limits.** Rate limits, cost of a vendor, and a stop rule if the platform objects.

## What would happen after written approval

Not started. In order: record the approval and the answers in `docs/decisions.md`; set the flag; write the
collection stage with the manifest check, keyed ids and the schemas above; run it on a small sample first and
compare with the existing data as described; then widen. Each step gets its own tests and a human sign-off line.
