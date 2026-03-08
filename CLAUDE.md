# CLAUDE.md — Законы кодовой базы

> Это не рекомендации. Это законы. Нарушение любого пункта = невалидный код.

## Проект

Учебная платформа (аналог Udemy/Coursera lite) на 10M пользователей. Монорепа: Python (бизнес-логика) + Rust (performance-critical) + TypeScript/Next.js (frontend). Документация в `docs/goals/` и `docs/phases/`.

## Язык общения

Русский. Комментарии в коде, commit messages, названия переменных и функций — на английском.

## Структура монорепы

Подробно описана в `STRUCTURE.md`. Краткая карта:

```
proto/               — protobuf контракты (source of truth для межсервисного API)
libs/py/             — shared Python: config, logging, errors, db utils
libs/rs/             — shared Rust: common types, proto codegen, rag-chunker (pyo3 FFI)
services/py/         — Python сервисы: identity, course, enrollment, payment, notification, ai, learning, rag, mcp
services/rs/         — Rust сервисы: api-gateway, ws-gateway, embedding-orchestrator
apps/                — Frontend: buyer (Next.js SSR/SSG), seller (Next.js dashboard)
packages/            — Shared frontend: ui/ (UI Kit), api-client/ (codegen), shared/ (utils)
deploy/              — Docker, K8s manifests
tools/               — seed scripts, CLI утилиты, AI orchestrator
docs/                — goals, phases, architecture, ADR
```

---

## Методика работы агента

> Это не рекомендация. Это обязательный процесс. Пропуск шага = невалидная работа.

### Принцип: Scope → Parallel Agents, не Plan Files

Не создавать файлы планов в `docs/plans/`. Вместо этого:

1. **Декомпозиция по scope** — разбить задачу на независимые скоупы (backend service, frontend feature, infra, docs)
2. **Параллельные агенты** — независимые скоупы реализуются параллельными субагентами через Task tool
3. **Последовательные зависимости** — если скоуп B зависит от A, B запускается только после завершения A

```
Задача пришла
  → Определить скоупы (backend / frontend / infra / docs)
  → Независимые скоупы → параллельные агенты
  → Зависимые скоупы → последовательно
  → Тесты → верификация → коммит
```

### TDD — обязателен для backend

Для каждого Python сервиса и любого нетривиального кода:

1. **Red** — написать failing test первым
2. **Green** — минимальная реализация чтобы тест прошёл
3. **Refactor** — очистить код, убрать дублирование
4. **Verify** — `uv run --package <name> pytest tests/ -v` = все тесты зелёные
5. **Только потом** — коммит

Пропуск шага 1 = невалидная работа. Без обсуждений.

### Закрытие сессии (ОБЯЗАТЕЛЬНО)

```
ЗАКОН: Сессия НЕ завершена, пока документация не обновлена и коммит не создан.
```

В конце КАЖДОЙ сессии, где был изменён код:

1. **Обновить документацию** — все затронутые файлы из списка ниже
2. **Создать локальный коммит** — НЕ пушить, только `git commit`
   - Один коммит на логически связанное изменение
   - Формат: `<type>(<scope>): <description>`
   - Коммит включает и код, и обновлённую документацию
3. **НЕ пушить** — коммиты остаются локальными. Push только по явной просьбе пользователя

**Полный чеклист файлов для обновления:**

| Файл | Когда обновлять |
|------|----------------|
| `README.md` | Новый сервис, изменение кол-ва тестов, изменение статуса фазы |
| `STRUCTURE.md` | Новый сервис, новый hook, новый пакет, изменение дерева |
| `CLAUDE.md` | Новый сервис в карте, новая тест-команда, новые порты |
| `docs/TECHNICAL-OVERVIEW.md` | Новый сервис, порт, тесты, изменение стека или структуры |
| `docs/architecture/01-SYSTEM-OVERVIEW.md` | Новый сервис, порт, диаграмма системы |
| `docs/architecture/02-API-REFERENCE.md` | Новый endpoint, изменение request/response |
| `docs/architecture/03-DATABASE-SCHEMAS.md` | Новая таблица, изменение схемы |
| `docs/architecture/04-AUTH-FLOW.md` | Изменение auth, JWT claims, ролей |
| `docs/architecture/05-INFRASTRUCTURE.md` | Docker, env vars, мониторинг |
| `docs/architecture/06-SHARED-LIBRARY.md` | Изменение common library API |
| `docs/phases/PHASE-*.md` | Завершение задачи из текущей фазы |

