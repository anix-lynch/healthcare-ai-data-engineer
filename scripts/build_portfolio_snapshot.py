"""Build portfolio cockpit payload snapshots from backend evidence."""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
OUT_PATH_A1 = REPO_ROOT / "portfolio" / "B1_executive_dashboard" / "control_room_payload.json"
OUT_PATH_A2 = REPO_ROOT / "portfolio" / "B2_trust_dashboard" / "trust_room_payload.json"
OUT_PATH_A5 = REPO_ROOT / "portfolio" / "B5_bigquery_dataset" / "warehouse_room_payload.json"
sys.path.insert(0, str(REPO_ROOT))

from api.app.control_room import build_control_room_payload
from api.app.trust_room import build_trust_room_payload
from api.app.warehouse_room import build_warehouse_room_payload


def main() -> None:
    payload_a1 = build_control_room_payload()
    OUT_PATH_A1.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH_A1.write_text(json.dumps(payload_a1, indent=2) + "\n")
    print(f"wrote {OUT_PATH_A1}")

    payload_a2 = build_trust_room_payload()
    OUT_PATH_A2.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH_A2.write_text(json.dumps(payload_a2, indent=2) + "\n")
    print(f"wrote {OUT_PATH_A2}")

    payload_a5 = build_warehouse_room_payload()
    OUT_PATH_A5.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH_A5.write_text(json.dumps(payload_a5, indent=2) + "\n")
    print(f"wrote {OUT_PATH_A5}")


if __name__ == "__main__":
    main()
