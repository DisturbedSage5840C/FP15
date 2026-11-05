PY ?= .venv/bin/python

.PHONY: verify inventory ingest ids segment test all
verify:   ## check raw hash manifest (writes it on first run)
	$(PY) -m src.verify_raw
inventory: ## write reports/data_inventory.md (files, sheets, header layouts, row counts)
	$(PY) -m src.inventory
ingest:   ## harmonise sheets into data/interim and write reports/harmonise_summary.md
	$(PY) -m src.harmonise
ids:      ## build leader_id table across the three people lists
	$(PY) -m src.ids
segment:  ## split cells into author blocks and clean
	$(PY) -m src.segment
test:
	$(PY) -m pytest -q
all: verify inventory ingest ids segment test
