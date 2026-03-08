# KnowledgeOS — Product Scope & Analysis

> Дата: 2026-03-08 | Автор: Arman | Статус: Active

---

## 1. Продукт As-Is

### Что это

B2B AI-платформа для онбординга инженеров. Берёт кодовую базу и документацию компании, строит граф знаний и проводит персонализированные 15-минутные сессии с AI-коучем. Цель: сократить онбординг с 90 дней до 30.

### Что реализовано

| Слой | Компоненты | Статус |
|------|-----------|--------|
| **Backend** | 9 Python-сервисов (identity, payment, notification, ai, learning, rag, course, enrollment, mcp) | Полностью работают, 1634 теста |
| **Rust performance** | api-gateway (JWT, rate limiting), ws-gateway (WebSocket), embedding-orchestrator | Работают |
| **Frontend** | buyer app — 28 страниц, 71 компонент, Dark Knowledge тема | Работает |
| **Инфраструктура** | Docker Compose (dev/prod/staging), Prometheus, Grafana, seed-данные | Готова |
| **AI pipeline** | Tri-agent (Strategist → Designer → Coach), mock-режим без API ключей | Работает |
| **RAG** | Ingestion документов, Qdrant vectors, GitHub adapter, concept extraction | Работает |

### Что умеет продукт (функционал)

**Ядро:**
- Регистрация → выбор организации → онбординг (5 шагов)
- Загрузка документов/GitHub репо → автоматическая разбивка на чанки → извлечение концептов → граф знаний
- Генерация ежедневных миссий (15 мин): recap вопросы → чтение → вопросы → код-кейс
- AI-коуч ведёт сессию в сократическом стиле со стримингом ответов
- Spaced repetition (FSRS) для флешкарт
- Trust Levels (0-5) — прогрессивный доступ к системам компании
- Семантический поиск по базе знаний
- Team analytics — heatmap прогресса команды
- Gamification: streaks, badges, XP, leaderboard

**B2B:**
- Мультитенантность (org_id изоляция)
- Org subscriptions (Stripe)
- Org admin dashboard (управление участниками)
- Per-org LLM конфигурация

**Инфраструктура:**
- Все внешние API работают в mock-режиме (Gemini, Stripe, email, embeddings)
- Docker Compose поднимает всё одной командой
- Seed-данные: Acme Engineering (10 участников, 47 концептов, 16 миссий, флешкарты)
- Demo user: `demo@acme.com` / `demo123`

### Текущий демо-формат

```
docker compose up → seed → pnpm dev → открыть localhost:3001

Путь: Landing → Register → Onboarding (5 шагов) → Dashboard (7 блоков) →
→ Knowledge Graph → Start Mission → Coach Session (streaming) →
→ Flashcards → Search → Team Analytics → Badges

Время: ~5-7 минут
```

Всё работает локально, без внешних API ключей. Полностью автономная демонстрация.

---

## 2. Gap Analysis: Demo vs Production

### Что есть и чего не хватает

| Область | Demo (сейчас) | Production (нужно) | Критичность |
|---------|--------------|-------------------|-------------|
| **AI ответы** | Mock — шаблонные ответы | Реальный Gemini/Claude — адаптивные ответы | Блокер для пилота |
| **Embeddings** | Stub — случайные вектора | Реальные Gemini embeddings — качественный поиск | Блокер для пилота |
| **Email** | Stub — логи | Resend/SendGrid — реальная доставка | Нужно к пилоту |
| **Платежи** | Mock Stripe | Реальный Stripe | Нужно к revenue |
| **Деплой** | Docker Compose локально | Cloud (VPS/K8s) с доменом и HTTPS | Блокер для пилота |
| **GitHub OAuth** | Адаптер есть, OAuth flow нет | Полный OAuth + webhook auto-ingestion | Нужно к пилоту |
| **Авторизация** | JWT, базовые роли | + OAuth login (Google/GitHub), email verification в проде | Желательно |
| **Мониторинг** | Prometheus/Grafana локально | Alerting, error tracking (Sentry), uptime monitoring | Нужно к проду |
| **Backup** | Скрипты есть | Автоматический cron backup, point-in-time recovery | Нужно к проду |
| **Rate limiting** | Redis-based (работает) | + DDoS protection (Cloudflare) | Желательно |
| **Тесты** | 1634 unit | + E2E (Playwright), + integration с реальными API | Желательно |
| **CI/CD** | GitHub Actions (lint, tests, build) | + auto-deploy на push в main | Нужно к проду |
| **Документация для клиента** | Нет | Onboarding guide, FAQ, API docs | Нужно к пилоту |

