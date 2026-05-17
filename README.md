# healthcare-ai-data-engineer

> **Focused presentation cut of [`healthcare-genai-fullstack`](https://github.com/anix-lynch/healthcare-genai-fullstack) — AI Data Engineer lens.**

This repo presents the **data backbone** slice of the master monorepo, narrowed for the AI Data Engineer interview signal:

- dbt medallion architecture (bronze → silver → gold)
- FastAPI surface over the warehouse
- LLM-augmented clinical enrichment (Vertex AI)
- patient identity resolution
- lightweight data-quality gate before mart release
- ML feature pipeline scaffold

The point: **trusted, AI-ready data** that downstream GenAI applications can chew on without hallucinating their way out of garbage input.

It does **not** duplicate the full monorepo. The Layer 2 GenAI patterns and Layer 3 governance scripts live in the master repo.

---

## Status

🚧 Work in progress — incrementally extracted from the master monorepo.  
See [`ROADMAP.md`](ROADMAP.md) for what is landing next, in small commits.

---

## Master monorepo

Full architecture context (3 layers · 7 patterns · multi-cloud adapter):

→ https://github.com/anix-lynch/healthcare-genai-fullstack

Standalone Layer 1 audit target (richer copy with all scripts + data):

→ https://github.com/anix-lynch/healthcare-api

---

## Source of truth

This repo is a **presentation lens**, not an independent codebase.  
When in doubt, the monorepo is authoritative.

The goal here is **interview clarity** for the AI Data Engineer role specifically,  
not a parallel infrastructure project.