**Чего НЕ делать:**
- Не пушить без явного запроса
- Не создавать PR без явного запроса
- Не обновлять документацию спекулятивно ("на будущее")
- Не добавлять в CLAUDE.md одноразовый контекст текущей сессии

### Верификация перед коммитом

Перед каждым коммитом, содержащим код:

**Python:**
```bash
cd services/py/<name> && uv run --package <name> pytest tests/ -v
```
Все тесты должны быть зелёными. Красный тест = нет коммита.

**Frontend:**
```bash
cd apps/<name> && pnpm build
```
Build должен пройти без ошибок. Broken build = нет коммита.

**Rust:**
```bash
cd services/rs/<name> && cargo test && cargo clippy -- -D warnings
```
0 warnings, 0 failures. Иначе = нет коммита.

### Атомарные коммиты

- Один коммит = одно логическое изменение
- Коммит содержит и код и тесты к нему — никогда по отдельности
- Формат: `<type>(<scope>): <description>`
- Без соавторства и автогенерированных подписей

---

## Архитектурные правила

### Разделение языков

- Python — бизнес-логика, CRUD, admin, ML pipelines, интеграции с внешними API
- Rust — API gateway, поиск, видео-процессинг, real-time messaging, платежный движок
- Решение о языке для нового сервиса: p99 < 50ms или > 10K RPS — Rust. Остальное — Python.

### Clean Architecture в Python сервисах

```
services/py/{name}/
├── app/
│   ├── routes/          — HTTP handlers. Только: парсинг запроса, вызов service, формирование ответа
│   ├── services/        — Use cases. Оркестрация: domain + repositories. Управление транзакциями
│   ├── domain/          — Entities, Value Objects. Чистый Python. БЕЗ импортов фреймворков
│   └── repositories/    — Интерфейс (ABC) + реализация (SQL). Маппинг domain ↔ DB
├── tests/
└── migrations/
```

Правило зависимостей — **нарушение запрещено**:
```
routes → services → domain ← repositories
```
- `domain/` не импортирует ничего из `routes/`, `services/`, `repositories/`, фреймворков
- `routes/` не обращается к `repositories/` напрямую
- `services/` не знает про HTTP коды и request/response объекты

Нарушение направления зависимости = невалидный код.

### Слои внутри Rust сервиса

```
services/rs/{name}/src/
├── main.rs          — точка входа, dependency wiring
├── config.rs        — конфигурация из env vars
├── routes/          — HTTP/gRPC handlers
├── services/        — бизнес-логика
└── adapters/        — внешние зависимости (DB, Redis, S3, внешние API)
```

### Межсервисное взаимодействие

- Внутри одного bounded context — прямой вызов через gRPC
- Между доменами — асинхронные события через NATS JetStream
- Публичный API для клиентов — REST (через api-gateway)
- Контракты определяются в `proto/`. Нет proto-контракта = нет вызова
- Сервис **никогда** не читает базу данных другого сервиса

### События

- Определяются в `proto/events/v1/`
- Имя в past tense (`order.created`, `payment.processed`), timestamp, aggregate_id, version
- Обработчики — идемпотентные. Одно событие может прийти дважды
- Новые поля — только добавлять, не удалять (backward compatible)

---

## Правила написания кода

### YAGNI — абсолютный закон

- Не создавать директории, файлы, классы, функции "на будущее"
- Не выносить код в `libs/` пока он не используется в 3+ местах
- Три похожих строки лучше преждевременной абстракции
- Новый сервис — только осознанное архитектурное решение

Создание кода "на будущее" = невалидная работа.

### SOLID

- **SRP**: один модуль — одна причина для изменения
- **OCP**: новый провайдер/тип — добавляется без изменения существующего кода
- **LSP**: любая реализация интерфейса работает без проверки типа
- **ISP**: маленькие интерфейсы. `UserRepository` не содержит методы для заказов
- **DIP**: `services/` зависит от абстрактного `Repository`, не от `SQLRepository`

### Python

