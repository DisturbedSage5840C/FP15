# FP15: Leaders and Social Media (ILGC-3, Plaksha University)

Read this at the start of every session. Rules here are the only copy; do not restate them elsewhere.

## The question and the claim limit
How do Indian corporate leaders present themselves in LinkedIn posts, and does the presentation differ by leader profile (Founder-CEO vs Professional CEO, title family, gender, sector, firm size, tenure)?
Every claim is about the image projected in public posts. Never write "personality", "is narcissistic" or similar. An I-rate (first-person singular share) is one signal, not a narcissism score.

## Data rules
- data/raw is read-only. Never edit, move or delete anything in it. Hash it in data/raw/MANIFEST.sha256 on first run and verify the hash at the start of every pipeline run.
- No scraping and no network downloads of new post data. The team has asked the course mentors to allow scraping of likes, reposts and followers and to add foreign leaders. None of that is approved. Until he approves in writing, nobody scrapes anything and the study covers the Indian corporate leaders already in the data.
- Original variables (per the data owner): leader_name, company_name, current_title, role_start_year, ceo_type, platform, post_date, post_date_text. In the workbooks seen so far role_start_year and post_date are empty. Check which are filled in each workbook and report; never fill them in by guessing.
- Posts are nested in leaders. Analysis files carry leader_id only, never names. Raw post text is not pasted into chat, issues or public places.
- Any LLM call sends only post text and an ID, with no-training settings on where the provider offers them.
- Company_Data.xlsx: drop every email and phone column at load, before anything is written to disk. Treat "." and "-" as blank. Values like "186.6M" and "2.5B" are parsed in one function. Gender is used exactly as coded in the file until the mentors confirm what 1 and 0 mean. Never infer gender from names. Every firm in it is listed, so listed vs unlisted cannot be tested.
- Missing stays missing. Nothing is guessed.

## Thresholds (live in configs/thresholds.yaml only)
15 posts minimum for the main analysis; 95% segmentation accuracy on 200 hand-checked cells; Krippendorff alpha 0.67 or higher on the 300-post gold set; dictionary-to-human correlation about 0.4.

## Gates (a human sign-off line in docs/decisions.md is required before work moves past each)
- G1 segmentation: 95% on 200 random cells.
- G2 measures against the gold set.
- G3 pre-registration locked with a dated hash.
- G4 clean rebuild of every table and figure from raw files.
The gold set stays closed while dictionaries are built.

## Method in one paragraph
Three measurement layers: dictionaries and counts; embeddings, topics and classifiers; an LLM judge on about 2,800 posts, validated on the gold set. Empirical Bayes shrinkage from post to leader. Mixed models with posts nested in leaders, Benjamini-Hochberg FDR, a robustness multiverse, pre-registered hypotheses.
Main trait measures are Northouse's five (intelligence, self-confidence, determination, integrity, sociability). Business knowledge, desire to lead and a task-versus-relational pair are exploratory and only built if the mentors approve.

## How to run
One make target per stage (see Makefile). `make all` rebuilds every table and figure from raw files. Scripts, not notebooks, for anything that produces a result. Every stage has tests in tests/.

## Working rules
- The repo is the source of truth for code and numbers. Any decision that changes results is written in docs/decisions.md with a date.
- Do not decide what a construct means, code gold-set posts, or sign off a gate. Those are human jobs. Stop and ask.
- Small commits, one stage at a time. Report numbers as committed files in reports/, not pasted from memory.
- If something in the data surprises you, write it in docs/decisions.md under "Findings" and say so; do not quietly fix it.
