# AI Service

Port 8006 | No dedicated DB (Redis only) | Package: ai | 316 tests

## Domain

LLM orchestrator (Gemini, OpenAI, Claude, or Mock). Strategist -> Designer -> Coach pipeline.
Missions (daily/complete), AI credits, unified search (query router + RAG/external).

## Services

- AIService, TutorService — core LLM interactions
- CreditService — AI credit tracking (Redis-backed)
- StrategistService — analyzes learner state, calls RAG/course services
- DesignerService — structures learning content
- CoachService — delivers coaching, optional WebSocket streaming via WsPublisher
- AgentOrchestrator — orchestrates Strategist -> Designer pipeline
- ModerationService — content moderation via LLM
- StudyPlanService — generates study plans
- LLMResolver — resolves LLM config
- UnifiedSearchService + QueryRouter — decides RAG vs external vs hybrid search

## Routes

ai, coach_routes, orchestrator_routes, llm_config_routes, search_routes

## Key patterns

- LLM providers: `GeminiProvider` (httpx), `OpenAIProvider` (openai SDK), `ClaudeProvider` (anthropic SDK), `SelfHostedProvider` (httpx OpenAI-compat), `MockLLMProvider` (dev/no-key)
- Provider selection via `LLMResolver._make_default_provider()`: `LLM_PROVIDER` env var → API key auto-detect (gemini > openai > anthropic) → mock
- Per-org override: `self_hosted` internal provider via org LLM config in Redis cache
- AICache: Redis-backed caching layer
- No database — stateless orchestrator, state lives in Redis cache
- httpx.AsyncClient for inter-service HTTP calls
- Custom health check (no common health router) — checks Redis + LLM provider key
- **Push mastery model**: Learning pushes mastery data in POST /ai/mission/daily body.
  AI never calls Learning back for mastery — eliminates circular HTTP dependency.

## Dependencies (calls other services via HTTP)

- RAG service (8008): semantic search, document retrieval, org concepts
- Course service (8002): course content
- WS Gateway: streaming coach responses

## Mission daily endpoint contract

`POST /ai/mission/daily` — body: `{org_id, mastery: [{concept_id, mastery}...]}`

Learning fetches its own mastery locally, includes it in the request.
AI uses the provided mastery for path planning — no callback to Learning.

## Test command

```bash
cd services/py/ai && uv run --package ai pytest tests/ -v
```
