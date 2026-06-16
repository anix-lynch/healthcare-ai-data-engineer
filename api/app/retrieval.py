"""
BM25 retrieval over the L1-enriched corpus.

Loads data/raw/enriched_use_397.jsonl from the L1 pantry. Each row already
has chief_complaint + hpi + physician_note + vitals — pre-enriched at L1
time by Vertex AI (gemini-2.5-flash). Retrieval combines those three text
fields into a single document for BM25 indexing.

Why this lives in repo#2 (data engineer lane), not repo#1 (genai lane):
    repo#2 = "L1 + serving" — it proves the L1 substrate can feed any
    downstream chef. /api/retrieve serves the retrieval-feature view of
    the corpus; the genai chef (repo#1) consumes this kind of view but
    layers its own re-ranking + generation on top.
"""
import json
import os
import re
import math
from collections import Counter
from typing import List, Dict, Any

try:
    from rank_bm25 import BM25Okapi
except ImportError:
    class BM25Okapi:  # type: ignore[no-redef]
        """Small fallback BM25 so the demo API does not 503 when deps drift."""

        def __init__(self, corpus: List[List[str]], k1: float = 1.5, b: float = 0.75):
            self.corpus = corpus
            self.k1 = k1
            self.b = b
            self.doc_len = [len(doc) for doc in corpus]
            self.avgdl = sum(self.doc_len) / len(self.doc_len) if self.doc_len else 0.0
            self.freqs = [Counter(doc) for doc in corpus]
            doc_freq: Counter[str] = Counter()
            for doc in corpus:
                doc_freq.update(set(doc))
            n_docs = len(corpus)
            self.idf = {
                term: math.log(1 + (n_docs - freq + 0.5) / (freq + 0.5))
                for term, freq in doc_freq.items()
            }

        def get_scores(self, query_tokens: List[str]) -> List[float]:
            scores: List[float] = []
            for idx, freqs in enumerate(self.freqs):
                doc_len = self.doc_len[idx] or 1
                score = 0.0
                for term in query_tokens:
                    tf = freqs.get(term, 0)
                    if not tf:
                        continue
                    denom = tf + self.k1 * (1 - self.b + self.b * doc_len / (self.avgdl or 1.0))
                    score += self.idf.get(term, 0.0) * (tf * (self.k1 + 1)) / denom
                scores.append(score)
            return scores

_TOKEN_RE = re.compile(r"[a-z0-9]+")


def _tokenize(text: str) -> List[str]:
    return _TOKEN_RE.findall(text.lower())


class CorpusRetriever:
    def __init__(self, jsonl_path: str):
        self.rows: List[Dict[str, Any]] = []
        with open(jsonl_path, "r") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                self.rows.append(json.loads(line))

        docs_tokens = [_tokenize(self._doc_text(r)) for r in self.rows]
        self.bm25 = BM25Okapi(docs_tokens)

    @staticmethod
    def _doc_text(row: Dict[str, Any]) -> str:
        parts = [
            row.get("chief_complaint", ""),
            row.get("hpi", ""),
            row.get("physician_note", ""),
            row.get("Medical Condition", ""),
            row.get("Medication", ""),
        ]
        return " ".join(str(p) for p in parts if p)

    def search(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        scores = self.bm25.get_scores(_tokenize(query))
        ranked = sorted(
            enumerate(scores), key=lambda x: x[1], reverse=True
        )[:k]
        out = []
        for idx, score in ranked:
            row = self.rows[idx]
            out.append({
                "rank": len(out) + 1,
                "score": round(float(score), 4),
                "id": idx,
                "age": row.get("Age"),
                "gender": row.get("Gender"),
                "medical_condition": row.get("Medical Condition"),
                "chief_complaint": row.get("chief_complaint"),
                "esi_tier_truth": row.get("esi_tier_truth"),
                "snippet": (row.get("hpi") or "")[:240],
            })
        return out


_RETRIEVER: CorpusRetriever | None = None


def get_retriever() -> CorpusRetriever:
    global _RETRIEVER
    if _RETRIEVER is None:
        here = os.path.dirname(__file__)
        path = os.path.join(here, "../../data/raw/enriched_use_397.jsonl")
        _RETRIEVER = CorpusRetriever(path)
    return _RETRIEVER
