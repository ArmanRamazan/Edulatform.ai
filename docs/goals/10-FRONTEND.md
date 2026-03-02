# 10 — Frontend Architecture

> Владелец: Architect / Frontend Lead
> Последнее обновление: 2026-02-24

---

## Бизнес-контекст

80%+ трафика — мобильный. Первое впечатление — страница курса из поисковика или соцсетей. Если страница грузится > 2 сек — пользователь уходит. Фронтенд должен быть быстрым, SEO-friendly и работать на слабых устройствах.

---

## Три приложения

| Приложение | Аудитория | Приоритет | Описание |
|-----------|----------|-----------|----------|
| **Student App** | Студенты | P0 | Каталог курсов, поиск, карточка курса, видео-уроки, прогресс обучения |
| **Teacher Dashboard** | Преподаватели | P0 | Управление курсами, уроками, аналитика, video upload |
| **Admin Panel** | Операторы | P1 | Модерация, финансы, поддержка, настройки платформы |

---

## Стек и ADR

### ADR-F01: Next.js (App Router) как основной фреймворк
- [x] ✅ **Решение:** Next.js с App Router
- **Контекст:** SSR/SSG для SEO страниц курсов и каталога. React Server Components для уменьшения JS bundle. Streaming SSR для быстрого FCP. Встроенный image optimization
- **Альтернативы:** Nuxt (меньше экосистема), Remix (слабее SSG), SvelteKit (меньше специалистов)

### ADR-F02: Монорепа — фронтенд внутри общей репы
- [x] ✅ **Решение:** `apps/` директория в корне монорепы, shared UI в `packages/ui/`
- **Контекст:** Общие proto-типы, единый CI, атомарные изменения API + фронтенд
- **Инструмент:** Turborepo для build orchestration фронтенд-части

### ADR-F03: Tailwind CSS + Radix UI как UI foundation
- [x] ✅ **Решение:** Tailwind для стилей, Radix UI для accessible primitives
- **Контекст:** Tailwind — утилитарный, минимальный CSS output, purge неиспользуемого. Radix — headless, accessible из коробки, не навязывает стиль
- **Альтернативы:** Shadcn/UI поверх Radix (рассмотреть), MUI (тяжелый, не нужен), Chakra (хуже tree-shaking)

### ADR-F04: Zustand для client state, TanStack Query для server state
- [x] ✅ **Решение:** Zustand (client) + TanStack Query (server cache)
- **Контекст:** Zustand — минимальный (1KB), без boilerplate. TanStack Query — кэширование, дедупликация запросов, optimistic updates. Не нужен Redux — оверкил для этого проекта
- **Пересмотр:** Если state станет сложным (> 20 stores), оценить другие решения

### ADR-F05: TypeScript strict mode
- [x] ✅ **Решение:** TypeScript с `strict: true`
- **Контекст:** На 10M users баги стоят дорого. Строгая типизация ловит ошибки до продакшена

---

## Структура в монорепе

```
apps/
├── buyer/                    # Next.js — студенческое приложение
│   ├── app/                  #   App Router pages
│   │   ├── (marketing)/      #     Лендинги, SEO страницы (SSG)
│   │   ├── (courses)/        #     Каталог, поиск, карточка курса (SSR)
│   │   ├── (learning)/       #     Прогресс, видео-уроки (client)
│   │   ├── (account)/        #     Профиль, мои курсы, настройки
│   │   └── courses/[id]/     #     Страница курса (SSR/ISR)
│   ├── components/           #   Компоненты специфичные для student app
│   ├── hooks/                #   Custom hooks
│   ├── lib/                  #   API клиент, утилиты
│   └── public/               #   Статика
│
├── seller/                   # Next.js — дашборд преподавателя
│   ├── app/
│   │   ├── (dashboard)/      #     Обзор, метрики
│   │   ├── (courses)/        #     Управление курсами и уроками
│   │   ├── (students)/       #     Студенты, прогресс, Q&A
│   │   ├── (content)/        #     Upload видео, материалы
│   │   └── (analytics)/      #     Аналитика курсов
│   ├── components/
│   ├── hooks/
│   └── lib/
│
└── admin/                    # Next.js — админ-панель (Phase 1)
    └── ...

packages/
├── ui/                       # Shared UI kit (Radix + Tailwind)
│   ├── components/           #   Button, Input, Modal, Card, VideoPlayer...
│   ├── tokens/               #   Design tokens: colors, spacing, typography
│   └── index.ts
│
├── api-client/               # Typed API client (сгенерированный из OpenAPI)
│   ├── generated/            #   Auto-generated types и fetch functions
│   └── index.ts
│
└── shared/                   # Shared utilities
    ├── validators/            #   Zod schemas (переиспользуются в формах и API)
    ├── formatters/            #   Цены, даты, числа
    └── constants/             #   Enum-ы, маршруты, конфиг
```