### Критический путь до первого пилота

```
1. Деплой на VPS ($20-50/мес) ← блокер
2. Реальные Gemini embeddings + AI ответы ($50-100/мес) ← блокер
3. GitHub OAuth для загрузки репо клиента ← блокер
4. Домен + HTTPS + DNS ← блокер
5. Базовая документация для клиента ← блокер
```

Всё остальное (Stripe, email, OAuth login, K8s) — не блокирует первый пилот.

---

## 3. Горизонт 1: Первый платящий пилот

### Цель

1 компания (5-20 инженеров) платит $1K-3K/мес за использование платформы для онбординга.

### Что нужно сделать

| Задача | Оценка (solo dev) | Стоимость |
|--------|-------------------|-----------|
| Деплой на VPS (Hetzner/DigitalOcean) | 2-3 дня | $20-50/мес |
| Домен + SSL + Cloudflare | 1 день | $10-15/год |
| Подключить Gemini API (AI + embeddings) | 1-2 дня | $50-200/мес (зависит от нагрузки) |
| GitHub OAuth flow (загрузка репо клиента) | 3-5 дней | $0 |
| Resend для email (verification, reminders) | 1 день | $0 (free tier: 3K emails/мес) |
| Landing page с формой waitlist | 1-2 дня | $0 |
| Базовый onboarding guide для клиента | 1-2 дня | $0 |
| Тестирование на реальных данных | 3-5 дней | $0 |
| **Итого** | **~2-3 недели** | **$80-265/мес** |

### Минимальный бюджет для запуска пилота

| Статья | Месяц | Комментарий |
|--------|-------|-------------|
| VPS (4 vCPU, 8GB RAM) | $30-40 | Hetzner CPX31 — хватит на 1 org, 20 users |
| Домен | $1/мес | (~$12/год) |
| Gemini API | $50-100 | 20 users × 1 mission/day × 30 дней |
| Resend | $0 | Free tier |
| **Итого** | **$80-140/мес** | Укладывается в бюджет $150-200 |

### Как найти первого клиента

**Варианты (без бюджета на маркетинг):**

1. **Личные контакты** — знакомые тимлиды/CTO в tech компаниях. Предложить бесплатный пилот на 1 месяц
2. **LinkedIn outreach** — cold outreach к Engineering Managers с pain point "onboarding takes 3 months"
3. **Dev communities** — написать пост на Habr/Medium: "Как мы сократили онбординг с 3 месяцев до 1 с помощью AI"
4. **Бесплатный пилот** — первые 1-3 клиента бесплатно, в обмен на feedback и кейс-стади
5. **ProductHunt launch** — бесплатный, может дать 500-2000 визитов за день

**Рекомендация:** вариант 1 + 4. Найти 1 знакомую команду, предложить бесплатно на месяц, собрать метрики.

### Метрики успеха пилота

| Метрика | Цель | Как измеряем |
|---------|------|-------------|
| Daily session completion | > 60% | completed_missions / active_users |
| Time on platform | > 15 мин/день | session duration |
| Knowledge retention (7d) | > 50% | flashcard review accuracy |
| NPS от менеджера | > 30 | опрос после 2 недель |
| "Готовы платить?" | Да | прямой вопрос после бесплатного месяца |

---

## 4. Горизонт 2: Product-Market Fit (5-10 клиентов)

### Цель

5-10 платящих клиентов, MRR $5K-30K, подтверждённые метрики удержания и ценности.

### Что нужно дополнительно

