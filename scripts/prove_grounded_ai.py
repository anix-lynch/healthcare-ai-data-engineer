#!/usr/bin/env python3
"""
Bullet 3 proof: grounded AI responses with source-level citations over REAL openFDA.
Runs api/app/ask.answer() against the deduped openFDA corpus for:
  1. an answerable safety question  -> expect grounded answer citing [doc N] from real reports
  2. an out-of-corpus question       -> expect the exact refusal string (no hallucination)
Writes a machine-readable receipt. GREEN requires: grounded generation actually ran,
the answerable case cites >=1 doc, and the refusal case refuses.
"""
import json, os, sys, re

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "api"))
from app import retrieval, ask  # noqa: E402

CORPUS = os.path.join(os.path.dirname(__file__), "..", "data", "corpus", "openfda_corpus.jsonl")
REFUSAL = "Not supported by the retrieved evidence."

# point the retriever at the clean canonical corpus (one row per safetyreportid)
retrieval._RETRIEVER = retrieval.CorpusRetriever(CORPUS)

ANSWERABLE = "What adverse reactions are reported for LUCENTIS?"
UNANSWERABLE = "What is the recommended aspirin dose for a headache?"  # not an openFDA report field


def check(label, q):
    r = ask.answer(q, k=5)
    cited = sorted(set(int(n) for n in re.findall(r"\[doc (\d+)\]", r.get("answer", ""))))
    return {
        "label": label, "question": q, "grounded": r.get("grounded"),
        "model": r.get("model"), "answer": r.get("answer"),
        "cited_docs": cited,
        "sources": [{"doc": s["doc"], "id": s["id"], "drug": s["drug"]} for s in r.get("sources", [])[:5]],
        "note": r.get("note"),
    }


def main():
    ans = check("answerable", ANSWERABLE)
    ref = check("refusal", UNANSWERABLE)

    grounded_ran = bool(ans["grounded"]) and bool(ref["grounded"])
    answerable_cites = len(ans["cited_docs"]) >= 1
    refused = REFUSAL.lower() in (ref["answer"] or "").lower()

    green = grounded_ran and answerable_cites and refused
    receipt = {
        "proof": "bullet3_grounded_ai_citations",
        "claim_phrase": "grounded AI responses, with ... source-level citations",
        "corpus": "openfda_corpus.jsonl (300 deduped real FAERS reports)",
        "retrieval": "BM25 top-k over governed report fields",
        "generation": ans["model"],
        "cases": {"answerable": ans, "refusal": ref},
        "checks": {"grounded_generation_ran": grounded_ran,
                   "answerable_cites_doc": answerable_cites,
                   "refuses_out_of_corpus": refused},
        "verdict": "GREEN — grounded Gemini cited real reports and refused out-of-evidence"
                   if green else "YELLOW — see checks (grounded gen unavailable or a check failed)",
    }
    out = "data/quality/bullet3_grounded_ai_proof.json"
    json.dump(receipt, open(out, "w"), indent=2)
    print("WROTE", out)
    print(f"  answerable: grounded={ans['grounded']} cites={ans['cited_docs']}")
    print(f"    answer: {ans['answer'][:160]}")
    print(f"  refusal:    grounded={ref['grounded']} refused={refused}")
    print(f"    answer: {ref['answer'][:120]}")
    print("VERDICT:", receipt["verdict"])
    if not green:
        print("  NOTE answerable:", ans["note"])
    return 0 if green else 1


if __name__ == "__main__":
    raise SystemExit(main())
