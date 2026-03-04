# 11 — AI Agent Standards & Tri-Agent System

> Владелец: Architect / AI Lead
> Последнее обновление: 2026-03-05

---

## Контекст

AI — ядро продукта, а не вспомогательная функция. Tri-Agent система обеспечивает адаптивный онбординг: Strategist строит learning path, Designer собирает mission, Coach ведёт Socratic сессию. RAG обеспечивает контекст из кодобазы и документации компании-клиента.

---

## 1. Tri-Agent Orchestration

### Архитектура

```
                     ┌─────────────┐
                     │  Strategist  │  Макро-планирование
                     │  Agent       │  Learning path, concept ordering
                     └──────┬──────┘
                            │ learning_path
                            ▼
                     ┌─────────────┐
                     │  Designer    │  Микро-планирование
                     │  Agent       │  Mission blueprint assembly
                     └──────┬──────┘
                            │ mission_blueprint
                            ▼
                     ┌─────────────┐
                     │  Coach       │  Исполнение
                     │  Agent       │  Socratic session, real-time
                     └─────────────┘
                            ↕
                     ┌─────────────┐
                     │  RAG Service │  Контекст
                     │  (pgvector)  │  Company code/docs search
                     └─────────────┘
```

### Strategist Agent

**Ответственность:** Макро-планирование обучения. Определяет порядок concept-ов, строит learning path, адаптивно перестраивает при отклонениях.

**Входные данные:**
- Профиль инженера (опыт, текущий trust level, пройденные concepts)
- Concept graph организации (зависимости между concepts)
- Результаты pre-test / последних assessments

**Выходные данные — Learning Path:**
```json
{
  "user_id": "uuid",
  "org_id": "uuid",
  "concepts_ordered": [
    {"concept_id": "uuid", "priority": 1, "estimated_missions": 3},
    {"concept_id": "uuid", "priority": 2, "estimated_missions": 2}
  ],
  "estimated_days": 25,
  "replanned_at": "2026-03-05T10:00:00Z",
  "replan_reason": "mastery_threshold_exceeded"
}
```

**Алгоритм:**
1. Topological sort concept graph по зависимостям
2. Приоритизация по: gap analysis (что не знает) → business impact (что важнее для роли) → dependency order
3. Mastery thresholds: concept считается освоенным при mastery >= 0.7
4. Adaptive replanning: если mastery растёт быстрее/медленнее ожидаемого → пересчёт path
5. Триггеры replan: trust level change, 3+ failed missions подряд, явный запрос

### Designer Agent

**Ответственность:** Сборка конкретной mission (ежедневного задания) из learning path и RAG контекста.

**Входные данные:**
- Текущий concept из learning path (от Strategist)
- RAG results: релевантные файлы и документация компании
- User profile: trust level, preferred difficulty

**Выходные данные — Mission Blueprint:**
```json
{
  "mission_id": "uuid",
  "concept_id": "uuid",
  "title": "Understanding the Auth Middleware",
  "phases": {
    "recap": {
      "summary": "Вчера мы разобрали HTTP middleware pattern...",
      "key_points": ["middleware chain", "request/response cycle"]
    },
    "reading": {
      "rag_references": [
        {"file": "src/middleware/auth.ts", "lines": "15-45", "relevance": 0.92}
      ],
      "focus_questions": ["Почему здесь используется bearer token, а не cookie?"]
    },
    "questions": {
      "conceptual": ["Объясни разницу между authentication и authorization"],
      "applied": ["Как бы ты добавил rate limiting в этот middleware?"]
    },
    "code_case": {
      "task": "Реализуй middleware для проверки API key",
      "starter_code": "...",
      "test_cases": ["..."],
      "hints": ["..."]
    },
    "wrap_up": {
      "summary_prompt": "Перечисли 3 главных вывода из сегодняшней миссии"
    }
  },
  "estimated_duration_min": 45,
  "difficulty": "intermediate"
}
```

### Coach Agent

**Ответственность:** Ведение Socratic сессии в реальном времени. Задаёт вопросы, не даёт ответы напрямую, направляет к самостоятельному решению.

**Coach Session Protocol — фазы:**

| Фаза | Описание | Переход |
|------|----------|---------|
| `recap` | Краткое повторение предыдущей сессии, проверка retention | Автоматически после 2-3 вопросов |
| `reading` | Направление к изучению кода/документации из RAG | После подтверждения прочтения |
| `questions` | Socratic вопросы по concept-у, углубление понимания | После 3+ правильных ответов |
| `code_case` | Практическое задание: написать/исправить код | После submit или timeout |
| `wrap_up` | Резюме, self-assessment, preview следующей миссии | Завершение сессии |

