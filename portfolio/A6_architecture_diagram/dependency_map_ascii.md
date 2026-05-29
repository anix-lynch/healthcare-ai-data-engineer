+--------------------------------------------------------------------------------+
| 🧭 A6 DEPENDENCY MAP — what file/process feeds what downstream                 |
| Question: which files are helpful, and what clicks are reliable?              |
+--------------------------------------------------------------------------------+

PORTFOLIO COCKPIT
  portfolio/README.md
    -> portfolio/manifest.json
    -> portfolio/PROMPT_FOR_AGENT.md
    -> A1/A2/A3 screenshots + ascii + specs

BACKEND PROOF
  data/quality/l1_checkpoint_report.json
    -> portfolio/A1_executive_dashboard/control_room_payload.json
    -> portfolio/A2_trust_dashboard/evidence_links.md
    -> api/app/control_room.py

  data/derived/patient_identity_map.json
    -> api/app/control_room.py
    -> A1 / A2 trust visuals

  openapi_snapshot.json
    -> api/app/main.py
    -> portfolio/A1 control-room payload

TRANSFORM + QA
  scripts/patient_identity.py
    -> data/derived/patient_identity_map.json
    -> scripts/build_portfolio_snapshot.py

  scripts/checkpoint.py
    -> data/quality/l1_checkpoint_report.json
    -> tests/test_checkpoint.py

  dbt-project/
    -> docs/dag.md
    -> portfolio/A3_dbt_documentation/*
    -> portfolio/A5_bigquery_dataset/*

SURFACE
  api/app/main.py
    -> /api/control-room
    -> /api/portfolio/a1
    -> /api/stats
    -> downstream dashboard consumers

REPO STORY
  README.md
    -> portfolio/README.md
    -> portfolio/manifest.json
    -> docs/contracts.md

BLAST RADIUS
  checkpoint failure -> trust room turns red
  identity failure -> A1/A2 degrade
  dbt failure -> A3/A5 trust drops
  api failure -> no live surface

This map should let another agent answer:
what file do I open, what file do I trust, what file do I change?
