.PHONY: install serve checkpoint enrich-sample patient-id eval-checkpoint clean help

help:
	@echo "Targets:"
	@echo "  install            pip install requirements"
	@echo "  serve              uvicorn api/app on :8000"
	@echo "  checkpoint         run L1 data quality gate (7 checks)"
	@echo "  patient-id         (re)build encounter→patient identity map"
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

# Enrich 5 rows as smoke (needs GCP_PROJECT_ID + ADC). Honest scope:
# the real run is enrich_parallel.py with --rows 500.
enrich-sample:
	python scripts/enrich_clinical_narrative.py --rows 5 --out /tmp/enrich_sample.csv

test:
	pytest tests/ -v

clean:
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
	rm -rf .pytest_cache
