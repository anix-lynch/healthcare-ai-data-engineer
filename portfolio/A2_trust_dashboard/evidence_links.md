# Evidence Links

This file maps the trust dashboard claims to the proof files that actually
support them.

| Claim | Proof |
| --- | --- |
| 7/7 quality checks passed | [data/quality/l1_checkpoint_report.json](../../data/quality/l1_checkpoint_report.json) |
| Duplicate encounters are zero | [data/quality/l1_checkpoint_report.json](../../data/quality/l1_checkpoint_report.json) |
| Temporal sanity is enforced | [data/quality/l1_checkpoint_report.json](../../data/quality/l1_checkpoint_report.json) |
| PII leakage is checked | [data/quality/l1_checkpoint_report.json](../../data/quality/l1_checkpoint_report.json) |
| Identity resolution exists | [data/derived/patient_identity_map.json](../../data/derived/patient_identity_map.json) |
| CI enforces the gate | [.github/workflows/quality.yml](../../.github/workflows/quality.yml) |
| Check logic is test-backed | [tests/test_checkpoint.py](../../tests/test_checkpoint.py) |
