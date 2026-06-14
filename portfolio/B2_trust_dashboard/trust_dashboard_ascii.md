+----------------------------------------------------------------------+
| ❤️ TRUST INVESTIGATION ROOM                                          |
| Can we trust the patient and visit numbers?                          |
| PROD 🟢 | Updated from checkpoint timestamp                           |
+----------------------------------------------------------------------+
| 😌 CURRENT STATUS                                                     |
| 🟡 Mostly healthy - 1 issue needs attention (not patient-facing yet) |
| No fake patients detected                                             |
+----------------------------------------------------------------------+
| ❤️ TRUST VITALS (traffic light + inline benchmark)                    |
| 1) QC passed?                    100.0% 🟢   good >95  | strong >99   |
| 2) Missing key fields?             0.12% 🟡   good <1   | strong <0.1 |
| 3) Duplicate visits?               0.00% 🟢   good <1   | strong =0    |
| 4) Fake patients?                 99.88% 🟡   good >=99 | strong =100  |
| 5) Can we trace every number?    100.0% 🟢   good >=90 | strong >=95  |
| 6) Do systems agree?             100.0% 🟢   good >=99 | strong >=99.9|
+----------------------------------------------------------------------+
| 📎 EVIDENCE + BLAST RADAR                                             |
| - visit↔patient relationship: 99.88% 🟡  impacts KPI/ER/RAG lookup    |
| - MRN null spike:             0.12% 🟡  nudges owner + lineage fix    |
| - duplicate visit_id:         0.00% 🟢  no blast impact               |
+----------------------------------------------------------------------+
| 🚑 TRIAGE + AUTO-MITIGATIONS + GOOD LUCK HUMAN (HITL)                |
| - issue owner + ETA + runbook links                                   |
| - auto-heal steps + degraded-mode safety message                      |
| - human picks KPI contract, writes definition, enforces semantic test |
+----------------------------------------------------------------------+
