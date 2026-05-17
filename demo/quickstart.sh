#!/usr/bin/env bash
# Quickstart — run the 3 most important things in 30 seconds.
#
#   1) Layer 1 data quality gate (checkpoint)
#   2) Patient identity map size (sanity)
#   3) FastAPI surface — show OpenAPI spec preview
#
# Doesn't need GCP auth, dbt, or Vertex. Pure-Python sanity.

set -e
ROOT=$(cd "$(dirname "$0")/.." && pwd)
cd "$ROOT"

echo "── 1) L1 quality checkpoint ───────────────────────"
python scripts/checkpoint.py | tail -15

echo ""
echo "── 2) Patient identity map ────────────────────────"
python -c "
import json
m = json.load(open('data/derived/patient_identity_map.json'))
s = m['stats']
print(f'  encounters:    {s[\"n_encounters\"]:,}')
print(f'  patients:      {s[\"n_unique_patients\"]:,}')
print(f'  avg per pt:    {s[\"encounters_per_patient_avg\"]}')
print(f'  top repeater:  {s[\"max_encounters_per_patient\"]} encounters')
"

echo ""
echo "── 3) OpenAPI snapshot (first 30 lines) ───────────"
head -30 openapi_snapshot.json 2>/dev/null || echo "(openapi_snapshot.json not present)"

echo ""
echo "Done. Next: \`make serve\` to start the FastAPI on :8000"
