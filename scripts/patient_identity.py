"""
Patient identity resolution for Layer 1.

Why this exists:
    Layer 2's Rachel retrieval has a `filter_cross_patient` guardrail hook
    that REQUIRES a stable patient_id per source_id. Until now, Layer 1
    exposed only an encounter_id and an inconsistently-cased `Name` field.
    The hook sat idle for weeks because there was nothing to filter against.

What this is:
    - normalize_name():      lowercase + collapse whitespace + strip
    - patient_id_from_name(): deterministic short ID, stable across encounters
    - build_identity_map():  one-shot CSV → JSON {encounter_id: patient_id}

What this is NOT:
    - real master data management (MDM)
    - probabilistic entity resolution (rapidfuzz / SPLINK)
    - PHI-secure identity exchange

In a real EHR we'd use MRN. Here the synthetic dataset gives us only Name,
so we assume "same normalized name = same patient." This holds for the
55K-row Kaggle dataset. Real production would replace this with MRN lookup.

Identity ID format:
    P-{10char_hex}   first 10 of SHA256(normalize_name(name))
    short enough for logs, long enough for collision safety (~1 per 10^12)

Encounter ID format:
    L1-{row_idx:06d}  matches existing retriever case_id convention
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CSV = REPO_ROOT / "data" / "raw" / "healthcare_dataset.csv"
DEFAULT_OUT = REPO_ROOT / "data" / "derived" / "patient_identity_map.json"


def normalize_name(name: str) -> str:
    """Collapse whitespace + lowercase. 'Bobby JacksOn' → 'bobby jackson'."""
    if not name:
        return ""
    return " ".join(name.lower().split())


def patient_id_from_name(name: str) -> str:
    """
    Deterministic short ID from normalized name.
    Stable across runs, stable across encounters of the same patient.
    """
    norm = normalize_name(name)
    if not norm:
        return "P-unknown"
    return "P-" + hashlib.sha256(norm.encode("utf-8")).hexdigest()[:10]


def encounter_id_from_row_idx(row_idx: int) -> str:
    """Match the existing convention in shared/retrieval/retriever.py."""
    return f"L1-{row_idx:06d}"


def build_identity_map(raw_csv: Path) -> dict:
    """
    Walk the raw CSV, build {encounter_id: patient_id} map + stats.
    Returns the map; caller can dump to JSON.
    """
    encounter_to_patient: dict[str, str] = {}
    patient_to_encounters: dict[str, list[str]] = {}
    with raw_csv.open(newline="") as f:
        for i, row in enumerate(csv.DictReader(f)):
            eid = encounter_id_from_row_idx(i)
            pid = patient_id_from_name(row.get("Name", ""))
            encounter_to_patient[eid] = pid
            patient_to_encounters.setdefault(pid, []).append(eid)

    return {
        "version": 1,
        "encounter_to_patient": encounter_to_patient,
        "stats": {
            "n_encounters": len(encounter_to_patient),
            "n_unique_patients": len(patient_to_encounters),
            "encounters_per_patient_avg": round(
                len(encounter_to_patient) / max(1, len(patient_to_encounters)), 3
            ),
            "max_encounters_per_patient": max(
                (len(v) for v in patient_to_encounters.values()), default=0
            ),
            "top_repeat_patients": dict(
                Counter({k: len(v) for k, v in patient_to_encounters.items()})
                .most_common(5)
            ),
        },
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw-csv", type=Path, default=DEFAULT_CSV)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    if not args.raw_csv.exists():
        raise SystemExit(f"raw CSV missing: {args.raw_csv}")

    print(f"Reading raw CSV: {args.raw_csv}")
    payload = build_identity_map(args.raw_csv)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w") as f:
        json.dump(payload, f, indent=2)

    s = payload["stats"]
    print()
    print(f"Wrote identity map → {args.out}")
    print(f"  encounters:           {s['n_encounters']:,}")
    print(f"  unique patients:      {s['n_unique_patients']:,}")
    print(f"  avg encounters/pt:    {s['encounters_per_patient_avg']}")
    print(f"  max encounters/pt:    {s['max_encounters_per_patient']}")
    print(f"  top repeat patients (encounter count):")
    for pid, n in s["top_repeat_patients"].items():
        print(f"    {pid}: {n}")


if __name__ == "__main__":
    main()
