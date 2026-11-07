# FP15: Leaders and Social Media

ILGC-3 project, Plaksha University.

**Question.** How do Indian corporate leaders present themselves in LinkedIn posts, and does the presentation differ by leader profile (Founder-CEO vs Professional CEO, title family, gender, sector, firm size, tenure)?

**Claim limit.** Every claim is about the image projected in public posts. Nothing here measures or labels a leader's personality. An I-rate (share of first-person singular words) is one signal, not a narcissism score.

## What is in this repository, and what is not

This repository holds code, tests, configuration, decisions and **count-only reports**. It does not hold the data.

- `data/raw/` (the post workbooks and `Company_Data.xlsx`) is git-ignored. Only the hash manifest `data/raw/MANIFEST.sha256` is tracked.
- `data/interim/` and `data/derived/*.csv` are git-ignored. They can hold names, post text and post links.
- Reports in `reports/` contain counts, column headers, pseudonymous `leader_id` values and file or sheet indexes. They contain no leader names, company names, cell values or post text.
- No scraping or network download of post data is done or approved. The study covers the Indian corporate leaders already in the data.

To reproduce the numbers you need the raw files from the project team; they are not published here.

## Setup

```bash
python3.11 -m venv .venv
.venv/bin/pip install -e ".[dev]"
```

Place the raw files under `data/raw/` (read-only). The first run hashes them into `data/raw/MANIFEST.sha256`; every later run verifies that hash and stops if anything changed.

## How to run

One make target per stage. Scripts produce every result; there are no notebooks.

| Target | What it does | Output |
|---|---|---|
| `make verify` | Checks the raw hash manifest (writes it on first run) | none |
| `make inventory` | Lists files, sheets, header layouts and row counts | `reports/data_inventory.md` |
| `make ingest` | Harmonises the post sheets and profiles Company_Data (email and phone columns dropped at load) | `reports/harmonise_summary.md`, `reports/company_data_profile.md` |
| `make ids` | Proposes `leader_id` matches across the roster, summaries and Company_Data; ambiguous names are not auto-resolved | `reports/id_matching.md` |
| `make reaction-check` | Counts trailing-number shapes in raw posts and draws a 50-cell hand-check sample | `reports/reaction_count_check.md` |
| `make extra-features` | Proposes which text features can be computed reliably, with failure examples | `reports/extra_features.md` |
| `make company-columns` | Proposes the 20 most useful Company_Data columns and their fill share for leaders with 15+ posts | `reports/company_columns.md` |
| `make segment` | Splits cells into author blocks and cleans them. **Not written yet.** | none |
| `make test` | Runs the test suite | none |
| `make all` | Runs the stages above in order | all reports |

Tests: `.venv/bin/python -m pytest -q --cov=src --cov-report=term-missing`.

## Status

Done: raw hash check, inventory, harmonising, Company_Data loading, `leader_id` proposal, reaction-count check, extra text features, Company_Data column proposal.

Not started: segmentation (author blocks), the three measurement layers, gold set, models. See `docs/decisions.md`.

Known caveats, all logged under Findings in `docs/decisions.md`:

- `reports/harmonise_summary.md` and `reports/id_matching.md` still print the earlier count of 544 leaders. That figure counts leaders with at least one self-authored post, which needs segmentation, so it is not comparable with the 563 to 567 raw-cell counts. Do not compare them.
- The 15-post minimum is currently applied to raw post cells, a cell-level proxy, until author blocks exist.
- Several Company_Data numeric columns are text with bracketed notes or capped values (for example "500+"). The Step C report shows how many cells read as numbers.
- `leader_id` is an unsalted hash of a normalised name, so it is a pseudonym, not anonymisation.

## Method in one paragraph

Three measurement layers: dictionaries and counts; embeddings, topics and classifiers; and an LLM judge on about 2,800 posts, validated on a 300-post gold set. Empirical Bayes shrinkage from post to leader. Mixed models with posts nested in leaders, Benjamini-Hochberg FDR, a robustness multiverse, and pre-registered hypotheses. Main trait measures are Northouse's five: intelligence, self-confidence, determination, integrity and sociability. Other measures are exploratory and only built if the mentors approve.

## Gates

A human sign-off line in `docs/decisions.md` is required before work moves past each gate. Code never signs one off.

| Gate | Check |
|---|---|
| G1 | Segmentation: 95% accuracy on 200 random cells |
| G2 | Measures against the gold set (Krippendorff alpha 0.67 or higher) |
| G3 | Pre-registration locked with a dated hash |
| G4 | Clean rebuild of every table and figure from raw files |

The gold set stays closed while dictionaries are built. Every threshold lives in `configs/thresholds.yaml` and nowhere else.

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
