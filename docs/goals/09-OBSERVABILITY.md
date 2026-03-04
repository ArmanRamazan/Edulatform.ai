# 09 — Наблюдаемость и SLO

> Владелец: Architect / SRE
> Последнее обновление: 2026-03-05

---

## Контекст

B2B платформа адаптивного онбординга. Ключевые потоки: Coach session (Socratic диалог), RAG search (поиск по кодобазе компании), Agent orchestration (Strategist → Designer → Coach). Наблюдаемость должна отражать качество обучения, а не торговые метрики.

---

## SLO (Service Level Objectives)

### Tier 1 — Критические (качество обучения)

| Сервис | Метрика | SLO | Бюджет ошибок/мес |
|--------|---------|-----|-------------------|
| Coach (AI) | Response latency p99 | < 2s | — |
| Coach (AI) | Session availability | 99.9% | 43.2 мин downtime |
| RAG Search | Latency p95 | < 500ms | — |
| RAG Search | Availability | 99.9% | 43.2 мин downtime |
| Identity | Availability | 99.95% | 21.6 мин downtime |
| Identity | Auth latency p99 | < 300ms | — |

### Tier 2 — Важные (функциональность платформы)

| Сервис | Метрика | SLO |
|--------|---------|-----|
| Strategist (AI) | Learning path generation p95 | < 5s |
| Designer (AI) | Mission assembly p95 | < 3s |
| Learning API | Progress endpoints p95 | < 200ms |
| Notification | Delivery time | < 30 sec (email), < 5 sec (push) |
| RAG Ingestion | Document processing throughput | > 100 docs/min |

### Tier 3 — Background (допускает деградацию)

| Сервис | Метрика | SLO |
|--------|---------|-----|
| RAG Embedding generation | Throughput | > 500 chunks/min |
| Analytics aggregation | Data freshness | < 5 min lag |
| Trust Level recalculation | Processing time | < 1 min per user |

---

## Observability Stack

### Metrics (Prometheus + Grafana)

**Реализовано:**
- [x] Prometheus + Grafana (self-hosted, docker-compose.prod.yml)
- [x] RED метрики: FastAPI instrumentator на всех Python сервисах
- [x] DB pool метрики: pool_size, pool_free, pool_used
- [x] DB query duration histogram (per service, per operation)
- [x] Grafana dashboard: RPS, latency, errors, DB pool

**TODO:**

#### Agent Orchestration Metrics
- [ ] `agent_session_duration_seconds` — histogram по agent type (strategist/designer/coach)
- [ ] `agent_phase_transitions_total` — counter переходов между фазами coach session
- [ ] `agent_session_completion_rate` — gauge: завершённые / начатые сессии
- [ ] `agent_llm_tokens_total` — counter входных/выходных токенов per agent per org
- [ ] `agent_llm_latency_seconds` — histogram latency вызовов Gemini Flash

#### RAG Pipeline Metrics
- [ ] `rag_ingestion_documents_total` — counter обработанных документов
- [ ] `rag_ingestion_duration_seconds` — histogram времени обработки документа
- [ ] `rag_embedding_generation_seconds` — histogram времени генерации embedding
- [ ] `rag_search_latency_seconds` — histogram latency vector search
- [ ] `rag_search_results_count` — histogram количества результатов
- [ ] `rag_index_size_bytes` — gauge размер vector index per org

#### Trust Level Metrics
- [ ] `trust_level_distribution` — gauge: количество пользователей на каждом уровне (0-5) per org
- [ ] `trust_level_progression_total` — counter переходов между уровнями
- [ ] `trust_level_avg_time_to_level_seconds` — histogram среднее время достижения уровня

#### Organization Metrics
- [ ] `org_active_users_total` — gauge активных пользователей per org
- [ ] `org_missions_completed_total` — counter завершённых миссий per org
- [ ] `org_resource_usage` — gauge: CPU/memory/storage per org для биллинга

---

### Logging

- [ ] Structured logging (JSON) — единый формат для всех Python сервисов
- [ ] Log aggregation: Loki
- [ ] Log levels: ERROR (alert), WARN (investigate), INFO (audit), DEBUG (dev only)
- [ ] PII masking: email, имена → masked автоматически
- [ ] Company code snippets в логах → masked (security B2B)
- [ ] Correlation ID: сквозной `trace_id` + `session_id` + `org_id` через все сервисы

### Tracing

- [ ] Distributed tracing: OpenTelemetry → Jaeger/Tempo
- [ ] Auto-instrumentation для FastAPI
- [ ] Trace sampling: 100% для errors, 10% для normal, 1% для health checks
- [ ] Agent session tracing: полный путь Strategist → Designer → Coach → RAG search
- [ ] LLM call spans: model, tokens, latency, cache hit/miss

### Alerting

| Priority | Триггер | Действие | SLA |
|----------|---------|----------|-----|
| P0 (Page) | Coach sessions failing > 5%, Identity down, RAG search > 2s p95 | Немедленный вызов | 5 мин |
| P1 (Notify) | LLM latency degradation, embedding backlog > 1000, trust recalc stuck | Slack notification | 15 мин |
| P2 (Ticket) | Non-critical failures, capacity warnings, org approaching limits | Создать тикет | 24 часа |

- [ ] Alert fatigue prevention: не более 5 алертов в день на дежурного
- [ ] Runbooks: каждый P0/P1 алерт имеет привязанный runbook

---

## Dashboards

### System Overview
- Health всех сервисов (identity, ai, learning, rag, notification)
- Error rate, latency p50/p95/p99 per service
- SLO burn rate, error budget remaining

### Agent Performance
- Coach session metrics: длительность, фаза, completion rate
- LLM usage: tokens consumed, latency distribution, cache hit rate
- Agent errors: failed generations, timeouts, retries

### RAG Pipeline
- Ingestion: documents/min, queue depth, error rate
- Search: latency distribution, relevance scores, empty results rate
- Index: size per org, embedding generation throughput

### Organization Dashboard (per org)
- Active users, missions started/completed
- Trust Level distribution и progression
- Resource usage (LLM tokens, storage, API calls)
- Average onboarding time (цель: < 30 дней)

### Infrastructure
- CPU, memory, disk, network per service
- PostgreSQL: connections, query time, cache hit ratio
- Redis: memory, connections, hit rate
- pgvector: index size, search performance

---

## Per-Org Resource Tracking

B2B модель требует точного учёта ресурсов per organization:

| Ресурс | Метрика | Единица |
|--------|---------|---------|
| LLM tokens | Input + output tokens per org | tokens/month |
| RAG storage | Vector index + documents per org | GB |
| API calls | Requests per org | calls/month |
| Coach sessions | Session count + duration per org | hours/month |
| Active users | Unique active users per org | users/month |

Данные агрегируются для:
- Биллинга (org billing dashboard)
- Capacity planning (прогноз роста)
- Fair usage enforcement (rate limits per org)
