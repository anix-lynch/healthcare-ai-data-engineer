# A2 Trust Dashboard

Purpose

This is the quality cockpit for the question:
"Can we trust the patient and visit numbers?"

What it proves

- the quality gate is enforced and recorded
- duplicates, temporal sanity, and PII leakage are checked
- identity resolution is not hand-waved

Proof files

- [data/quality/l1_checkpoint_report.json](../../data/quality/l1_checkpoint_report.json)
- [scripts/checkpoint.py](../../scripts/checkpoint.py)
- [tests/test_checkpoint.py](../../tests/test_checkpoint.py)
- [.github/workflows/quality.yml](../../.github/workflows/quality.yml)
- [data/derived/patient_identity_map.json](../../data/derived/patient_identity_map.json)
- [trust_room_payload.json](trust_room_payload.json)

Backend endpoint

- `/api/trust-room`
- `/api/portfolio/a2`

Final visual proof

- [screenshots/trust_dashboard.png](screenshots/trust_dashboard.png)

ASCII mockup

- [trust_dashboard_ascii.md](trust_dashboard_ascii.md)

Specs and evidence map

- [trust_metrics_spec.yml](trust_metrics_spec.yml)
- [evidence_links.md](evidence_links.md)
