# Phase 0 — Foundation [COMPLETED, pre-pivot]

> **Эра:** B2C Course Marketplace (до пивота на B2B Agentic Onboarding)
>
> **Статус:** ✅ ЗАВЕРШЕНА. Инфраструктура переиспользуется в B2B продукте.
>
> **Цель:** запустить работающую учебную платформу с полным циклом обучения.

---

## Что было построено

### Инфраструктура (переиспользуется)

- ✅ uv workspace (Python монорепа)
- ✅ Shared library: config (BaseSettings), errors, security (JWT + extra_claims), database (asyncpg pool)
- ✅ Docker Compose dev (hot reload) + prod (monitoring, graceful shutdown)
- ✅ Prometheus + Grafana: RPS, latency p50/p95/p99, error rate, pool metrics
- ✅ Seed script: 50K users + 100K courses (asyncpg COPY)
- ✅ Locust load testing: 3 scenarios

### Identity Service (переиспользуется)

- ✅ POST /register, POST /login, GET/PATCH /me
- ✅ JWT refresh tokens (rotation + family-based reuse detection)
- ✅ Admin role, teacher verification
- ✅ Email verification, forgot password
- ✅ Rate limiting (per-IP Redis sliding window)
- ✅ Health checks (/health/live, /health/ready)
- ✅ Referral program, public profiles, follows

### Сервисы B2C (dormant после пивота)

Эти сервисы были построены для B2C marketplace. Код остается в репозитории, но не используется в B2B продукте:

- **Course Service** (:8002) — CRUD курсов, pg_trgm поиск, модули/уроки, отзывы, категории, bundles
- **Enrollment Service** (:8003) — запись на курс, прогресс, lesson completion, auto-completion
- **Payment Service** (:8004) — mock-оплата, subscriptions, teacher earnings, coupons, refunds, gifts

### Frontend (частично переиспользуется)

- ✅ Next.js 15 buyer app (Tailwind CSS 4, TypeScript strict)
- ✅ TanStack Query + error boundaries + loading skeletons
- ✅ API proxy через Next.js rewrites

---

## Метрики при завершении

- 5 Python сервисов, 7 PostgreSQL баз данных
- 157 unit тестов (identity 48, course 59, enrollment 25, payment 13, notification 12)
- Baseline: 55 RPS → 157 RPS после оптимизации, p99 = 51ms
- Docker Compose dev + prod конфигурации

---

## Примечание

Foundation-слой (Identity, common lib, Docker, monitoring) является фундаментом B2B продукта. Course/Enrollment/Payment сервисы — dormant, могут быть реактивированы если B2B продукт потребует marketplace-функциональность.
