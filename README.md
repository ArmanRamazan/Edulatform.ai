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
  │   Flashcards (FSRS)         Concept Mastery      │
  │   Socratic AI Tutor         Progress Analytics   │
  └──────────────────────────────────────────────────┘
```

Каждый урок автоматически превращается в квизы, саммари и флешкарты. AI-тьютор помогает разобраться в сложных темах через сократический диалог. Knowledge graph отслеживает, что студент *действительно усвоил*, а не просто просмотрел.

## Ключевые метрики

| Метрика | Индустрия | Наша цель |
|---------|-----------|-----------|
| Completion rate | 13% | **40%+** |
| 7-day retention | ~30% | **60%+** |
| Активное обучение | < 5% времени | **> 40% времени** |

## Архитектура

Монорепа: **Python** (бизнес-логика, 7 микросервисов) + **Next.js** (frontend) + **Rust** (performance-critical, Phase 4).

- **7 сервисов**: Identity, Course, Enrollment, Payment, Notification, AI, Learning
- **301 unit-тестов**, нагрузочное тестирование через Locust
- **157 RPS, p99 = 51ms** на текущей стадии
- **AI**: Quiz generation, Summary, Socratic Tutor (Gemini Flash), FSRS spaced repetition
- **Knowledge Graph**: concepts, prerequisites, concept mastery tracking
- Prometheus + Grafana для observability
- Clean Architecture, каждый сервис — своя PostgreSQL

## Быстрый старт

```bash
# Запуск бэкенда (Docker, hot reload)
docker compose -f docker-compose.dev.yml up

# Фронтенд
cd apps/buyer && npm install && npm run dev

# Тесты (301 тестов, 7 сервисов)
uv sync --all-packages
cd services/py/identity && uv run --package identity pytest tests/ -v
cd services/py/course && uv run --package course pytest tests/ -v
cd services/py/enrollment && uv run --package enrollment pytest tests/ -v
cd services/py/payment && uv run --package payment pytest tests/ -v
cd services/py/notification && uv run --package notification pytest tests/ -v
cd services/py/ai && uv run --package ai pytest tests/ -v
cd services/py/learning && uv run --package learning pytest tests/ -v
```

## AI Orchestrator

Автономный executor для реализации roadmap через Claude Code:

```bash
cd tools/orchestrator
./run.sh                        # все оставшиеся фазы
./run.sh --phase 2.4            # конкретный milestone
./run.sh --phase 2.4 --dry-run  # preview задач
./run.sh --resume               # продолжить после паузы
./run.sh --status               # показать прогресс
```

## Документация

- [Technical Overview](docs/TECHNICAL-OVERVIEW.md) — стек, порты, структура, полный quickstart
- [Product Vision](docs/goals/01-PRODUCT-VISION.md) — Learning Velocity Engine, core loop
- [Roadmap](docs/goals/00-ROADMAP.md) — от 10K до 10M пользователей
- [Architecture](docs/goals/02-ARCHITECTURE-PRINCIPLES.md) — ADR, принципы, технологии

## Статус

**Phase 2.3 — Knowledge Graph (завершён).** 7 сервисов, фронтенд, мониторинг, 224 теста. AI-слой: quiz generation, summary, Socratic tutor. Learning Engine: квизы + FSRS flashcards + knowledge graph + concept mastery. Далее — gamification (2.4), MVP polish (2.5), затем Phase 3 (Growth: реальные платежи, seller app, SEO, CI/CD).

| Стадия | Пользователи | Статус |
|--------|-------------|--------|
| **Phase 0 — Foundation** | до 10K | ✅ Готово |
| **Phase 1 — Launch** | 10K → 100K | ✅ Готово |
| **Phase 2 — Learning Intelligence** | 10K → 100K | 🟡 2.0–2.3 ✅, 2.4–2.5 🔴 |
| **Phase 3 — Growth** | 100K → 1M | 🔴 Не начато |
| **Phase 4 — Scale** | 1M → 10M | 🔴 Не начато |
