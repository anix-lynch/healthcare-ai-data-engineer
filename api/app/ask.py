"""
Grounded RAG answer path — makes "AI data engineer" literally true.

Pipeline (L2 reasoning over the L1 substrate):
    1. BM25 retrieve top-K rows from the landed openFDA corpus (data/raw/openfda/**/*.jsonl).
    2. Build a numbered context block — one [doc N] per retrieved row.
    3. Ground a Gemini answer on ONLY that context, forcing [doc N] citations
       and a refusal when the answer isn't in the retrieved evidence.

Why BM25 + grounded generation, not Vertex AI Search (Discovery Engine):
    The corpus is the landed openFDA reports. A managed search index buys
    nothing at that scale and adds a console-managed datastore the owner
    would have to babysit. BM25 over the governed corpus + grounded
    Gemini is the right-sized tool: real retrieval, real grounding, zero
    console steps, every answer traceable to a served repo artifact.

PII contract: grounds ONLY on redacted landed fields (drug, reactions, seriousness).
"""
from __future__ import annotations

import os
from typing import Any, Dict, List

try:
    from .retrieval import get_retriever
except Exception:  # pragma: no cover - import shim for direct execution
    from retrieval import get_retriever  # type: ignore

_MODEL_NAME = os.environ.get("ASK_MODEL", "gemini-2.5-flash")
_PROJECT = os.environ.get("GCP_PROJECT_ID") or os.environ.get("GOOGLE_CLOUD_PROJECT") or "bchan-genai-lab"
_LOCATION = os.environ.get("GCP_LOCATION", "us-central1")

_SYSTEM = (
    "You are a drug-safety analyst answering ONLY from the retrieved adverse-event "
    "evidence below. Every claim must cite its source as [doc N]. If the evidence "
    "does not contain the answer, say exactly: 'Not supported by the retrieved "
    "evidence.' Keep it to 2-4 sentences. Do not invent drugs, reactions, or details."
)

# Lazy singletons so the module imports cleanly even when Vertex is absent.
_MODEL = None
_INIT_ERROR: str | None = None


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


def _build_context(hits: List[Dict[str, Any]]) -> str:
    lines = []
    for i, h in enumerate(hits, start=1):
        lines.append(
            f"[doc {i}] drug={h.get('drug')} serious={h.get('serious')} "
            f"country={h.get('country')} received={h.get('received')}\n"
            f"  reactions: {h.get('reactions')}"
        )
    return "\n".join(lines)


def answer(question: str, k: int = 5) -> Dict[str, Any]:
    """
    Grounded answer over the openFDA corpus.

    Returns a stable contract:
      {
        question, k, model, grounded (bool), answer (str),
        sources: [ {doc, id, score, drug, reactions, serious} ],
        corpus, note
      }
    `grounded` is False (with a clear note) when Vertex is unavailable, but the
    retrieval sources are ALWAYS returned so the path is never a dead button.
    """
    hits = get_retriever().search(question, k=k)
    sources = [
        {
            "doc": i,
            "id": h.get("id"),
            "score": h.get("score"),
            "drug": h.get("drug"),
            "reactions": h.get("reactions"),
            "serious": h.get("serious"),
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
            "sources": sources,
            "corpus": "openfda_faers",
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
        # Auth lapse / transient Vertex error → degrade to retrieval-only,
        # never 500 the endpoint.
        return {
            "question": question,
            "k": k,
            "model": _MODEL_NAME,
            "grounded": False,
            "answer": "Retrieval ran (sources below); grounded generation errored.",
            "sources": sources,
            "corpus": "openfda_faers",
            "note": f"{type(exc).__name__}: {exc}",
        }

    return {
        "question": question,
        "k": k,
        "model": _MODEL_NAME,
        "grounded": True,
        "answer": answer_text,
        "sources": sources,
        "corpus": "openfda_faers",
        "note": "BM25 top-k retrieval → grounded Gemini, answers cite [doc N].",
    }
