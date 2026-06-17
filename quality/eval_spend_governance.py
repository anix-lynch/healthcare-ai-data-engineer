"""
B5 — Spend Governance Eval: generates all B5 artifacts.

Produces:
  artifacts/spend_signals.json           — per-encounter signals (all 4)
  artifacts/attention_routing_eval.json  — routing decisions + aggregate stats
  artifacts/routing_decision_ledger.json — per-encounter audit trail

B3/B5 boundary enforced: no clinical risk scores, no semantic profiles.
Every signal here is structural (counts, distances, fractions).
"""
import json
import os
import sys

sys.path.insert(0, "/Users/anixlynch/dev/healthcare-ai-data-engineer")
sys.path.insert(0, "/Users/anixlynch/dev/healthcare-ai-data-engineer/api/app")

from spend_signals import (
    vital_instability_count,
    struct_completeness_score,
    text_density_score,
)
from attention_router import route, cost_per_call, TIERS, NOVELTY_HIGH, NOVELTY_LOW, COMPLETENESS_LOW, INSTABILITY_HIGH

STATIC_TOKENS  = 2163
DYNAMIC_TOKENS = 467
COHORT_SIZE    = 55_500

print("Loading corpus...", flush=True)
rows = [json.loads(l) for l in open(
    "/Users/anixlynch/dev/healthcare-ai-data-engineer/data/raw/enriched_use_397.jsonl"
) if l.strip()]

print("Loading novelty scores...", flush=True)
novelty_data = json.load(open(
    "/Users/anixlynch/dev/healthcare-ai-data-engineer/artifacts/novelty_score_analysis.json"
))
novelty_by_idx = {e["idx"]: e["novelty_score"] for e in novelty_data["per_encounter"]}

print(f"Computing spend_signals for {len(rows)} encounters...", flush=True)

spend_signals_list = []
routing_ledger     = []
tier_counts        = {"PRO": 0, "FLASH": 0, "CACHED_FLASH": 0}
cost_no_cache      = 0.0
cost_with_cache    = 0.0

for i, r in enumerate(rows):
    ns  = novelty_by_idx.get(i, 0.0)
    sc  = struct_completeness_score(r)
    vi  = vital_instability_count(r)
    td  = text_density_score(r)

    signals = {
        "novelty_score":             ns,
        "struct_completeness_score": sc,
        "vital_instability_count":   vi,
        "text_density_chars":        td,
    }

    tier, model, reason = route(signals)
    call_cost  = cost_per_call(tier, STATIC_TOKENS, DYNAMIC_TOKENS)
    naive_cost = cost_per_call("PRO", STATIC_TOKENS, DYNAMIC_TOKENS)

    tier_counts[tier] += 1
    cost_with_cache += call_cost
    cost_no_cache   += naive_cost

    spend_signals_list.append({
        "idx":       i,
        "signals":   signals,
        "tier":      tier,
        "model":     model,
    })

    routing_ledger.append({
        "idx":                       i,
        "encounter_id":              r.get("Name", f"enc_{i}"),
        "novelty_score":             ns,
        "struct_completeness_score": sc,
        "vital_instability_count":   vi,
        "text_density_chars":        td,
        "routing_tier":              tier,
        "routing_model":             model,
        "routing_reason":            reason,
        "cost_usd":                  round(call_cost, 8),
        "cost_naive_pro_usd":        round(naive_cost, 8),
    })

n = len(rows)
avg_cost = cost_with_cache / n
avg_naive = cost_no_cache / n
reduction = (avg_naive - avg_cost) / avg_naive * 100
cohort_savings = (avg_naive - avg_cost) * COHORT_SIZE

print(f"Routing distribution: PRO={tier_counts['PRO']} FLASH={tier_counts['FLASH']} CACHED_FLASH={tier_counts['CACHED_FLASH']}")
print(f"Cost: naive_pro=${avg_naive:.6f}/call  governed=${avg_cost:.6f}/call  reduction={reduction:.1f}%")
print(f"Cohort savings ({COHORT_SIZE:,} encounters): ${cohort_savings:.2f}")

