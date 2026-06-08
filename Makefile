.PHONY: help install ingest gate freshness features pipeline serve test clean
help:        ## list targets
	@grep -E '^[a-z_-]+:.*##' $(MAKEFILE_LIST) | sed -E 's/:.*## /\t/'
install:     ## install deps
	pip install -r requirements.txt
ingest:      ## pull live openFDA adverse-event reports
	python ingestion/openfda_pull.py --since 20260101 --max 500
gate:        ## fail-closed quality gate on the landed data
	python ingestion/openfda_gate.py --strict
freshness:   ## freshness SLA + stale-table alert
	python ingestion/freshness_check.py --strict
features:    ## point-in-time feature build + leak guard
	python ingestion/openfda_features.py
pipeline: ingest gate freshness features  ## run the whole pipeline
serve:       ## run the grounded API locally
	uvicorn api.app.main:app --reload
test:        ## pytest
	pytest -q
clean:       ## drop landed data + reports
	rm -rf data/raw/openfda data/freshness/*.json data/quality/*.json
