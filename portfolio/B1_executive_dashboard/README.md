# B1 Executive Dashboard

Purpose

This is the portfolio-facing cockpit view for the question:
"Can we trust the hospital data today?"

What it proves

- the dataset has a visible top-line health check
- the trust gate passes before anything is published
- the data product has a clear executive summary

Proof files

- [data/quality/l1_checkpoint_report.json](../../data/quality/l1_checkpoint_report.json)
- [data/derived/patient_identity_map.json](../../data/derived/patient_identity_map.json)
- [control_room_payload.json](control_room_payload.json)
- [docs/contracts.md](../../docs/contracts.md)
- [openapi_snapshot.json](../../openapi_snapshot.json)
- [README.md](../../README.md)

Backend endpoint

- `/api/control-room`
- `/api/portfolio/b1`

Final visual proof

- [screenshots/executive_dashboard.png](screenshots/executive_dashboard.png)

ASCII mockup

- [executive_dashboard_ascii.md](executive_dashboard_ascii.md)

Spec

- [dashboard_spec.yml](dashboard_spec.yml)