---

## Страницы и экраны

### Student App

| Страница | Рендеринг | Performance Budget | Статус |
|----------|----------|-------------------|--------|
| **Главная** (каталог + поиск) | SSR + streaming | LCP < 1.5s, CLS < 0.1 | ✅ |
| **Поиск** | SSR (query) | Результат < 200ms, FID < 100ms | ✅ |
| **Карточка курса** + curriculum | SSR | LCP < 2s | ✅ |
| **Страница урока** | Client-side (auth) | — | ✅ |
| **Прогресс обучения** (прогресс-бар) | Client-side | INP < 200ms | ✅ |
| **Регистрация / Логин** | Client-side | TTI < 1.5s | ✅ |
| **Onboarding** (3-step wizard) | Client-side (auth required) | TTI < 1.5s | ✅ |
| **Создание курса** | Client-side (auth protected) | FCP < 1s | ✅ |
| **Редактирование курса** | Client-side (auth protected) | FCP < 1s | ✅ |
| **Мои курсы** (enrollments) | Client-side (auth protected) | FCP < 1s | ✅ |
| **Уведомления** | Client-side (auth protected) | FCP < 1s | ✅ |
| **Admin: teachers** | Client-side (admin only) | — | ✅ |
| **Категории** + фильтры | SSR + ISR | LCP < 2s | 🔴 |
| **Отзывы** (форма + список) | SSR (список) + client (форма) | — | ✅ (backend), 🔴 (frontend page) |

### Teacher Dashboard

| Страница | Описание | Статус |
|----------|---------|--------|
| **Обзор** | Revenue, студенты, completion rate, графики за неделю/месяц | 🔴 |
| **Курсы** — список | Таблица с поиском, фильтрами, статус (draft/published) | 🔴 |
| **Курсы** — редактирование | Форма: описание, модули, уроки, видео, цены | 🔴 |
| **Уроки** — video upload | Upload видео, прогресс транскодирования, preview | 🔴 |
| **Студенты** — список | Enrolled студенты, прогресс, Q&A | 🔴 |
| **Аналитика** | Просмотры, enrollments, completion, drop-off points, revenue | 🔴 |
| **Финансы** | Баланс, история выплат, комиссии, вывод средств | 🔴 |
| **Промо** | Создание скидок, купонов, bundles | 🔴 |

### Admin Panel (Phase 1)

| Страница | Описание | Статус |
|----------|---------|--------|
| **Модерация** — очередь | Курсы/видео на проверку, approve/reject с причиной | 🔴 |
| **Пользователи** | Поиск, блокировка, история действий | 🔴 |
| **Преподаватели** — верификация | Очередь верификации, документы, approve/reject | 🔴 |
| **Финансы** | Общий revenue, комиссии, payouts, reconciliation | 🔴 |
| **Контент** | Категории, баннеры, промо-страницы | 🔴 |

---

## Ключевые компоненты UI Kit (`packages/ui/`)

### TODO: определить и реализовать

#### Базовые
- [ ] 🔴 Button (variants: primary, secondary, ghost, danger; sizes: sm, md, lg)
- [ ] 🔴 Input, Textarea, Select, Checkbox, Radio, Switch
- [ ] 🔴 Modal / Dialog, Drawer (mobile bottom sheet)
- [ ] 🔴 Toast / Notifications
- [ ] 🔴 Skeleton loaders
- [ ] 🔴 Pagination, Infinite scroll

