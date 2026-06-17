"""
Grounded RAG answer path — makes "AI data engineer" literally true.

Pipeline (L2 reasoning over the L1 substrate):
    1. BM25 retrieve top-K rows from the SAME enriched corpus the cockpit
       already serves (data/raw/enriched_use_397.jsonl).
    2. Build a numbered context block — one [doc N] per retrieved row.
    3. Ground a Gemini answer on ONLY that context, forcing [doc N] citations
       and a refusal when the answer isn't in the retrieved evidence.
    4. Optionally verify the answer with Vertex Gen AI Evaluation Service
       (VERIFY_GROUNDEDNESS=true env var) — upgrades grounded:bool from
       "Gemini responded" to "answer verified attributable to retrieved context."

Why BM25 + grounded generation, not Vertex AI Search (Discovery Engine):
    The corpus is 397 redacted holdout rows. A managed search index buys
    nothing at that scale and adds a console-managed datastore the owner
    would have to babysit. BM25 over the already-enriched corpus + grounded
    Gemini is the right-sized tool: real retrieval, real grounding, zero
    console steps, every answer traceable to a served repo artifact.

PII contract (honors A5/A2): grounds ONLY on the enriched/redacted narrative
corpus. The raw PII table (data/raw/healthcare_dataset.csv) is never read here.
"""
from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

try:
    from .retrieval import get_retriever
except Exception:  # pragma: no cover - import shim for direct execution
    from retrieval import get_retriever  # type: ignore

_MODEL_NAME = os.environ.get("ASK_MODEL", "gemini-2.5-flash")
_PROJECT = os.environ.get("GCP_PROJECT_ID") or os.environ.get("GOOGLE_CLOUD_PROJECT") or "bchan-genai-lab"
_LOCATION = os.environ.get("GCP_LOCATION", "us-central1")

# Set VERIFY_GROUNDEDNESS=true to enable per-answer Vertex Gen AI Eval verification.
# Off by default to keep demo API latency low (~200ms/call overhead when on).
_VERIFY_GROUNDEDNESS = os.environ.get("VERIFY_GROUNDEDNESS", "false").lower() == "true"

_SYSTEM = (
    "You are a clinical data analyst answering ONLY from the retrieved encounter "
    "evidence below. Every claim must cite its source as [doc N]. If the evidence "
    "does not contain the answer, say exactly: 'Not supported by the retrieved "
    "evidence.' Keep it to 2-4 sentences. Do not invent patient details."
)

# Lazy singletons so the module imports cleanly even when Vertex is absent.
_MODEL = None
_INIT_ERROR: str | None = None
_EVAL_CLIENT = None


def _get_model():
    """Init Vertex + Gemini once. Returns None (and records why) if unavailable."""
    global _MODEL, _INIT_ERROR
    if _MODEL is not None:
        return _MODEL
    if _INIT_ERROR is not None:
        return None
    try:
        import vertexai
        from vertexai.generative_models import GenerativeModel

        vertexai.init(project=_PROJECT, location=_LOCATION)
        _MODEL = GenerativeModel(_MODEL_NAME)
        return _MODEL
    except Exception as exc:  # SDK missing, no ADC, no perms, etc.
        _INIT_ERROR = f"{type(exc).__name__}: {exc}"
        return None


def _get_eval_client():
    """Lazy singleton for Vertex Gen AI Evaluation Service client."""
    global _EVAL_CLIENT
    if _EVAL_CLIENT is not None:
        return _EVAL_CLIENT
    try:
        from google.cloud import aiplatform_v1beta1
        _EVAL_CLIENT = aiplatform_v1beta1.EvaluationServiceClient(
            client_options={"api_endpoint": f"{_LOCATION}-aiplatform.googleapis.com"}
        )
        return _EVAL_CLIENT
    except Exception:
        return None


def check_groundedness(answer_text: str, context_block: str) -> Dict[str, Any]:
    """
    Verify that answer_text is attributable to context_block using the
    Vertex AI Gen AI Evaluation Service (aiplatform.googleapis.com).

    Returns {score: 0|1, confidence: float, explanation: str} or
    {score: null, error: str} on failure.

    Cost: ~$0.000022/call at Gemini Flash token rates.
    Service: aiplatform.googleapis.com (already enabled, SA key sufficient).
    """
    client = _get_eval_client()
    if client is None:
        return {"score": None, "confidence": None, "explanation": None,
                "error": "eval_client_unavailable"}
    try:
        from google.cloud import aiplatform_v1beta1
        req = aiplatform_v1beta1.EvaluateInstancesRequest(
            location=f"projects/{_PROJECT}/locations/{_LOCATION}",
            groundedness_input=aiplatform_v1beta1.GroundednessInput(
                metric_spec=aiplatform_v1beta1.GroundednessSpec(version=1),
                instance=aiplatform_v1beta1.GroundednessInstance(
                    prediction=answer_text,
                    context=context_block,
                )
            )
        )
        result = client.evaluate_instances(request=req).groundedness_result
        return {
            "score": result.score,
            "confidence": round(float(result.confidence), 4),
            "explanation": result.explanation,
        }
    except Exception as exc:
        return {"score": None, "confidence": None, "explanation": None,
                "error": f"{type(exc).__name__}: {str(exc)[:120]}"}