| Задача | Оценка (solo dev) | Стоимость |
|--------|-------------------|-----------|
| Stripe интеграция (реальные платежи) | 3-5 дней | 2.9% + $0.30 за транзакцию |
| OAuth login (Google/GitHub SSO) | 3-5 дней | $0 |
| Multi-org isolation тестирование | 2-3 дня | $0 |
| Webhook ingestion (auto-update при push в repo) | 3-5 дней | $0 |
| Admin dashboard для org owner | 2-3 дня | Уже частично есть |
| Sentry error tracking | 1 день | $0 (free tier) |
| Автоматический backup | 1 день | $5/мес (S3) |
| Апгрейд инфры (больше RAM для 5+ orgs) | 1 день | $60-100/мес |
| Customer support flow (email/Slack) | 2-3 дня | $0 |
| Analytics dashboard для себя (retention, usage) | 3-5 дней | $0 |
| **Итого** | **~4-6 недель** | **$65-105/мес доп.** |

### Инфраструктура на 5-10 клиентов

| Компонент | Конфигурация | Стоимость |
|-----------|-------------|-----------|
| VPS (8 vCPU, 16GB RAM) | Hetzner CPX41 | $60/мес |
| Managed PostgreSQL | Или продолжать на VPS | $0-30/мес |
| Redis | На том же VPS | $0 |
| Gemini API | 100-200 users | $200-500/мес |
| S3 backup | 50GB | $5/мес |
| Домен + Cloudflare | DNS + CDN + DDoS | $1/мес |
| **Итого инфра** | | **$270-600/мес** |

### Unit Economics при PMF

**При 5 клиентах (Pilot tier $2K/мес):**

| Статья | Сумма |
|--------|-------|
| Revenue (MRR) | $10,000 |
| Инфра | -$400 |
| Gemini API | -$300 |
| Домен/сервисы | -$50 |
| **Gross Profit** | **$9,250 (92.5% margin)** |

**При 10 клиентах ($2K/мес):**

| Статья | Сумма |
|--------|-------|
| Revenue (MRR) | $20,000 |
| Инфра | -$600 |
| Gemini API | -$500 |
| Сервисы | -$100 |
| **Gross Profit** | **$18,800 (94% margin)** |

### Метрики PMF

| Метрика | Цель | Сигнал PMF |
|---------|------|-----------|
| Logo retention (месяц) | > 80% | Клиенты не уходят |
| Net Revenue Retention | > 100% | Клиенты расширяют seats |
| Органические referrals | > 30% new | Приходят по рекомендации |
| Time-to-productivity | -40% vs baseline | Измеримая ценность |
| Sean Ellis test | > 40% "very disappointed" | Продукт необходим |

---

## 5. Горизонт 3: Seed-раунд

### Что показать инвестору

**Traction (идеальный сценарий):**
- 5-10 платящих клиентов
- MRR $10K-20K
- Рост 15-20% MoM
- 1-2 кейс-стади с конкретными цифрами ("сократили онбординг с 12 до 4 недель")

**Продукт:**
- Работающая платформа с реальными пользователями
- AI-коуч, который реально учит (не просто чат-бот)
- Knowledge graph из реального кода клиента
- Демо за 5 минут: загрузка репо → граф знаний → миссия → коуч

**Рынок:**
- TAM: $4.2B (enterprise onboarding software)
- SAM: $800M (tech company onboarding)
- SOM: $50M (AI-powered dev onboarding)
- Pain point: $50K-100K стоимость онбординга одного senior инженера (3 месяца × зарплата × потеря продуктивности)

### Сколько просить

| Стадия | Сумма | На что | Runway |
|--------|-------|--------|--------|
| Pre-seed (friends/angels) | $50K-150K | 6-12 мес runway, 1 человек | Довести до PMF |
| Seed | $500K-1.5M | Команда 3-5 чел, маркетинг, инфра | 12-18 мес |

### На что пойдут деньги (Seed $500K)

| Статья | Сумма | % |
|--------|-------|---|
| Команда (2-3 инженера) | $300K | 60% |
| Инфраструктура (12 мес) | $30K | 6% |
| API costs (LLM, embeddings) | $30K | 6% |
| Маркетинг + sales | $80K | 16% |
| Юридические, бухгалтерия | $20K | 4% |
| Резерв | $40K | 8% |

