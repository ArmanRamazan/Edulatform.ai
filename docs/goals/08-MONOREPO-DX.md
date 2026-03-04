# 08 — Монорепа и Developer Experience

> Владелец: Principal Developer / Platform Team
> Последнее обновление: 2026-03-05

---

## Контекст

B2B Agentic Adaptive Learning платформа. Миссия: сократить онбординг инженеров с 3 месяцев до 1 через AI-ментора. Tri-Agent система (Strategist → Designer → Coach), RAG по кодобазе компании, Trust Levels 0-5.

---

## Структура монорепы

```
eduplatform/
├── CLAUDE.md                    # AI-assistant instructions
├── README.md
├── STRUCTURE.md
├── pyproject.toml               # Python workspace root (uv)
│
├── proto/                       # Protobuf контракты
│   ├── identity/v1/
│   ├── learning/v1/
│   ├── ai/v1/
│   ├── rag/v1/
│   └── events/v1/
│
├── libs/
│   └── py/
│       └── common/              # Shared Python: logging, errors, config, db utils
│
├── services/
│   └── py/
│       ├── identity/            # Auth, users, orgs, trust levels (port 8001)
│       ├── ai/                  # Tri-Agent orchestration (port 8006)
│       ├── learning/            # Missions, progress, assessments (port 8007)
│       ├── rag/                 # Code/docs ingestion, vector search (port 8008)
│       ├── notification/        # Email, push, reminders (port 8005)
│       │
│       │ # --- Dormant (B2C legacy, kept but not actively developed) ---
│       ├── course/              # (port 8002) — frozen
│       ├── enrollment/          # (port 8003) — frozen
│       └── payment/             # (port 8004) — frozen
│
├── apps/
│   ├── buyer/                   # Next.js — engineer experience (B2B)
│   └── seller/                  # Next.js — dormant (teacher marketplace)
│
├── packages/
│   ├── ui/                      # Shared UI kit (Radix + Tailwind)
│   ├── api-client/              # Typed API client
│   └── shared/                  # Shared utilities
│
├── deploy/                      # Docker, K8s manifests
│   ├── docker/
│   └── k8s/
│
├── tools/
│   ├── orchestrator/            # Autonomous Claude Code sprint executor
│   │   ├── orchestrator.py
│   │   ├── run.sh
│   │   ├── tasks/               # YAML sprint/phase task files
│   │   ├── .state/              # Persisted execution state
│   │   └── .logs/               # Execution logs
│   ├── seed/                    # Database seeding scripts
│   └── locust/                  # Load test scenarios
│
└── docs/
    ├── goals/                   # Эти файлы
    ├── architecture/            # System overview, API ref, DB schemas
    └── phases/                  # Phase plans
```

---

## Сервисы и порты

| Сервис | Порт | Статус | Описание |
|--------|------|--------|----------|
| identity | 8001 | Active | Auth, users, organizations, trust levels |
| notification | 8005 | Active | Email, push, reminders |
| ai | 8006 | Active | Tri-Agent: Strategist, Designer, Coach |
| learning | 8007 | Active | Missions, progress, assessments, knowledge graph |
| rag | 8008 | Active | Code/docs ingestion, pgvector search, embeddings |
| course | 8002 | Dormant | B2C course CRUD (frozen) |
| enrollment | 8003 | Dormant | B2C enrollment (frozen) |
| payment | 8004 | Dormant | B2C payments (frozen) |

### Базы данных (Docker dev)

| БД | Порт | Сервис |
|----|------|--------|
| identity-db | 5433 | identity |
| learning-db | 5438 | learning |
| rag-db | 5439 | rag (PostgreSQL + pgvector) |
| notification-db | 5437 | notification |
| ai-db | 5440 | ai (session state, credits) |

---

## Local Development

### Быстрый старт

```bash
# 1. Установить зависимости
uv sync --all-packages

# 2. Поднять dev-окружение
docker compose -f docker-compose.dev.yml up

# 3. Seed данные
docker compose -f docker-compose.dev.yml --profile seed up seed

# 4. Запустить один сервис локально (hot reload)
cd services/py/identity && uv run uvicorn app.main:app --reload --port 8001
```

