# 03 — Инфраструктура и масштабирование

> Владелец: Architect / SRE Lead
> Последнее обновление: 2026-03-05
>
> Обновлено под B2B pivot. Фокус на org-scoped нагрузку и LLM costs.

---

## Стратегия масштабирования по фазам

### Phase 1: Pilot — 1-5 компаний, < 100 пользователей

Минимальная инфраструктура. Один Docker Compose на одном сервере.

| Компонент | Конфигурация | Оценка стоимости/мес |
|-----------|-------------|---------------------|
| API (Python) | 5 active сервисов + RAG | $150 |
| PostgreSQL | 6 БД (identity, ai, learning, notification, rag, payment) | $100 |
| Redis | 1 инстанс, 4GB (cache + agent memory) | $50 |
| LLM API (Gemini Flash) | ~100 users × 1 mission/day × 30 days | $100-200 |
| Embedding API | One-time per repo + incremental | $10-20 |
| Object Storage | < 100GB (documents, chunks) | $5 |
| **Итого** | | **~$400-500/мес** |

**Revenue (5 Pilot clients):** $5K-15K/мес → **Margin: 90%+**

---

### Phase 2: Growth — 5-50 компаний, < 5K пользователей

Multi-worker deployment. Redis cluster для session state.

| Компонент | Конфигурация | Оценка |
|-----------|-------------|--------|
| API (Python) | 3-5 workers per service, Gunicorn/Uvicorn | $800 |
| PostgreSQL | 6 БД + read replicas для RAG search | $500 |
| Redis Cluster | 3 nodes, 16GB total (agent memory + cache) | $300 |
| LLM API | ~5K users × daily sessions | $1,000-2,000 |
| Embedding API | 50 companies × incremental re-index | $100 |
| pgvector | Dedicated resources для vector search | incl. in PG |
| **Итого** | | **~$3,000-4,000/мес** |

**Revenue (50 clients):** $50K-150K/мес → **Margin: 95%+**

---

### Phase 3: Scale — 50+ компаний, 10K+ пользователей

Kubernetes, horizontal scaling, dedicated vector search.

| Компонент | Конфигурация | Оценка |
|-----------|-------------|--------|
| K8s cluster (managed) | EKS/GKE, 10-20 nodes | $3,000 |
| API pods | HPA, 3-10 pods per service | incl. |
| PostgreSQL | Managed (RDS/CloudSQL), multi-AZ | $2,000 |
| Redis Cluster | Managed, 64GB | $500 |
| LLM API | 10K+ users, model routing optimization | $5,000-10,000 |
| Vector DB | Dedicated pgvector instance или Qdrant | $500 |
| Monitoring | Prometheus + Grafana (managed) | $300 |
| **Итого** | | **~$12,000-16,000/мес** |

---

## RAG Service Sizing

### pgvector capacity per company

| Метрика | Типичная компания | Крупная компания |
|---------|-------------------|------------------|
| Repos | 5-20 | 50-200 |
| Total code + docs | 50-200 MB | 1-5 GB |
| Chunks (512 tokens) | 10K-50K | 100K-500K |
| Embeddings (768 dims, float32) | 30-150 MB | 300 MB-1.5 GB |
| ivfflat index | ~20% overhead | ~20% overhead |

### Embedding throughput

| Операция | Latency | Throughput |
|----------|---------|------------|
| Single embedding (Gemini) | ~100ms | 10/sec |
| Batch embedding (100 chunks) | ~2 sec | 50/sec |
| Full repo re-index (50K chunks) | ~17 min | batch job |
| Semantic search (top-10) | < 50ms | — |

### Total pgvector sizing (Phase 2, 50 companies)

```
50 companies × 50K chunks average = 2.5M vectors
2.5M × 768 dims × 4 bytes = ~7.5 GB vectors
+ ivfflat index overhead (~20%) = ~9 GB total
PostgreSQL с 32GB RAM справится без проблем.
```

---

## LLM Cost Estimates

### Per-user per-day cost (1 daily Mission)

| Вызов | Tokens (in/out) | Cost (Gemini Flash) |
|-------|-----------------|---------------------|
| Strategist (path planning) | 2K/500 | $0.0003 |
| Designer (mission assembly) | 3K/2K | $0.001 |
| RAG search (3 queries) | — | $0 (local pgvector) |
| Coach (5 exchanges avg) | 5K/2K | $0.002 |
| Recap scoring | 1K/200 | $0.0002 |
| **Total per user/day** | | **~$0.004** |
| **Per user/month (22 work days)** | | **~$0.08** |

### Per-company cost

| Tier | Users | LLM cost/мес | Revenue | Margin |
|------|-------|-------------|---------|--------|
| Pilot (20 seats) | 20 | $1.60 | $1K-3K | 99%+ |
| Enterprise (100 seats) | 100 | $8 | $10K+ | 99%+ |
| Large (500 seats) | 500 | $40 | $50K+ | 99%+ |

> LLM costs negligible. Основные расходы — infrastructure и engineering time.

---

## Текущая инфраструктура (Phase 1)

### Docker Compose

- `docker-compose.dev.yml` — hot reload, все сервисы
- `docker-compose.prod.yml` — production mode, Prometheus + Grafana

### Порты

| Сервис | Порт | БД порт | Статус |
|--------|------|---------|--------|
| Identity | 8001 | 5433 | ✅ Active |
| Course | 8002 | 5434 | 💤 Dormant |
| Enrollment | 8003 | 5435 | 💤 Dormant |
| Payment | 8004 | 5436 | 💤 Dormant (кроме org billing) |
| Notification | 8005 | 5437 | ✅ Active |
| AI | 8006 | — | ✅ Active |
| Learning | 8007 | 5438 | ✅ Active |
| RAG | 8008 | 5439 | 🔴 Sprint 17 |
| Buyer frontend | 3000 | — | ✅ Active |

### Мониторинг

- Prometheus: scrape каждые 15s
- Grafana: 22 панели (request rate, latency, error rate, DB connections)
- Health checks: `/health` на каждом сервисе

---

## TODO: Infrastructure

### Pilot (Sprint 17-22)
- [ ] Добавить RAG service в Docker Compose
- [ ] pgvector extension в PostgreSQL image
- [ ] Redis memory для agent state (отдельный DB index)
- [ ] Background job runner для embedding generation

### Growth (Post-launch)
- [ ] Multi-worker deployment (Gunicorn + Uvicorn)
- [ ] PostgreSQL read replicas для RAG search
- [ ] Redis Cluster для agent memory + cache
- [ ] CI/CD: GitHub Actions (lint → test → build → deploy)
- [ ] Backup strategy: daily PG dumps + WAL archiving

### Scale (Future)
- [ ] Managed K8s (EKS/GKE)
- [ ] HPA per service
- [ ] Dedicated vector search (если pgvector bottleneck)
- [ ] Multi-region (если international clients)
