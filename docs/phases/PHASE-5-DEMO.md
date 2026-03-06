# Phase 5 — Demo-Ready Product [IN PROGRESS]

> **Статус:** В РАЗРАБОТКЕ
>
> Цель: развернуть KnowledgeOS локально через `docker compose up` и пройти полный демо-сценарий end-to-end.
>
> Аудитория: инвесторы (визуальный wow) + техническая аудитория (архитектура, тесты, масштабируемость).

---

## Золотой путь демо

```
Landing → Register → Onboarding (5 шагов) → Dashboard (7 блоков) →
→ Knowledge Graph (Concept Map + Mind Map) → Start Mission →
→ Coach Session (streaming, 5 фаз) → Complete → Score →
→ Flashcards Review → Unified Search → Team Analytics →
→ Messages → Badges
```

**Время прохождения:** ~5-7 минут.

**Demo user:** `demo@acme.com` / `demo123` — всё уже настроено через seed.

---

## Sprint 30: AI Mock Provider

> **Scope:** ai | **Agent:** ml-engineer

### Проблема

AI сервис зависит от `GEMINI_API_KEY`. Без ключа все AI-фичи возвращают ошибки: миссии, coach, quiz generation, unified search, content moderation.

### Решение

`MockLLMProvider` — fallback реализация `LLMProvider` ABC. Автоматически активируется когда `GEMINI_API_KEY` пустой.

### Задачи

- [ ] **mock-llm-provider** — Реализовать `MockLLMProvider(LLMProvider)` в `services/py/ai/app/services/llm_provider.py`
  - Метод `complete()` возвращает реалистичные ответы с задержкой 0.5-1.5с
  - Определяет тип запроса по ключевым словам в prompt (mission/quiz/summary/coach/search/moderation)
  - Для каждого типа — банк из 3-5 шаблонов ответов
  - Token counts: рандомные реалистичные значения (in: 200-800, out: 100-500)

- [ ] **mock-mission-data** — Банк mock данных для миссий
  - 3 mission blueprints (Python, Rust, TypeScript концепты)
  - Каждый blueprint: recap (2 вопроса), reading (2 мин текст), questions (3 шт), code_case
  - Coach messages для всех 5 фаз: recap, reading, questions, code_case, wrap_up
  - Score calculation: 60-95% рандом

- [ ] **mock-search-data** — Mock данные для unified search
  - Query router: always returns "internal" для demo
  - 10 mock search results с реалистичными snippets
  - External search: 5 mock web results

- [ ] **mock-activation** — Автоматическое переключение на mock
  - В `LLMResolver`: если нет API ключа → return `MockLLMProvider`
  - Логирование: `logger.info("Using mock LLM provider (no API key)")`
  - Без изменения продового кода — только добавление fallback

- [ ] **mock-streaming** — SSE endpoint для coach streaming
  - `GET /ai/coach/stream/{session_id}` — Server-Sent Events
  - Mock режим: отдаёт заготовленный ответ по токенам (30-50ms между словами)
  - Prod режим: проксирует streaming от Gemini (когда ключ есть)

**Тест:** `cd services/py/ai && uv run --package ai pytest tests/ -v`

---

## Sprint 31: Payment Guard + Stripe Mock

> **Scope:** backend | **Agent:** backend-engineer

### Проблема

Payment сервис зависит от `STRIPE_SECRET_KEY`. Billing page крашится без ключа.

### Задачи

- [ ] **stripe-mock-mode** — Если нет `STRIPE_SECRET_KEY`:
  - `GET /payments/subscriptions/org/{org_id}` → mock Enterprise Plan (active, unlimited seats)
  - `GET /payments/earnings/me` → mock earnings data
  - `POST /payments/*` → return success с mock IDs
  - Логирование: `logger.info("Stripe mock mode (no API key)")`

- [ ] **billing-frontend-guard** — Frontend billing page
  - Показывает "Enterprise Plan (Demo)" badge
  - Кнопки управления подпиской disabled с tooltip "Available in production"
  - Не крашит UI, не показывает ошибки