- Фреймворк: FastAPI
- Type hints обязательны для всех публичных функций
- Domain entities — `dataclass(frozen=True)` или `pydantic.BaseModel`, не ORM модели
- Async по умолчанию для I/O операций
- Конфигурация через pydantic `BaseSettings` + env vars
- Зависимости — через FastAPI `Depends()`, не глобальные переменные
- Импорты на уровне модуля (PEP 8). Без lazy imports внутри функций — провоцирует circular imports и усложняет чтение
- Линтер: ruff. Формат: ruff format. Типы: mypy (strict mode)

### Rust

- Async runtime: tokio
- HTTP: axum
- Serialization: serde
- Error handling: thiserror (библиотеки), anyhow (приложения)
- `#![deny(clippy::all)]`
- Форматирование: rustfmt

### TypeScript / Frontend

- Next.js (App Router). TypeScript, `strict: true`
- Стили: Tailwind CSS. Без CSS modules, styled-components, emotion
- UI примитивы: Radix UI (headless, accessible)
- Client state: Zustand. Server state: TanStack Query
- Build: Turborepo. Lint: ESLint. Format: Prettier. Package manager: pnpm

#### Компоненты

- Server Components по умолчанию. `"use client"` только при hooks, event handlers, browser API
- Один app → `apps/{app}/components/`. 2+ apps → `packages/ui/`
- Props через `interface`, не `type`. `children` через `React.ReactNode`
- Только named export. Без default export. Без `index.tsx` барелей

#### Рендеринг

- SSG — лендинги, маркетинг. ISR с revalidate
- SSR — каталог, поиск, карточка. Streaming с loading.tsx
- Client-side — корзина, checkout, формы, дашборды
- Только App Router conventions. Без Pages Router

#### API взаимодействие

- API client в `apps/buyer/lib/api.ts` — типизированные namespace-объекты
- Data fetching в Client Components — через TanStack Query hooks
- Optimistic updates для: корзина, лайки, закладки, прогресс уроков

#### Performance

- Initial JS bundle: < 100KB gzip (buyer), < 150KB (seller)
- `next/image` для изображений. `next/link` для навигации. Без `<img>`, `<a>`
- Dynamic import для: charts, rich text editor, video player, modals
- Шрифты через `next/font`. Без внешних CDN

### Тесты — закон, не рекомендация

**Python backend:**
- Unit тесты: `AsyncMock(spec=Repository)`, проверяют domain/ и services/
- Integration тесты: реальная БД через testcontainers для repositories/
- Каждый тест — независимый, без зависимости от порядка и состояния
- Фикстуры в `tests/conftest.py` каждого сервиса
- pytest-asyncio с `asyncio_mode = "auto"`

**Frontend:**
- Vitest для unit/component тестов, Playwright для E2E
- MSW для мока API. Без прямых моков fetch

**Что не тестировать:**
- Тривиальный код (геттеры, маппинг без логики)
- Boilerplate (config, `__init__.py`)

**Тесты проверяют поведение, не реализацию.** Тест-тавтология (мокает всё и проверяет что мок вызван) = невалидный тест.

### Базы данных

- PostgreSQL — основная. Каждый сервис — своя БД
- Redis — кэш и сессии
- Meilisearch — поиск (owned by search service)
- ClickHouse — аналитика (Phase 2+)
- Миграции: идемпотентные SQL файлы (`CREATE TABLE IF NOT EXISTS`). Forward only
- Миграции **не блокируют** таблицу на запись (no exclusive locks)

### Безопасность — без исключений

- Пароли: только bcrypt/argon2 хэш. Никогда в открытом виде
- Карты: только токены провайдера. Никогда номера
- PII: маскировать в логах. Никогда email, phone, card numbers
- SQL: только parameterized queries (`$1, $2, ...`). Никогда string concatenation
- Секреты: env vars или secrets manager. Никогда в коде или конфигах
- Входные данные: валидация на уровне routes/ (pydantic) до передачи в services/

Нарушение безопасности = немедленное исправление, без обсуждений.

---

## AI Safety & Agent Interaction

> Подробности в `docs/goals/11-AI-AGENT-STANDARDS.md`

### Для coding agents

- AI-generated код проходит тот же review, что и ручной
- Security-critical зоны — повышенное внимание:
  - `migrations/` — проверка на data loss и locking
  - auth-related код — проверка authorization logic
  - JWT/token handling — проверка на leakage
  - SQL queries — проверка на injection
- Если код непонятен — разобраться или переписать. Не принимать слепо
- Тесты проверяют реальное поведение, не тавтологии

### Context Engineering

