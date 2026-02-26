# EduPlatform — Roadmap

> **Подход:** Product-first. Сначала уникальные фичи, которые дифференцируют продукт.
> Оптимизация и масштабирование — после того как продукт доказал ценность.
>
> **Ключевая ставка:** не "ещё один видеокурсник", а **Learning Velocity Platform** —
> AI-ускорение обучения через адаптивные пути, spaced repetition, Socratic tutoring
> и knowledge graphs.

---

## Стадии развития продукта

```
Foundation ✅ → Learning Intelligence (← мы здесь) → Growth → Scale
```

| Стадия | Пользователи | Суть | Критерий перехода |
|--------|-------------|------|-------------------|
| Foundation | до 10K | Базовая платформа, полный цикл обучения | ✅ 201 тест, 157 RPS, p99=51ms |
| **Learning Intelligence** | **10K → 100K** | **AI-тьютор, квизы, spaced repetition, knowledge graph, gamification** | **Completion rate > 40%, retention 7d > 60%** |
| Growth | 100K → 1M | Реальные платежи, seller dashboard, SEO, mobile, CI/CD | Revenue $100K/мес, 1000 teachers |
| Scale | 1M → 10M | Rust gateway, event bus, video platform, multi-region | 5K+ RPS, horizontal scaling |

---

## Навигация по документам

| # | Документ | Описание |
|---|----------|----------|
| 01 | [Видение продукта](./01-PRODUCT-VISION.md) | Learning Velocity Engine, core loop, метрики |
| 02 | [Архитектура](./02-ARCHITECTURE-PRINCIPLES.md) | ADR, принципы, выбор технологий |
| 03 | [Инфраструктура](./03-INFRASTRUCTURE.md) | Docker, мониторинг, стоимость |
| 04 | [Домены](./04-DOMAINS.md) | Bounded contexts, event matrix |
| 05 | [Стратегия данных](./05-DATA-STRATEGY.md) | Polyglot persistence, CQRS |
| 06 | [Безопасность](./06-SECURITY.md) | Threat model, compliance |
| 07 | [Видео и медиа](./07-VIDEO-MEDIA.md) | CDN, транскодирование |
| 08 | [Монорепа и DX](./08-MONOREPO-DX.md) | Build tools, testing strategy |
| 09 | [Observability](./09-OBSERVABILITY.md) | Prometheus, Grafana, метрики |
| 10 | [Frontend](./10-FRONTEND.md) | Next.js, UI Kit, performance |
| 11 | [AI Agent Standards](./11-AI-AGENT-STANDARDS.md) | MCP, context engineering, AI safety |

Продуктовая стратегия — [`strategy/PRODUCT-VISION.md`](../strategy/PRODUCT-VISION.md).

---

## Foundation — до 10K пользователей ✅ DONE

### Phase 0 — MVP ✅ DONE

Полный цикл: admin верифицирует teacher → teacher создаёт курс с модулями и уроками → student находит курс → записывается → проходит уроки → видит прогресс → оставляет отзыв.

- 5 Python-сервисов (identity, course, enrollment, payment, notification)
- Buyer frontend (Next.js): каталог, поиск, курс, уроки, прогресс, отзывы, admin
- Docker Compose (dev + prod), Prometheus + Grafana, Locust, seed data
- 113 тестов, baseline 55 RPS

### Phase 1 — Оптимизация + UX ✅ DONE

| Milestone | Что сделано | Результат |
|-----------|-------------|-----------|
| 1.0 | pg_trgm GIN index, pool 5→20 | search p99: 803ms → <50ms |
| 1.1 | Redis cache, FK indexes, cursor pagination | 157 RPS, p99=51ms, pool 10% |
| 1.2 | JWT refresh, rate limiting, CORS, XSS, health checks | 146 тестов |
| 1.3 | Categories, email verify, forgot password, auto-completion, TanStack Query | 157 тестов |

**Итого Foundation:** 201 тест, 7 backend сервисов + frontend + shared lib, полный user journey.

---

## Learning Intelligence — 10K → 100K пользователей 🔵 IN PROGRESS