**Тест:** `cd services/py/payment && uv run --package payment pytest tests/ -v`

---

## Sprint 32: Onboarding Wizard

> **Scope:** frontend | **Agent:** frontend-engineer

### Проблема

После регистрации пользователь попадает на dashboard и не понимает что делать. Нет guided flow.

### Решение

5-шаговый onboarding wizard: Select Org → Role & Experience → AI Pretest → Plan Preview → First Mission.

### Задачи

- [ ] **onboarding-layout** — `apps/buyer/app/(app)/onboarding/page.tsx`
  - Server component wrapper
  - Step indicator (1-5) с анимацией прогресса
  - Stepper bar сверху: фиолетовый градиент по заполнению

- [ ] **onboarding-step1-org** — Select Organization
  - Загружает орги пользователя через `useMyOrganizations()`
  - Карточки с logo, name, member count
  - Если одна орга — auto-select с 1с задержкой + анимация
  - Persist выбор в OrgProvider

- [ ] **onboarding-step2-profile** — Role & Experience
  - "What's your role?" — карточки: Junior / Mid / Senior / Lead (иконки)
  - "Primary stack?" — карточки: Python / Rust / TypeScript / Go / Java
  - Сохраняет в localStorage + `PATCH /users/me` (profile update)
  - Анимация выбора: scale + border glow

- [ ] **onboarding-step3-pretest** — AI Pretest
  - 5 multiple-choice вопросов по выбранному стеку
  - Mock: заготовленные вопросы (по 5 на Python/Rust/TypeScript)
  - Таймер на вопрос (30с), progress bar
  - Анимация: правильно → зелёная вспышка, неправильно → красная
  - Результат: `POST /pretests/` с ответами

- [ ] **onboarding-step4-plan** — Plan Preview
  - "AI проанализировал ваш уровень"
  - Мини-граф: 5-7 нодов концептов с цветами mastery (зелёный/жёлтый/красный)
  - Статистика: "12 концептов за ~3 недели"
  - "Первая миссия: [concept name]" с превью
  - Framer Motion: fade-in по секциям

- [ ] **onboarding-step5-start** — Launch
  - "Ready to start your journey?" + animated CTA
  - Кнопка с glow pulse эффектом
  - Click → set onboarding complete in profile → redirect to /dashboard
  - Confetti animation (optional, lightweight)

- [ ] **onboarding-redirect** — Middleware/guard
  - Если user.onboarding_complete === false → redirect to /onboarding
  - Если true → пропускает на dashboard
  - Check в `(app)/layout.tsx` через useAuth()

**Тест:** `cd apps/buyer && pnpm build`

---

## Sprint 33: Knowledge Graph (React Flow)

> **Scope:** frontend | **Agent:** frontend-engineer

### Проблема

ConceptHub существует но нет визуальной карты знаний. Это главный wow-момент для инвесторов.

### Решение

Два режима на одной странице: Concept Map (обзор) + Mind Map (zoom на концепт).

### Задачи

- [ ] **reactflow-setup** — Установка и настройка
  - `pnpm add @xyflow/react` в apps/buyer
  - Базовый компонент `KnowledgeGraph.tsx` ("use client", dynamic import с ssr: false)
  - Dark Knowledge тема для React Flow: тёмный фон, фиолетовые рёбра

- [ ] **concept-map-view** — Основной вид: Concept Map
  - Ноды = концепты из `GET /concepts/graph?org_id=X`
  - Размер ноды = количество связей (важность)
  - Цвет по mastery: `#6b6b80` (0%) → `#7c5cfc` (50%) → `#34d399` (100%)
  - Рёбра = prerequisite/related (разные стили: solid/dashed)
  - Layout: dagre (иерархический DAG)
  - Zoom/pan, minimap в углу
  - Фильтр: по mastery level (show all / gaps only / mastered)
  - Клик на ноду → переход в Mind Map

