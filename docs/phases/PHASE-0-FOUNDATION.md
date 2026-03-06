# Phase 0 — Foundation [COMPLETED]

> **Статус:** ЗАВЕРШЕНА

## Что было построено

### Инфраструктура
- Монорепа: Python + Rust + TypeScript
- uv workspace для Python, pnpm для frontend, cargo для Rust
- Docker Compose (dev с hot reload, prod с мониторингом)
- PostgreSQL per service (5 баз), Redis для кэша

### Сервисы (5)
- **identity** (8001) — регистрация, логин, JWT auth, профили, email verification, password reset
- **course** (8002) — CRUD курсов, модулей, уроков, отзывов
- **enrollment** (8003) — запись на курсы, отслеживание прогресса
- **payment** (8004) — платежи, подписки (Stripe)
- **notification** (8005) — уведомления

### Архитектура
- Clean Architecture в каждом сервисе (routes → services → domain ← repositories)
- Common library (errors, security, database, config)
- API Gateway на Rust (axum) — JWT validation + reverse proxy
- JWT HS256 с ролями (student/teacher/admin)

### Тесты
- 621 тест по 5 сервисам
- pytest-asyncio, AsyncMock для юнитов
- TDD workflow

## Результат

Работающий фундамент: 5 микросервисов, API gateway, auth, CRUD операции, Docker инфраструктура.
