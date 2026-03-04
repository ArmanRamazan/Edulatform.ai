# 10 — Frontend Architecture

> Владелец: Architect / Frontend Lead
> Последнее обновление: 2026-03-05

---

## Бизнес-контекст

B2B платформа адаптивного онбординга инженеров. Основные пользователи: новые инженеры компании-клиента (выполняют миссии, общаются с AI Coach), менеджеры (отслеживают прогресс), администраторы организации (управление, биллинг, настройка RAG).

Нет каталога курсов, корзины, checkout, видео-плеера. Основной UX: daily mission dashboard + Coach chat + knowledge graph.

---

## Приложения

| Приложение | Аудитория | Статус | Описание |
|-----------|----------|--------|----------|
| **Buyer App** | Инженеры + org admins | Active | Mission dashboard, Coach chat, knowledge, progress, admin |
| **Seller App** | — | Dormant | B2C teacher marketplace (frozen, не развивается) |

---

## Стек

| Решение | Технология | Статус |
|---------|-----------|--------|
| Framework | Next.js (App Router) | ✅ |
| Styles | Tailwind CSS | ✅ |
| UI primitives | Radix UI (headless, accessible) | ✅ |
| Client state | Zustand | ✅ |
| Server state | TanStack Query | ✅ |
| Build | Turborepo | ✅ |
| Types | TypeScript `strict: true` | ✅ |
| Package manager | pnpm | ✅ |

---

## Структура Buyer App

```
apps/buyer/
├── app/
│   ├── layout.tsx               # Root layout, providers
│   ├── page.tsx                 # Landing / redirect to dashboard
│   ├── (auth)/
│   │   ├── login/page.tsx       # Login (org SSO or credentials)
│   │   └── register/page.tsx    # Registration
│   ├── onboarding/
│   │   └── page.tsx             # New engineer onboarding wizard
│   ├── dashboard/
│   │   └── page.tsx             # Daily mission, streaks, trust level
│   ├── mission/
│   │   └── [id]/page.tsx        # Active mission: Coach chat + tasks
│   ├── knowledge/
│   │   └── page.tsx             # Knowledge graph, concept mastery
│   ├── progress/
│   │   └── page.tsx             # Learning progress, trust level history
│   ├── admin/
│   │   ├── page.tsx             # Org admin dashboard
│   │   ├── analytics/page.tsx   # Team progress, onboarding metrics
│   │   └── billing/page.tsx     # Org billing, resource usage
│   └── api/                     # Next.js API routes (BFF)
│
├── components/
│   ├── MissionDashboard.tsx     # Today's mission, progress overview
│   ├── CoachChat.tsx            # Socratic dialogue interface
│   ├── KnowledgeGraph.tsx       # Concept map visualization
│   ├── TrustLevel.tsx           # Trust level indicator (0-5)
│   ├── OrgSwitcher.tsx          # Organization context switcher
│   ├── AdminDashboard.tsx       # Org admin: team progress, settings
│   ├── MissionCard.tsx          # Mission summary card
│   ├── ConceptNode.tsx          # Knowledge graph node
│   ├── StreakIndicator.tsx      # Learning streak display
│   └── PhaseProgress.tsx        # Coach session phase indicator
│
├── hooks/
│   ├── use-daily.ts             # Daily mission, today's tasks
│   ├── use-coach.ts             # Coach session: start, send message, end
│   ├── use-knowledge-base.ts    # Knowledge graph, concept mastery
│   ├── use-trust-level.ts       # Trust level state, progression
│   ├── use-organizations.ts     # Org context, membership, switching
│   ├── use-admin.ts             # Admin: team stats, user management
│   ├── use-billing.ts           # Org billing, resource usage
│   ├── use-progress.ts          # Learning progress, history
│   └── use-notifications.ts     # Notification feed
│
├── lib/
│   ├── api.ts                   # Typed API client (namespace objects)
│   └── utils.ts                 # Shared utilities
│
└── public/
```

---

## Страницы и рендеринг

| Страница | Route | Рендеринг | Performance Budget |
|----------|-------|----------|-------------------|
| **Dashboard** | `/dashboard` | SSR + client hydration | LCP < 1.5s |
| **Mission** | `/mission/[id]` | Client-side (auth, WebSocket) | TTI < 1.5s |
| **Knowledge Graph** | `/knowledge` | Client-side (interactive) | INP < 200ms |
| **Progress** | `/progress` | SSR | LCP < 2s |
| **Onboarding** | `/onboarding` | Client-side (wizard) | TTI < 1.5s |
| **Admin Dashboard** | `/admin` | SSR + client | LCP < 2s |
| **Admin Analytics** | `/admin/analytics` | SSR + client charts | LCP < 2.5s |
| **Admin Billing** | `/admin/billing` | SSR | LCP < 2s |
| **Login** | `/login` | Client-side | TTI < 1s |

