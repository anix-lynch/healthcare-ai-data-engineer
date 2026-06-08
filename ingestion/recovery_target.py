"""
Recovery target for the freshness watchdog.

In production the watchdog's recovery action is the real full pipeline
(ingestion/run_pipeline.py). This wrapper lets the watchdog tests inject
DETERMINISTIC faults so the control-loop behaviour (bounded retry, exhaustion,
unsafe-escalation) can be proven without hammering the live FDA API.

Exit-code contract the watchdog understands:
  0  success
  3  UNSAFE failure  -> escalate immediately, do NOT retry
  1  transient       -> retry with bounded backoff

FAULT_MODE env:
  none | <unset>          -> run the real pipeline (run_pipeline.py)
  transient_then_ok:N     -> fail (exit 1) on attempts <= N, then run real pipeline
  always_transient        -> always exit 1
  unsafe                  -> exit 3 (e.g. major schema drift / reconciliation mismatch)
WATCHDOG_ATTEMPT env = current attempt number (set by the watchdog).
"""
from __future__ import annotations
import os, subprocess, sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def main():
    mode = os.environ.get("FAULT_MODE", "none")
    attempt = int(os.environ.get("WATCHDOG_ATTEMPT", "1"))

    if mode == "unsafe":
        print("[recovery_target] UNSAFE fault injected (schema drift / reconciliation mismatch)", file=sys.stderr)
        return 3
    if mode == "always_transient":
        print(f"[recovery_target] transient fault (attempt {attempt})", file=sys.stderr)
        return 1
    if mode.startswith("transient_then_ok:"):
        n = int(mode.split(":")[1])
        if attempt <= n:
            print(f"[recovery_target] transient fault (attempt {attempt} <= {n})", file=sys.stderr)
            return 1
        # recovered window: run the real pipeline so verification genuinely passes
    return subprocess.run([sys.executable, "ingestion/run_pipeline.py"], cwd=REPO).returncode


if __name__ == "__main__":
    sys.exit(main())
