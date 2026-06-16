#!/usr/bin/env python3
"""Semantic product registry -- versioned knowledge products for agent consumption.

Context = a pile of retrieved rows.
Knowledge product = versioned, schematized, documented artifact any agent can
                    consume with a stable contract.
"""
from __future__ import annotations
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
ARTIFACTS = REPO_ROOT / 'artifacts'
GENERATED_AT = '2026-06-16'

SEMANTIC_PRODUCTS = [
    {
        'product_id': 'SP-001', 'name': 'PatientProfile', 'version': '1.0.0',
        'description': 'Complete patient identity + longitudinal history from dim_patient + stg_healthcare + feature store',
        'grain': '1 object per canonical patient_id',
        'owner': 'Analytics Engineering',
        'consumed_by': ['Baymax case manager', 'RAG retrieval layer', 'ESI classifier'],
        'api_endpoint': '/api/patients/{patient_id}',
        'freshness_sla_hours': 24,
        'contract_id': 'SP-001-v1',
        'breaking_change_policy': 'semver major bump required; 30-day deprecation notice to consumers',
        'schema': {
            'patient_id': {'type': 'string', 'format': 'P-{10hex}', 'source': 'scripts/patient_identity.py'},
            'demographics': {'type': 'object', 'fields': {'age': 'integer', 'gender': 'string', 'blood_type': 'string'}},
            'identity': {'type': 'object', 'fields': {
                'canonical_name_hash': 'string', 'first_admission': 'date',
                'last_admission': 'date', 'total_encounters': 'integer'}},
            'encounter_history': {'type': 'array', 'item_fields': {
                'encounter_id': 'string', 'admission_date': 'date',
                'medical_condition': 'string', 'admission_type': 'string', 'length_of_stay_days': 'integer'}},
            'current_conditions': {'type': 'array', 'items': 'string'},
            'current_medications': {'type': 'array', 'items': 'string'},
        },
        'source_tables': ['BigQuery:healthcare_analytics.dim_patient', 'BigQuery:healthcare_analytics.stg_healthcare'],
        'versioning': 'semver; schema changes require version bump',
    },
    {
        'product_id': 'SP-002', 'name': 'RiskProfile', 'version': '1.0.0',
        'description': 'Readmission risk + medication safety + comorbidity flags from Feast feature store + openFDA signals',
        'grain': '1 object per canonical patient_id',
        'owner': 'AI Data',
        'consumed_by': ['Baymax advance() decision loop', 'high-utilizer signal detector'],
        'api_endpoint': '/api/patients/{patient_id}/risk',
        'freshness_sla_hours': 24,
        'contract_id': 'SP-002-v1',
        'breaking_change_policy': 'semver major bump required',
        'schema': {
            'patient_id': {'type': 'string'},
            'readmission_risk': {'type': 'object', 'fields': {
                'is_readmission': 'boolean', 'days_since_last_admission': 'integer',
                'previous_admission_count': 'integer', 'prior_avg_los': 'float'}},
            'medication_risk': {'type': 'object', 'fields': {
                'flagged_medications': {'type': 'array', 'items': 'string'},
                'openfda_serious_rate': 'float', 'openfda_router_decision': 'string'}},
            'comorbidity': {'type': 'object', 'fields': {
                'conditions': {'type': 'array', 'items': 'string'}, 'high_utilizer_flag': 'boolean'}},
            'feature_freshness_ts': {'type': 'timestamp'},
        },
        'source_tables': ['Feast:patient_encounter_features', 'openFDA:FAERS signals'],
        'feature_view': 'patient_encounter_features (Feast)',
        'versioning': 'semver',
    },
    {
        'product_id': 'SP-003', 'name': 'MedicationProfile', 'version': '1.0.0',
        'description': 'Medication safety: clinical plausibility status + openFDA FAERS adverse event signals',
        'grain': '1 object per (patient_id, medication)',
        'owner': 'AI Data',
        'consumed_by': ['Baymax drug_risk organ', 'clinical plausibility gate'],
        'api_endpoint': '/api/patients/{patient_id}/medications',
        'freshness_sla_hours': 72,
        'contract_id': 'SP-003-v1',
        'breaking_change_policy': 'semver major bump required',
        'schema': {
            'patient_id': {'type': 'string'},
            'medications': {'type': 'array', 'item_fields': {
                'medication_name': 'string',
                'plausibility_status': {'type': 'enum', 'values': ['CLEAR', 'SOFT_WARNING', 'HARD_BLOCK']},
                'openfda_serious_rate': 'float', 'openfda_flagged': 'boolean',
                'age_gate_applies': 'boolean', 'age_gate_min': 'integer'}},
        },
        'source_tables': ['data/quality/clinical_plausibility.yaml', 'data/quality/openfda_signal_proof.json'],
        'versioning': 'semver',
    },
    {
        'product_id': 'SP-004', 'name': 'EncounterSummary', 'version': '1.0.0',
        'description': 'Enriched single-encounter knowledge: LLM-generated narrative + vitals + ESI tier + BM25 retrieval score',
        'grain': '1 object per encounter_id',
        'owner': 'AI Data',
        'consumed_by': ['BM25 retrieval layer', 'ESI classifier', 'physician note grounding'],
        'api_endpoint': '/api/encounters/{encounter_id}',
        'freshness_sla_hours': 168,
        'contract_id': 'SP-004-v1',
        'breaking_change_policy': 'semver major bump required',
        'schema': {
            'encounter_id': {'type': 'string'},
            'patient_id': {'type': 'string'},
            'admission_date': {'type': 'date'},
            'clinical_narrative': {'type': 'object', 'fields': {
                'chief_complaint': 'string', 'hpi': 'string', 'physician_note': 'string'}},
            'vitals': {'type': 'object', 'fields': {
                'bp_systolic': 'integer', 'bp_diastolic': 'integer', 'heart_rate': 'integer',
                'respiratory_rate': 'integer', 'temperature_f': 'float', 'spo2_pct': 'float'}},
            'acuity': {'type': 'object', 'fields': {
                'esi_tier_truth': 'integer', 'acuity_red_flags': {'type': 'array', 'items': 'string'}}},
            'enrichment_source': {'type': 'enum', 'values': ['gemini-2.5-flash', 'synthetic']},
            'holdout': 'boolean',
        },
        'source_tables': ['data/raw/enriched_use_397.jsonl'],
        'versioning': 'semver',
    },
]


