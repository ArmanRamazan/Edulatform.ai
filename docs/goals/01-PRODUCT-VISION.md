# 01 — Видение продукта: Learning Velocity Platform

> Владелец: CEO / CPO
> Последнее обновление: 2026-03-03

---

## Миссия

**Не просто смотри видео — учись быстрее.**

Платформа, которая оптимизирует скорость обучения через AI-адаптацию, knowledge graphs, spaced repetition и активное обучение. Цель — 10M активных пользователей с completion rate 40%+ (vs 13% у индустрии).

---

## Почему не "ещё один Udemy"

87.4% онлайн-курсов никогда не завершаются. Причина — пассивное потребление видео без адаптации, обратной связи и активного обучения.

Существующие платформы делают **одно из**:
- Видео-курсы (Coursera/Udemy) — без AI-адаптации
- AI-адаптация (Squirrel AI) — только K-12, не general-purpose
- Knowledge management (Obsidian/NotebookLM) — инструменты, не платформы
- Gamification (Duolingo) — только языки

**Никто не объединяет все четыре** для взрослых. Мы это делаем.

---

## Core Learning Loop

Продукт реализует 4-step evidence-based цикл обучения:

```
  ┌──────────────┐     ┌──────────────┐
  │  1. CONSUME   │────▶│  2. PRACTICE  │
  │  Video/Text   │     │  Quiz/Code    │
  │  AI Summary   │     │  Active Recall│
  └──────────────┘     └──────┬───────┘
         ▲                     │
         │                     ▼
  ┌──────┴───────┐     ┌──────────────┐
  │  4. CONNECT   │◀────│  3. REFLECT   │
  │  Knowledge    │     │  AI Tutor     │
  │  Graph        │     │  Socratic Q   │
  └──────────────┘     └──────────────┘

  Spaced Repetition планирует повторения по всем 4 шагам
```

---

## Текущее состояние продукта (Phase 0–2.4 ✅, 3.1–3.2 backend ✅)

### Что работает

| Возможность | Статус |
|-------------|--------|
| Регистрация, авторизация (JWT, roles, refresh tokens) | ✅ |
| Email verification, forgot password | ✅ |
| Admin: верификация teachers | ✅ |
| Rate limiting (per-IP, Redis sliding window) | ✅ |
| CORS, XSS sanitization, health checks | ✅ |
| Каталог курсов + ILIKE поиск (pg_trgm, p99 < 50ms) | ✅ |
| Категории + фильтрация (level, is_free) + сортировка | ✅ |
| Redis кэширование (cache-aside, TTL 5 min) | ✅ |
| Cursor-based pagination | ✅ |
| CRUD курсов, модулей, уроков (verified teachers) | ✅ |
| Curriculum (модули + уроки) | ✅ |
| Enrollment (запись на курс) | ✅ |
| Progress tracking + auto-completion при 100% | ✅ |
| Reviews & ratings (1-5 stars + text) | ✅ |
| Payments (mock) | ✅ |
| Notifications (in-app) | ✅ |
| Buyer frontend (Next.js): все страницы | ✅ |
| TanStack Query + error boundaries + skeletons | ✅ |
| Prometheus + Grafana (22 panels) | ✅ |
| 400 тестов по 7 сервисам | ✅ |
| AI Service: quiz gen, summary, Socratic tutor, credits | ✅ |
| Learning Engine: quizzes, FSRS flashcards, knowledge graph | ✅ |
| Gamification: XP, streaks, badges, leaderboard, discussions | ✅ |
| Stripe backend: subscriptions, earnings, payouts | ✅ |
| Onboarding flow | ✅ |
| Seller App scaffolded (auth + API client) | ✅ |

### Замкнутый цикл обучения ✅

Admin → teacher creates course → student finds → enrolls → completes lessons → takes quiz → reviews flashcards → asks AI tutor → earns XP/badges → joins leaderboard → discusses.

### Чего НЕ хватает для полного Growth

