"""
B5 — Attention Router: routes encounters to Gemini tier based on spend_signals.

The routing DECISION is the output. The spend_signals Feature Store values are the input.
This module does NOT interpret clinical meaning — it reads structural signals and applies
auditable thresholds.

Routing tiers:
    PRO          — novel, incomplete, or high-instability encounters
    FLASH        — moderate signals
    CACHED_FLASH — familiar, complete, stable encounters

Portability:
    Replace the signal sources with domain-specific equivalents:
    - Finance:   novelty = distance from known patterns, completeness = form fields filled
    - Legal:     novelty = distance from precedent corpus, instability = clause count
    - Insurance: novelty = distance from settled claims, completeness = documentation rate
    The routing logic and audit trail are identical across domains.
"""
from __future__ import annotations
from typing import Dict, Any, Tuple
import math


# --- Thresholds (tunable without code changes) -------------------------
# These are the governance parameters. Change them to shift cost vs recall tradeoff.

NOVELTY_HIGH   = 0.1452  # above this → PRO (p67 of corpus distribution; novel encounter)
NOVELTY_LOW    = 0.1055  # below this → CACHED_FLASH (p33 of corpus distribution; familiar pattern)

COMPLETENESS_LOW = 0.75 # below this → PRO (incomplete record = ambiguous = expensive)

INSTABILITY_HIGH = 2    # >= this → PRO (2+ vitals out of range)

# --- Model config -------------------------------------------------------
TIERS = {
    "PRO":          {"model": "gemini-2.5-pro",   "input_cost_per_m": 1.25,  "label": "pro"},
    "FLASH":        {"model": "gemini-2.5-flash",  "input_cost_per_m": 0.075, "label": "flash"},
    "CACHED_FLASH": {"model": "gemini-2.5-flash",  "input_cost_per_m": 0.01875, "label": "cached_flash",
                     "note": "reads from Vertex Context Cache — static context pre-loaded"},
}


def route(signals: Dict[str, Any]) -> Tuple[str, str, str]:
    """Determine routing tier from spend_signals.

    Returns: (tier_name, model_name, routing_reason)

    Decision logic is explicit and auditable — no black box.
    Every routing decision can be traced back to a specific signal threshold.
    """
    novelty     = signals.get("novelty_score", 0.0)
    completeness = signals.get("struct_completeness_score", 1.0)
    instability  = signals.get("vital_instability_count", 0)

    # PRO conditions — any of these triggers expensive reasoning
    if novelty >= NOVELTY_HIGH:
        return "PRO", TIERS["PRO"]["model"], f"novelty_score={novelty:.4f} >= threshold {NOVELTY_HIGH}"
    if completeness < COMPLETENESS_LOW:
        return "PRO", TIERS["PRO"]["model"], f"struct_completeness={completeness:.3f} < threshold {COMPLETENESS_LOW}"
    if instability >= INSTABILITY_HIGH:
        return "PRO", TIERS["PRO"]["model"], f"vital_instability_count={instability} >= threshold {INSTABILITY_HIGH}"

    # CACHED_FLASH — familiar, complete, stable
    if novelty < NOVELTY_LOW and completeness == 1.0 and instability == 0:
        return "CACHED_FLASH", TIERS["CACHED_FLASH"]["model"], f"novelty={novelty:.4f} < {NOVELTY_LOW}, completeness=1.0, instability=0"

    # Default → FLASH
    return "FLASH", TIERS["FLASH"]["model"], (
        f"novelty={novelty:.4f}, completeness={completeness:.3f}, instability={instability} — moderate signals"
    )


def cost_per_call(tier: str, static_tokens: int, dynamic_tokens: int) -> float:
    """Compute per-call cost in USD based on tier and token counts.

    CACHED_FLASH reads static tokens from Vertex Context Cache at 75% discount.
    PRO and FLASH pay standard rates on all tokens.
    """
    cfg = TIERS[tier]
    rate = cfg["input_cost_per_m"] / 1_000_000
    if tier == "CACHED_FLASH":
        # Static tokens read from cache at cached rate; dynamic at standard Flash rate
        cached_rate = TIERS["CACHED_FLASH"]["input_cost_per_m"] / 1_000_000
        flash_rate  = TIERS["FLASH"]["input_cost_per_m"] / 1_000_000
        return static_tokens * cached_rate + dynamic_tokens * flash_rate
    else:
        return (static_tokens + dynamic_tokens) * rate
