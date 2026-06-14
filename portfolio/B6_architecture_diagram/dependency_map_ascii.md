+--------------------------------------------------------------------------------+
| 🧭 B6 DEPENDENCY MAP — what file/process feeds what downstream                 |
| Question: which files are helpful, and what clicks are reliable?              |
+--------------------------------------------------------------------------------+

PORTFOLIO COCKPIT
  portfolio/README.md
    -> portfolio/manifest.json
    -> portfolio/PROMPT_FOR_AGENT.md
    -> B1/B2/B3 screenshots + ascii + specs

BACKEND PROOF
  data/quality/l1_checkpoint_report.json
    -> portfolio/B1_executive_dashboard/control_room_payload.json
    -> portfolio/B2_trust_dashboard/evidence_links.md
    -> api/app/control_room.py

  data/derived/patient_identity_map.json
    -> api/app/control_room.py
    -> B1 / B2 trust visuals

  openapi_snapshot.json
    -> api/app/main.py
    -> portfolio/B1 control-room payload

TRANSFORM + QA
  scripts/patient_identity.py
    -> data/derived/patient_identity_map.json
    -> scripts/build_portfolio_snapshot.py

  scripts/checkpoint.py
    -> data/quality/l1_checkpoint_report.json
    -> tests/test_checkpoint.py

  dbt-project/
    -> docs/dag.md
    -> portfolio/B3_dbt_documentation/*
    -> portfolio/B5_bigquery_dataset/*

SURFACE
  api/app/main.py
    -> /api/control-room
    -> /api/portfolio/b1
    -> /api/stats
    -> downstream dashboard consumers

REPO STORY
  README.md
    -> portfolio/README.md
    -> portfolio/manifest.json
    -> docs/contracts.md

BLAST RADIUS
  checkpoint failure -> trust room turns red
  identity failure -> B1/B2 degrade
  dbt failure -> B3/B5 trust drops
  api failure -> no live surface

This map should let another agent answer:
what file do I open, what file do I trust, what file do I change?
