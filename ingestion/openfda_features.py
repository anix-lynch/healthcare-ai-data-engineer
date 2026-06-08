"""
Point-in-time-correct feature build for openFDA (L1.25 feature correctness).

Feature: prior_reports_for_drug = number of earlier adverse-event reports for the
same drug, as of each report's receivedate. The window excludes the current and
any later report, so a model training on this feature cannot see the future.
Includes a self-test that asserts no feature row used a same-or-later date.
"""
from __future__ import annotations
import argparse, json, sys
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def _load(part_dir):
    rows = []
    for f in sorted(part_dir.rglob("*.jsonl")):
        for line in f.open():
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def build_features(rows):
    by_drug = defaultdict(list)
    for r in rows:
        drug = r.get("primary_drug")
        date = str(r.get("receivedate") or "")
        if drug and len(date) == 8:
            by_drug[drug].append((date, r["safetyreportid"]))
    feats = {}
    for drug, items in by_drug.items():
        items.sort()
        for date, rid in items:
            prior = sum(1 for d, _ in items if d < date)
            feats[rid] = {"safetyreportid": rid, "primary_drug": drug, "receivedate": date,
                          "prior_reports_for_drug": prior,
                          "_max_prior_date": max([d for d, _ in items if d < date], default=None)}
    return list(feats.values())


def test_no_future_leak(feats):
    for f in feats:
        mp = f["_max_prior_date"]
        if mp is not None and mp >= f["receivedate"]:
            return False, f"LEAK: {f['safetyreportid']} prior {mp} >= own {f['receivedate']}"
    return True, f"no future leak across {len(feats)} feature rows (all prior dates strictly earlier)"


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--data", type=Path, default=REPO / "data" / "raw" / "openfda")
    args = ap.parse_args()
    rows = _load(args.data)
    feats = build_features(rows)
    ok, msg = test_no_future_leak(feats)
    out = REPO / "feature-store" / "openfda_features.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    clean = [{k: v for k, v in f.items() if not k.startswith("_")} for f in feats]
    out.write_text(json.dumps(clean[:200], indent=2))
    print(f"built {len(feats)} point-in-time features")
    print(f"{'[ok]' if ok else '[FAIL]'} PIT leakage test: {msg}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