### Что нужно построить к раунду (помимо PMF)

| Задача | Зачем |
|--------|-------|
| Kubernetes deployment | "Мы готовы к масштабу" |
| SOC 2 compliance (базовый) | Enterprise клиенты требуют |
| Analytics dashboard (ClickHouse) | Показать data-driven подход |
| Jira/Slack интеграции | Расширить value proposition |
| Self-serve onboarding | Снизить CAC |
| Model routing (Gemini → Claude → local) | Показать оптимизацию costs |

---

## 6. Гипотезы и риски

### Ключевые гипотезы (нужно валидировать)

| # | Гипотеза | Как проверить | Статус |
|---|----------|--------------|--------|
| H1 | Инженеры будут тратить 15 мин/день на AI-сессии | Пилот: daily completion rate > 60% | Не проверена |
| H2 | AI-коуч на базе кода компании полезнее чем ChatGPT | Пилот: NPS > 30, "лучше чем просто спросить коллегу" | Не проверена |
| H3 | Менеджеры готовы платить $1-3K/мес за ускорение онбординга | Пилот: готовность платить после бесплатного месяца | Не проверена |
| H4 | Spaced repetition реально улучшает retention архитектурных решений | Пилот: 7d recall > 50% | Не проверена |
| H5 | Knowledge graph из кода даёт лучший контекст чем wiki | Пилот: qualitative feedback | Не проверена |
| H6 | Trust Levels мотивируют больше чем обычный XP | Пилот: engagement rate | Не проверена |

### Риски

| Риск | Вероятность | Влияние | Митигация |
|------|------------|---------|-----------|
| **Нет спроса** — компании не хотят платить за AI-онбординг | Высокая | Критический | Бесплатные пилоты, customer development до написания кода |
| **AI недостаточно умный** — Gemini Flash не справляется с code review quality | Средняя | Высокий | Model routing, fallback на Claude, fine-tuning |
| **Solo founder burnout** — один человек не может и код, и продажи, и поддержку | Высокая | Высокий | Найти co-founder (sales/product), ограничить scope |
| **Конкуренция** — GitHub Copilot Workspace, Cursor, большие игроки | Средняя | Средний | Фокус на onboarding niche (не general coding assistant) |
| **Security concerns** — компании не хотят отдавать код на внешнюю платформу | Высокая | Высокий | On-premise опция, SOC 2, data isolation |
| **LLM costs растут** — при масштабе API costs съедают маржу | Низкая | Средний | Model routing, caching, self-hosted models |
| **Бюджет $150-200** — не хватит на первый месяц VPS + API | Средняя | Блокер | Начать с free tier Gemini (15 RPM), минимальный VPS |

---

## 7. Конкурентный ландшафт

| Продукт | Что делает | Цена | Наше отличие |
|---------|-----------|------|-------------|
| **Onboard.io** | Checklists + tasks | $5/user/мес | У нас AI + knowledge graph, а не чеклисты |
| **Trainual** | SOP documentation | $8/user/мес | У нас персонализация + spaced repetition |
| **Guru** | Knowledge wiki + AI search | $10/user/мес | У нас structured learning, не просто поиск |
| **GitHub Copilot** | Code completion | $19/user/мес | У нас обучение, не автокомплит |
| **Cursor** | AI IDE | $20/user/мес | Другой use case (productivity vs onboarding) |

**Наша ниша:** структурированное обучение новых инженеров на основе кода компании. Не wiki, не чат-бот, не IDE — а AI-ментор с программой обучения.

---

## 8. Стратегия: KnowledgeOS как портфолио и самопиар

### Позиционирование

KnowledgeOS — это не стартап для продаж. Это **открытый проект-портфолио**, демонстрирующий уровень senior/staff engineer в нескольких доменах одновременно. Цель — получить сильную работу (Backend, Systems, AI/ML) или крупные контракты ($5K-50K) через видимость в dev-сообществе.

### Что делает проект уникальным для найма