> **Цель:** превратить "видеокурсник" в платформу ускоренного обучения.
> Каждая фаза добавляет один evidence-based механизм повышения retention и completion.
>
> **Baseline (индустрия):** 13% completion rate, пассивное видео.
> **Target:** 40%+ completion, 60%+ retention (7d), активное обучение.

### Phase 2.0 — AI Service + Quiz Foundation

> **Цель:** от пассивного видео к активному обучению. Квизы после каждого урока.

| # | Задача | Зачем | Статус |
|---|--------|-------|--------|
| 2.0.1 | AI Service (Python): model routing (cheap/mid/expensive) | Центральная точка LLM-вызовов | ✅ |
| 2.0.2 | Gemini Flash API интеграция + Redis кэширование ответов | Дешёвая генерация ($0.08/M tokens) | ✅ |
| 2.0.3 | Quiz model в Learning Engine: questions, answers, attempts | Активное вспоминание | ✅ |
| 2.0.4 | AI Quiz Generator: авто-генерация вопросов из lesson content | Масштабирование без ручной работы | ✅ |
| 2.0.5 | AI Lesson Summary: краткое содержание каждого урока | Быстрый повтор | ✅ |
| 2.0.6 | Frontend: quiz UI после урока + summary блок | UX активного обучения | ✅ |
| 2.0.7 | Тесты: AI service + learning engine + frontend | Качество | ✅ |

**Метрики:** quiz completion rate, accuracy, time-on-quiz.
**Evidence:** Active recall → +25% retention vs passive review.

---

### Phase 2.1 — Spaced Repetition + Flashcards

> **Цель:** долгосрочное запоминание через научно обоснованное повторение.

| # | Задача | Зачем | Статус |
|---|--------|-------|--------|
| 2.1.1 | FSRS интеграция (py-fsrs, open source) | Алгоритм оптимального повторения | ✅ |
| 2.1.2 | Flashcard model: cards из quiz-ошибок + ключевые концепты | Автоматическая генерация карточек | ✅ |
| 2.1.3 | Smart notifications: FSRS-scheduled review reminders | "Пора повторить!" в нужный момент | 🔴 |
| 2.1.4 | Frontend: flashcard UI (swipe, rate difficulty) | UX повторения | ✅ |
| 2.1.5 | "Review due" badge в header + dashboard | Вовлечение | ✅ |
| 2.1.6 | Тесты: FSRS scheduling, card CRUD | Качество | ✅ |

**Метрики:** retention rate (7d, 30d), review streak, забывание vs baseline.
**Evidence:** Spaced repetition → +60% long-term retention vs massed study.

---

### Phase 2.2 — Socratic AI Tutor

> **Цель:** глубокое понимание через диалог. AI не даёт ответ — ведёт к нему.

| # | Задача | Зачем | Статус |
|---|--------|-------|--------|
| 2.2.1 | Chat interface per lesson (ask questions about content) | Контекстная помощь | ✅ |
| 2.2.2 | Socratic prompt pipeline (Gemini Flash) | Наводящие вопросы вместо ответов | ✅ |
| 2.2.3 | Контекст: lesson content как RAG-источник | Тьютор знает материал урока | ✅ |
| 2.2.4 | Rate tutor response (thumbs up/down) | Улучшение промптов | ✅ |
| 2.2.5 | Frontend: chat drawer на странице урока | UX | ✅ |
| 2.2.6 | Тесты: tutor service, prompt pipeline | Качество | ✅ |

**Метрики:** questions asked/lesson, understanding score, NPS.
**Evidence:** Socratic method → deeper conceptual understanding (Khanmigo model).

---

### Phase 2.3 — Knowledge Graph + Adaptive Path

> **Цель:** персонализация. Пропускай известное, фокусируйся на пробелах.

| # | Задача | Зачем | Статус |
|---|--------|-------|--------|
| 2.3.1 | Concept model: knowledge points per course (teacher-defined) | Граф знаний курса | ✅ |
| 2.3.2 | Concept mastery tracking (per-student, 0.0→1.0) | Персональный уровень | ✅ |
| 2.3.3 | Adaptive pre-test: входной тест → определение уровня | Пропуск изученного | 🔴 YAGNI |
| 2.3.4 | Learning Velocity Dashboard: concepts/hour, тренд | Метакогниция | 🔴 YAGNI |
| 2.3.5 | Frontend: mastery progress + teacher concept management | Визуальная карта знаний | ✅ |
| 2.3.6 | Teacher UI: concept CRUD + prerequisites per course | Создание графа | ✅ |
| 2.3.7 | Тесты: concept CRUD, mastery, quiz integration | Качество | ✅ |