- API endpoints возвращают достаточно данных в одном запросе
- Docstrings описывают **что** и **когда**, а не только **как**
- Новый endpoint должен быть понятен AI-агенту без дополнительного контекста

### MCP Protocol Readiness

- Группировать endpoints логически
- Возвращать self-contained responses (related data, не только IDs)
- `description` в Pydantic models и FastAPI decorators
- Не создавать MCP Server до реального use case (YAGNI)

### AI-Specific Security (Phase 2+)

- UGC → sanitize перед подачей в LLM
- PII → маскировать перед передачей AI-агентам
- AI actions → отдельный audit trail
- AI-агенты = та же авторизация, что и пользователи

---

## Git

### Commits

- Формат: `<type>(<scope>): <description>`
- Types: `feat`, `fix`, `refactor`, `test`, `docs`, `chore`, `perf`
- Scope: имя сервиса (`identity`, `course`, `enrollment`, `payment`, `notification`, `ai`, `learning`, `rag`, `buyer`, `seller`, `ui`, `deploy`, `proto`)
- Пример: `feat(course): add course level support`
- Без соавторства и автогенерированных подписей

### Branches

- `main` — стабильная ветка, всегда deployable
- `feat/<scope>/<short-description>` — новая функциональность
- `fix/<scope>/<short-description>` — исправление бага

---

## Документация

### `docs/architecture/` — source of truth

После изменений в архитектуре **обязательно обновить**:

- `01-SYSTEM-OVERVIEW.md` — диаграмма, порты, стек
- `02-API-REFERENCE.md` — endpoints, request/response, JWT
- `03-DATABASE-SCHEMAS.md` — SQL schemas, ENUMs, миграции
- `04-AUTH-FLOW.md` — аутентификация, авторизация
- `05-INFRASTRUCTURE.md` — Docker, env vars, monitoring
- `06-SHARED-LIBRARY.md` — common library API

Документация соответствует коду, а не планам. Несоответствие = баг.

---

## Контекст проекта

- Глобальные цели: `docs/goals/`
- Текущая фаза: `docs/phases/`
- Текущая архитектура: `docs/architecture/`
- AI/MCP стандарты: `docs/goals/11-AI-AGENT-STANDARDS.md`
- Package manager: uv. Workspace в корне, `uv sync --all-packages`
- Dev: `docker compose -f docker-compose.dev.yml up`
- Prod: `docker compose -f docker-compose.prod.yml up -d`
- Seed: `docker compose -f docker-compose.dev.yml --profile seed up seed`
- Load test: `docker compose -f docker-compose.prod.yml --profile loadtest up locust`

### Тест-команды

```bash
cd services/py/identity    && uv run --package identity pytest tests/ -v
cd services/py/course      && uv run --package course pytest tests/ -v
cd services/py/enrollment  && uv run --package enrollment pytest tests/ -v
cd services/py/payment     && uv run --package payment pytest tests/ -v
cd services/py/notification && uv run --package notification pytest tests/ -v
cd services/py/ai          && uv run --package ai pytest tests/ -v
cd services/py/learning    && uv run --package learning pytest tests/ -v
cd services/py/rag         && uv run --package rag pytest tests/ -v
cd services/py/mcp         && uv run --package mcp-server pytest tests/ -v
cd services/rs/api-gateway && cargo test && cargo clippy -- -D warnings
cd services/rs/ws-gateway && cargo test && cargo clippy -- -D warnings
cd services/rs/embedding-orchestrator && cargo test && cargo clippy -- -D warnings
cd libs/rs/rag-chunker     && cargo test && cargo clippy -- -D warnings
```

---

## Что ЗАПРЕЩЕНО

- Подключать AI/LLM зависимости без обсуждения архитектуры
- Создавать MCP Server, agents, RAG pipelines "на будущее"
- Передавать raw PII в AI контексты
- Создавать README.md, CHANGELOG.md без прямой просьбы
- Добавлять комментарии к очевидному коду
- Создавать wrapper-ы для одного использования
- Добавлять зависимости без необходимости (stdlib предпочтительнее)
- Рефакторить код не затронутый текущей задачей
- Добавлять error handling для невозможных ситуаций
- Менять публичный API без обсуждения
- Создавать файлы планов в `docs/plans/`
- Коммитить без прохождения тестов
- Пропускать TDD для backend-кода
- Принимать AI-generated код без верификации
