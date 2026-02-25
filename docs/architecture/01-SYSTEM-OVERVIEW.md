# 01 — Обзор системы

> Последнее обновление: 2026-02-25
> Стадия: Phase 2.1 (Spaced Repetition + Flashcards)

---

## Что есть сейчас

EduPlatform — учебная платформа с полным циклом обучения. Семь бэкенд-сервисов (Identity, Course, Enrollment, Payment, Notification, AI Service для генерации квизов и саммари через Gemini Flash, Learning Engine для спейс-репитишен квизов и flashcards с FSRS), фронтенд и инфраструктура мониторинга/нагрузочного тестирования. Три роли: Student, Teacher, Admin. Студент может найти курс по категориям и фильтрам, записаться, пройти уроки, отслеживать прогресс (auto-completion при 100%), оставить отзыв, проходить квизы, повторять flashcards по FSRS. Преподаватель может создать курс с модулями и уроками, создавать квизы. Администратор верифицирует преподавателей. Email verification и forgot password. Frontend на TanStack Query с optimistic updates и error boundaries. Оптимизирована производительность (157 RPS, p99 51ms) и надёжность (health checks, rate limiting, CORS, refresh tokens, XSS sanitization).

```
┌─────────────────────────────────────────────────────────────────┐
│                    КЛИЕНТЫ                                       │
│                                                                 │
│     Browser (http://localhost:3001)                              │
│         │                                                       │
│         ▼                                                       │
│   ┌───────────┐                                                 │
│   │  Buyer    │  Next.js 15 / Tailwind CSS 4                    │
│   │  App      │  TypeScript strict                              │
│   │  :3001    │                                                 │
│   └─────┬─────┘                                                 │
│         │  /api proxy (next.config.ts rewrites)                 │
│         │                                                       │
├─────────┼───────────────────────────────────────────────────────┤
│         │          BACKEND SERVICES                              │
│         │                                                       │
│   ┌──────┴──────────────────────────────────────────────────────┐     │
│   │         │           │          │          │           │      │     │
│   ▼         ▼           ▼          ▼          ▼           ▼      ▼     │
│ ┌────────┐ ┌────────┐ ┌────────┐ ┌───────┐ ┌────────┐ ┌──────┐ ┌─────┐│
│ │Identity│ │ Course │ │Enroll- │ │Payment│ │Notif.  │ │  AI  │ │Learn││
│ │ :8001  │ │ :8002  │ │ment    │ │ :8004 │ │ :8005  │ │ :8006│ │:8007││
│ │ Python │ │ Python │ │ :8003  │ │Python │ │ Python │ │Python│ │Pytho││
│ │ FastAPI│ │ FastAPI│ │ Python │ │FastAPI│ │ FastAPI│ │FastA.│ │FastAP││
│ └───┬────┘ └───┬────┘ └───┬────┘ └──┬────┘ └───┬────┘ └──┬───┘ └──┬───┘│
│     │          │          │         │          │          │     │
├─────┼──────────┼──────────┼─────────┼──────────┼──────────┼────┤
│     │        DATA LAYER   │         │          │          │    │
│     │          │          │         │          │          │    │
│ ┌───▼──┐ ┌───▼──┐ ┌───▼──┐ ┌───▼──┐ ┌───▼──┐          ┌───▼──┐  │
│ │iden- │ │cours-│ │enrol-│ │paym- │ │noti- │  (no DB) │learn-│  │
│ │tity  │ │e db  │ │ment  │ │ent db│ │f. db │  AI uses │ing db│  │
│ │db    │ │:5434 │ │db    │ │:5436 │ │:5437 │  Redis   │:5438 │  │
│ │:5433 │ │      │ │:5435 │ │      │ │      │  only    │      │  │
│ └──────┘ └──────┘ └──────┘ └──────┘ └──────┘          └──────┘  │
│                                                              │
│              ┌──────────┐                                    │
│              │  Redis   │  :6379 (cache, rate limiting)      │
│              └──────────┘                                    │
│                                                              │
├──────────────────────────────────────────────────────────────┤
│                   OBSERVABILITY                               │
│                                                              │
│   ┌────────────┐    ┌────────────┐    ┌────────────┐        │
│   │ Prometheus │───▶│  Grafana   │    │   Locust   │        │
│   │   :9090    │    │   :3000    │    │   :8089    │        │
│   └────────────┘    └────────────┘    └────────────┘        │
└──────────────────────────────────────────────────────────────┘
```

---

## Порты