### Docker Compose

- **Dev:** `docker compose -f docker-compose.dev.yml up` — hot reload, volume mounts
- **Prod:** `docker compose -f docker-compose.prod.yml up -d` — monitoring, multi-worker
- **Seed:** `docker compose -f docker-compose.dev.yml --profile seed up seed`
- **Load test:** `docker compose -f docker-compose.prod.yml --profile loadtest up locust`

### WSL2 Docker

`COPY --from=ghcr.io/astral-sh/uv:latest` не работает из-за `credsStore: desktop.exe` в `~/.docker/config.json`. Используем `ADD` + `tar`:

```dockerfile
ADD https://github.com/astral-sh/uv/releases/latest/download/uv-x86_64-unknown-linux-gnu.tar.gz /tmp/uv.tar.gz
RUN tar -xzf /tmp/uv.tar.gz -C /usr/local/bin/ --strip-components=1
```

---

## Тестовые команды

### Active сервисы

```bash
cd services/py/identity      && uv run --package identity pytest tests/ -v
cd services/py/ai            && uv run --package ai pytest tests/ -v
cd services/py/learning      && uv run --package learning pytest tests/ -v
cd services/py/rag           && uv run --package rag pytest tests/ -v
cd services/py/notification  && uv run --package notification pytest tests/ -v
```

### Dormant сервисы (тесты должны проходить, но не развиваются)

```bash
cd services/py/course        && uv run --package course pytest tests/ -v
cd services/py/enrollment    && uv run --package enrollment pytest tests/ -v
cd services/py/payment       && uv run --package payment pytest tests/ -v
```

### Frontend

```bash
cd apps/buyer && pnpm build
```

---

## uv Workspace

Python workspace в корне (`pyproject.toml`). Сервисы — virtual workspace members (no build-system). `common` lib — installable (hatchling), сервисы ссылаются через `workspace = true`.

```toml
# pyproject.toml (root)
[tool.uv.workspace]
members = ["services/py/*", "libs/py/*"]
```

Запуск из директории сервиса: `uv run --package <name>`.

---

## Orchestrator Tool

Автономный исполнитель задач для Claude Code. Принимает YAML-файлы с описанием спринтов.

```bash
# Запуск спринта
cd tools/orchestrator && ./run.sh tasks/sprint-1-launch-blockers.yaml

# Статус
cd tools/orchestrator && ./run.sh --status

# Возобновление после прерывания
cd tools/orchestrator && ./run.sh --resume

# Остановка
touch tools/orchestrator/.stop
```

**Формат задач (YAML):**
```yaml
phase: "sprint-N"
description: "Описание спринта"
tasks:
  - id: task-1
    title: "Название"
    scope: backend|frontend|infra
    prompt: "Подробный промпт для Claude Code"
    test: "cd services/py/X && uv run --package X pytest tests/ -v"
    depends_on: []
```

Состояние в `.state/state.json`, логи в `.logs/`.

---

## Code Quality

### Python
- Линтер + форматирование: `ruff`
- Типы: `mypy` (strict)
- Тесты: `pytest` + `pytest-asyncio` (asyncio_mode = "auto")
- Type hints обязательны для публичных функций

### TypeScript / Frontend
- `strict: true` в tsconfig
- ESLint + Prettier
- Build: Turborepo
- Package manager: pnpm

### Pre-commit (TODO)
- [ ] ruff check + format (Python)
- [ ] mypy (Python)
- [ ] ESLint + Prettier (TypeScript)
- [ ] Architectural tests: domain не импортирует infrastructure

---

## TODO

### Build и CI
- [ ] Selective CI: тесты только для изменённых сервисов
- [ ] Docker build optimization: multi-stage, layer caching, < 60 сек на сервис
- [ ] CI time budget: full pipeline < 10 мин, PR checks < 5 мин

### Testing
- [ ] Integration tests: testcontainers для repositories
- [ ] Contract tests между сервисами (Pact)
- [ ] E2E: регистрация → mission → coach session → completion
- [ ] Load tests: Locust сценарии для coach sessions и RAG search
