PY ?= .venv/bin/python

.PHONY: check-key verify inventory ingest ids leader-table handcheck reaction-check extra-features company-columns company-numeric post-cleaning segmentation-sample hinglish-check dedup-check dedup-characterise segmentation-score test all
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
post-cleaning: check-key ## dedupe, clean interface lines into a new column, parse age and language (reports/post_cleaning.md)
	$(PY) -m src.post_cleaning
segmentation-sample: check-key ## draw the 200-cell blind check sample for the human (data/derived, git-ignored); never overwrites it
	$(PY) -m src.segment
hinglish-check: check-key ## draw 30 flagged cells for the human precision check (data/derived, git-ignored); never overwrites it
	$(PY) -m src.hinglish_check
dedup-check: check-key ## count what the looser dedupe key collapsed (reports/dedup_check.md); changes nothing
	$(PY) -m src.dedup_check

dedup-characterise: check-key ## describe the content-different groups: size, link type, how texts differ (reports/dedup_characterisation.md)
	$(PY) -m src.dedup_characterise
segmentation-score: ## compare the human counts with the segmenter (reports/segmentation_check.md); does NOT sign off G1; not part of make all
	$(PY) -m src.segment_score
test:
	$(PY) -m pytest -q
all: check-key verify inventory ingest ids leader-table handcheck reaction-check extra-features company-columns company-numeric post-cleaning segmentation-sample test
