# FP15: Leaders and Social Media

ILGC-3 project, Plaksha University.

**Question.** How do Indian corporate leaders present themselves in LinkedIn posts, and does the presentation differ by leader profile (Founder-CEO vs Professional CEO, title family, gender, sector, firm size, tenure)?

**Claim limit.** Every claim is about the image projected in public posts. Nothing here measures or labels a leader's personality. An I-rate (share of first-person singular words) is one signal, not a narcissism score.

## What is in this repository, and what is not

This repository holds code, tests, configuration, decisions and **count-only reports**. It does not hold the data.

- `data/raw/` (the post workbooks and `Company_Data.xlsx`) is git-ignored. Only the hash manifest `data/raw/MANIFEST.sha256` is tracked.
- `data/interim/` and `data/derived/*.csv` are git-ignored. They can hold names, post text and post links.
- Reports in `reports/` contain counts, column headers and file or sheet indexes. They contain no leader names, company names, cell values, post text or `leader_id` values.
- The repo is public. No names, post text, links or reversible ids may ever be committed.
- No scraping or network download of post data is done or approved. The study covers the Indian corporate leaders already in the data. `scraping_approved` in `configs/thresholds.yaml` is a human switch and stays `false` until the course mentors approve in writing; `tests/test_no_network.py` fails if pipeline code reaches the network while it is false. What was asked and what must be answered first: `docs/scraping_spec.md`.

To reproduce the numbers you need the raw files from the project team; they are not published here.

## Setup

```bash
python3.11 -m venv .venv
.venv/bin/pip install -e ".[dev]"
```

Place the raw files under `data/raw/` (read-only). The first run hashes them into `data/raw/MANIFEST.sha256`; every later run verifies that hash and stops if anything changed.

Set the secret that keys `leader_id`. It lives in the `FP15_ID_KEY` environment variable or in a git-ignored `.env` file (`FP15_ID_KEY=<long random string>`), never in the repo. Keep the same key across runs, or ids change. `make check-key` fails with a clear message when it is missing and never prints the value.

## How to run

One make target per stage. Scripts produce every result; there are no notebooks.

| Target | What it does | Output |
|---|---|---|
| `make check-key` | Fails with a clear message unless the `leader_id` key is set; the value is never shown | none |
| `make verify` | Checks the raw hash manifest (writes it on first run) | none |
| `make inventory` | Lists files, sheets, header layouts and row counts | `reports/data_inventory.md` |
| `make ingest` | Harmonises the post sheets and profiles Company_Data (email and phone columns dropped at load) | `reports/harmonise_summary.md`, `reports/company_data_profile.md` |
| `make ids` | Proposes `leader_id` matches across the roster, summaries and Company_Data; ambiguous names are not auto-resolved | `reports/id_matching.md` |
| `make leader-table` | Builds the base list of leaders who have posts and looks each one up in the roster, summaries and Company_Data; names found only in those lists are counted, not resolved | `reports/leader_table.md` |
| `make leader-master` | Builds the retained union of post sheets, roster, summaries and Company_Data. Shared roster or summary keys are flagged rather than dropped; internally shared post or Company_Data keys remain distinct entries. | `reports/leader_master.md` |
| `make handcheck` | Lists the leaders whose Company_Data match is ambiguous, missing or has a different company, with candidate rows side by side and empty decision columns for a human | `data/derived/handcheck_names.csv` (git-ignored; holds names) |
| `make company-numeric` | Numeric versions of LatestRevenueUSD, NumberofEmployees and ProfitUSD2024 (bracketed columns are not parsed); flags bare-number profit cells whose scale is unstated | `data/interim/company_numeric.csv` (git-ignored), `reports/company_numeric.md` |
| `make reaction-check` | Counts trailing-number shapes in raw posts and draws a 50-cell hand-check sample | `reports/reaction_count_check.md` |
| `make extra-features` | Proposes which text features can be computed reliably, with failure examples | `reports/extra_features.md` |
| `make company-columns` | Proposes the 20 most useful Company_Data columns and their fill share for leaders with 15+ posts | `reports/company_columns.md` |
| `make post-cleaning` | Drops exact duplicate cells within a leader, removes applied interface lines into a NEW column, parses relative age to months (not a date), flags language (script, plus a possible-Hinglish word-list rule for Hindi in Latin letters), and marks reaction counts `unverified` until a human confirms Step A | `data/interim/posts_clean.csv` and `data/derived/interface_candidates.csv` (git-ignored), `reports/post_cleaning.md` |
| `make hinglish-check` | Draws up to 30 cells flagged `Hinglish` into a git-ignored file with an empty `human_right` column for the precision check; never overwrites an existing file. |
| `make segmentation-sample` | Draws the blind 200-cell sample (one cell per leader) with empty human columns; never overwrites an existing sample. The segmenter counts a repost or embedded post as one post by the leader (`is_repost`, embedded text kept out of the leader voice). It is NOT run on all cells until the sample is confirmed | `data/derived/segmentation_check_200.csv` (git-ignored) |
| `make segmentation-score` | Compares the human counts with the segmenter. Reports a fact, does not sign off G1. Not part of `make all` | `reports/segmentation_check.md` |
| `make segmentation-viewer` | Writes a private `n` to leader and company lookup and copies a single-file offline counting page, so the human can do the G1 hand count one cell at a time. Counts nothing, holds no segmenter count, never touches the live sample. Not part of `make all` | `data/derived/segmentation_check_200_names.csv`, `data/derived/segmentation_counter.html` (both git-ignored; the names file holds names) |
| `make gold-set-draw` | Draws the provisional Option A 300-post gold set. The ids and post text stay in a git-ignored file; the report has counts only. | `reports/gold_set_draw.md` |
| `make provisional-measures` | Computes provisional English-only I-rate and we-rate per cleaned cell. | `data/derived/provisional_post_measures.csv` (git-ignored) |
| `make provisional-leaders` | Produces provisional shrunk leader summaries for all cells and without possible-Hinglish cells. | `reports/provisional_leader_measures.md` |
| `make provisional-compare` | Runs provisional Step 14C group comparisons. | `reports/provisional_comparisons.md` |
| `make provisional-multiverse` | Runs the provisional Step 14D robustness grid for the without-sector comparisons. | `reports/provisional_multiverse.md` |
| `make code-goldset-ai` | Runs AI-1 coding of the opened gold set twice per post, with cache and a human template. Requires `OPENAI_API_KEY`; it fails before sending text when that credential is absent. | Git-ignored `data/interim/goldset_AI1.csv`, cache and human template |
| `make report-goldset-ai` | Renders the counts-only AI-1 coding report after the AI-1 file exists. | `reports/goldset_ai_coding.md` |
| `make test` | Runs the test suite | none |
| `make all` | Runs the stages above in order | all reports |