| Пробел | Почему критично |
|--------|----------------|
| Stripe frontend (checkout, pricing page) | Нельзя принимать реальные платежи |
| Seller App pages | Teachers не видят аналитику и earnings |
| SEO | Нет органического трафика |
| CI/CD | Нет автоматического тестирования на PR |
| Real email delivery | Verification/reset через stdout stub |
| Certificates | Нет мотивации завершить курс до конца |
| Video upload | Нет видео-контента от teachers |

---

## Ключевые бизнес-метрики (North Star)

| Метрика | Foundation ✅ | Learning Intelligence | Growth | Scale |
|---------|-------------|----------------------|--------|-------|
| MAU | 1-100 (тест) | 10K → 100K | 1M | 10M |
| Course completion rate | ~13% (industry) | **40%+** | 50%+ | 60%+ |
| Retention 7d | unknown | **60%+** | 70%+ | 75%+ |
| DAU/MAU | unknown | **25%+** | 30%+ | 35%+ |
| Avg quiz score | N/A | **70%+** | 75%+ | 80%+ |
| Time-to-competency | baseline | **-30%** | -40% | -50% |
| Revenue / мес | $0 | $6K | $1.4M | $18M |

---

## Revenue Streams (обновлённые)

| Источник | Описание | Фаза |
|----------|----------|------|
| Subscription (Student) | $9.99/мес — unlimited courses, spaced repetition, knowledge graph | Growth |
| Subscription (Pro) | $19.99/мес — AI tutor, velocity dashboard, Obsidian export | Growth |
| Team/B2B | $14.99/seat — admin dashboard, team analytics | Growth |
| Commission | % с платных курсов | Growth |
| Certificates | Платные сертификаты при completion | Growth |
| Free tier | 5 courses, 10 tutor chats, basic quizzes | Learning Intelligence |

---

## Конкурентные преимущества

1. **Learning Velocity** — единственная платформа, которая измеряет и оптимизирует скорость обучения
2. **Evidence-based** — каждая фича основана на исследованиях (spaced repetition, active recall, Socratic method)
3. **AI дешёвый** — $0.03/user/мес через model routing (80% запросов на Gemini Flash Lite)
4. **Полный цикл** — consume → practice → reflect → connect (не просто видео)
5. **Knowledge graph** — визуальная карта знаний как метакогнитивный инструмент

---

## Ключевые продуктовые потоки

### Student Journey

- [x] ✅ Каталог курсов с поиском и фильтрами
- [x] ✅ Регистрация, email verification, login
- [x] ✅ Запись на курс (бесплатный / платный)
- [x] ✅ Прохождение уроков (markdown + video)
- [x] ✅ Прогресс: % завершения, auto-completion
- [x] ✅ Отзыв и оценка курса
- [x] ✅ Quiz после каждого урока (AI-generated)
- [x] ✅ AI Summary урока
- [x] ✅ Flashcards (FSRS-scheduled)
- [x] ✅ AI Socratic Tutor (chat per lesson)
- [x] ✅ Knowledge graph visualization
- [ ] 🔴 Learning Velocity Dashboard (sprint-10)
- [x] ✅ XP, streaks, badges
- [x] ✅ Course discussions
- [ ] 🟡 Реальные платежи (Stripe) — backend ✅, frontend sprint-3
- [ ] 🔴 Сертификат по завершении (PDF) — sprint-8
- [ ] 🔴 Push/email уведомления — sprint-7

### Teacher Journey

- [x] ✅ Регистрация, верификация через admin
- [x] ✅ CRUD курсов, модулей, уроков
- [x] ✅ "Мои курсы" dashboard
- [x] ✅ Тегирование concepts per lesson (knowledge graph)
- [ ] 🟡 Seller App — scaffolded, pages sprint-2/6
- [ ] 🟡 Аналитика — backend ✅ (GET /analytics/teacher), frontend sprint-6
- [ ] 🔴 Загрузка видео — sprint-13
- [ ] 🔴 Промо-инструменты — sprint-12

### Platform Operations

- [x] ✅ Admin panel (верификация teachers)
- [ ] 🔴 Модерация контента
- [ ] 🔴 Dispute resolution
- [ ] 🔴 Финансовая отчётность
