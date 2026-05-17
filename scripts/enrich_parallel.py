"""
Parallel enrichment orchestrator — x6 workers, checkpointing, retries.

Reads:  /tmp/enrich_plan_500.jsonl   (one source row per line, from stratified_sampler)
Writes: /tmp/enriched_500.jsonl       (one enriched row per line, streamed checkpoint)
Writes: /tmp/failed_rows.jsonl        (rows that failed all retries)

Why parallel x6:
    Serial = 500 × 9s = 75 min watching paint dry in hospital basement 😭
    Parallel x6 ≈ 13 min, well under 60 RPM quota cap.

Why checkpoint every 25:
    If the run dies at row 423, you keep the 400 you've already paid for.
    --resume flag skips rows already enriched in the JSONL.

Why exponential backoff:
    Vertex sometimes returns transient 503 / DEADLINE_EXCEEDED.
    Retry @ 1s → 2s → 4s, then write to failed_rows.jsonl and move on.
"""
from __future__ import annotations
import argparse
import json
import sys
import time
import threading
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

# Pull existing enrichment building blocks
sys.path.insert(0, str(Path(__file__).parent))
from enrich_clinical_narrative import (
    PROMPT_TEMPLATE,
    RESPONSE_SCHEMA,
    _vertex_generate,
    _flatten,
    _mock_generate,
)

REPO_ROOT = Path(__file__).resolve().parents[1]


# ── Per-row enrichment with retry ──────────────────────────────────────────
def enrich_one(row: dict, *, model: str, dry_run: bool, max_retries: int = 3) -> dict:
    """
    Enrich a single source row. Returns the merged dict (source + flattened enrichment).

    Raises RuntimeError after max_retries exhausted.
    """
    if dry_run:
        return {**row, **_flatten(_mock_generate(row))}

    # Inject scenario_hint as a directive at the end of the prompt
    extra_hint = ""
    if row.get("scenario_hint"):
        extra_hint = f"\n\nSCENARIO TO PORTRAY (override generic for this row): {row['scenario_hint']}\n"

    prompt = PROMPT_TEMPLATE.format(
        age=row.get("Age", ""),
        gender=row.get("Gender", ""),
        blood_type=row.get("Blood Type", ""),
        medical_condition=row.get("Medical Condition", ""),
        admission_type=row.get("Admission Type", ""),
        medication=row.get("Medication", ""),
        test_results=row.get("Test Results", ""),
        los_days="?",
    ) + extra_hint

    last_err: Exception | None = None
    for attempt in range(max_retries):
        try:
            enrich = _vertex_generate(prompt, model_name=model)
            return {**row, **_flatten(enrich)}
        except Exception as e:
            last_err = e
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)  # 1s, 2s, 4s
    raise RuntimeError(f"failed after {max_retries} tries: {last_err}")


# ── Main runner ────────────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", type=Path, default=Path("/tmp/enrich_plan_500.jsonl"))
    ap.add_argument("--out", type=Path, default=Path("/tmp/enriched_500.jsonl"))
    ap.add_argument("--failed-out", type=Path, default=Path("/tmp/failed_rows.jsonl"))
    ap.add_argument("--model", default="gemini-2.5-flash")
    ap.add_argument("--parallel", type=int, default=6)
    ap.add_argument("--checkpoint-every", type=int, default=25)
    ap.add_argument("--resume", action="store_true", help="skip rows already in --out")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if not args.plan.exists():
        sys.exit(f"plan file missing: {args.plan}. Run stratified_sampler.py first.")

    # Load plan
    plan: list[dict] = []
    with args.plan.open() as f:
        for line in f:
            line = line.strip()
            if line:
                plan.append(json.loads(line))
    print(f"[parallel] loaded {len(plan)} rows from {args.plan.name}")

    # Resume: skip rows already enriched
    done_keys: set[tuple] = set()
    if args.resume and args.out.exists():
        with args.out.open() as f:
            for line in f:
                try:
                    r = json.loads(line)
                    done_keys.add((r.get("Name"), r.get("Date of Admission"), r.get("case_type", "")))
                except json.JSONDecodeError:
                    pass
        print(f"[parallel] resume: {len(done_keys)} rows already enriched, skipping")
    plan = [r for r in plan if (r.get("Name"), r.get("Date of Admission"), r.get("case_type", "")) not in done_keys]
    print(f"[parallel] {len(plan)} rows to enrich")

    if not plan:
        print("[parallel] nothing to do.")
        return

    # Open output files for append (so checkpoint = always-on)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.failed_out.parent.mkdir(parents=True, exist_ok=True)
    out_lock = threading.Lock()
    failed_lock = threading.Lock()
    out_fh = args.out.open("a")
    failed_fh = args.failed_out.open("a")

    t0 = time.time()
    done = 0
    failed = 0

    def worker(row: dict) -> tuple[dict | None, dict | None]:
        try:
            enriched = enrich_one(row, model=args.model, dry_run=args.dry_run)
            return enriched, None
        except Exception as e:
            return None, {**row, "_error": str(e)[:300]}

    print(f"[parallel] starting {args.parallel} workers, model={args.model}, dry_run={args.dry_run}")
    print()

    try:
        with ThreadPoolExecutor(max_workers=args.parallel) as pool:
            futures = {pool.submit(worker, r): r for r in plan}
            for future in as_completed(futures):
                enriched, failure = future.result()

                if enriched is not None:
                    with out_lock:
                        out_fh.write(json.dumps(enriched) + "\n")
                        out_fh.flush()
                    done += 1
                else:
                    with failed_lock:
                        failed_fh.write(json.dumps(failure) + "\n")
                        failed_fh.flush()
                    failed += 1

                total_processed = done + failed
                if total_processed % args.checkpoint_every == 0 or total_processed == len(plan):
                    elapsed = time.time() - t0
                    rate = total_processed / elapsed if elapsed > 0 else 0
                    print(f"  [{total_processed:>4}/{len(plan)}] "
                          f"✅ {done} · ❌ {failed} · "
                          f"{elapsed:.0f}s elapsed · {rate:.1f} rows/s")
    finally:
        out_fh.close()
        failed_fh.close()

    elapsed = time.time() - t0
    print()
    print(f"DONE.  ✅ enriched: {done}  ·  ❌ failed: {failed}  ·  time: {elapsed:.0f}s")
    print(f"  output:  {args.out}")
    if failed:
        print(f"  failed:  {args.failed_out}")
    if done and not args.dry_run:
        est_cost = done * 0.0005
        print(f"  estimated cost: ~${est_cost:.2f} (GCP credit absorbs)")


if __name__ == "__main__":
    main()
