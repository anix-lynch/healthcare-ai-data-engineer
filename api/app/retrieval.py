"""
BM25 retrieval over the openFDA adverse-event corpus.
Loads the landed FAERS reports (data/raw/openfda/**/*.jsonl); builds one document
per report from drug + reactions for BM25 indexing, so /api/ask can ground answers
in real safety reports with [doc N] citations. Grounds only on redacted landed fields.
"""
import glob, json, os, re
from typing import List, Dict, Any
from rank_bm25 import BM25Okapi

_TOKEN_RE = re.compile(r"[a-z0-9]+")
def _tokenize(t): return _TOKEN_RE.findall(t.lower())

class CorpusRetriever:
    def __init__(self, corpus_glob):
        self.rows = []
        for path in sorted(glob.glob(corpus_glob, recursive=True)):
            with open(path) as f:
                for line in f:
                    line = line.strip()
                    if line:
                        self.rows.append(json.loads(line))
        self.bm25 = BM25Okapi([_tokenize(self._doc_text(r)) for r in self.rows] or [[""]])
    @staticmethod
    def _doc_text(row):
        return " ".join(str(row.get(k, "")) for k in ("primary_drug", "reactions", "occurcountry") if row.get(k))
    def search(self, query, k=5):
        scores = self.bm25.get_scores(_tokenize(query))
        ranked = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)[:k]
        out = []
        for idx, score in ranked:
            row = self.rows[idx]
            out.append({"rank": len(out)+1, "score": round(float(score), 4),
                        "id": row.get("safetyreportid"), "drug": row.get("primary_drug"),
                        "reactions": row.get("reactions"), "serious": row.get("serious"),
                        "received": row.get("receivedate"), "country": row.get("occurcountry"),
                        "snippet": f"{row.get('primary_drug')}: {row.get('reactions')}"[:240]})
        return out

_RETRIEVER = None
def get_retriever():
    global _RETRIEVER
    if _RETRIEVER is None:
        here = os.path.dirname(__file__)
        _RETRIEVER = CorpusRetriever(os.path.join(here, "../../data/raw/openfda/**/*.jsonl"))
    return _RETRIEVER