Tests: `.venv/bin/python -m pytest -q --cov=src --cov-report=term-missing`.

## Status

Done: raw hash check, inventory, harmonising, Company_Data loading, `leader_id` proposal, the retained leader master, reaction-count check, extra text features, Company_Data profiling, post cleaning, and the provisional dictionary, leader, comparison and robustness-multiverse stages. The Option A 300-post gold set has been drawn.

Pending: human confirmation of segmentation; human coding of the gold set; validation of measures; pre-registration; and G1--G4 sign-offs. The AI-1 gold-set coding workflow is implemented and tested, but live coding and its report wait for a configured `OPENAI_API_KEY`; no scores have been invented. See `docs/decisions.md`.

Known caveats, all logged under Findings in `docs/decisions.md`:

- Counts have different units. The leader master identifies 564 leaders represented in post sheets, while the Option A gold-set pool has 563 leaders with at least one non-empty cleaned cell. Neither is a count of confirmed self-authored posts, because segmentation remains unsigned. Do not treat these as interchangeable denominators.
- The 15-post minimum is currently applied to raw post cells, a cell-level proxy, until author blocks exist.
- Several Company_Data numeric columns are text with bracketed notes or capped values (for example "500+"). The Step C report shows how many cells read as numbers.
- `leader_id` is a keyed HMAC of a normalised name. It is a pseudonym, not anonymisation, and it stays reversible by anyone who holds the key. Commits dc458bb, fe919e2 and 94b4812 still hold example ids from the earlier unsalted scheme in `reports/extra_features.md`; see the history entry in `docs/decisions.md`.

## Method in one paragraph

Three measurement layers: dictionaries and counts; embeddings, topics and classifiers; and an LLM judge on about 2,800 posts, validated on a 300-post gold set. Empirical Bayes shrinkage from post to leader. Mixed models with posts nested in leaders, Benjamini-Hochberg FDR, a robustness multiverse, and pre-registered hypotheses. Main trait measures are Northouse's five: intelligence, self-confidence, determination, integrity and sociability. Other measures are exploratory and only built if the mentors approve.

## Gates

A human sign-off line in `docs/decisions.md` is required before work moves past each gate. Code never signs one off.

| Gate | Check |
|---|---|
| G1 | Segmentation: 95% accuracy on 200 random cells |
| G2 | PENDING (human): measures against the gold set, including Krippendorff alpha 0.67 or higher |
| G3 | Pre-registration locked with a dated hash |
| G4 | Clean rebuild of every table and figure from raw files |

The gold set was opened only for provisional AI-assisted coding after the dictionaries were built; it cannot be used to tune them. Human re-coding remains required before G2. Every threshold lives in `configs/thresholds.yaml` and nowhere else.

## Layout

- `CLAUDE.md`: project rules, read at the start of every working session
- `configs/thresholds.yaml`: every pass mark and sampling setting
- `docs/decisions.md`: dated decisions, findings and gate sign-offs
- `docs/FIRST_PROMPT.md`: the original project brief
- `src/`: one module per stage
- `tests/`: tests for every stage
- `reports/`: committed, count-only reports (the source of truth for numbers)
- `data/`: raw, interim and derived data (git-ignored except the manifest)

## Licence

No licence has been chosen yet. Until one is added, all rights are reserved by the authors even though the repository is visible.
