# EduPlatform — Learning Velocity Platform

**87% онлайн-курсов никогда не завершаются.** Мы это меняем.

EduPlatform — не очередной видеохостинг с прогресс-баром. Это платформа, которая *ускоряет обучение* через AI-адаптацию, активное тестирование и научно обоснованные методы запоминания.

## Проблема

Индустрия онлайн-образования сломана. Completion rate курсов — **13%**. Студенты смотрят видео, не усваивают материал и бросают. Платформы зарабатывают на продаже контента, а не на результате обучения.

## Решение

**Learning Velocity Engine** — AI-слой поверх образовательного контента:

```
  ┌─────────────────────────────────────────────────┐
  │       CONSUME          →       PRACTICE          │
  │   Video / Text              Quiz / Active Recall │
  │   AI Summary                AI-generated tasks   │
  └────────────┬────────────────────────┬────────────┘
               │                        │
  ┌────────────▼────────────────────────▼────────────┐
  │       REINFORCE         →       REFLECT          │
  │   Spaced Repetition         Knowledge Graph      │
  │   Flashcards (FSRS)         Progress Analytics   │
  └──────────────────────────────────────────────────┘
```

Каждый урок автоматически превращается в квизы, саммари и флешкарты. AI-тьютор помогает разобраться в сложных темах через сократический диалог. Система отслеживает, что студент *действительно усвоил*, а не просто просмотрел.

## Ключевые метрики

| Метрика | Индустрия | Наша цель |
|---------|-----------|-----------|
| Completion rate | 13% | **40%+** |
| 7-day retention | ~30% | **60%+** |
| Активное обучение | < 5% времени | **> 40% времени** |

## Архитектура

Монорепа: **Python** (бизнес-логика, 7 микросервисов) + **Next.js** (frontend) + **Rust** (performance-critical, будет).

- **7 сервисов**: Identity, Course, Enrollment, Payment, Notification, AI, Learning
- **201 unit-тест**, нагрузочное тестирование через Locust
- **157 RPS, p99 = 51ms** на текущей стадии
- Prometheus + Grafana для observability
- Clean Architecture, каждый сервис — своя PostgreSQL

## Быстрый старт

```bash
# Запуск бэкенда (Docker, hot reload)
docker compose -f docker-compose.dev.yml up

# Фронтенд
cd apps/buyer && npm install && npm run dev

# Тесты
uv sync --all-packages
cd services/py/identity && uv run --package identity pytest tests/ -v
```

## Документация

- [Technical Overview](docs/TECHNICAL-OVERVIEW.md) — стек, порты, структура, полный quickstart
- [Product Vision](docs/goals/01-PRODUCT-VISION.md) — Learning Velocity Engine, core loop
- [Roadmap](docs/goals/00-ROADMAP.md) — от 10K до 10M пользователей
- [Architecture](docs/goals/02-ARCHITECTURE-PRINCIPLES.md) — ADR, принципы, технологии

## Статус

**Phase 2.1 — Learning Intelligence.** Foundation готов (7 сервисов, фронтенд, мониторинг, тесты). AI-слой: quiz generation, summary. Learning Engine: квизы + попытки + FSRS spaced repetition flashcards. Далее — Socratic tutor, knowledge graph, gamification.