| Сервис | Порт | Протокол |
|--------|------|----------|
| Identity API | 8001 | HTTP/REST |
| Course API | 8002 | HTTP/REST |
| Enrollment API | 8003 | HTTP/REST |
| Payment API | 8004 | HTTP/REST |
| Notification API | 8005 | HTTP/REST |
| AI Service API | 8006 | HTTP/REST |
| Learning Engine API | 8007 | HTTP/REST |
| Buyer Frontend | 3001 | HTTP |
| Identity DB (PostgreSQL) | 5433 | TCP |
| Course DB (PostgreSQL) | 5434 | TCP |
| Enrollment DB (PostgreSQL) | 5435 | TCP |
| Payment DB (PostgreSQL) | 5436 | TCP |
| Notification DB (PostgreSQL) | 5437 | TCP |
| Learning DB (PostgreSQL) | 5438 | TCP |
| Redis | 6379 | TCP |
| Prometheus | 9090 | HTTP |
| Grafana | 3000 | HTTP |
| Locust | 8089 | HTTP |

---

## Стек технологий

| Слой | Технология | Версия | Зачем |
|------|-----------|--------|-------|
| Backend | Python / FastAPI | 3.12 / 0.115+ | Бизнес-логика, Clean Architecture |
| Frontend | Next.js / React / TanStack Query | 15.3 / 19.1 / 5.x | SSR/SSG, App Router, optimistic updates |
| Стили | Tailwind CSS | 4.1 | Утилитарные стили |
| БД | PostgreSQL | 16 (Alpine) | Database-per-service |
| Кэш / Rate limit | Redis | 7 (Alpine) | Course cache (TTL 5min), rate limiting (sliding window), все сервисы |
| ORM | asyncpg | 0.30+ | Raw SQL, parameterized queries |
| Auth | PyJWT + bcrypt | 2.10+ / 4.0+ | JWT HS256, bcrypt хэширование |
| Config | pydantic-settings | 2.7+ | Env vars → typed settings |
| Метрики | prometheus-fastapi-instrumentator | 7.0+ | Автоматические HTTP метрики |
| Monitoring | Prometheus + Grafana | — | Scrape 5s, dashboards |
| Load testing | Locust | — | 3 user types: StudentUser (browse, enroll, curriculum, lessons, progress), SearchUser, TeacherUser |
| Seed | asyncpg + Faker | — | 1 admin + 50K users, 100K courses, ~35K modules, ~210K lessons, 100K reviews, 50K payments, 200K enrollments |
| Packages | uv workspace | — | Python монорепа |
| Docker | Docker Compose | — | Dev (hot reload) + Prod (monitoring) |

---

## Принципы архитектуры (реализованные)

1. **Database-per-service** — у каждого сервиса своя PostgreSQL (6 БД; AI Service stateless — только Redis cache)
2. **Clean Architecture** — routes → services → domain ← repositories
3. **JWT shared secret** — все 7 сервисов валидируют JWT самостоятельно, без обращения к Identity
4. **Клиент-оркестратор** — Frontend оркестрирует вызовы между сервисами (Payment → Enrollment → Notification)
5. **Роли в JWT claims** — `role` (student/teacher/admin), `is_verified` и `email_verified` передаются в extra_claims токена
6. **Forward-only миграции** — SQL файлы, выполняются при старте сервиса
7. **Owner check** — teacher может управлять только своими курсами/модулями/уроками (проверка teacher_id)
8. **Redis everywhere** — все 7 сервисов подключены к Redis (rate limiting + cache в Course и Learning)
9. **Health checks** — `/health/live` (liveness) + `/health/ready` (readiness) на всех 7 сервисах
10. **Refresh token rotation** — JWT access (1h) + refresh (30d) с family-based reuse detection

---

## Что оптимизировано (Phase 1.0–1.2)

| Оптимизация | Было | Стало |
|-------------|------|-------|
| pg_trgm GIN index на courses | search p99 = 803ms | search p99 = 35ms (23x) |
| Connection pool 5 → 5/20 (min/max) | 100% saturation | 10% saturation |
| Redis cache-aside (course, curriculum) | — | TTL 5 min, cache hit |
| FK indexes (11 новых) | full table scan на JOIN | index scan |
| Cursor pagination (keyset) | offset scan | constant time |
| Health checks (/health/live, /health/ready) | — | все 7 сервисов |
| Rate limiting (Redis sliding window) | — | 100/min global, 10/min login, 5/min register |
| CORS middleware | — | env-based origins |
| XSS sanitization (bleach) | — | course/lesson content |
| JWT refresh tokens | 1h access only | access (1h) + refresh (30d) + rotation |
| Graceful shutdown | — | timeout-graceful-shutdown 25s (prod) |

## Чего нет (намеренно, YAGNI)

| Чего нет | Почему | Когда появится |
|----------|--------|---------------|
| API Gateway | Не нужен для 7 сервисов с прямым доступом | Phase 3 (Rust/Axum) |
| Event bus (NATS) | Нет межсервисных событий, клиент оркестрирует | Phase 2 |
| CI/CD | Локальная разработка | Phase 1.7 |
| ~~Email-верификация~~ | ~~YAGNI для текущей стадии~~ | ✅ Phase 1.3 |
| ~~Категории курсов~~ | ~~Пока только поиск~~ | ✅ Phase 1.3 |
| Email отправка (SMTP) | Stub — логирование в stdout | Phase 2 |
