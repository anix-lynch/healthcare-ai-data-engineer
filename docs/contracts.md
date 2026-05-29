# L1 Output Contracts — what downstream layers consume

Frozen contracts the data backbone emits. Any breaking change here regresses
Layer 2 patterns. Treat as semantic-versioned.

---

## canonical_patient_context

Per-encounter view the AI app reads via `services/feature-api`.

```
encounter_id            str       Layer 1 surrogate, format L1-NNNNNN
patient_id              str       stable across encounters of same patient
chief_complaint         str       lay-language CC
hpi                     str       history of present illness narrative
vitals                  dict      BP/HR/RR/T/SpO2 at intake
lab_flags               list[str] semicolon-joined flags
diagnosis_family        str       condition cluster
medication_summary      str       
outcome                 str       discharge disposition
source_refs             list[dict] [{source_id, source_type, ingest_ts}]
```

## retrieval_corpus_view

Per-document view the RAG retriever indexes.

```
source_id               str       L1-NNNNNN | GUIDE-* | POLICY-*
patient_id              str       enables cross-patient leak guard
encounter_id            str
doc_text                str       rendered snippet (BM25 + dense input)
source_type             str       past_case | guideline | protocol
clinical_bucket         str       enables ClinicalRecall@K eval metric
timestamp               str
```

## feature_view

Per-patient features Crystal Ball and Smoke Detector consume.

```
predicted_los_features      dict     age · condition · admission_type · season
readmission_features        dict     prior_visits · comorbidity_proxy
mortality_features          dict     age · condition · acuity_red_flags
ops_capacity_features       dict     bed_pressure · ER_utilization · staffing
```

## eval_holdout_view

The 100-row holdout. NEVER feeds retrieval / training / index. Reserved
for final eval only.

```
query                  str
relevant_ids           list[str]
graded_relevance       dict      {source_id: 0|1|2|3}
query_bucket           str       enables ClinicalRecall@K
```

## audit_lineage_view

Per-row provenance + freshness.

```
source_system          str       csv | pdf | notes | sharepoint | direct
ingest_ts              str       ISO datetime
transform_version      str       which normalize step shipped this row
row_hash               str       sha256 of canonical row
pii_redaction_status   str       cleared | partial | needs_review
```

---

## Source of truth

This contract is published from this repo and should be treated as the stable
L1 surface until a versioned contract update lands here.