**Метрики:** time-to-competency, concepts mastered/week, skip rate.
**Evidence:** Squirrel AI knowledge graph (10K+ points) → TIME Best Invention 2025.

---

### Phase 2.4 — Gamification + Community

> **Цель:** мотивация и accountability. Превратить обучение в привычку.

| # | Задача | Зачем | Статус |
|---|--------|-------|--------|
| 2.4.1 | XP system: earn XP за lesson/quiz/review/flashcard | Мотивация | 🔴 |
| 2.4.2 | Streaks: daily learning streak (модель Duolingo) | Привычка | 🔴 |
| 2.4.3 | Badges/achievements (first course, 7-day streak, 100% mastery) | Milestones | 🔴 |
| 2.4.4 | Leaderboard per course (opt-in) | Соревнование | 🔴 |
| 2.4.5 | Course discussions: комментарии per lesson | Сообщество | 🔴 |
| 2.4.6 | Frontend: XP counter, streak flame, badge shelf | UX | 🔴 |
| 2.4.7 | Notification: streak at risk reminders | Retention | 🔴 |
| 2.4.8 | Тесты: XP calculation, streak logic, badges | Качество | 🔴 |

**Метрики:** DAU/MAU ratio, streak > 7d %, completion rate delta.
**Evidence:** Gamification + community → up to 96% completion rate.

---

### Phase 2.5 — MVP Polish + Demo Ready

> **Цель:** продукт готов к показу первым пользователям и инвесторам.

| # | Задача | Зачем | Статус |
|---|--------|-------|--------|
| 2.5.1 | Onboarding flow: guided first course experience | First-time UX | 🔴 |
| 2.5.2 | Landing page: value proposition, demo видео | Конверсия | 🔴 |
| 2.5.3 | Responsive mobile web | Мобильный доступ | 🔴 |
| 2.5.4 | Demo script update: показывает AI-фичи | Презентация | 🔴 |
| 2.5.5 | Seed data: courses с квизами, flashcards, concepts | Демо-данные | 🔴 |
| 2.5.6 | Bug fixes, UI polish, error states | Качество | 🔴 |

**Критерий:** можно показать продукт, провести demo, получить feedback.

---

## Growth — 100K → 1M пользователей (после MVP)

> Монетизация, teacher tools, инфраструктура. Только после валидации Learning Intelligence.

| Milestone | Содержание | Статус |
|-----------|-----------|--------|
| 3.1 | Реальные платежи (Stripe) + subscription tiers | 🔴 |
| 3.2 | Seller App: teacher dashboard, аналитика, revenue | 🔴 |
| 3.3 | SEO: meta tags, structured data, OG | 🔴 |
| 3.4 | CI/CD: GitHub Actions (lint → test → build) | 🔴 |
| 3.5 | Email delivery (SMTP/Resend вместо stub) | 🔴 |
| 3.6 | Certificate generation (PDF) | 🔴 |

---

## Scale — 1M → 10M пользователей (далёкое будущее)

> Тяжёлая инфраструктура. Только когда Growth упрётся в потолок.

| Milestone | Содержание | Статус |
|-----------|-----------|--------|
| 4.1 | API Gateway (Rust/Axum) | 🔴 |
| 4.2 | NATS JetStream event bus | 🔴 |
| 4.3 | Video platform (upload → transcode → HLS) | 🔴 |
| 4.4 | PostgreSQL read replicas / Citus | 🔴 |
| 4.5 | Self-hosted SLM (замена API на свои модели) | 🔴 |
| 4.6 | Multi-region, K8s, auto-scaling | 🔴 |

---

## Принцип принятия решений

```
Сначала продукт, потом инфраструктура.
Сначала фичи, которые меняют метрики обучения, потом оптимизация.
Каждая фича — ответ на конкретную проблему (87% курсов не завершаются).
Не масштабировать ДО того, как продукт доказал ценность.
AI дешёвый ($0.03/user/мес) — не бояться внедрять.
```