- [ ] **mind-map-view** — Zoom на концепт: Mind Map
  - Центральный нод = выбранный концепт (крупный, с иконкой)
  - Радиальные связи: prerequisites (сверху), dependents (снизу), related (по бокам)
  - Правая панель: mastery %, список миссий, flashcard count, team average
  - Кнопка "Start Mission" если mastery < 80%
  - "Back to Map" → возврат в Concept Map с анимацией

- [ ] **graph-page-integration** — Страница `/graph`
  - `apps/buyer/app/(app)/graph/page.tsx` — Server component
  - Загрузка данных через `useCourseGraph()`
  - Toggle: "Map View" / "Mind Map" (tabs)
  - Loading: skeleton графа
  - Empty state: "Upload documents to build your knowledge graph"

**Тест:** `cd apps/buyer && pnpm build`

---

## Sprint 34: Real-time (WebSocket)

> **Scope:** core + frontend | **Agent:** core-engineer + frontend-engineer

### Проблема

Нет real-time: нотификации по pull, coach отвечает одним блоком.

### Решение

WebSocket для нотификаций (badge count) + SSE для coach streaming.

### Задачи

- [ ] **ws-notification-backend** — WebSocket endpoint в ws-gateway
  - Rust ws-gateway (port 8011) уже в docker-compose
  - `GET /ws?token=JWT` → validate JWT → WebSocket connection
  - При новой нотификации → push `{"type":"notification","count":N}`
  - Redis pub/sub для cross-instance broadcast

- [ ] **ws-notification-frontend** — TopBar live badge
  - `apps/buyer/hooks/use-websocket.ts` — WebSocket hook
  - Auto-connect при авторизации, reconnect при disconnect
  - TopBar bell badge обновляется в реальном времени
  - Fallback на polling если WS unavailable

- [ ] **coach-streaming-backend** — SSE endpoint в AI сервисе
  - `GET /ai/coach/stream/{session_id}` — Server-Sent Events
  - Каждый event: `data: {"token": "слово", "done": false}`
  - Финальный event: `data: {"token": "", "done": true, "full_text": "..."}`
  - Mock mode: отдаёт заготовленный текст по словам (30-50ms)
  - Prod mode: проксирует streaming от Gemini

- [ ] **coach-streaming-frontend** — Mission session UI
  - `apps/buyer/hooks/use-coach-stream.ts` — EventSource hook
  - Typing indicator (три точки с анимацией)
  - Token-by-token rendering в чат-пузыре
  - Smooth scroll вниз при новых токенах
  - Fallback: если SSE не работает → обычный POST (текущее поведение)

**Тест:**
- Rust: `cd services/rs/api-gateway && cargo test`
- Frontend: `cd apps/buyer && pnpm build`

---

## Sprint 35: B2B Seed Data

> **Scope:** infra | **Agent:** devops-engineer

### Проблема

Seed создаёт 50K generic users. Для демо нужна конкретная организация с реалистичными данными.

### Решение

Расширить seed: Acme Engineering + реальный контент в RAG + mission history.

### Задачи

- [ ] **seed-demo-org** — Организация "Acme Engineering"
  - Org: name="Acme Engineering", slug="acme", logo_url (placeholder)
  - 10 members: demo user (admin) + 9 инженеров с разными mastery levels
  - Demo user: `demo@acme.com` / `demo123`, role=teacher, is_verified=true
  - Trust levels: demo=4 (Guardian), others: 1-3 (распределение)

- [ ] **seed-rag-documents** — 5 документов в RAG
  - Python best practices (2K words, markdown)
  - Rust ownership model (2K words)
  - TypeScript patterns (2K words)
  - System design basics (2K words)
  - API design guide (2K words)
  - Все привязаны к org "Acme Engineering"

- [ ] **seed-concepts** — Extracted concepts
  - 47 концептов из 5 документов
  - Prerequisite relationships (DAG)
  - Mastery levels для demo user: 10 > 80%, 15 at 40-60%, 22 < 30%
  - Team mastery: разброс по 10 members

- [ ] **seed-missions-history** — Mission history
  - 15 completed missions для demo user
  - Scores: 65-95%, разные концепты
  - Activity feed: 20 записей за последние 2 недели

