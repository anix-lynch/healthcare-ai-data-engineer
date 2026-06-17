# Medical Reference Layer — Static Context Cache

This document is the STATIC context layer cached via Vertex Context Caching.
Cached once per TTL window and shared across all inference calls.
Dynamic encounter content (patient-specific vitals, chief complaint, HPI, physician notes) is appended per-call.

---

## ESI Triage Protocol Reference

| ESI Tier | Name | Description | Key Indicators |
|----------|------|-------------|----------------|
| ESI 1 | Immediate | Life-threatening, requires immediate intervention | Unresponsive, pulseless, airway compromise, respiratory arrest |
| ESI 2 | Emergent | High risk situation or severe pain/distress | Altered mental status, lethargy, disorientation, severe pain (8-10), acute distress |
| ESI 3 | Urgent | Stable but requires 2+ resources | Multiple diagnostics needed, stable vitals, moderate pain |
| ESI 4 | Less Urgent | Requires 1 resource | Single diagnostic or treatment needed |
| ESI 5 | Non-Urgent | No resources needed | History, exam only; prescriptions, immunizations |

Triage decisions are based on: (1) immediate life threat, (2) high risk, (3) resource prediction.

---

## Vital Sign Reference Ranges (Adult, at rest)

| Parameter | Critical Low | Normal Low | Normal High | Critical High |
|-----------|-------------|------------|-------------|---------------|
| BP Systolic (mmHg) | < 70 | 90 | 140 | > 180 |
| BP Diastolic (mmHg) | < 40 | 60 | 90 | > 120 |
| Heart Rate (bpm) | < 40 | 50 | 100 | > 130 |
| Respiratory Rate (brpm) | < 8 | 12 | 20 | > 24 |
| SpO2 (%) | < 85 | 95 | 100 | — |
| Temperature (°F) | < 95.0 | 96.8 | 99.5 | > 103.0 |
| Temperature (°C) | < 35.0 | 36.0 | 37.5 | > 39.5 |

Modified Early Warning Score (MEWS): Points assigned when vitals exceed thresholds above.
Score ≥ 4 indicates clinical deterioration risk; score ≥ 6 indicates potential critical illness.

---

## Common Acuity Red Flags

| Flag | Definition | Clinical Significance |
|------|------------|----------------------|
| altered_mental_status | Change in consciousness, confusion, disorientation | Possible neurological event, sepsis, metabolic crisis |
| hypoxia | SpO2 < 90% | Respiratory compromise, requires immediate O2 |
| hypotension | Systolic BP < 90 mmHg | Shock, sepsis, hemorrhage, cardiac compromise |
| tachycardia | HR > 120 bpm | Infection, dehydration, hemorrhage, arrhythmia |
| tachypnea | RR > 24 bpm | Respiratory distress, metabolic acidosis, pain |
| high_fever | Temperature > 103°F (39.5°C) | Severe infection, sepsis risk |
| severe_pain | Pain scale 8-10/10 | Requires urgent assessment and management |
| acute_chest_pain | New onset chest pain | Possible ACS, PE, aortic dissection — time-sensitive |
| dyspnea | Difficulty breathing, shortness of breath | Multiple etiologies — requires urgent workup |
| diaphoresis | Profuse sweating | Often accompanies acute cardiac events |
| syncope | Brief loss of consciousness | Cardiac, neurological, or vasovagal etiology |

---

## Lab Value Reference Ranges

| Lab Test | Low (flag) | Normal Range | High (flag) |
|----------|------------|--------------|-------------|
| Hemoglobin (g/dL) | < 7.0 | 12.0–17.5 | > 20.0 |
| WBC (K/μL) | < 2.5 | 4.5–11.0 | > 30.0 |
| Platelets (K/μL) | < 50 | 150–400 | > 1000 |
| Glucose (mg/dL) | < 50 | 70–100 (fasting) | > 500 |
| Creatinine (mg/dL) | — | 0.6–1.2 | > 4.0 |
| Sodium (mEq/L) | < 120 | 136–145 | > 155 |
| Potassium (mEq/L) | < 3.0 | 3.5–5.0 | > 6.0 |
| INR | — | 0.9–1.1 | > 3.5 |
| Troponin I (ng/mL) | — | < 0.04 | > 0.1 (possible MI) |
| BNP (pg/mL) | — | < 100 | > 400 (heart failure) |

