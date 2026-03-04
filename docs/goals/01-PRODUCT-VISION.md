# 01 — Видение продукта: B2B Agentic Adaptive Learning

> Владелец: CEO / CPO
> Последнее обновление: 2026-03-05
>
> Этот документ — авторитетный источник продуктовой стратегии.
> Детали пивота: [12-AGENTIC-PIVOT.md](./12-AGENTIC-PIVOT.md).

---

## Миссия

**Сократить онбординг инженера с 3 месяцев до 1 месяца.**

Персональный AI-ментор, обученный на кодовой базе и архитектуре компании, проводит 15-минутные ежедневные сессии. Senior'ы не отвлекаются. Новичок набирает контекст в 3 раза быстрее.

---

## Целевой клиент

**B2B:** Технологические компании, онбордящие Mid/Senior инженеров.

**Боль:** Первые 2-3 месяца новичок отвлекает Senior'ов вопросами ("как поднять локальную базу?", "почему этот микросервис отваливается?"). Стоимость онбординга одного инженера: $10K-30K (потеря продуктивности команды).

**Ценность:** AI-ментор, обученный на реальном коде и документации компании, проводит структурированные 15-минутные сессии. Senior'ы освобождаются от рутинных вопросов. Новичок получает контекст адаптивно, в своём темпе.

---

## Архитектура: Tri-Agent System

Три AI-агента, каждый со своей зоной ответственности:

```
┌─────────────────────────────────────────────────────┐
│                   STRATEGIST                         │
│  Строит/адаптирует макро-путь обучения              │
│  Input: профиль, mastery graph, результаты сессий   │
│  Output: ordered list of concepts to learn           │
└──────────────┬──────────────────────────┬───────────┘
               │                          │
               ▼                          │
┌──────────────────────────┐              │
│      DESIGNER            │              │
│  Собирает 15-мин миссию  │              │
│  Input: concept + RAG    │              │
│  Output: Mission{        │              │
│    recap (2 вопроса)     │              │
│    reading (2 мин)       │              │
│    questions (3 шт)      │              │
│    code_case (1 шт)      │              │
│  }                       │              │
└──────────┬───────────────┘              │
           ▼                              │
┌──────────────────────────┐              │
│        COACH             │              │
│  Проводит сессию         │              │
│  Сократовский диалог     │              │
│  Фидбек → Strategist     │──────────────┘
│  Адаптивная сложность    │   (телеметрия)
└──────────────────────────┘
```

### Strategist Agent
- Анализирует профиль инженера (стек, опыт, пробелы)
- Строит граф зависимостей из knowledge base компании
- Адаптирует путь: завалил Docker → вставляет микро-урок перед Kubernetes
- Планирует spaced repetition для пройденных концептов

### Content Designer Agent
- Обращается в RAG (код, доки, ADR компании)
- Собирает миссию: выжимка + вопросы + code case из **реального кода**
- Калибрует сложность под текущий mastery level

### Coach Agent
- Проводит 15-минутную сессию в формате чата
- Сократовский метод: не даёт ответ, задаёт наводящий вопрос
- Настраиваемая личность (строгий/дружелюбный/с юмором)
- Собирает телеметрию: время ответа, правильность, уверенность

---

## Ключевые сущности

### Mission (15-минутная сессия)

Центральная единица обучения. Заменяет "урок" из B2C модели.

- `concept_id` — какой концепт изучаем
- `type` — daily (новый материал), review (spaced repetition), remedial (доработка пробелов)
- `recap_questions[]` — 2 вопроса по вчерашнему
- `reading_content` — 2-минутная выжимка из RAG
- `check_questions[]` — 3 вопроса на понимание
- `code_case` — реальный код с задачей
- `score`, `mastery_delta` — результат сессии

### Trust Level (0-5)

Заменяет XP. Прогрессивный доступ к ресурсам компании:

| Level | Название | Доступ |
|-------|----------|--------|
| 0 | Newcomer | Только чтение документации |
| 1 | Explorer | Dev окружение |
| 2 | Contributor | Staging repos |
| 3 | Builder | Prod repos (read) |
| 4 | Guardian | Code review capabilities |
| 5 | Architect | Full access |

### Company Knowledge Base

- Sources: GitHub repos, Confluence spaces, markdown files
- Concepts: извлечённые entities с relationships
- Embeddings: pgvector index для semantic search

---

## Ключевые метрики (North Star)

| Метрика | Baseline | Target (6 мес) |
|---------|----------|-----------------|
| Time-to-productivity | 90 дней | 30 дней |
| Senior interruptions/day | 5-8 | 1-2 |
| Knowledge retention (7d) | ~30% | 70%+ |
| Daily session completion | N/A | 80%+ |
| D30 Retention | N/A | 60%+ |

### Операционные метрики

| Метрика | Target |
|---------|--------|
| Mission generation latency | < 5 sec |
| Coach response time | < 2 sec |
| RAG search relevance (MRR@10) | > 0.7 |
| Daily active engineers / org | > 70% |

---

## Бизнес-модель

| Тир | Цена | Включено |
|-----|------|----------|
| **Pilot** | $1K-3K/мес | 1 repo + docs, до 20 инженеров, базовые агенты |
| **Enterprise** | $10K+/мес | Все интеграции (GitHub/Jira/Slack), PR-анализ, custom agents |
| **Outcome-based** | Per completion | Плата за успешно прошедших онбординг |

### Unit Economics (Pilot, 20 seats)

| Статья | Стоимость/мес |
|--------|---------------|
| LLM API (Gemini Flash) | ~$50-100 |
| Infrastructure | ~$200 |
| Embedding generation (one-time) | ~$10 |
| **Total COGS** | **~$300** |
| **Revenue** | **$1K-3K** |
| **Gross margin** | **70-90%** |

---

## Что переиспользуем из B2C фазы

| Компонент | Статус | Новая роль |
|-----------|--------|------------|
| Identity (auth, JWT, roles) | ✅ Active | + Organizations, Trust Levels |
| AI service (Gemini, cache, credits) | ✅ Active | + Tri-Agent orchestration |
| Learning (FSRS, concepts, mastery) | ✅ Active | + Missions, session tracking |
| Notification (in-app, email, DMs) | ✅ Active | Без изменений |
| Common lib, Docker, monitoring | ✅ Active | Без изменений |
| Course (marketplace) | 💤 Dormant | B2C marketplace не нужен |
| Enrollment | 💤 Dormant | Заменён org membership |
| Payment (individual) | 💤 Dormant | Org subscriptions вместо |

---

## Конкурентные преимущества

1. **Company-specific AI** — обучен на реальном коде и документации, не generic content
2. **Structured 15-min sessions** — не свободный чат, а Mission с recap + reading + questions + code
3. **Spaced repetition** — FSRS обеспечивает долгосрочное запоминание архитектурных решений
4. **Trust Levels** — прогрессивный доступ мотивирует и структурирует онбординг
5. **Measurable ROI** — time-to-productivity как объективная метрика для B2B sales

---

## Целевой User Journey (Engineer)

1. Компания подключает GitHub repos и документацию
2. Admin создаёт onboarding template (или использует готовый)
3. Новый инженер получает приглашение, заполняет профиль (стек, опыт)
4. Strategist строит персональный learning path
5. Каждый день — 15-минутная Mission (recap → reading → questions → code case)
6. Coach проводит сессию: наводящие вопросы, адаптивная сложность
7. Trust Level растёт → разблокируются repos, envs, tools
8. За 30 дней — полный контекст, уверенная навигация по кодовой базе
