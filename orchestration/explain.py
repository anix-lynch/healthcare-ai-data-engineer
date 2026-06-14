"""LLM-explained pipeline failures (Bullet 2).

When the quality gate quarantines rows, a single Gemini call turns the raw
counts + sample into a plain-language explanation an on-call human can act on —
the pipeline is self-explaining, not a silent red X. Uses Vertex (the $900 GCP
credit) via the deploy SA. Degrades to a deterministic template if Vertex is
unreachable, so a DAG test run never hard-fails on the network.
"""
from __future__ import annotations

import json
import os

PROJECT = os.environ.get("GCP_PROJECT_ID", "bchan-genai-lab")
LOCATION = os.environ.get("VERTEX_LOCATION", "us-central1")
MODEL = os.environ.get("VERTEX_MODEL", "gemini-2.5-flash")


def explain_failure(reason: str, n_quarantined: int, sample: list[dict]) -> dict:
    """Return {'source','explanation'} — Gemini if reachable, else a template."""
    prompt = (
        "You are the on-call data engineer's assistant. A pipeline quality gate "
        f"just quarantined {n_quarantined} encounter row(s) for: {reason}. "
        f"Here is a sample of the offending rows:\n{json.dumps(sample, default=str)[:1500]}\n\n"
        "In 2-3 sentences, plain language: what likely went wrong, and the single "
        "next action for the on-call engineer. No preamble."
    )
    try:
        import vertexai
        from vertexai.generative_models import GenerativeModel

        vertexai.init(project=PROJECT, location=LOCATION)
        resp = GenerativeModel(MODEL).generate_content(prompt)
        return {"source": f"vertex:{MODEL}", "explanation": resp.text.strip()}
    except Exception as e:
        return {
            "source": "template_fallback",
            "explanation": (
                f"{n_quarantined} row(s) quarantined for {reason}. The anomaly "
                "detector found numeric features far outside the normal "
                "distribution (e.g. billing or length-of-stay outliers). Next: "
                "inspect the quarantined sample and confirm whether it is a real "
                "data-source defect or a distribution shift before re-running."
            ),
            "fallback_reason": str(e)[:120],
        }