- [ ] **seed-gamification** — Gamification data
  - Demo user: streak=7, XP=2450, badges=[first_enrollment, streak_7, quiz_ace]
  - 25 flashcards (10 due today)
  - Leaderboard data для 10 members

- [ ] **seed-script-update** — Обновить `tools/seed/seed.py`
  - Новая функция `seed_demo_org()` вызывается после основного seed
  - Идемпотентна: можно вызывать повторно
  - Документация в README seed

**Тест:** Запуск seed через docker compose, проверка данных в БД.

---

## Sprint 36: Frontend Polish & Docker Health

> **Scope:** frontend + infra | **Agent:** frontend-engineer + devops-engineer

### Проблема

Frontend может не билдиться. Docker compose может не стартовать. Route protection отсутствует.

### Задачи

#### Frontend

- [ ] **frontend-build-fix** — Исправить `pnpm build`
  - Запустить build, исправить все type errors и import errors
  - `.env.example` с demo API URLs
  - Проверить что все dynamic imports работают

- [ ] **route-protection** — Middleware для auth
  - `apps/buyer/middleware.ts` — Next.js middleware
  - Без токена: redirect `/login` для всех `/(app)/*` routes
  - С токеном: пропускает
  - Исключения: `/(marketing)/*`, `/_next/*`, `/api/*`

- [ ] **org-flow-verify** — Org context e2e
  - Verify: JWT → org_id → OrgProvider → dashboard → missions
  - Fix если где-то обрывается цепочка
  - Org switcher в sidebar работает

- [ ] **empty-states** — Все страницы при отсутствии данных
  - Dashboard blocks: "No data yet" с иконкой
  - Graph: "Upload documents to build knowledge graph"
  - Search: placeholder state
  - Flashcards: "All caught up!"

- [ ] **loading-polish** — Loading и transition states
  - Все skeleton анимации работают
  - Page transitions: fade 200ms
  - No layout shift при загрузке данных

#### Infra

- [ ] **docker-compose-verify** — Все сервисы стартуют
  - Проверить порядок запуска (depends_on)
  - Healthchecks проходят для всех 10 сервисов
  - Миграции запускаются до seed

- [ ] **env-example** — `.env.example` файл
  - Все env vars с demo defaults
  - `GEMINI_API_KEY=` (пустой = mock mode)
  - `STRIPE_SECRET_KEY=` (пустой = mock mode)
  - JWT_SECRET, DATABASE_URLs, REDIS_URL

- [ ] **startup-script** — Один скрипт для запуска демо
  - `./demo.sh` → копирует .env.example → docker compose up → seed → open browser
  - Проверяет prerequisites (Docker, Node, pnpm)
  - Выводит URL и demo credentials

**Тест:**
- Frontend: `cd apps/buyer && pnpm build`
- Docker: `docker compose -f docker-compose.dev.yml up` (все healthy)

---

## Зависимости между спринтами

```
Sprint 30 (AI Mock) ──────────────┐
Sprint 31 (Stripe Guard) ─────────┤
Sprint 32 (Onboarding) ───────────┼──→ Sprint 36 (Polish + Docker)
Sprint 33 (Knowledge Graph) ──────┤
Sprint 34 (Real-time) ────────────┤
Sprint 35 (Seed Data) ────────────┘
```

Спринты 30-35 **параллельны** (независимые scope).
Спринт 36 зависит от всех — финальная интеграция и polish.

---

## Критерии готовности

- [ ] `docker compose up` поднимает все 10 сервисов
- [ ] `demo@acme.com` / `demo123` → login → dashboard с данными
- [ ] Onboarding wizard проходится end-to-end
- [ ] Knowledge Graph визуализирует 47 концептов
- [ ] Mission с coach streaming работает (mock)
- [ ] Flashcards review работает
- [ ] Search возвращает результаты
- [ ] Team Analytics показывает heatmap
- [ ] Нотификации live через WebSocket
- [ ] `pnpm build` проходит без ошибок