| Навык | Доказательство | Почему это впечатляет |
|-------|---------------|----------------------|
| **Python backend** | 9 микросервисов, Clean Architecture, FastAPI, asyncpg, 1634 теста | Не CRUD-todo, а production-grade система с domain isolation |
| **Rust systems** | api-gateway (axum, JWT, rate limiting), ws-gateway, PyO3 FFI | Python + Rust = редкий и ценный combo |
| **AI/ML/LLM** | Tri-agent pipeline, RAG с Qdrant, concept extraction, FSRS | Не "обёртка над ChatGPT", а полноценный AI-продукт |
| **System design** | Микросервисы, event-driven (NATS), multi-tenancy, protobuf contracts | Реальная распределённая система, не монолит |
| **DevOps** | Docker Compose (3 среды), Prometheus, Grafana, CI/CD, seed scripts | Production-ready инфра с мониторингом |
| **TDD** | 1634 теста, AsyncMock, conftest fixtures | Культура качества, а не "потом напишу" |
| **Код в одиночку** | 12 сервисов, 28 страниц UI, Rust + Python + TypeScript | Масштаб, который обычно делает команда из 3-5 человек |

### Целевые позиции

| Позиция | Рынок | Зарплата/рейт | Что показать |
|---------|-------|--------------|-------------|
| Backend Engineer (Python) | СНГ remote | $3-6K/мес | Clean Architecture, TDD, 9 сервисов |
| Backend Engineer (Python) | US/EU remote | $8-15K/мес | То же + масштаб системы |
| Systems Engineer (Rust) | US/EU remote | $10-18K/мес | api-gateway, PyO3, ws-gateway |
| AI/ML Engineer | US/EU remote | $10-20K/мес | RAG pipeline, tri-agent, FSRS |
| Freelance/Контракты | Международный | $5K-50K/проект | "Я построил это один — могу построить вам" |

---

### Фаза 1: Упаковка репозитория (1 неделя, $0)

Цель: человек заходит на GitHub → за 30 секунд понимает масштаб → хочет узнать больше.

#### 1.1 README как лендинг

Текущий README — технический. Нужно переформатировать для первого впечатления:

```
# KnowledgeOS

> AI-powered engineer onboarding platform. Built solo: 12 services, 1634 tests,
> Python + Rust + TypeScript.

[3-секундный GIF демо]

## What's Inside
- 9 Python microservices (FastAPI, Clean Architecture, TDD)
- 3 Rust services (axum, PyO3 FFI, WebSocket)
- RAG pipeline: GitHub repos → embeddings → knowledge graph → AI coach
- Tri-agent AI: Strategist → Designer → Coach (Socratic method)
- Spaced repetition (FSRS), gamification, real-time WebSocket
- 1634 tests, Docker Compose, Prometheus + Grafana

## Architecture
[Диаграмма]

## Quick Start
docker compose up → localhost:3001 → demo@acme.com / demo123
```

**Ключевые элементы:**
- GIF/видео демо в первом экране (3-5 секунд, анимация dashboard → graph → coach)
- Архитектурная диаграмма (Mermaid или SVG)
- Badges: тесты, линтер, build status
- "Built by one person" — явно указать

#### 1.2 Архитектурная диаграмма

Создать SVG/Mermaid диаграмму для README:

```
Client (Next.js) → Rust API Gateway → 9 Python Services
                                    → PostgreSQL (7 instances)
                                    → Redis, NATS, Qdrant
                                    → Prometheus + Grafana
```

#### 1.3 Демо-видео (3 минуты)

Записать screen recording (OBS, бесплатно):

```
0:00 — "Привет, я Arman. Я построил это один."
0:15 — docker compose up (ускоренно)
0:30 — Регистрация → онбординг
1:00 — Dashboard (7 блоков)
1:15 — Knowledge Graph (wow-момент)
1:30 — Mission → Coach session (streaming)
2:00 — Flashcards → Search
2:15 — Team analytics
2:30 — "Архитектура: 12 сервисов, Rust + Python, 1634 теста"
2:45 — GitHub ссылка
```

Выложить на YouTube (unlisted или public), вставить в README.

#### 1.4 Live demo ($7/мес, опционально)

Деплой на Hetzner CPX11 ($7/мес) чтобы рекрутер/клиент мог потыкать без установки Docker:

