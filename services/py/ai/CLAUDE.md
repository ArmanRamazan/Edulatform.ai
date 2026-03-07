# AI Service

Port 8006 | No dedicated DB (Redis only) | Package: ai | 257 tests

## Domain

LLM orchestrator using Gemini Flash. Strategist -> Designer -> Coach pipeline.
Missions (daily/complete), AI credits, unified search (query router + RAG/external).

## Services

- AIService, TutorService — core LLM interactions
- CreditService — AI credit tracking (Redis-backed)
- StrategistService — analyzes learner state, calls learning/course services
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

- LLM client: GeminiClient (httpx-based), all mocked in tests via AsyncMock
- AICache: Redis-backed caching layer
- No database — stateless orchestrator, state lives in Redis cache
- httpx.AsyncClient for inter-service HTTP calls
- Custom health check (no common health router) — checks Redis + Gemini API key

## Dependencies (calls other services via HTTP)

- Learning service (8007): concepts, missions, progress
- RAG service (8008): semantic search, document retrieval
- Course service (8002): course content
- WS Gateway: streaming coach responses

## Test command

```bash
cd services/py/ai && uv run --package ai pytest tests/ -v
```
