# 05 — Стратегия данных

> Владелец: Architect / Data Lead
> Последнее обновление: 2026-03-05
>
> Обновлено под B2B pivot. Фокус на org-scoped isolation и RAG storage.

---

## Принцип: Organization-scoped data isolation

Все данные, привязанные к контенту компании, содержат `organization_id`:

```sql
-- Каждый запрос к org-scoped данным:
SELECT * FROM missions WHERE user_id = $1 AND organization_id = $2;
SELECT * FROM chunks WHERE knowledge_base_id IN (
  SELECT id FROM knowledge_bases WHERE organization_id = $1
);
```

**Исключения** (общесистемные): users, auth tokens, system notifications.

**Enforcement:** application-level filtering через service layer. org_id берётся из JWT claims или path parameter, никогда из request body.

---

## Хранилища данных

| Хранилище | Назначение | Сервисы |
|-----------|-----------|---------|
| PostgreSQL | Основная БД, каждый сервис — своя | Все |
| PostgreSQL + pgvector | Embeddings, vector search | RAG (:8008) |
| Redis | Cache, agent memory, session state, rate limiting | AI (:8006), все |
| S3/local storage | Оригиналы документов | RAG (:8008) |

---

## pgvector для embeddings

### Конфигурация

- **Dimensions:** 768 (Gemini Embedding model)
- **Index type:** ivfflat (быстрый build, достаточная точность для < 10M vectors)
- **Distance metric:** cosine similarity
- **Lists parameter:** sqrt(n_vectors) для ivfflat

### Схема хранения

```sql
CREATE TABLE chunks (
    id UUID PRIMARY KEY,
    document_id UUID NOT NULL REFERENCES documents(id),
    organization_id UUID NOT NULL,
    content TEXT NOT NULL,
    metadata JSONB,           -- source file, line numbers, language
    embedding vector(768),
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_chunks_embedding ON chunks
    USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);

CREATE INDEX idx_chunks_org ON chunks (organization_id);
```

### Sizing per company

| Размер компании | Repos | Chunks | Embeddings storage | Index overhead |
|-----------------|-------|--------|-------------------|----------------|
| Small (5 repos) | 5 | 10K | ~30 MB | ~6 MB |
| Medium (20 repos) | 20 | 50K | ~150 MB | ~30 MB |
| Large (100 repos) | 100 | 250K | ~750 MB | ~150 MB |

### Total sizing (Phase 2, 50 companies)

```
50 companies × 50K chunks avg = 2.5M vectors
Embeddings: 2.5M × 768 × 4 bytes = ~7.5 GB
ivfflat index: ~1.5 GB
Chunk text content: ~2.5 GB
Total pgvector DB: ~12 GB
→ Один PostgreSQL instance с 32GB RAM справится.
```

---

## Document/Chunk storage

### Document model

```sql
CREATE TABLE documents (
    id UUID PRIMARY KEY,
    knowledge_base_id UUID NOT NULL REFERENCES knowledge_bases(id),
    organization_id UUID NOT NULL,
    source_type VARCHAR(20) NOT NULL,  -- 'github', 'upload', 'confluence'
    source_path TEXT NOT NULL,          -- 'repo/path/to/file.py'
    content_hash VARCHAR(64),           -- SHA-256 для dedup
    language VARCHAR(20),               -- 'python', 'go', 'markdown'
    chunk_count INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);
```

### Chunking strategy

- **Chunk size:** 512 tokens (оптимально для embedding quality)
- **Overlap:** 64 tokens (контекст на границах)
- **Code files:** chunk по функциям/классам (AST-based), fallback на token-based
- **Markdown:** chunk по sections (headers), fallback на token-based
- **Metadata:** source file path, line numbers, language tag

---

## Redis usage

### Agent Memory (AI service)

| Key pattern | TTL | Описание |
|-------------|-----|----------|
| `agent:session:{session_id}` | 30 min | Текущая coach session state |
| `agent:path:{user_id}:{org_id}` | 24h | Strategist learning path cache |
| `agent:mission:{mission_id}` | 1h | Designer mission draft |
| `agent:conversation:{session_id}` | 30 min | Coach conversation history |

### Cache (existing)

| Key pattern | TTL | Описание |
|-------------|-----|----------|
| `cache:*` | 5 min | General response cache |
| `ai:response:*` | 24h | AI response cache |
| `rate:*` | 1 min | Rate limiting counters |

### Memory sizing

| Phase | Users | Agent sessions/day | Redis memory |
|-------|-------|-------------------|-------------|
| Pilot | 100 | 100 | < 500 MB |
| Growth | 5K | 5K | ~2 GB |
| Scale | 10K+ | 10K+ | ~5 GB |

---

## Базы данных по сервисам

| Сервис | БД | Порт | Ключевые таблицы | Org-scoped |
|--------|----|------|-------------------|------------|
| Identity | identity-db | 5433 | users, refresh_tokens, organizations, org_memberships | Частично |
| RAG | rag-db | 5439 | knowledge_bases, documents, chunks (pgvector) | Да |
| AI | — | — | Stateless (Redis + LLM) | N/A |
| Learning | learning-db | 5438 | missions, trust_levels, quizzes, flashcards, concepts | Да |
| Notification | notification-db | 5437 | notifications, conversations, messages | Нет |
| Payment | payment-db | 5436 | org_subscriptions, org_invoices | Да |

### Dormant (не развиваются)

| Сервис | БД | Порт |
|--------|----|------|
| Course | course-db | 5434 |
| Enrollment | enrollment-db | 5435 |

---

## Data lifecycle

### Ingestion pipeline

```
GitHub repo → clone → parse files → chunk → embed → store in pgvector
                                          ↓
                                    extract concepts → store in learning-db
```

### Re-indexing

- **Trigger:** manual (admin API) или webhook (GitHub push)
- **Strategy:** content_hash comparison, only re-embed changed chunks
- **Concurrency:** background job, не блокирует search

### Data retention

| Данные | Retention | Причина |
|--------|-----------|---------|
| Embeddings | Пока org active | Нужны для search |
| Mission history | 2 years | Analytics, compliance |
| Agent conversation logs | 90 days | Debugging, improvement |
| Trust level history | Indefinite | Audit trail |
| Chunk content | Пока org active | RAG source |

---

## Compliance и Privacy

- **Org data isolation:** application-level, org_id на всех запросах
- **Code confidentiality:** embeddings хранятся отдельно от оригинального кода
- **GDPR:** right to deletion = delete all org data (cascading)
- **Data export:** org admin может запросить export всех данных организации
- **Audit logging:** all admin actions logged с timestamp и actor