- `https://demo.knowledgeos.dev` (или похожий домен)
- demo@acme.com / demo123
- Mock-режим (без API ключей)
- Только для демонстрации, не для продакшена

**Бюджет:** $7/мес VPS + $1/мес домен = **$8/мес**

---

### Фаза 2: Контент-маркетинг (2-3 недели, $0)

Цель: 3 статьи на площадках где сидят инженеры и рекрутеры. Каждая статья — повод посмотреть на GitHub.

#### Статья 1: Архитектурный обзор (Hacker News + dev.to + Habr)

**Заголовок:** "I built a 12-service AI platform solo — here's the architecture"

**Структура:**
1. Проблема: онбординг инженеров занимает 3 месяца
2. Решение: AI-коуч, обучённый на коде компании
3. Архитектура: почему 12 сервисов, а не монолит
4. Python для бизнес-логики, Rust для performance — как делил
5. Tri-agent AI pipeline: Strategist → Designer → Coach
6. 1634 теста: почему TDD обязателен
7. Что бы сделал иначе
8. Ссылка на GitHub

**Площадки:**
- **Hacker News** (Show HN) — потенциал: 100-500 upvotes, 10K-50K views
- **dev.to** — SEO-трафик, долгосрочная видимость
- **Habr** (русская версия) — СНГ аудитория, рекрутеры из Яндекс/VK/Kaspi

#### Статья 2: Rust + Python (Reddit r/rust + r/python)

**Заголовок:** "Why I used Rust for API gateway and Python for business logic in the same project"

**Структура:**
1. Критерии выбора: p99 < 50ms → Rust, остальное → Python
2. API Gateway на axum: JWT, rate limiting, reverse proxy
3. PyO3 FFI: Rust chunker вызывается из Python
4. WebSocket gateway на Rust + Python notification service
5. Результаты: latency, throughput, developer experience
6. Ссылка на код

**Площадки:**
- **Reddit r/rust** — активное community, любят real-world examples
- **Reddit r/python** — огромная аудитория
- **Lobsters** — quality-focused HN альтернатива

#### Статья 3: RAG для кода (AI/ML community)

**Заголовок:** "Building a RAG pipeline that turns GitHub repos into a knowledge graph"

**Структура:**
1. Проблема: как извлечь знания из кодовой базы
2. Pipeline: clone → chunk (Rust FFI) → embed (Gemini) → store (Qdrant)
3. Concept extraction: LLM извлекает концепты и связи
4. Semantic search: как работает поиск по коду
5. Knowledge graph: визуализация с React Flow
6. Метрики: chunking speed, search relevance
7. Ссылка на код

**Площадки:**
- **dev.to** / **Medium** (AI/ML tag)
- **Reddit r/MachineLearning**, **r/LocalLLaMA**
- **Twitter/X** — thread с картинками

---

### Фаза 3: Присутствие в сети (постоянно, $0)

#### LinkedIn

**Профиль:**
- Headline: "Backend & AI Engineer | Built a 12-service AI platform solo (Python + Rust)"
- Featured: ссылка на GitHub + демо-видео
- About: 3 абзаца — кто ты, что построил, что ищешь

**Контент (1-2 поста в неделю):**
- Архитектурные решения из проекта (с картинками/диаграммами)
- "Почему я выбрал X вместо Y" — короткие посты
- Числа: "1634 теста", "9 микросервисов", "12 сервисов один человек"

#### GitHub Profile

- Pin KnowledgeOS как главный репо
- Contribution graph должен быть зелёным (уже есть)
- README профиля: краткое intro + ссылка на проект

#### Twitter/X (опционально)

- Техно-контент: короткие threads про архитектуру
- Screenshots/GIFs из проекта
- Hashtags: #buildinpublic #rustlang #python #ai

---

### Фаза 4: Конвертация внимания в работу/контракты

#### Для найма (remote позиции)

**Где искать:**
- **LinkedIn Jobs** — "Backend Engineer Python", "Systems Engineer Rust", "AI Engineer"
- **Otta.com** — tech startups, remote-first
- **arc.dev** — remote developer marketplace
- **Toptal** — высокие рейты ($80-150/час), жёсткий отбор
- **WeWorkRemotely** — remote-only вакансии
- **hh.ru / Хабр Карьера** — СНГ рынок