---

## Ключевые компоненты

### MissionDashboard
- Текущая миссия дня (от Designer agent)
- Progress bar по фазам: recap → reading → questions → code_case → wrap_up
- Trust Level индикатор
- Streak counter

### CoachChat
- Socratic dialogue интерфейс
- Поддержка markdown + code blocks (syntax highlighting)
- Phase indicator (текущая фаза coach session)
- RAG context display (ссылки на документацию компании)
- Typing indicator для AI responses

### KnowledgeGraph
- Визуализация concept map (interactive, zoomable)
- Цветовая кодировка mastery level per concept
- Clickable nodes → детали по concept + related missions

### TrustLevel
- Визуальный индикатор уровня 0-5
- Progress к следующему уровню
- Список разблокированных возможностей на текущем уровне

### OrgSwitcher
- Переключение между организациями (если пользователь в нескольких)
- Отображение текущей org + роль

### AdminDashboard
- Team overview: активные пользователи, средний trust level
- Onboarding funnel: новые → active → trust level milestones
- RAG status: indexed documents, last sync
- Resource usage: LLM tokens, storage

---

## TanStack Query Hooks

| Hook | API Endpoints | Key Features |
|------|--------------|--------------|
| `use-daily` | GET /missions/today, GET /missions/history | staleTime: 5min, refetch on window focus |
| `use-coach` | POST /coach/session, POST /coach/message, POST /coach/end | Streaming responses, optimistic UI |
| `use-knowledge-base` | GET /concepts, GET /concepts/graph, GET /concepts/mastery | Lazy loading nodes |
| `use-trust-level` | GET /trust-level/me, GET /trust-level/history | Cache: 10min |
| `use-organizations` | GET /orgs/me, POST /orgs/switch | Persisted in Zustand |
| `use-admin` | GET /admin/team, GET /admin/stats, PATCH /admin/users | Role-gated |
| `use-billing` | GET /billing/usage, GET /billing/invoices | Org-admin only |
| `use-progress` | GET /progress/me, GET /progress/timeline | SSR prefetch |
| `use-notifications` | GET /notifications/me, PATCH /notifications/:id/read | Optimistic read |

---

## Performance

### Core Web Vitals

| Метрика | Engineer App | Admin Pages |
|---------|-------------|-------------|
| LCP | < 1.5s | < 2.5s |
| FID / INP | < 100ms | < 200ms |
| CLS | < 0.1 | < 0.15 |
| TTFB | < 400ms | < 500ms |
| Bundle size (initial) | < 100KB gzip | < 150KB gzip |

### Оптимизации

- `next/image` для изображений, `next/link` для навигации
- Dynamic import: KnowledgeGraph (d3/force-graph), CoachChat (markdown renderer), charts
- `next/font` для шрифтов (без внешних CDN)
- Server Components по умолчанию, `"use client"` только при hooks/events/browser API
- Prefetch: dashboard → mission page при hover

---

## Seller App (Dormant)

B2C teacher marketplace заморожен. Директория `apps/seller/` сохранена, но не развивается. Если B2B потребует teacher-like функциональность (content authoring для org admins), она будет добавлена в buyer app, а не в seller.

---

## API взаимодействие

- API client в `apps/buyer/lib/api.ts` — типизированные namespace-объекты
- Data fetching в Client Components через TanStack Query hooks
- Optimistic updates: notification read, mission progress
- Coach session: streaming responses через Server-Sent Events или WebSocket
- Error handling: per-route error boundaries + global fallback

---

## Тестирование

| Тип | Инструмент | Что тестируем |
|-----|-----------|--------------|
| Unit | Vitest | Hooks, утилиты, форматтеры |
| Component | Vitest + Testing Library | UI компоненты в изоляции |
| Integration | Playwright | Mission flow, coach session, admin |
| API mocks | MSW | Mock backend для тестов |

---

## TODO

- [ ] Реализовать MissionDashboard component
- [ ] Реализовать CoachChat с streaming responses
- [ ] Реализовать KnowledgeGraph visualization (d3 или force-graph)
- [ ] TrustLevel component с progression animation
- [ ] OrgSwitcher с Zustand persistence
- [ ] AdminDashboard с team metrics
- [ ] Все TanStack Query hooks
- [ ] Playwright E2E: onboarding → first mission → coach session
- [ ] Vitest setup с MSW
