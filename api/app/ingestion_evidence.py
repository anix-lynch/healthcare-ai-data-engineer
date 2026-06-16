"""Shared ingestion proof loaders for B1/B2 cockpit payloads."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
BULK_PROOF = REPO_ROOT / "data" / "quality" / "proof_bulk_load.json"
STREAM_PROOF = REPO_ROOT / "ingestion" / "proof_ingestion.json"
RECON_PROOF = REPO_ROOT / "quality" / "proof_reconciliation.json"


def _load(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open() as fh:
        return json.load(fh)


def build_ingestion_summary() -> dict[str, Any]:
    bulk = _load(BULK_PROOF)
    stream = _load(STREAM_PROOF)
    recon = _load(RECON_PROOF)

    bulk_ok = bool(bulk.get("reconciliation", {}).get("match"))
    stream_ok = bool(stream.get("reconciliation", {}).get("match"))
    clinical_stream = "clinical_plausibility_hard" in (stream.get("quarantine_reasons") or {})
    clinical_bulk = any(
        k.startswith("clinical_plausibility") for k in (bulk.get("quarantine_reasons") or {})
    )

    return {
        "worry_before_load": {
            "batch": {
                "proof": str(BULK_PROOF.relative_to(REPO_ROOT)),
                "topology": bulk.get("topology"),
                "source_rows": bulk.get("source_rows"),
                "clean_rows": bulk.get("clean_rows"),
                "quarantined_rows": bulk.get("quarantined_rows"),
                "reconcile_match": bulk_ok,
                "clinical_quarantine": clinical_bulk,
                "verdict": bulk.get("verdict"),
            },
            "stream": {
                "proof": str(STREAM_PROOF.relative_to(REPO_ROOT)),
                "source_rows_streamed": stream.get("source_rows_streamed"),
                "decisions": stream.get("decisions"),
                "quarantine_reasons": stream.get("quarantine_reasons"),
                "reconcile_match": stream_ok,
                "clinical_hard_block_exercised": clinical_stream,
                "verdict": stream.get("verdict"),
            },
        },
        "reconciliation": {
            "proof": str(RECON_PROOF.relative_to(REPO_ROOT)),
            "grain_chain": recon.get("grain_chain"),
            "all_pass": recon.get("all_pass"),
            "verdict": recon.get("verdict"),
        },
        "both_paths_green": bulk_ok and stream_ok,
    }