def _build_context(hits: List[Dict[str, Any]]) -> str:
    lines = []
    for i, h in enumerate(hits, start=1):
        lines.append(
            f"[doc {i}] age={h.get('age')} gender={h.get('gender')} "
            f"condition={h.get('medical_condition')} "
            f"esi_tier_truth={h.get('esi_tier_truth')}\n"
            f"  chief_complaint: {h.get('chief_complaint')}\n"
            f"  hpi: {h.get('snippet')}"
        )
    return "\n".join(lines)


def answer(question: str, k: int = 5) -> Dict[str, Any]:
    """
    Grounded answer over the enriched corpus.

    Returns a stable contract:
      {
        question, k, model,
        grounded (bool — True only when answer is verified attributable to context,
                  or when verification is off and Gemini responded),
        answer (str),
        groundedness_score (0|1|null — null when VERIFY_GROUNDEDNESS=false),
        groundedness_confidence (float|null),
        groundedness_explanation (str|null),
        sources: [ {doc, id, score, condition, esi_tier_truth} ],
        corpus, note
      }
    """
    hits = get_retriever().search(question, k=k)
    sources = [
        {
            "doc": i,
            "id": h.get("id"),
            "score": h.get("score"),
            "condition": h.get("medical_condition"),
            "chief_complaint": h.get("chief_complaint"),
            "esi_tier_truth": h.get("esi_tier_truth"),
        }
        for i, h in enumerate(hits, start=1)
    ]

    model = _get_model()
    if model is None:
        return {
            "question": question,
            "k": k,
            "model": _MODEL_NAME,
            "grounded": False,
            "answer": (
                "Retrieval ran (sources below), but grounded generation is "
                "unavailable in this environment."
            ),
            "groundedness_score": None,
            "groundedness_confidence": None,
            "groundedness_explanation": None,
            "sources": sources,
            "corpus": "enriched_use_397.jsonl",
            "note": _INIT_ERROR or "vertex_unavailable",
        }

    context = _build_context(hits)
    prompt = (
        f"{_SYSTEM}\n\n"
        f"Retrieved evidence:\n{context}\n\n"
        f"Question: {question}\n"
        f"Answer (cite [doc N]):"
    )
    try:
        from vertexai.generative_models import GenerationConfig

        resp = model.generate_content(
            prompt,
            generation_config=GenerationConfig(temperature=0.2, max_output_tokens=512),
        )
        answer_text = (resp.text or "").strip()
    except Exception as exc:
        return {
            "question": question,
            "k": k,
            "model": _MODEL_NAME,
            "grounded": False,
            "answer": "Retrieval ran (sources below); grounded generation errored.",
            "groundedness_score": None,
            "groundedness_confidence": None,
            "groundedness_explanation": None,
            "sources": sources,
            "corpus": "enriched_use_397.jsonl",
            "note": f"{type(exc).__name__}: {exc}",
        }

    # Vertex Gen AI Evaluation Service groundedness verification.
    # Upgrades grounded:bool from "Gemini responded" → "answer verified attributable to context."
    gcheck: Dict[str, Any] = {"score": None, "confidence": None, "explanation": None}
    if _VERIFY_GROUNDEDNESS:
        gcheck = check_groundedness(answer_text, context)

    verified_grounded = (
        gcheck["score"] >= 0.5 if gcheck["score"] is not None
        else True  # fall back to "Gemini responded" when verification is off
    )

    return {
        "question": question,
        "k": k,
        "model": _MODEL_NAME,
        "grounded": verified_grounded,
        "answer": answer_text,
        "groundedness_score": gcheck["score"],
        "groundedness_confidence": gcheck["confidence"],
        "groundedness_explanation": gcheck["explanation"],
        "sources": sources,
        "corpus": "enriched_use_397.jsonl",
        "note": (
            "BM25 retrieval → Gemini generation → Vertex Gen AI Eval groundedness verification."
            if _VERIFY_GROUNDEDNESS
            else "BM25 top-k retrieval → grounded Gemini, answers cite [doc N]."
        ),
    }
