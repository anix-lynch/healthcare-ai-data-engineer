"""
openFDA Trust API -- the serving face of the L1 pipeline.
  GET /api/retrieve?q=   BM25 retrieval over the openFDA reports
  GET /api/ask?q=        grounded Gemini answer, [doc N] citations, refuses on no-evidence
  GET /health            liveness
Grounds only on redacted landed fields. /api/ask degrades to retrieval-only if Vertex is absent.
"""
from __future__ import annotations
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
try:
    from .retrieval import get_retriever
    from .ask import answer as grounded_answer
except Exception:
    from retrieval import get_retriever  # type: ignore
    from ask import answer as grounded_answer  # type: ignore

app = FastAPI(title="openFDA Trust API",
    description="Grounded retrieval over a live FDA adverse-event corpus. Cites [doc N]; refuses when evidence is missing.",
    version="2.0.0", docs_url="/docs")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.get("/")
def root():
    return {"service": "openFDA Trust API", "source": "openfda_faers (live FDA adverse-event reports)",
            "endpoints": {"retrieve": "/api/retrieve?q=", "ask": "/api/ask?q=", "health": "/health"}, "docs": "/docs"}

@app.get("/health")
def health(): return {"status": "ok"}

@app.get("/api/retrieve")
def retrieve(q: str = Query(..., min_length=2), k: int = Query(5, ge=1, le=20)):
    return {"query": q, "k": k, "method": "bm25_okapi", "corpus": "openfda_faers",
            "results": get_retriever().search(q, k=k)}

@app.get("/api/ask")
def ask(q: str = Query(..., min_length=2), k: int = Query(5, ge=1, le=10)):
    return grounded_answer(q, k=k)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