**Правила Coach:**
- Никогда не даёт прямой ответ на вопрос. Задаёт наводящие вопросы
- Если инженер застрял 3+ раза — даёт подсказку (hint), не ответ
- Адаптирует сложность в реальном времени на основе ответов
- При каждом ответе обновляет concept mastery estimate
- Максимальная длительность сессии: 60 минут (soft limit с предупреждением)

---

## 2. Agent Memory

### Redis-Based Persistent Profiles

Каждый agent хранит состояние в Redis для персистентности между сессиями.

```
# Ключи в Redis
agent:strategist:{user_id}     → Learning path state (JSON)
agent:coach:{user_id}          → Session history, conversation memory (JSON)
agent:designer:{user_id}       → Last mission context, preferences (JSON)
user:profile:{user_id}         → Aggregated profile for all agents (JSON)
```

**User Profile (shared между agents):**
```json
{
  "user_id": "uuid",
  "org_id": "uuid",
  "trust_level": 2,
  "concepts_mastered": ["uuid1", "uuid2"],
  "concepts_in_progress": [{"id": "uuid3", "mastery": 0.45}],
  "learning_style": "hands-on",
  "avg_session_duration_min": 35,
  "streak_days": 12,
  "total_missions_completed": 28,
  "last_session_at": "2026-03-04T18:00:00Z"
}
```

**TTL:** Profile данные — без TTL (persistent). Session state — 24h TTL с refresh при активности.

---

## 3. RAG Integration

### Pipeline

```
Company Code/Docs → Ingestion → Chunking → Embedding → pgvector Index
                                                            ↓
                                              Designer/Coach → Search Query
                                                            ↓
                                                     Relevant Chunks
```

### Ingestion
- Источники: Git repositories, Confluence/Notion export, internal docs (Markdown, RST)
- Chunking: по функциям/классам для кода, по секциям для документации
- Embedding model: `text-embedding-004` (Google)
- Storage: PostgreSQL + pgvector extension (rag-db, port 5439)
- Org isolation: каждый document привязан к `org_id`, search фильтрует по org

### Search
- Semantic search: cosine similarity по pgvector
- Hybrid: semantic + keyword (для точного поиска по именам функций/классов)
- Top-K: 5-10 chunks per query, с relevance score threshold > 0.7
- Context window management: chunks суммарно < 4K tokens для Coach, < 8K для Designer

### RAG Service (port 8008)

**Endpoints:**
- `POST /rag/ingest` — загрузка документов/кода для индексации (org-admin only)
- `POST /rag/search` — semantic search по indexed content
- `GET /rag/status/{org_id}` — статус индекса организации
- `DELETE /rag/documents/{id}` — удаление документа из индекса

---

## 4. Trust Levels (0-5)

Trust Levels заменяют B2C XP систему. Прогрессивный доступ к возможностям платформы.

| Level | Название | Требования | Разблокированные возможности |
|-------|---------|------------|------------------------------|
| 0 | Observer | Регистрация | Просмотр knowledge graph, чтение документации |
| 1 | Learner | Pre-test пройден | Coach sessions, daily missions |
| 2 | Practitioner | 10+ missions, mastery >= 0.5 по 5+ concepts | Code challenges, peer discussions |
| 3 | Contributor | 30+ missions, mastery >= 0.7 по 15+ concepts | Доступ к production code review задачам |
| 4 | Mentor | 60+ missions, mastery >= 0.8 по 30+ concepts | Менторство новых инженеров, content suggestions |
| 5 | Expert | Верификация тимлидом | Полный доступ, участие в architecture decisions |

**Автоматический расчёт:** Trust level пересчитывается после каждой завершённой mission. Level 5 требует ручной верификации.

---

## 5. LLM Usage

### Model Selection

| Задача | Модель | Обоснование |
|--------|--------|-------------|
| Coach session | Gemini Flash | Низкая latency (< 2s), достаточное качество для Socratic dialogue |
| Strategist planning | Gemini Flash | Structured output, concept ordering |
| Designer assembly | Gemini Flash | Mission blueprint generation |
| Embeddings | text-embedding-004 | Высокое качество для code/docs, 768 dimensions |

### Credit System

| Plan | Лимит | Аудитория |
|------|-------|-----------|
| Trial | 10 sessions/day | Пробный период организации |
| Standard | 100 sessions/day per org | Стандартная подписка |
| Enterprise | Unlimited | Enterprise подписка |

### Caching
- Redis cache для повторяющихся RAG queries (TTL: 1 hour)
- Conversation memory в Redis (per user, per session)
- Embedding cache: не пересчитывать embeddings для неизменённых документов

---

## 6. Safety & Security

### Фундаментальные правила

```
ЗАКОН: Код и документация компании-клиента — конфиденциальные данные.
Никакой код клиента не отправляется внешним сервисам без явного consent организации.
```

### Data Flow Security

