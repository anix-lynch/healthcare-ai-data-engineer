"""Entry point: run the fault-injection harness, then compute + emit artifacts.

    python -m reliability.run_suite        # or: make reliability

One command → ledger.jsonl → artifacts/. Deterministic (seeded), runs in <2s.
"""
from __future__ import annotations

from reliability import harness, metrics


def main() -> dict:
    runs = harness.run_suite()
    print(f"harness: {len(runs)} pipeline executions → reliability/ledger.jsonl")
    m = metrics.main()
    return m


if __name__ == "__main__":
    main()
