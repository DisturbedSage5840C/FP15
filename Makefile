PY ?= .venv/bin/python

.PHONY: verify inventory ingest ids reaction-check extra-features company-columns segment test all
verify:   ## check raw hash manifest (writes it on first run)
	$(PY) -m src.verify_raw
inventory: ## write reports/data_inventory.md (files, sheets, header layouts, row counts)
	$(PY) -m src.inventory
ingest:   ## harmonise sheets and profile Company_Data (contact columns dropped at load)
	$(PY) -m src.harmonise
	$(PY) -m src.company_data
ids:      ## build leader_id table across the three people lists
	$(PY) -m src.ids
reaction-check: ## count trailing-number shapes in raw posts and draw the hand-check sample (data/derived, git-ignored)
	$(PY) -m src.reaction_count_check
extra-features: ## propose which text features are reliable and list cells the rules handle badly (reports/extra_features.md)
	$(PY) -m src.extra_features
company-columns: ## propose the 20 most useful Company_Data columns and their fill share for leaders with 15+ posts (reports/company_columns.md)
	$(PY) -m src.company_columns
segment:  ## split cells into author blocks and clean
	$(PY) -m src.segment
test:
	$(PY) -m pytest -q
all: verify inventory ingest ids reaction-check extra-features company-columns segment test