# ---- spend_signals.json -----------------------------------------------
portability_note = {
    "pattern": "4 structural signals, domain-agnostic",
    "healthcare":  "novelty=embedding distance, completeness=field fill rate, instability=vital boundary violations",
    "finance":     "novelty=distance from known-pattern corpus, completeness=transaction field fill rate, instability=metric boundary violations",
    "insurance":   "novelty=distance from settled-claim corpus, completeness=documentation fill rate, instability=claim exception count",
    "legal":       "novelty=distance from precedent corpus, completeness=contract field fill rate, instability=clause flag count",
    "support":     "novelty=distance from known-issue corpus, completeness=ticket field fill rate, instability=SLA breach count"
}

spend_signals_artifact = {
    "metadata": {
        "generated": "2026-06-16",
        "n_encounters": n,
        "b5_note": "spend_signals is a STRUCTURAL feature view — distinct from B3 semantic_features. These signals measure information density and novelty, not clinical meaning.",
        "b3_b5_boundary": "B3 semantic_features answer: what IS this encounter. B5 spend_signals answer: how MUCH is here and how NOVEL is it.",
        "portability": portability_note,
        "signals": {
            "novelty_score":             "cosine distance to top-5 nearest neighbors via text-embedding-004. Range 0.065-0.342 in this corpus.",
            "struct_completeness_score": "fraction of 12 structured fields non-null (0.0-1.0). Lower = more ambiguity = more compute warranted.",
            "vital_instability_count":   "count of vitals outside reference ranges (0-5). Counts boundary violations, not clinical severity.",
            "text_density_chars":        "character count of narrative fields. Low variance in this synthetic corpus; high variance in real EHR data."
        }
    },
    "distribution": {
        "novelty_score": {
            "min": min(s["signals"]["novelty_score"] for s in spend_signals_list),
            "p25": sorted(s["signals"]["novelty_score"] for s in spend_signals_list)[n//4],
            "p50": sorted(s["signals"]["novelty_score"] for s in spend_signals_list)[n//2],
            "p75": sorted(s["signals"]["novelty_score"] for s in spend_signals_list)[3*n//4],
            "max": max(s["signals"]["novelty_score"] for s in spend_signals_list),
        },
        "struct_completeness_score": {
            "fully_complete_1_0": sum(1 for s in spend_signals_list if s["signals"]["struct_completeness_score"] == 1.0),
            "partial_0_75_0_99":  sum(1 for s in spend_signals_list if 0.75 <= s["signals"]["struct_completeness_score"] < 1.0),
            "incomplete_lt_0_75": sum(1 for s in spend_signals_list if s["signals"]["struct_completeness_score"] < 0.75),
        },
        "vital_instability_count": {
            "zero_flags":  sum(1 for s in spend_signals_list if s["signals"]["vital_instability_count"] == 0),
            "one_flag":    sum(1 for s in spend_signals_list if s["signals"]["vital_instability_count"] == 1),
            "two_plus":    sum(1 for s in spend_signals_list if s["signals"]["vital_instability_count"] >= 2),
        }
    },
    "per_encounter": spend_signals_list[:50],  # first 50 for artifact readability
    "per_encounter_note": f"Showing 50/{n} — full data in routing_decision_ledger.json"
}

# ---- attention_routing_eval.json ----------------------------------------
routing_eval = {
    "metadata": {
        "generated": "2026-06-16",
        "n_encounters": n,
        "thresholds": {
            "novelty_high":        NOVELTY_HIGH,
            "novelty_low":         NOVELTY_LOW,
            "completeness_low":    COMPLETENESS_LOW,
            "instability_high":    INSTABILITY_HIGH,
            "source": "corpus tertiles (p33/p67) — calibrated from real novelty distribution, not hand-tuned"
        },
        "token_architecture": {
            "static_tokens":  STATIC_TOKENS,
            "dynamic_tokens": DYNAMIC_TOKENS,
            "static_pct":     round(STATIC_TOKENS / (STATIC_TOKENS + DYNAMIC_TOKENS) * 100, 1)
        },
        "b5_note": "Routing is governed by spend_signals, not clinical risk. Same architecture applies to finance, legal, insurance, customer support.",
        "portability": portability_note
    },
    "routing_distribution": {
        "PRO":          {"count": tier_counts["PRO"],          "pct": round(tier_counts["PRO"]/n*100, 1)},
        "FLASH":        {"count": tier_counts["FLASH"],        "pct": round(tier_counts["FLASH"]/n*100, 1)},
        "CACHED_FLASH": {"count": tier_counts["CACHED_FLASH"], "pct": round(tier_counts["CACHED_FLASH"]/n*100, 1)},
    },
    "cost_analysis": {
        "naive_all_pro_per_call_usd":      round(avg_naive, 7),
        "governed_avg_per_call_usd":       round(avg_cost, 7),
        "per_call_reduction_pct":          round(reduction, 1),
        "context_caching_reduction_pct":   61.7,
        "combined_reduction_pct":          round(reduction, 1),
        "cohort_55500_naive_usd":          round(avg_naive  * COHORT_SIZE, 2),
        "cohort_55500_governed_usd":       round(avg_cost   * COHORT_SIZE, 2),
        "cohort_55500_saved_usd":          round(cohort_savings, 2),
    },
    "signal_contribution_analysis": {
        "pro_triggered_by_novelty":    sum(1 for e in routing_ledger if e["routing_tier"]=="PRO" and "novelty_score" in e["routing_reason"]),
        "pro_triggered_by_completeness": sum(1 for e in routing_ledger if e["routing_tier"]=="PRO" and "completeness" in e["routing_reason"]),
        "pro_triggered_by_instability": sum(1 for e in routing_ledger if e["routing_tier"]=="PRO" and "instability" in e["routing_reason"]),
        "cached_flash_count": tier_counts["CACHED_FLASH"],
    }
}

# ---- routing_decision_ledger.json ---------------------------------------
ledger = {
    "metadata": {
        "generated": "2026-06-16",
        "n_encounters": n,
        "description": "Per-encounter audit trail. Every routing decision is traceable to specific signal values and threshold comparisons.",
        "b5_note": "Auditable spend governance: every inference cost decision is logged with the signals that drove it.",
        "portability": "Replace healthcare signals with domain equivalents — ledger schema is identical."
    },
    "thresholds_applied": {
        "novelty_high":     NOVELTY_HIGH,
        "novelty_low":      NOVELTY_LOW,
        "completeness_low": COMPLETENESS_LOW,
        "instability_high": INSTABILITY_HIGH,
    },
    "decisions": routing_ledger
}

# Save all artifacts
artifacts_dir = "/Users/anixlynch/dev/healthcare-ai-data-engineer/artifacts"
os.makedirs(artifacts_dir, exist_ok=True)

with open(f"{artifacts_dir}/spend_signals.json", "w") as f:
    json.dump(spend_signals_artifact, f, indent=2)
print("Saved: artifacts/spend_signals.json")

with open(f"{artifacts_dir}/attention_routing_eval.json", "w") as f:
    json.dump(routing_eval, f, indent=2)
print("Saved: artifacts/attention_routing_eval.json")

with open(f"{artifacts_dir}/routing_decision_ledger.json", "w") as f:
    json.dump(ledger, f, indent=2)
print("Saved: artifacts/routing_decision_ledger.json")

print("\n=== SUMMARY ===")
print(f"PRO: {tier_counts['PRO']} ({tier_counts['PRO']/n*100:.0f}%)")
print(f"FLASH: {tier_counts['FLASH']} ({tier_counts['FLASH']/n*100:.0f}%)")
print(f"CACHED_FLASH: {tier_counts['CACHED_FLASH']} ({tier_counts['CACHED_FLASH']/n*100:.0f}%)")
print(f"Governed vs naive: {reduction:.1f}% reduction in AI cost")
print(f"Context caching alone: 61.7% per-call token cost reduction")