| Данные | Где хранятся | Кто имеет доступ | Внешние сервисы |
|--------|-------------|-----------------|-----------------|
| Company code | rag-db (pgvector) | RAG service only | Embedding API (text-embedding-004) — только chunks |
| User PII | identity-db | Identity service only | Никогда |
| Session transcripts | Redis + ai-db | AI service only | LLM API — masked PII |
| Mission blueprints | learning-db | Learning service | Никогда |

### PII Masking

Перед отправкой в LLM:
- Имена пользователей → `[USER]`
- Email → `[EMAIL]`
- Внутренние URLs → `[INTERNAL_URL]`
- API keys/tokens в коде → `[REDACTED]`

### Audit Trail

Каждое взаимодействие с LLM логируется:
```json
{
  "timestamp": "2026-03-05T10:00:00Z",
  "org_id": "uuid",
  "user_id": "uuid",
  "agent": "coach",
  "action": "generate_response",
  "model": "gemini-flash",
  "tokens_in": 1200,
  "tokens_out": 350,
  "latency_ms": 1100,
  "session_id": "uuid",
  "phase": "questions"
}
```

### Org Consent Model

При onboarding организации:
- Явное согласие на отправку code chunks в embedding API
- Опция: self-hosted embedding model (Phase 2)
- Data retention policy: org может запросить полное удаление всех данных
- Geographic data residency: выбор региона хранения (Phase 2)

### Prompt Injection Defence

- UGC (имена, комментарии) sanitize перед подачей в LLM context
- System prompt изолирован от user input (separate message roles)
- Coach не выполняет произвольные инструкции из user messages
- RAG chunks обрабатываются как data, не как instructions

---

## 7. Coding Agent Standards

### CLAUDE.md как Source of Truth

`CLAUDE.md` содержит все правила для coding agents, работающих с кодобазой. Обновляется при каждом архитектурном изменении.

### Security-Critical Zones (повышенное внимание при AI-generated коде)

- `migrations/` — проверка на data loss и locking
- Auth-related код в identity service — authorization logic
- JWT/token handling — проверка на leakage
- RAG ingestion — проверка на injection через indexed content
- Agent prompts — проверка на prompt injection vectors

### Review Checklist для AI-Generated Code

1. Направление зависимостей (Clean Architecture) соблюдено
2. Type hints на всех публичных функциях
3. Тесты покрывают поведение, а не реализацию
4. SQL queries параметризованы ($1, $2, ...)
5. PII не попадает в логи
6. Org isolation: данные одной организации не видны другой

---

## 8. MCP Readiness

### Текущее состояние

MCP Server не создан (YAGNI). Подготовка:
- Endpoints сгруппированы логически (по agent / по domain)
- API responses self-contained (related data, не только IDs)
- `description` в Pydantic models и FastAPI decorators
- OpenAPI spec автогенерируется из FastAPI

### Будущие MCP Resources (когда появится реальный use case)

| Resource | Описание |
|----------|----------|
| `missions` | Текущие и завершённые missions пользователя |
| `concepts` | Knowledge graph: concepts, mastery, dependencies |
| `progress` | Trust level, streak, completion timeline |
| `rag_documents` | Indexed documents организации |

### Будущие MCP Tools

| Tool | Описание |
|------|----------|
| `start_mission` | Начать новую mission |
| `search_knowledge` | Поиск по indexed кодобазе |
| `get_concept_mastery` | Текущий уровень mastery по concept |
| `get_team_progress` | Прогресс команды (admin) |

---

## 9. Implementation Phases

### Phase 1 — Agent Foundation (текущая)

- [ ] Strategist: learning path generation (concept ordering + adaptive replan)
- [ ] Designer: mission blueprint assembly (RAG integration)
- [ ] Coach: Socratic session protocol (5 phases)
- [ ] RAG: ingestion pipeline + pgvector search
- [ ] Agent memory: Redis persistent profiles
- [ ] Trust Levels: auto-calculation + progression

### Phase 2 — Hardening

- [ ] PII masking pipeline (Presidio или custom)
- [ ] Org consent flow для data processing
- [ ] Self-hosted embedding option
- [ ] Advanced RAG: hybrid search, reranking
- [ ] Coach: multi-language support
- [ ] Analytics: per-org onboarding time tracking

### Phase 3 — Scale

- [ ] MCP Server для внешних интеграций
- [ ] AI Gateway: centralized LLM access control
- [ ] Self-hosted SLM для PII-sensitive операций
- [ ] A/B testing mission strategies
- [ ] Multi-org federation

---

## Принцип

```
AI-агенты — ядро продукта, не дополнение.
Tri-Agent система проектируется как первоклассный архитектурный компонент.
Безопасность данных клиента — абсолютный приоритет.
Каждое взаимодействие с LLM — аудируемо, ограничено, изолировано по org.
```