#### Каталог курсов
- [ ] 🔴 CourseCard (thumbnail, title, level badge, price/free, duration, rating)
- [ ] 🔴 CourseGrid (responsive: 2 col mobile, 3 tablet, 4 desktop)
- [ ] 🔴 SearchBar (with autocomplete dropdown)
- [ ] 🔴 FilterPanel (category tree, level, price range, ratings, duration)
- [ ] 🔴 SortDropdown (relevance, newest, popular, rating)
- [ ] 🔴 CategoryBreadcrumbs

#### Видео
- [ ] 🔴 VideoPlayer (HLS, poster, play/pause, speed control, resume, progress tracking)
- [ ] 🔴 VideoUploader (drag-n-drop, progress, preview, crop thumbnail)
- [ ] 🔴 LessonList (sidebar with checkmarks for completed lessons)

#### Enrollment
- [ ] 🔴 EnrollButton (free → instant, paid → checkout)
- [ ] 🔴 ProgressBar (% completion, current lesson)
- [ ] 🔴 CertificateCard (completion date, verify link)
- [ ] 🔴 PaymentForm (Stripe Elements integration)

#### Teacher
- [ ] 🔴 DataTable (sortable, filterable, selectable rows, bulk actions)
- [ ] 🔴 StatsCard (number + trend arrow + sparkline)
- [ ] 🔴 Chart (line, bar — Recharts или lightweight альтернатива)
- [ ] 🔴 FileUploader (video: single, drag-n-drop, progress)
- [ ] 🔴 RichTextEditor (описание курса — lightweight, без WYSIWYG монстров)
- [ ] 🔴 CurriculumEditor (drag-n-drop модули и уроки)

---

## Performance

### Core Web Vitals целевые значения

| Метрика | Student (mobile) | Teacher Dashboard | Admin |
|---------|-----------------|-----------------|-------|
| LCP | < 1.5s | < 2.5s | < 3s |
| FID / INP | < 100ms | < 200ms | < 300ms |
| CLS | < 0.1 | < 0.15 | < 0.2 |
| TTFB | < 400ms | < 500ms | — |
| Bundle size (initial) | < 100KB gzip | < 150KB gzip | < 200KB gzip |

### TODO: Performance

- [ ] 🔴 Bundle analyzer: отслеживать размер каждого route bundle в CI
- [ ] 🔴 Image optimization: Next.js Image component, WebP/AVIF, srcset, lazy loading
- [ ] 🔴 Video: poster frame → autoplay muted → user interaction → sound. Без autoplay с звуком
- [ ] 🔴 Font loading: `font-display: swap`, preload critical fonts, subset кириллица + латиница
- [ ] 🔴 Code splitting: dynamic import для тяжелых компонентов (charts, editors, video player)
- [ ] 🔴 Prefetch: prefetch следующей вероятной страницы (hover на карточке → prefetch курса)
- [ ] 🔴 Service Worker: офлайн shell для student app, кэш каталога (Phase 2)
- [ ] 🔴 Стратегия Third-party scripts: отложенная загрузка analytics после LCP

---

## SEO

### Критично для платформы — органический трафик = бесплатные студенты

- [ ] 🔴 Страницы курсов — SSR, structured data (Course schema, aggregateRating)
- [ ] 🔴 Категории — SSR, canonical URLs, хлебные крошки
- [ ] 🔴 Sitemap: автогенерация для всех курсов, категорий
- [ ] 🔴 Open Graph / Twitter Cards: каждая страница — title, description, image (или video preview)
- [ ] 🔴 Video SEO: VideoObject schema, video sitemap для Google Video Search
- [ ] 🔴 Мультиязычность: hreflang tags, URL strategy (subdomain vs path prefix)
- [ ] 🔴 robots.txt: закрыть профиль, admin от индексации
- [ ] 🔴 Page Speed: Google учитывает Core Web Vitals в ранжировании — бюджеты выше

---

## Mobile

### 80%+ трафика — мобильные устройства