Lab flag severity: CRITICAL = immediate action required; ABNORMAL = monitoring required; NORMAL = no action.

---

## Medication Reference (Common in Emergency/Urgent Care)

| Medication | Drug Class | Common Indications | Key Safety Notes |
|------------|-----------|-------------------|-----------------|
| Aspirin | Antiplatelet / NSAID | ACS, pain, fever, anti-inflammatory | Avoid in bleeding risk, peptic ulcer |
| Ibuprofen | NSAID | Pain, fever, inflammation | Avoid in renal impairment, GI history |
| Paracetamol / Acetaminophen | Analgesic / Antipyretic | Pain, fever | Max 3g/day; liver toxicity risk in overdose |
| Penicillin | Beta-lactam antibiotic | Bacterial infections, streptococcal | Check allergy; cross-reactivity with cephalosporins |
| Insulin (regular) | Hormone | Hyperglycemia, diabetic ketoacidosis | Monitor glucose; hypoglycemia risk |
| Furosemide | Loop diuretic | Fluid overload, heart failure, edema | Monitor electrolytes (K+, Na+); BP drop risk |
| Prednisone | Corticosteroid | Asthma exacerbation, inflammation, allergic reaction | Short-term: glucose rise; long-term: immunosuppression |
| Atorvastatin (Lipitor) | Statin | Hyperlipidemia, cardiovascular risk reduction | Myopathy risk; check liver enzymes |
| Metformin | Biguanide | Type 2 diabetes | Contraindicated in renal failure; lactic acidosis risk |
| Lisinopril | ACE inhibitor | Hypertension, heart failure | Cough, hyperkalemia, contraindicated in pregnancy |

Drug interaction principles:
- NSAIDs + anticoagulants = increased bleeding risk
- ACE inhibitors + potassium-sparing diuretics = hyperkalemia risk
- Statins + certain antibiotics (e.g., clarithromycin) = myopathy risk
- Always verify allergies before prescribing antibiotics

---

## Common Conditions — Clinical Summary

| Condition | ICD-10 | Key Presentation | Standard Management |
|-----------|--------|-----------------|---------------------|
| Asthma | J45 | Wheezing, dyspnea, cough, chest tightness | Bronchodilators (albuterol), corticosteroids, O2 if hypoxic |
| Hypertension | I10 | Usually asymptomatic; headache if severe | Antihypertensives, salt/fluid restriction, monitoring |
| Type 2 Diabetes | E11 | Polydipsia, polyuria, fatigue, hyperglycemia | Glucose monitoring, metformin, insulin if indicated |
| Arthritis (Osteo) | M19 | Joint pain, stiffness, decreased ROM | NSAIDs, PT, joint protection, weight management |
| Cancer (general) | varies | Constitutional symptoms (weight loss, fatigue) | Varies by type/stage; pain management, supportive care |
| Obesity | E66 | BMI > 30; metabolic risk | Dietary counseling, exercise, pharmacotherapy, bariatric eval |
| COPD | J44 | Chronic cough, dyspnea, reduced exercise tolerance | Bronchodilators, inhaled steroids, O2 therapy, pulmonary rehab |

---

## Admission Type Guide

| Type | Definition | Urgency | Typical ESI |
|------|------------|---------|-------------|
| Emergency | Immediate risk to life or limb | Immediate | ESI 1-2 |
| Urgent | Requires treatment within 24-48 hours | High | ESI 2-3 |
| Elective | Scheduled, non-urgent procedure | Low | ESI 4-5 |

---

## Insurance Authorization Notes

| Provider | Auth Requirements | Emergency Exception |
|----------|-------------------|---------------------|
| Cigna | Pre-auth for elective procedures | Emergency services covered without pre-auth |
| Blue Cross | Referral required for specialists | Emergency covered with 24-hr notification |
| Medicare | Medicare Part A/B guidelines apply | Emergency: always covered |
| UnitedHealthcare | Prior auth portal required | Emergent/urgent: covered, document within 24hr |
| Aetna | Prior auth for imaging (CT, MRI) | Life-threatening: no pre-auth needed |

---

*Static reference layer — cached via Vertex Context Caching.*
*Dynamic content (encounter-specific data) appended per call.*
*Pattern portable to: legal (case law reference), finance (regulatory reference), insurance (policy definitions), customer support (product documentation).*