def build_api_contracts() -> dict:
    return {
        'generated_at': GENERATED_AT, 'version': '1.0.0',
        'contracts': [{
            'product_id': p['product_id'], 'name': p['name'],
            'endpoint': p['api_endpoint'], 'method': 'GET',
            'response_schema': p['schema'], 'freshness_sla_hours': p['freshness_sla_hours'],
            'contract_id': p['contract_id'],
            'breaking_change_policy': p['breaking_change_policy'],
            'consumed_by': p['consumed_by'],
        } for p in SEMANTIC_PRODUCTS],
    }


def write_examples() -> str:
    lines = [
        '# Agent Consumption Examples -- Semantic Products',
        f'> Generated: {GENERATED_AT}',
        '',
        '## PatientProfile (SP-001) -- who is this patient?',
        '',
        '```python',
        '# Baymax case manager consuming PatientProfile',
        'import httpx',
        'profile = httpx.get("/api/patients/P-abc1234567").json()',
        '# Agent has: identity, history, conditions, medications',
        '# Contract guarantees freshness <= 24h. No raw SQL needed.',
        'patient_age = profile["demographics"]["age"]',
        'last_admission = profile["identity"]["last_admission"]',
        'conditions = profile["current_conditions"]',
        '```',
        '',
        '## RiskProfile (SP-002) -- is this patient high-risk?',
        '',
        '```python',
        'risk = httpx.get("/api/patients/P-abc1234567/risk").json()',
        '# Point-in-time correct from Feast feature store',
        'prior_count = risk["readmission_risk"]["previous_admission_count"]',
        'days_since = risk["readmission_risk"]["days_since_last_admission"]',
        'high_utilizer = risk["comorbidity"]["high_utilizer_flag"]',
        'if high_utilizer and prior_count > 3:',
        '    trigger_escalation_protocol()',
        '```',
        '',
        '## MedicationProfile (SP-003) -- is this medication safe?',
        '',
        '```python',
        'meds = httpx.get("/api/patients/P-abc1234567/medications").json()',
        'for med in meds["medications"]:',
        '    if med["plausibility_status"] == "HARD_BLOCK":',
        '        # Same rule as ingestion layer -- consistent clinical safety',
        '        raise ClinicalSafetyError(f\'HARD_BLOCK: {med["medication_name"]}\')',
        '    if med["openfda_flagged"]:',
        '        add_warning_to_response(med["medication_name"], med["openfda_serious_rate"])',
        '```',
        '',
        '## EncounterSummary (SP-004) -- what happened in this encounter?',
        '',
        '```python',
        'results = bm25.search("chest pain shortness of breath", k=5)',
        'for enc in results:',
        '    # Typed product fields, not a blob of text',
        '    context = {',
        '        "complaint": enc["clinical_narrative"]["chief_complaint"],',
        '        "hpi": enc["clinical_narrative"]["hpi"],',
        '        "esi": enc["acuity"]["esi_tier_truth"],',
        '        "hr": enc["vitals"]["heart_rate"],',
        '        "spo2": enc["vitals"]["spo2_pct"],',
        '    }',
        '```',
        '',
        '## Context vs Knowledge Product',
        '',
        '| Context | Knowledge Product |',
        '|---|---|',
        '| Raw SQL result | Versioned, schematized object |',
        '| Assembled per-request | Cached, freshness-SLA-guaranteed |',
        '| No ownership | Named owner, contract ID |',
        '| No consumer tracking | consumed_by[] registry |',
        '| No breaking-change policy | semver + 30-day deprecation |',
        '| Agent re-derives structure | Agent consumes typed fields |',
    ]
    return '\n'.join(lines) + '\n'


def main():
    ARTIFACTS.mkdir(exist_ok=True)
    registry = {'generated_at': GENERATED_AT, 'version': '1.0.0',
                'total_products': len(SEMANTIC_PRODUCTS), 'products': SEMANTIC_PRODUCTS}
    patient = next(p for p in SEMANTIC_PRODUCTS if p['product_id'] == 'SP-001')
    risk = next(p for p in SEMANTIC_PRODUCTS if p['product_id'] == 'SP-002')
    contracts = build_api_contracts()
    examples = write_examples()
    (ARTIFACTS / 'semantic_products.json').write_text(json.dumps(registry, indent=2))
    (ARTIFACTS / 'patient_profile_schema.json').write_text(json.dumps(patient, indent=2))
    (ARTIFACTS / 'risk_profile_schema.json').write_text(json.dumps(risk, indent=2))
    (ARTIFACTS / 'api_contracts.json').write_text(json.dumps(contracts, indent=2))
    (ARTIFACTS / 'agent_consumption_examples.md').write_text(examples)
    print(f'B3 semantic products: {len(SEMANTIC_PRODUCTS)} products | {len(contracts["contracts"])} API contracts')

if __name__ == '__main__':
    main()