- [ ] 🔴 Mobile-first responsive design. Desktop — адаптация, не наоборот
- [ ] 🔴 Touch targets: минимум 44x44px для интерактивных элементов
- [ ] 🔴 Bottom navigation bar для student app (главная, поиск, мои курсы, профиль)
- [ ] 🔴 Pull-to-refresh на списках
- [ ] 🔴 Swipe gestures: переключение уроков, навигация
- [ ] 🔴 PWA manifest: install prompt, splash screen, standalone mode
- [ ] 🔴 Оптимизация для медленных сетей: skeleton screens, progressive image loading, offline fallback
- [ ] 🔴 Deep linking: ссылки из push/email открывают правильную страницу
- [ ] 🔴 Native app (Phase 3): React Native или Capacitor — решить позже, пока PWA

---

## API взаимодействие

### Typed API client

- [ ] 🔴 OpenAPI spec генерируется из FastAPI (backend) автоматически
- [ ] 🔴 TypeScript клиент генерируется из OpenAPI spec (`openapi-typescript-codegen` или `orval`)
- [ ] 🔴 Авто-обновление при изменении backend API в CI
- [ ] 🔴 TanStack Query wrappers вокруг сгенерированного клиента
- [ ] 🔴 Optimistic updates для enrollment, favorites, отзывов
- [ ] 🔴 WebSocket клиент для: progress tracking, Q&A, real-time notifications

### Error handling на фронте

- [ ] 🔴 Global error boundary (React Error Boundary) с fallback UI
- [ ] 🔴 Per-route error boundaries для изоляции
- [ ] 🔴 Toast notifications для операционных ошибок (enrollment, оплата)
- [ ] 🔴 Retry стратегия: автоматический retry для network errors (TanStack Query built-in)
- [ ] 🔴 Offline indicator + queue actions для отправки при восстановлении сети

---

## Интернационализация (i18n)

- [ ] 🔴 next-intl или next-i18next — определить библиотеку
- [ ] 🔴 Поддержка RTL (если целевые рынки требуют)
- [ ] 🔴 Формат: цены (валюта, разделители), даты, числа — через Intl API
- [ ] 🔴 Языки Phase 1: русский, английский
- [ ] 🔴 Стратегия: ключи в коде, переводы в JSON файлах, lazy load по locale

---

## Тестирование фронтенда

| Тип | Инструмент | Что тестируем | Когда |
|-----|-----------|--------------|-------|
| Unit | Vitest | Hooks, утилиты, форматтеры | Каждый PR |
| Component | Vitest + Testing Library | UI компоненты в изоляции | Каждый PR |
| Integration | Playwright | Критические flow (поиск → курс → enrollment) | Каждый PR |
| Visual regression | Playwright screenshots | UI не сломался после изменений | Каждый PR |
| Accessibility | axe-core + Playwright | WCAG 2.1 AA compliance | Еженедельно |
| Performance | Lighthouse CI | Core Web Vitals не деградировали | Каждый PR |

### TODO: Testing

- [ ] 🔴 Vitest + React Testing Library setup
- [ ] 🔴 Playwright setup с base fixtures (auth, seeded data)
- [ ] 🔴 Lighthouse CI в GitHub Actions: fail PR если LCP > budget
- [ ] 🔴 Storybook для UI Kit components (документация + visual testing)
- [ ] 🔴 Mock Service Worker (MSW) для тестов без реального API

---

## Фазовость

### Phase 0: MVP ✅ DONE
- Student: каталог, поиск, карточка курса, curriculum, страница урока, прогресс, enrollment, notifications
- Teacher: создание/редактирование курса, мои курсы (через buyer app)
- Admin: верификация teachers (/admin/teachers)
- UI Kit: CourseCard, Header
- Seller app: заглушка (пустые директории)

### Phase 1: Launch
- Teacher dashboard MVP (курсы, студенты, базовая аналитика)
- Video upload + player (HLS streaming)
- Admin panel MVP (модерация, пользователи)
- Push notifications (Web Push API)
- Student-Teacher Q&A
- i18n: 2 языка

### Phase 2: Growth
- CurriculumEditor (drag-n-drop модули и уроки)
- Advanced teacher analytics (Recharts)
- A/B testing разных UI вариантов
- Performance optimization: Service Worker, advanced prefetching
- Recommendation widgets

### Phase 3: Scale
- Native mobile app (React Native или Capacitor)
- Live lessons UI (video + chat + Q&A overlay)
- AI-powered course search
- PWA offline mode (cached lessons)
- 5+ языков