**Сопроводительное письмо (шаблон):**
```
I'm a backend/systems engineer who built KnowledgeOS — a 12-service
AI platform with Python, Rust, and TypeScript. Solo.

Highlights:
- 9 Python microservices (FastAPI, Clean Architecture, 1634 tests)
- Rust API gateway (axum, JWT, WebSocket, rate limiting)
- RAG pipeline: GitHub → embeddings → knowledge graph → AI coach
- Tri-agent AI system, spaced repetition (FSRS), real-time streaming

GitHub: [link] | Live demo: [link] | Architecture deep-dive: [article link]

I'm looking for [Backend/AI/Systems] roles where I can work on
complex distributed systems. Happy to discuss.
```

#### Для контрактов/фриланса

**Где искать:**
- **Upwork** — профиль с проектом как showcase, bidding на $5K+ контракты
- **Toptal** — после прохождения отбора, высокие рейты
- **LinkedIn** — прямые предложения после статей
- **Referrals** — после статей на HN/dev.to люди пишут сами

**Позиционирование:**
"Я один построил enterprise-grade AI платформу. Могу построить такую же для вас."

---

### Timeline и бюджет

| Неделя | Действие | Бюджет | Результат |
|--------|---------|--------|-----------|
| **1** | README переделать, GIF записать, диаграмму нарисовать | $0 | GitHub выглядит как портфолио |
| **1** | Записать 3-мин демо-видео, выложить на YouTube | $0 | Визуальное доказательство |
| **2** | Статья 1: архитектурный обзор → HN + dev.to + Habr | $0 | Первый трафик на GitHub |
| **2** | LinkedIn: обновить профиль, первый пост | $0 | Профессиональное присутствие |
| **3** | Статья 2: Rust + Python → Reddit | $0 | Rust community видимость |
| **3** | Деплой live demo (опционально) | $8/мес | Можно потыкать без Docker |
| **4** | Статья 3: RAG pipeline → AI community | $0 | AI/ML видимость |
| **4** | Начать отправлять заявки на вакансии/контракты | $0 | Конвертация в работу |
| **5+** | 1-2 LinkedIn поста в неделю, отклики на вакансии | $0 | Постоянный поток |

**Общий бюджет: $0-8/мес**

---

### Метрики успеха (через 2 месяца)

| Метрика | Цель | Как измерить |
|---------|------|-------------|
| GitHub stars | > 50 | GitHub |
| Статьи опубликованы | 3 | HN + dev.to + Habr |
| HN upvotes (лучшая статья) | > 50 | Hacker News |
| LinkedIn connections (tech) | +100 | LinkedIn |
| Входящие сообщения (работа/контракт) | > 5 | LinkedIn + email |
| Собеседования пройдено | > 3 | Трекинг |
| Оффер/контракт получен | > 1 | Цель |

---

## 9. Резюме

### Что есть
Полностью работающий open-source продукт: 12 сервисов, 1634 теста, 28 страниц UI, AI pipeline, RAG, knowledge graph, gamification, mock-режим. Технически — одна из самых продвинутых solo-dev платформ.

### Стратегия
KnowledgeOS — это **портфолио-проект** для самопиара. Не стартап для продаж. Цель — видимость в dev-сообществе → сильная работа (Backend/Systems/AI) или крупные контракты.

### Что делать (в порядке приоритета)
1. **Неделя 1:** Переделать README, записать GIF + видео, обновить LinkedIn
2. **Неделя 2-3:** Написать 2 технические статьи (HN, dev.to, Habr)
3. **Неделя 3-4:** Третья статья + начать подавать на вакансии
4. **Неделя 5+:** Постоянный контент + отклики на вакансии/контракты

### Бюджет
$0-8/мес. Всё остальное — время и усилия.

### Главный актив
Не код. Код — это доказательство. Главный актив — **история**: "Я один построил enterprise-grade AI платформу с 12 сервисами и 1634 тестами". Эта история продаёт тебя лучше любого резюме.
