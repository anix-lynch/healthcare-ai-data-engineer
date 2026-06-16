# Agent Consumption Examples -- Semantic Products
> Generated: 2026-06-16

## PatientProfile (SP-001) -- who is this patient?

```python
# Baymax case manager consuming PatientProfile
import httpx
profile = httpx.get("/api/patients/P-abc1234567").json()
# Agent has: identity, history, conditions, medications
# Contract guarantees freshness <= 24h. No raw SQL needed.
patient_age = profile["demographics"]["age"]
last_admission = profile["identity"]["last_admission"]
conditions = profile["current_conditions"]
```

## RiskProfile (SP-002) -- is this patient high-risk?

```python
risk = httpx.get("/api/patients/P-abc1234567/risk").json()
# Point-in-time correct from Feast feature store
prior_count = risk["readmission_risk"]["previous_admission_count"]
days_since = risk["readmission_risk"]["days_since_last_admission"]
high_utilizer = risk["comorbidity"]["high_utilizer_flag"]
if high_utilizer and prior_count > 3:
    trigger_escalation_protocol()
```

## MedicationProfile (SP-003) -- is this medication safe?

```python
meds = httpx.get("/api/patients/P-abc1234567/medications").json()
for med in meds["medications"]:
    if med["plausibility_status"] == "HARD_BLOCK":
        # Same rule as ingestion layer -- consistent clinical safety
        raise ClinicalSafetyError(f'HARD_BLOCK: {med["medication_name"]}')
    if med["openfda_flagged"]:
        add_warning_to_response(med["medication_name"], med["openfda_serious_rate"])
```

## EncounterSummary (SP-004) -- what happened in this encounter?

```python
results = bm25.search("chest pain shortness of breath", k=5)
for enc in results:
    # Typed product fields, not a blob of text
    context = {
        "complaint": enc["clinical_narrative"]["chief_complaint"],
        "hpi": enc["clinical_narrative"]["hpi"],
        "esi": enc["acuity"]["esi_tier_truth"],
        "hr": enc["vitals"]["heart_rate"],
        "spo2": enc["vitals"]["spo2_pct"],
    }
```

## Context vs Knowledge Product

| Context | Knowledge Product |
|---|---|
| Raw SQL result | Versioned, schematized object |
| Assembled per-request | Cached, freshness-SLA-guaranteed |
| No ownership | Named owner, contract ID |
| No consumer tracking | consumed_by[] registry |
| No breaking-change policy | semver + 30-day deprecation |
| Agent re-derives structure | Agent consumes typed fields |
