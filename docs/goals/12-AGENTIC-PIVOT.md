# 12 — Пивот: Agentic Adaptive Learning для B2B-онбординга инженеров

> Этот документ заменяет 01-PRODUCT-VISION.md как целевой ориентир продукта.

## Миссия

Сократить онбординг инженера с 3 месяцев до 1 месяца через персонального AI-ментора, обученного на кодовой базе и архитектуре компании. 15 минут в день — новичок в контексте без стресса.

## Целевой клиент

**B2B:** Технологические компании, онбордящие Mid/Senior инженеров.

**Боль:** Первые 2-3 месяца новичок отвлекает Senior'ов вопросами ("как поднять локальную базу?", "почему этот микросервис отваливается?"). Стоимость онбординга одного инженера: $10K-30K (потеря продуктивности команды).

**Ценность:** AI-ментор, обученный на реальном коде и доках компании, проводит 15-минутные сессии. Senior'ы не отвлекаются. Новичок набирает контекст в 3 раза быстрее.

## Ключевые метрики

| Метрика | Baseline | Target (6 мес) |
|---------|----------|-----------------|
| Time-to-productivity | 90 дней | 30 дней |
| Senior interruptions/day | 5-8 | 1-2 |
| Knowledge retention (7d) | ~30% | 70%+ |
| Daily session completion | N/A | 80%+ |
| D30 Retention | N/A | 60%+ |

## Архитектура: Tri-Agent System

Три агента, каждый со своей зоной ответственности:

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
- Идёт в RAG (код, доки, ADR компании)
- Собирает миссию: выжимка + вопросы + code case из **реального кода**
- Калибрует сложность под текущий mastery level

### Coach Agent
- Проводит 15-минутную сессию в формате чата
- Сократовский метод: не даёт ответ, задаёт наводящий вопрос
- Настраиваемая личность (строгий/дружелюбный/с юмором)
- Собирает телеметрию: время ответа, правильность, уверенность

## Ключевые сущности

### Mission (15-минутная сессия)
```
Mission {
  id, user_id, organization_id
  concept_id          — какой концепт изучаем
  type: daily | review | remedial
  status: pending | in_progress | completed

  recap_questions[]   — 2 вопроса по вчерашнему (spaced repetition)
  reading_content     — 2-мин выжимка из RAG
  check_questions[]   — 3 вопроса на понимание
  code_case           — реальный код с задачей

  started_at, completed_at
  score, mastery_delta
}
```

### Trust Level (заменяет XP)
```
TrustLevel {
  user_id, organization_id
  level: 0-5
  unlocked_areas[]    — что разблокировано (repos, envs, tools)

  Прогрессия:
  0 = Newcomer     — только чтение доков
  1 = Explorer     — доступ к dev окружению
  2 = Contributor  — доступ к staging repos
  3 = Builder      — доступ к prod repos (read)
  4 = Guardian     — code review capabilities
  5 = Architect    — full access
}
```

### Company Knowledge Base
```
KnowledgeBase {
  organization_id
  sources[]: github_repos, confluence_spaces, markdown_files
  concepts[]: extracted entities with relationships
  embeddings: pgvector index для semantic search
}
```

## Что переиспользуем

| Существующий компонент | Новая роль |
|----------------------|------------|
| Identity service (auth, JWT, roles) | + Organizations, Trust Levels |
| AI service (Gemini client, cache, credits) | + Tri-Agent orchestration |
| Learning service (FSRS, concepts, mastery) | + Missions, session tracking |
| Knowledge graph (concepts + prerequisites) | → Company knowledge graph |
| Socratic tutor (TutorService) | → Coach Agent |
| Quiz generation (AIService) | → Mission question generation |
| Flashcards (FSRS) | → Spaced repetition в recap |
| Streaks | → Daily session streaks |
| Common lib (config, errors, security, DB) | Без изменений |
| Docker, Prometheus, Grafana | Без изменений |

## Что строим нового

| Компонент | Сервис | Порт |
|-----------|--------|------|
| RAG service (ingestion, embeddings, search) | `services/py/rag/` | 8008 |
| Strategist Agent | `services/py/ai/` (расширение) | 8006 |
| Designer Agent | `services/py/ai/` (расширение) | 8006 |
| Coach Agent (эволюция Tutor) | `services/py/ai/` (расширение) | 8006 |
| Mission Engine | `services/py/learning/` (расширение) | 8007 |
| Trust Level System | `services/py/learning/` (расширение) | 8007 |
| Organization Model | `services/py/identity/` (расширение) | 8001 |
| GitHub/Docs Adapter | `services/py/rag/` | 8008 |
| Frontend: Mission UX, Coach Chat, Graph | `apps/buyer/` (redesign) | 3000 |

## Бизнес-модель

| Тир | Цена | Включено |
|-----|------|----------|
| **Pilot** | $1K-3K/мес | 1 repo + docs, до 20 инженеров, базовые агенты |
| **Enterprise** | $10K+/мес | Все интеграции (GitHub/Jira/Slack), PR-анализ, custom agents |
| **Outcome-based** | Per completion | Плата за успешно прошедших онбординг |

## Спринты реализации

| Sprint | Тема | Задач | Зависимости |
|--------|------|-------|-------------|
| 17 | RAG Foundation | 5 | — |
| 18 | Tri-Agent System | 5 | 17 |
| 19 | Mission Engine + Trust Levels | 6 | 18 |
| 20 | Company Integration + Multi-tenant | 5 | 17 |
| 21 | Frontend: Mission UX + Coach Chat | 5 | 18, 19 |
| 22 | B2B: Admin + Pricing + Analytics | 4 | 20, 21 |

**Total: 30 задач, 6 спринтов.**

Sprint 8 (DevOps) остаётся как есть — CI/CD и email нужны для любого запуска.
