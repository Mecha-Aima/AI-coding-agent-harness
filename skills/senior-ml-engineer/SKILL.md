---
name: senior-ml-engineer
description: >-
  Production ML and LLM harness concerns: retries, cost/token limits, RAG-shaped
  pipelines, evaluation loops, and monitoring—applied to extending this agent
  repo or adjacent services. Use when the user mentions MLOps, RAG, embeddings,
  drift, deployment, or model routing beyond a single chat completion.
---

# Senior ML engineer (LLM harness + MLOps)

## Scope in this repo

The default harness optimizes for **reliable tool use** and **governance**, not training. Use this skill when extending toward:

- **RAG**: chunking, embeddings, vector store choice, reranking, citation to sources.
- **Routing**: model tier selection, fallbacks, latency budgets.
- **Evaluation**: golden sets, regression on prompts, tool-call accuracy metrics.
- **Ops**: logging, rate limits, cost accounting per session.

## LLM integration patterns

- **Retries**: exponential backoff; distinguish 429 vs 5xx vs validation errors.
- **Truncation**: explicit summarization or `maybe_compact`-style strategies; avoid silent drop of tool results.
- **Structured output**: schema validation (Pydantic or JSON schema) **after** the model returns.

## RAG decisions (compact)

| Need | Often choose |
|------|----------------|
| Prototype / small | in-memory or sqlite + `sqlite-vec` / simple store |
| Managed scale | Pinecone, Weaviate, Qdrant Cloud |
| Already on Postgres | **pgvector** |

Chunk **200–800 tokens** with overlap unless documents are tiny; tune for recall on representative queries.

## Monitoring

Track at minimum: **latency p95**, **error rate**, **tokens in/out**, **tool failure rate**. For RAG add **hit rate** / **nDCG** on labeled queries when available.

## What not to claim

- Do not reference **`python scripts/model_deployment_pipeline.py`** or other scripts unless they exist in the workspace.
- For **pure harness** bugs (permissions, MCP handshake), pair with **`senior-backend`** and **`code-review`**.
