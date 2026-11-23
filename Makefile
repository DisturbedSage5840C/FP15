PY ?= .venv/bin/python

.PHONY: check-key verify inventory ingest ids leader-table handcheck reaction-check extra-features company-columns company-numeric ceo-gender-counts post-cleaning segmentation-sample segmentation-sample-report hinglish-check dedup-check dedup-characterise segmentation-score segmentation-viewer eda eda-variables gold-set-audit outcome-feasibility test test-stats dict-measures-test judge-io-test provisional-measures provisional-leaders all
check-key: ## fail with a clear message unless FP15_ID_KEY is set (environment or git-ignored .env); the value is never shown
	$(PY) -m src.id_key
verify:   ## check raw hash manifest (writes it on first run)
	$(PY) -m src.verify_raw
inventory: ## write reports/data_inventory.md (files, sheets, header layouts, row counts)
	$(PY) -m src.inventory
ingest:   ## harmonise sheets and profile Company_Data (contact columns dropped at load)
	$(PY) -m src.harmonise
	$(PY) -m src.company_data
ids: check-key ## build the keyed leader_id table across the three people lists
	$(PY) -m src.ids
leader-table: check-key ## base list of leaders with posts, enriched from roster, summaries and Company_Data (reports/leader_table.md)
	$(PY) -m src.leader_table
handcheck: check-key ## list ambiguous, unmatched and mismatched Company_Data names with candidates (data/derived/handcheck_names.csv, git-ignored)
	$(PY) -m src.handcheck_names
reaction-check: check-key ## count trailing-number shapes in raw posts and draw the hand-check sample (data/derived, git-ignored)
	$(PY) -m src.reaction_count_check
extra-features: check-key ## propose which text features are reliable and list cells the rules handle badly (reports/extra_features.md)
	$(PY) -m src.extra_features
company-columns: ## propose the 20 most useful Company_Data columns and their fill share for leaders with 15+ posts (reports/company_columns.md)
	$(PY) -m src.company_columns
company-numeric: ## numeric LatestRevenueUSD, NumberofEmployees and ProfitUSD2024 (reports/company_numeric.md)
	$(PY) -m src.company_numeric
ceo-gender-counts: ## ceo_type split per leader and Company_Data Gender counts as coded (reports/ceo_type_gender_counts.md); counts only
	$(PY) -m src.ceo_gender_counts
post-cleaning: check-key ## dedupe, clean interface lines into a new column, parse age and language (reports/post_cleaning.md)
	$(PY) -m src.post_cleaning
segmentation-sample: check-key ## draw the 200-cell blind check sample for the human (data/derived, git-ignored); never overwrites it
	$(PY) -m src.segment
segmentation-sample-report: check-key ## counts and seed of the G1 sample (reports/segmentation_sample.md); no refs, ids or text; does NOT sign off G1
	$(PY) -m src.segment_sample_report
hinglish-check: check-key ## draw 30 flagged cells for the human precision check (data/derived, git-ignored); never overwrites it
	$(PY) -m src.hinglish_check
dedup-check: check-key ## count what the looser dedupe key collapsed (reports/dedup_check.md); changes nothing
	$(PY) -m src.dedup_check

dedup-characterise: check-key ## describe the content-different groups: size, link type, how texts differ (reports/dedup_characterisation.md)
	$(PY) -m src.dedup_characterise
segmentation-score: ## compare the human counts with the segmenter (reports/segmentation_check.md); does NOT sign off G1; not part of make all
	$(PY) -m src.segment_score
segmentation-viewer: check-key ## private n -> name lookup and the local G1 counting page (data/derived, git-ignored, holds names); counts nothing, does NOT sign off G1; not part of make all
	$(PY) -m src.segment_viewer
eda: ## limits of the data we already have, counts only (reports/eda_limitations.md); "<5" under the disclosure minimum; no scraping, no gate signed
	$(PY) -m src.eda
eda-variables: ## every variable we hold, its source, study role and fill rate, with a check against the write-up numbers (reports/eda_variable_map.md); counts only; no scraping, no gate signed
	$(PY) -m src.eda_variables
gold-set-audit: ## gold-set sampler run on invented tables shaped like ours (reports/gold_set_sampler_audit.md); synthetic only, counts only; draws nothing real; not part of make all
	$(PY) -m src.gold_set_audit
outcome-feasibility: ## which firm-outcome measures Company_Data can give (reports/outcome_feasibility.md); counts only; no scraping, no gate signed; not part of make all
	$(PY) -m src.outcome_feasibility
test:
	$(PY) -m pytest -q
dict-measures-test: ## tests for the dictionary-layer scoring code and its slot config; invented sentences only; no real data, no download; not part of make all
	$(PY) -m pytest -q tests/test_dict_measures.py tests/test_dictionaries_config.py
judge-io-test: ## tests for the LLM-judge plumbing (request, reply check, batch) with a fake client; invented sentences only; no network, no real call; not part of make all
	$(PY) -m pytest -q tests/test_judge_io.py
provisional-measures: check-key verify ## PROVISIONAL per-post pronoun rates for every cleaned cell (data/derived/provisional_post_measures.csv, git-ignored, ids and numbers only); exploratory, G1 unsigned; not part of make all
	$(PY) -m src.provisional_measures
provisional-leaders: check-key verify ## PROVISIONAL leader-level mean rates, shrunk from post to leader (data/derived/provisional_leader_measures.csv, git-ignored; reports/provisional_leader_measures.md, aggregates only, "<5" under the minimum); exploratory, G1 unsigned; not part of make all
	$(PY) -m src.provisional_leaders
test-stats: ## tests for the statistics tools only (agreement, gold-set sampler, shrinkage and BH, and the thresholds loader they share); synthetic data only; not part of make all
	$(PY) -m pytest -q tests/test_thresholds.py tests/test_agreement.py tests/test_gold_set.py tests/test_stats_tools.py
all: check-key verify inventory ingest ids leader-table handcheck reaction-check extra-features company-columns company-numeric ceo-gender-counts post-cleaning segmentation-sample segmentation-sample-report eda eda-variables test
