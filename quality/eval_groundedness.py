#!/usr/bin/env python3
"""
Batch groundedness eval: runs 20 golden clinical queries through the full
/api/ask pipeline (BM25 retrieve → Gemini generate → Vertex Gen AI Eval verify)
and writes artifacts/grounded_answer_eval.json.

Requires:
  - GOOGLE_APPLICATION_CREDENTIALS set to SA key
  - VERIFY_GROUNDEDNESS=true (set in this script before importing ask)
  - Run from repo root: python3 quality/eval_groundedness.py
"""
import json, os, sys, time
from pathlib import Path

# Force verification on for this run
os.environ["VERIFY_GROUNDEDNESS"] = "true"
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "/Users/anixlynch/.config/secrets/bchan-genai-deploy.json"
os.environ["GCP_PROJECT_ID"] = "bchan-genai-lab"

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "api" / "app"))

from ask import answer, check_groundedness

GOLDEN = REPO / "data" / "quality" / "golden_retrieval_set.json"
OUT    = REPO / "artifacts" / "grounded_answer_eval.json"

queries = json.loads(GOLDEN.read_text())["queries"]
results = []
scores  = []

print(f"Running {len(queries)} golden queries through full grounding pipeline...\n")

for q in queries:
    t0 = time.time()
    resp = answer(q["query"], k=5)
    elapsed = round((time.time() - t0) * 1000)

    score     = resp.get("groundedness_score")
    conf      = resp.get("groundedness_confidence")
    expl      = resp.get("groundedness_explanation", "")
    grounded  = resp.get("grounded")

    scores.append(score if score is not None else 0)

    result = {
        "id":                      q["id"],
        "query":                   q["query"],
        "expects_condition":       q.get("expects_condition"),
        "answer":                  resp.get("answer", "")[:300],
        "sources_retrieved":       len(resp.get("sources", [])),
        "groundedness_score":      score,
        "groundedness_confidence": conf,
        "groundedness_explanation": (expl or "")[:400],
        "grounded":                grounded,
        "latency_ms":              elapsed,
    }
    results.append(result)

    status = "GROUNDED" if score == 1 else ("PARTIAL" if score == 0.5 else "NOT_GROUNDED" if score == 0 else "UNVERIFIED")
    print(f"  {q['id']} [{status}] score={score} conf={conf} ({elapsed}ms)")

verified = [r for r in results if r["groundedness_score"] is not None]
grounded_rate = sum(1 for r in verified if r["groundedness_score"] >= 0.5) / len(verified) if verified else 0
avg_score = sum(r["groundedness_score"] for r in verified) / len(verified) if verified else 0
avg_conf  = sum(r["groundedness_confidence"] for r in verified if r["groundedness_confidence"]) / len(verified) if verified else 0

artifact = {
    "eval_date":               "2026-06-16",
    "pipeline":                "BM25 retrieval (Hit@5=0.95) → Gemini generation → Vertex Gen AI Eval groundedness verification",
    "service":                 "google.cloud.aiplatform_v1beta1.EvaluationServiceClient",
    "endpoint":                "us-central1-aiplatform.googleapis.com",
    "corpus":                  "data/raw/enriched_use_397.jsonl",
    "corpus_size_rows":        497,
    "golden_query_set":        "data/quality/golden_retrieval_set.json",
    "n_queries":               len(queries),
    "n_verified":              len(verified),
    "aggregates": {
        "grounded_response_rate": round(grounded_rate, 4),
        "avg_groundedness_score": round(avg_score, 4),
        "avg_confidence":         round(avg_conf, 4),
    },
    "per_query":               results,
    "note": (
        "grounded_response_rate = fraction of verified answers where groundedness_score >= 0.5. "
        "Score 1 = fully attributable to retrieved context. "
        "Score 0 = model introduced claims not in evidence."
    ),
}

OUT.write_text(json.dumps(artifact, indent=2))
print(f"\n{'='*60}")
print(f"grounded_response_rate : {grounded_rate:.1%}")
print(f"avg groundedness_score : {avg_score:.3f}")
print(f"avg confidence         : {avg_conf:.3f}")
print(f"\nArtifact written to: {OUT}")
