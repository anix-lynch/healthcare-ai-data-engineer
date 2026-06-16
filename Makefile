.PHONY: install serve checkpoint enrich-sample patient-id portfolio-snapshot feast-apply eval-checkpoint clean help

help:
	@echo "Targets:"
	@echo "  install            pip install requirements"
	@echo "  serve              uvicorn api/app on :8000"
	@echo "  ge                 run GE release gates at source + AI-facing boundaries"
	@echo "  checkpoint         run healthcare-specific quality guards"
	@echo "  patient-id         (re)build encounter→patient identity map"
	@echo "  portfolio-snapshot generate A1 control-room payload"
	@echo "  load-bq             classify + load clean/quarantine to BigQuery (needs ADC)"
	@echo "  enrich-sample      enrich 5 rows via Vertex (needs GCP_PROJECT_ID env)"
	@echo "  test               pytest tests/"
	@echo "  clean              remove __pycache__ + .pytest_cache"

install:
	pip install -r requirements.txt

serve:
	uvicorn api.app.main:app --reload --port 8000

checkpoint:
	python scripts/checkpoint.py

patient-id:
	python scripts/patient_identity.py

portfolio-snapshot:
	python scripts/build_portfolio_snapshot.py

# Enrich 5 rows as smoke (needs GCP_PROJECT_ID + ADC). Honest scope:
# the real run is enrich_parallel.py with --rows 500.
enrich-sample:
	python scripts/enrich_clinical_narrative.py --rows 5 --out /tmp/enrich_sample.csv

# Register the L1.25 feature definitions with the BigQuery offline store.
# Definitions are unit-tested offline by `make test`; this is the live apply.
feast-apply:
	cd feature-store && GOOGLE_CLOUD_PROJECT=bchan-genai-lab feast apply

load-bq:
	python scripts/load_bigquery.py

reconcile:
	python quality/reconcile.py

reliability:
	python3 -m reliability.run_suite

release-gate: ge checkpoint test reliability

test:
	python3 -m pytest \
		tests/test_api.py \
		tests/test_ask.py \
		tests/test_baymax_organs.py \
		tests/test_retrieve_classify.py \
		-v

clean:
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
	rm -rf .pytest_cache

# Great Expectations release gates at source + AI-facing boundaries.
# Domain checks (PII, identity) stay in `make checkpoint`.
ge:
	.ge-venv/bin/python scripts/run_ge.py
