# RAG Service

Port 8008 | DB port 5439 | Package: rag | 173 tests

## Domain

pgvector-based RAG pipeline. Document ingestion, semantic search,
LLM concept extraction, knowledge base management. GitHub adapter.

## Services & Repos

- IngestionService (DocumentRepo, EmbeddingClient, ExtractionService)
- SearchService (SearchRepo, EmbeddingClient)
- ExtractionService (ConceptStoreRepo) — LLM-based concept extraction
- KnowledgeBaseService (DocumentRepo, ConceptStoreRepo, IngestionService, SearchService)
- GitHubAdapter — ingest GitHub repos as knowledge base

## Routes (factory pattern)

Routes use `create_*_router()` factories that accept service getters and JWT config:
ingestion_routes, search_routes, concept_routes, knowledge_base_routes, github_routes

## Migrations

001_init (pgvector setup), 002_concepts

## Embedding clients (strategy pattern)

- GeminiEmbeddingClient — production (Gemini API)
- OrchestratorEmbeddingClient — routes through Rust embedding-orchestrator with Gemini fallback
- StubEmbeddingClient — tests/dev (random vectors)
- Selection logic: openai_api_key set? -> Gemini. embedding_service_url set? -> Orchestrator. Neither? -> Stub

## Rust FFI

- `libs/rs/rag-chunker/` — Rust chunker compiled via pyo3
- Python fallback when Rust binary unavailable
- Test Rust: `cd libs/rs/rag-chunker && cargo test`

## Key patterns

- No Redis (unlike other services) — no rate limiting middleware
- JWT validation done per-router via factory params
- pgvector extension required in PostgreSQL

## Test command

```bash
cd services/py/rag && uv run --package rag pytest tests/ -v
```
