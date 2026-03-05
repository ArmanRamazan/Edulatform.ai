# 02 — API Reference

> Последнее обновление: 2026-03-05
> Стадия: B2B Agentic Adaptive Learning Pivot

---

## Общие endpoints (все сервисы)

### GET /health/live

Liveness probe. Всегда 200 если процесс жив.

**Response `200`:** `{"status": "ok"}`

### GET /health/ready

Readiness probe. Проверяет PostgreSQL и Redis (если есть).

**Response `200`:** `{"status": "ok", "checks": {"postgres": "ok", "redis": "ok"}}`
**Response `503`:** `{"status": "degraded", "checks": {"postgres": "unavailable"}}`

---

## API Gateway (`:8080`)

### JWT Verification Middleware

API Gateway валидирует JWT (HS256) для всех non-public routes. Public routes пропускаются без авторизации.

**Public routes (без JWT):**
- `GET /health/*`
- `POST /auth/register`
- `POST /auth/login`
- `POST /auth/forgot-password`

**Все остальные routes** требуют `Authorization: Bearer <token>`.

При успешной валидации gateway устанавливает upstream headers для Python-сервисов:

| Header | Source | Описание |
|--------|--------|----------|
| `X-User-Id` | `claims.sub` | UUID пользователя |
| `X-User-Role` | `claims.role` | `student` / `teacher` / `admin` |
| `X-User-Verified` | `claims.is_verified` | `true` / `false` |
| `X-Organization-Id` | `claims.organization_id` | UUID организации (отсутствует если null) |

**Ошибки:**

| Code | Причина |
|------|---------|
| 401 | Отсутствует Authorization header |
| 401 | Невалидная подпись JWT |
| 401 | Истёкший токен (exp < now) |

---

### Rate Limiting

Все запросы через API Gateway проходят Redis sliding window rate limiting по IP.

### Лимиты по route groups

| Route | Method | Лимит | Окно |
|-------|--------|-------|------|
| `/auth/register` | POST | 5 req | 60s |
| `/auth/login` | POST | 10 req | 60s |
| `/ai/*` | POST | 30 req | 60s |
| Все остальные | * | 100 req | 60s |

### Response Headers

Все ответы через gateway содержат rate limit headers:

| Header | Описание |
|--------|----------|
| `X-RateLimit-Limit` | Максимум запросов в окне |
| `X-RateLimit-Remaining` | Оставшиеся запросы |
| `X-RateLimit-Reset` | Unix timestamp сброса окна |

### 429 Too Many Requests

При превышении лимита:

```json
{ "error": "rate limit exceeded" }
```

Headers: `Retry-After` (секунды до сброса).

### Fail-open

При недоступности Redis запросы пропускаются без ограничений (fail-open).

### IP Extraction

Приоритет: `X-Forwarded-For` header (первый IP) > peer address.

---

### Reverse Proxy Routing

API Gateway маршрутизирует запросы к Python backend-сервисам на основе URL prefix. Неизвестные пути возвращают `404`.

| Prefix | Upstream | Сервис |
|--------|----------|--------|
| `/auth`, `/me`, `/users`, `/organizations`, `/follow`, `/referral` | `:8001` | Identity |
| `/payments`, `/subscriptions`, `/coupons`, `/earnings`, `/gifts`, `/org-subscriptions` | `:8004` | Payment |
| `/notifications`, `/conversations`, `/messages`, `/streak-reminders`, `/flashcard-reminders` | `:8005` | Notification |
| `/ai` | `:8006` | AI |
| `/quizzes`, `/flashcards`, `/concepts`, `/missions`, `/trust-level`, `/daily`, `/streaks`, `/leaderboard`, `/discussions`, `/xp`, `/badges`, `/pretests`, `/velocity`, `/activity`, `/study-groups` | `:8007` | Learning |
| `/kb`, `/sources`, `/upload`, `/templates` | `:8008` | RAG |

**Поведение:**
- Path и query params передаются upstream без изменений
- Request body и headers форвардятся (кроме hop-by-hop)
- `X-User-*` headers добавляются из JWT claims
- Timeout: 30s per request
- Connection pooling через reqwest Client
- Логирование на DEBUG: method, path, upstream, duration_ms

**Ошибки:**

| Code | Причина |
|------|---------|
| 404 | Путь не соответствует ни одному prefix |
| 502 | Upstream сервис недоступен |
| 504 | Upstream timeout (30s) |

---

## Identity Service (`:8001`)

### POST /register

Регистрация нового пользователя. Роль по умолчанию — `student`.

**Request:**
```json
{
  "email": "user@example.com",
  "password": "secret123",
  "name": "Ivan Petrov",
  "role": "student"          // optional, default "student". Enum: "student" | "teacher" | "admin"
}
```

**Response `200`:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "urlsafe-base64-token...",
  "token_type": "bearer"
}
```

**Errors:**
| Code | Причина |
|------|---------|
| 409 | Email уже зарегистрирован |
| 422 | Невалидные данные (email формат, пустые поля) |
| 429 | Too many registration attempts (5/min per IP) |

---

### POST /login

Аутентификация по email + password.

**Request:**
```json
{
  "email": "user@example.com",
  "password": "secret123"
}
```

**Response `200`:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "urlsafe-base64-token...",
  "token_type": "bearer"
}
```

**Errors:**
| Code | Причина |
|------|---------|
| 400 | Неверный email или пароль |
| 422 | Невалидные данные |
| 429 | Too many login attempts (10/min per IP) |

---

### GET /me

Информация о текущем пользователе. Требует JWT.

**Headers:** `Authorization: Bearer <token>`

**Response `200`:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "email": "user@example.com",
  "name": "Ivan Petrov",
  "role": "student",
  "is_verified": false,
  "email_verified": false,
  "created_at": "2026-02-20T12:00:00+00:00"
}
```

**Errors:** `401` — отсутствует или невалидный токен.

---

### PATCH /me

Обновление профиля текущего пользователя. Требует JWT.

**Headers:** `Authorization: Bearer <token>`

**Request:**
```json
{
  "name": "New Name",       // optional
  "bio": "About me...",     // optional
  "avatar_url": "https://..." // optional
}
```

**Response `200`:** Объект `UserResponse`.

**Errors:** `401` — невалидный токен. `422` — невалидные данные.

---

### POST /refresh

Обновление пары токенов. Refresh token rotation — старый токен инвалидируется.

**Request:**
```json
{
  "refresh_token": "urlsafe-base64-token..."
}
```

**Response `200`:**
```json
{
  "access_token": "new-access-token...",
  "refresh_token": "new-refresh-token...",
  "token_type": "bearer"
}
```

**Errors:** `401` — невалидный, просроченный или повторно использованный refresh token. Token reuse detection: если revoked token используется повторно, вся token family отзывается.

---

### POST /logout

Отзыв refresh token family (выход с устройства).

**Request:**
```json
{
  "refresh_token": "urlsafe-base64-token..."
}
```

**Response `204`:** No content.

---

### POST /verify-email

Подтверждение email по токену из ссылки. Публичный endpoint.

**Request:**
```json
{
  "token": "raw-verification-token"
}
```

**Response `200`:** Объект `UserResponse`.

**Errors:** `400` — невалидный, просроченный или уже использованный токен.

---

### POST /forgot-password

Запрос сброса пароля. Всегда возвращает 204 (не раскрывает существование email). Rate limit: 3/hour per user.

**Request:**
```json
{
  "email": "user@example.com"
}
```

**Response `204`:** No content (всегда).

---

### POST /reset-password

Установка нового пароля по токену сброса.

**Request:**
```json
{
  "token": "raw-reset-token",
  "new_password": "newsecret123"
}
```

**Response `204`:** No content.

**Errors:** `400` — невалидный, просроченный или уже использованный токен.

---

### PATCH /admin/users/{user_id}/verify

Верифицировать преподавателя. Только для `role=admin`.

**Headers:** `Authorization: Bearer <token>`

**Response `200`:**
```json
{
  "id": "...",
  "email": "teacher@example.com",
  "name": "Ivan Petrov",
  "role": "teacher",
  "is_verified": true,
  "created_at": "2026-02-20T12:00:00+00:00"
}
```

**Errors:** `401` — невалидный токен. `403` — не admin. `404` — пользователь не найден. `409` — не teacher или уже верифицирован.

---

### GET /referral/me

Статистика реферальной программы текущего пользователя. Требует JWT.

**Headers:** `Authorization: Bearer <token>`

**Response `200`:**
```json
{
  "referral_code": "REF-A1B2C3D4",
  "total_referrals": 5,
  "completed_referrals": 3,
  "pending_referrals": 2
}
```

---

### POST /referral/apply

Применение реферального кода. Привязывает текущего пользователя как реферала. Требует JWT.

**Request:**
```json
{
  "referral_code": "REF-A1B2C3D4"
}
```

**Response `201`:** Объект реферала с `id`, `referrer_id`, `referee_id`, `status: "pending"`.

**Errors:** `404` — код не найден. `409` — уже применил код / нельзя реферить себя.

---

### POST /referral/complete

Завершение реферала (admin/внутренний триггер). Обновляет статус на `completed`.

**Request:**
```json
{
  "referee_id": "uuid"
}
```

**Response `200`:** Объект реферала с `status: "completed"`.

**Errors:** `404` — реферал не найден.

---

### GET /users/{user_id}/profile

Публичный профиль пользователя. Не требует авторизации. Возвращает 404 если профиль приватный.

**Response `200`:**
```json
{
  "id": "uuid",
  "name": "Ivan Petrov",
  "bio": "About me...",
  "avatar_url": "https://...",
  "role": "teacher",
  "is_verified": true,
  "created_at": "2026-01-01T00:00:00Z",
  "is_public": true
}
```

**Errors:** `404` — пользователь не найден или профиль приватный.

---

### GET /users/{user_id}/stats

Публичная статистика пользователя (только данные Identity сервиса).

**Response `200`:**
```json
{
  "name": "Ivan Petrov",
  "role": "teacher",
  "is_verified": true,
  "member_since": "2026-01-01T00:00:00Z"
}
```

**Errors:** `404` — пользователь не найден или профиль приватный.

---

### PATCH /users/me/visibility

Переключение видимости профиля. Требует JWT.

**Request:**
```json
{
  "is_public": false
}
```

**Response `204`:** No Content.

---

### POST /follow/{user_id}

Подписаться на пользователя. Требует JWT.

**Response `201`:**
```json
{
  "id": "uuid",
  "follower_id": "uuid",
  "following_id": "uuid",
  "created_at": "2026-03-04T12:00:00Z"
}
```

**Errors:** `400` — подписка на себя. `404` — пользователь не найден. `409` — уже подписан.

---

### DELETE /follow/{user_id}

Отписаться от пользователя. Требует JWT.

**Response `204`:** No Content.

**Errors:** `404` — не подписан.

---

### GET /followers/me

Список подписчиков текущего пользователя. Требует JWT.

**Query params:** `limit` (default 20, max 100), `offset` (default 0).

**Response `200`:**
```json
{
  "items": [{"id": "uuid", "name": "...", "avatar_url": "..."}],
  "total": 10
}
```

---

### GET /following/me

Список подписок текущего пользователя. Требует JWT.

**Query params:** `limit` (default 20, max 100), `offset` (default 0).

**Response `200`:** Аналогично `/followers/me`.

---

### GET /users/{user_id}/followers/count

Количество подписчиков пользователя. Публичный.

**Response `200`:**
```json
{
  "user_id": "uuid",
  "followers_count": 42,
  "following_count": 15
}
```

---

### POST /organizations (NEW)

Создание организации. Требует JWT. Создатель автоматически становится `owner`.

**Headers:** `Authorization: Bearer <token>`

**Request:**
```json
{
  "name": "Acme Corp",
  "slug": "acme-corp",
  "domain": "acme.com"
}
```

**Response `201`:**
```json
{
  "id": "uuid",
  "name": "Acme Corp",
  "slug": "acme-corp",
  "domain": "acme.com",
  "owner_id": "uuid",
  "created_at": "2026-03-05T00:00:00Z"
}
```

**Errors:** `409` — slug или domain уже заняты. `422` — невалидные данные.

---

### GET /organizations/me (NEW)

Список организаций текущего пользователя. Требует JWT.

**Response `200`:**
```json
{
  "items": [
    {
      "id": "uuid",
      "name": "Acme Corp",
      "slug": "acme-corp",
      "role": "owner",
      "joined_at": "2026-03-05T00:00:00Z"
    }
  ]
}
```

---

### GET /organizations/{org_id} (NEW)

Информация об организации. Требует JWT + membership в организации.

**Response `200`:**
```json
{
  "id": "uuid",
  "name": "Acme Corp",
  "slug": "acme-corp",
  "domain": "acme.com",
  "owner_id": "uuid",
  "member_count": 25,
  "created_at": "2026-03-05T00:00:00Z"
}
```

**Errors:** `403` — не член организации. `404` — организация не найдена.

---

### POST /organizations/{org_id}/members (NEW)

Добавление участника в организацию. Требует JWT + role `owner` или `admin` в организации.

**Request:**
```json
{
  "user_id": "uuid",
  "role": "member"    // "member" | "admin" | "owner"
}
```

**Response `201`:**
```json
{
  "id": "uuid",
  "organization_id": "uuid",
  "user_id": "uuid",
  "role": "member",
  "joined_at": "2026-03-05T00:00:00Z"
}
```

**Errors:** `403` — нет прав. `404` — организация или пользователь не найдены. `409` — уже член.

---

### DELETE /organizations/{org_id}/members/{user_id} (NEW)

Удаление участника из организации. Требует JWT + role `owner` или `admin`.

**Response `204`:** No Content.

**Errors:** `403` — нет прав. `404` — не найден.

---

### GET /organizations/{org_id}/members (NEW)

Список участников организации. Требует JWT + membership.

**Query params:** `limit` (default 50), `offset` (default 0).

**Response `200`:**
```json
{
  "items": [
    {
      "id": "uuid",
      "user_id": "uuid",
      "name": "Ivan Petrov",
      "email": "ivan@acme.com",
      "role": "member",
      "joined_at": "2026-03-05T00:00:00Z"
    }
  ],
  "total": 25
}
```

---

## AI Service (`:8006`)

### GET /ai/credits/me

Баланс кредитов текущего пользователя. Требует JWT.

**Response `200`:**
```json
{
  "user_id": "uuid",
  "tier": "student",
  "daily_limit": 100,
  "used_today": 15,
  "remaining": 85
}
```

---

### POST /ai/quiz/generate

Генерация квиза из содержания урока. Требует JWT.

**Request:**
```json
{
  "lesson_content": "Text of the lesson...",
  "num_questions": 5
}
```

**Response `200`:** Список вопросов с вариантами ответов.

---

### POST /ai/summary/generate

Генерация краткого содержания. Требует JWT.

**Request:**
```json
{
  "content": "Long text to summarize..."
}
```

**Response `200`:** Сжатое summary текста.

---

### POST /ai/tutor/chat

Socratic AI-тьютор (чат по уроку). Требует JWT.

**Request:**
```json
{
  "lesson_id": "uuid",
  "message": "I don't understand recursion..."
}
```

**Response `200`:** Ответ тьютора (Socratic method).

---

### POST /ai/tutor/feedback

Оценка ответа тьютора (thumbs up/down). Требует JWT.

**Request:**
```json
{
  "message_id": "uuid",
  "rating": "up"    // "up" | "down"
}
```

**Response `200`:** `{"status": "recorded"}`.

---

### POST /ai/course/outline

Генерация outline курса. Только teacher/admin.

**Request:**
```json
{
  "topic": "Introduction to Rust",
  "target_audience": "junior developers",
  "num_modules": 5
}
```

**Response `200`:** Структурированный outline с модулями и уроками.

---

### POST /ai/lesson/generate

Генерация контента урока. Только teacher/admin.

**Request:**
```json
{
  "title": "Ownership and Borrowing",
  "outline": "Key concepts...",
  "level": "beginner"
}
```

**Response `200`:** Сгенерированный контент урока.

---

### POST /ai/study-plan

Персонализированный недельный план обучения. Требует JWT. Вызывает Learning Service для получения concept mastery.

**Request:**
```json
{
  "course_id": "uuid",
  "hours_per_week": 5
}
```

**Response `200`:** Недельный план с ежедневными задачами.

---

### POST /ai/moderate

Модерация контента (advisory). Только teacher/admin.

**Request:**
```json
{
  "content": "Text to moderate..."
}
```

**Response `200`:** Результат модерации (safe/flagged + причины).

---

### POST /ai/strategist/plan-path (NEW)

Планирование пути обучения для пользователя в организации. Требует JWT + org membership.

**Request:**
```json
{
  "organization_id": "uuid",
  "user_id": "uuid",
  "template_id": "uuid"    // optional, onboarding template
}
```

**Response `200`:**
```json
{
  "learning_path": [
    {"concept_id": "uuid", "concept_name": "Git Basics", "estimated_days": 2, "priority": 1},
    {"concept_id": "uuid", "concept_name": "CI/CD Pipeline", "estimated_days": 3, "priority": 2}
  ],
  "total_estimated_days": 30,
  "current_trust_level": 1,
  "target_trust_level": 3
}
```

---

### POST /ai/strategist/next-concept (NEW)

Выбор следующего концепта для изучения. Требует JWT.

**Request:**
```json
{
  "organization_id": "uuid"
}
```

**Response `200`:**
```json
{
  "concept_id": "uuid",
  "concept_name": "Docker Networking",
  "reason": "Prerequisite for Kubernetes deployment, which is next in your path",
  "estimated_minutes": 15,
  "difficulty": "intermediate"
}
```

---

### POST /ai/strategist/adapt (NEW)

Адаптация пути обучения на основе прогресса. Требует JWT.

**Request:**
```json
{
  "organization_id": "uuid",
  "feedback": "too_easy"    // "too_easy" | "too_hard" | "stuck" | "auto"
}
```

**Response `200`:**
```json
{
  "adjustments": [
    {"action": "skip", "concept_id": "uuid", "reason": "Already mastered"},
    {"action": "add", "concept_id": "uuid", "reason": "Fills knowledge gap"}
  ],
  "new_pace": "accelerated"
}
```

---

### POST /ai/designer/mission (NEW)

Генерация 15-минутной миссии для концепта. Требует JWT.

**Request:**
```json
{
  "concept_id": "uuid",
  "organization_id": "uuid",
  "difficulty": "intermediate",
  "mission_type": "code_review"    // "code_review" | "debugging" | "implementation" | "quiz"
}
```

**Response `200`:**
```json
{
  "mission": {
    "title": "Review Authentication Middleware",
    "description": "...",
    "estimated_minutes": 15,
    "steps": [
      {"order": 1, "type": "read", "content": "..."},
      {"order": 2, "type": "question", "content": "..."},
      {"order": 3, "type": "code", "content": "..."}
    ],
    "context_snippets": [
      {"source": "auth/middleware.py", "content": "..."}
    ]
  }
}
```

---

### POST /ai/designer/recap (NEW)

Генерация recap/summary после завершения миссии. Требует JWT.

**Request:**
```json
{
  "mission_id": "uuid",
  "user_answers": [...]
}
```

**Response `200`:**
```json
{
  "recap": "...",
  "key_takeaways": ["...", "..."],
  "mastery_delta": 0.15,
  "next_suggestion": "Try a debugging mission on the same topic"
}
```

---

### POST /ai/coach/start

Начало structured 15-min coaching session. Требует JWT. Consumes 1 credit.

**Request:**
```json
{
  "mission_id": "uuid",
  "personality": "friendly"  // optional, default "friendly"
}
```

**Response `200`:**
```json
{
  "session_id": "uuid-string",
  "content": "Welcome! Let's start with a quick recap. What is a closure?",
  "phase": "recap",
  "phase_progress": 1
}
```

---

### POST /ai/coach/chat

Сообщение в активной Coach session. Требует JWT. Consumes 1 credit.

**Request:**
```json
{
  "session_id": "uuid-string",
  "message": "A closure captures variables from the enclosing scope"
}
```

**Response `200`:**
```json
{
  "session_id": "uuid-string",
  "content": "Good thinking! Can you give an example?",
  "phase": "recap",
  "phase_progress": 1
}
```

Phases: `recap` → `read` → `check` → `practice` → `wrap-up`

---

### POST /ai/coach/end

Завершение Coach session с оценкой. Требует JWT.

**Request:**
```json
{
  "session_id": "uuid-string"
}
```

**Response `200`:**
```json
{
  "session_id": "uuid-string",
  "score": 78.0,
  "mastery_delta": 0.15,
  "duration_seconds": 600,
  "strengths": ["Good understanding of closures"],
  "gaps": ["Needs practice with async decorators"]
}
```

---

### GET /ai/mission/daily

Получение ежедневной миссии. Orchestrator координирует Strategist → Designer pipeline. Кэшируется на день. Требует JWT. Потребляет 1 AI credit.

**Query params:** `org_id` (UUID, required).

**Response `200`:**
```json
{
  "concept_name": "Python Decorators",
  "concept_id": "uuid",
  "recap_questions": [{"question": "...", "expected_answer": "...", "concept_ref": "closures"}],
  "reading_content": "Decorators are functions...",
  "check_questions": [{"question": "...", "options": ["A","B","C","D"], "correct_index": 1, "explanation": "..."}],
  "code_case": {"code_snippet": "...", "language": "python", "question": "...", "expected_answer": "...", "source_path": "..."} | null
}
```

**Response `403`:** AI credit limit reached.
**Response `404`:** No concept available (all mastered).

---

### POST /ai/mission/complete

Завершение сессии и адаптация learning path. Вызывает Coach.end_session → Orchestrator.complete_session (adapt path + update mastery). Требует JWT.

**Request:**
```json
{
  "session_id": "string",
  "concept_id": "uuid",
  "org_id": "uuid"
}
```

**Response `200`:**
```json
{
  "next_concept_preview": "Async Python" | null,
  "total_completed": 5,
  "score": 85.0,
  "mastery_delta": 0.2
}
```

---

### POST /ai/memory/{user_id} (NEW)

Обновление agent memory для пользователя. Требует JWT (admin или internal).

**Request:**
```json
{
  "learning_style": "visual",
  "preferred_difficulty": "intermediate",
  "strengths": ["backend", "sql"]
}
```

**Response `200`:** Обновлённый объект memory.

---

### GET /ai/config/llm/{org_id} (NEW)

Получение текущей LLM-конфигурации для организации. Только admin.

**Response `200`:**
```json
{
  "internal_provider": "gemini",
  "internal_model_url": null,
  "external_provider": "gemini",
  "embedding_provider": "gemini",
  "data_isolation": "standard"
}
```

---

### PUT /ai/config/llm/{org_id} (NEW)

Обновление LLM-конфигурации. Только admin. Validation: strict isolation требует self_hosted; self_hosted требует internal_model_url.

**Request:**
```json
{
  "internal_provider": "self_hosted",
  "internal_model_url": "http://vllm:8000/v1",
  "data_isolation": "strict"
}
```

**Response `200`:** Обновлённая конфигурация.
**Response `400`:** Невалидная конфигурация (strict + gemini, self_hosted без URL).

---

### POST /ai/config/llm/{org_id}/test (NEW)

Тест подключения к LLM-провайдеру. Только admin. Отправляет "ping" и возвращает результат.

**Request:**
```json
{
  "internal_provider": "self_hosted",
  "internal_model_url": "http://vllm:8000/v1"
}
```

**Response `200`:**
```json
{
  "success": true,
  "response_preview": "pong",
  "tokens_in": 5,
  "tokens_out": 2
}
```

---

## Learning Engine (`:8007`)

### Quizzes (4 endpoints)

#### POST /quizzes
Создание квиза для урока. Teacher-only (role=teacher + is_verified).

#### GET /quizzes/lesson/{lesson_id}
Получение квиза для урока. Authenticated.

#### POST /quizzes/{quiz_id}/submit
Сдача квиза. Student-only. Автоматически обновляет concept mastery (score × 0.3).

#### GET /quizzes/{quiz_id}/attempts/me
Мои попытки квиза. Student-only.

---

### Flashcards + FSRS (4 endpoints)

#### POST /flashcards
Создание карточки. Student-only.

#### GET /flashcards/due
Карточки к повторению (FSRS algorithm). Student-only.

#### POST /flashcards/{id}/review
Повторение карточки с рейтингом. Student-only.

#### DELETE /flashcards/{id}
Удаление карточки. Student-only (owner).

---

### Concepts / Knowledge Graph (7 endpoints)

#### GET /concepts/course/{course_id}
Граф концептов курса. Authenticated.

#### GET /concepts/course/{course_id}/mastery
Мастерство по концептам курса. Authenticated.

#### POST /concepts
Создание концепта. Teacher-only.

#### PUT /concepts/{id}
Обновление концепта. Teacher-only.

#### DELETE /concepts/{id}
Удаление концепта. Teacher-only.

#### POST /concepts/{id}/prerequisites
Добавление prerequisite связи. Teacher-only.

#### DELETE /concepts/{id}/prerequisites/{prereq_id}
Удаление prerequisite связи. Teacher-only.

---

### Streaks (2 endpoints)

#### GET /streaks/me
Текущий streak пользователя. Authenticated.

#### POST /streaks/checkin
Отметка ежедневной активности. Authenticated.

---

### Leaderboard (5 endpoints)

#### GET /leaderboard
Общий рейтинг. Authenticated.

#### GET /leaderboard/course/{course_id}
Рейтинг по курсу. Authenticated.

#### GET /leaderboard/weekly
Еженедельный рейтинг. Authenticated.

#### GET /leaderboard/me
Позиция текущего пользователя. Authenticated.

#### GET /leaderboard/friends
Рейтинг среди подписок. Authenticated.

---

### Discussions (8 endpoints)

#### POST /discussions
Создание комментария. Authenticated.

#### GET /discussions/lesson/{lesson_id}
Threaded список обсуждений урока. Authenticated. Сортировка: pinned → teacher_answer → date.

#### PATCH /discussions/{id}
Обновление комментария. Owner only.

#### DELETE /discussions/{id}
Удаление комментария. Owner or admin.

#### POST /discussions/{id}/upvote
Голосование за комментарий. Authenticated.

#### POST /discussions/{id}/reply
Ответ на комментарий (max 2 уровня вложенности). Authenticated.

#### PATCH /discussions/{id}/pin
Закрепление/открепление комментария. Teacher-only.

#### PATCH /discussions/{id}/mark-answer
Отметить как ответ преподавателя. Teacher-only.

---

### XP (1 endpoint)

#### GET /xp/me
XP текущего пользователя. Authenticated.

**Response `200`:**
```json
{
  "user_id": "uuid",
  "total_xp": 1500,
  "level": 7,
  "xp_to_next_level": 200
}
```

XP rewards: lesson_complete=10, quiz_submit=20, flashcard_review=5.

---

### Badges (1 endpoint)

#### GET /badges/me
Значки текущего пользователя. Authenticated.

Badge types: `first_enrollment`, `streak_7`, `quiz_ace`, `mastery_100`.

---

### Adaptive Pre-tests (3 endpoints)

#### POST /pretests/start
Начало adaptive pre-test. Student-only.

#### POST /pretests/answer
Ответ на вопрос pre-test. Student-only.

#### GET /pretests/results
Результаты pre-test. Student-only.

Concept-order-based difficulty, min 5 questions, mastery thresholds: 0.7 correct / 0.1 wrong.

---

### Velocity (1 endpoint)

#### GET /velocity/me
Скорость обучения текущего пользователя. Authenticated.

---

### Activity Feed (2 endpoints)

#### GET /activity/me
Персональная лента активности. Authenticated.

#### GET /activity/feed
Общая лента активности (друзья). Authenticated.

Activity types: `quiz_completed`, `flashcard_reviewed`, `badge_earned`, `streak_milestone`, `concept_mastered`.

---

### Study Groups (6 endpoints)

#### POST /study-groups
Создание учебной группы. Authenticated.

#### GET /study-groups/course/{course_id}
Группы по курсу. Authenticated.

#### POST /study-groups/{id}/join
Вступление в группу. Authenticated.

#### DELETE /study-groups/{id}/leave
Выход из группы. Authenticated.

#### GET /study-groups/{id}/members
Участники группы. Authenticated.

#### GET /study-groups/me
Мои группы. Authenticated.

---

### Certificates (3 endpoints)

#### POST /certificates/generate
Генерация сертификата при завершении курса. Student-only.

#### GET /certificates/me
Мои сертификаты. Authenticated.

#### GET /certificates/{id}
Получение сертификата. Public (для проверки).

---

### Missions (5 endpoints)

#### GET /missions/today
Сегодняшняя миссия пользователя (get-or-create). Вызывает AI Service для генерации blueprint если миссии на сегодня нет. Authenticated.

**Query params:** `org_id` (required, UUID).

**Response `200`:**
```json
{
  "id": "uuid",
  "user_id": "uuid",
  "organization_id": "uuid",
  "concept_id": "uuid | null",
  "mission_type": "daily",
  "status": "pending",
  "blueprint": {"topic": "...", "questions": [...]},
  "score": null,
  "mastery_delta": null,
  "started_at": null,
  "completed_at": null,
  "created_at": "2026-03-05T08:00:00Z"
}
```

---

#### POST /missions/{id}/start
Начало выполнения миссии. Меняет статус на `in_progress`, устанавливает `started_at`. Authenticated (owner only).

**Response `200`:** Same as GET /missions/today with `status: "in_progress"`.

**Errors:** `404` — not found, `403` — not owner, `400` — already started.

---

#### POST /missions/{id}/complete
Завершение миссии. Вызывает AI Coach для оценки session. Обновляет trust level. Authenticated (owner only).

**Request:**
```json
{
  "session_id": "coach-session-uuid"
}
```

**Response `200`:**
```json
{
  "id": "uuid",
  "status": "completed",
  "score": 0.85,
  "mastery_delta": 0.1,
  "completed_at": "2026-03-05T09:12:00Z"
}
```

**Errors:** `404` — not found, `403` — not owner, `400` — not in_progress, `502` — AI service error.

---

#### GET /missions/me
История миссий пользователя. Authenticated.

**Query params:** `limit` (default 20, max 100), `offset` (default 0).

**Response `200`:**
```json
{
  "missions": [...]
}
```

---

#### GET /missions/streak
Streak миссий пользователя. Authenticated.

**Response `200`:**
```json
{
  "current_streak": 7
}
```

---

### Trust Levels (2 endpoints)

#### GET /trust-level/me
Trust level текущего пользователя. Authenticated.

**Query params:** `org_id` (required, UUID).

**Response `200`:**
```json
{
  "id": "uuid",
  "user_id": "uuid",
  "organization_id": "uuid",
  "level": 2,
  "level_name": "Contributor",
  "total_missions_completed": 20,
  "total_concepts_mastered": 10,
  "unlocked_areas": [],
  "level_up_at": "2026-03-05T12:00:00Z",
  "next_level": {
    "level": 3,
    "level_name": "Builder",
    "missions_required": 30,
    "concepts_required": 15,
    "missions_remaining": 10,
    "concepts_remaining": 5
  }
}
```

При level=5 (Architect), `next_level` = `null`.

---

#### GET /trust-level/org/{org_id}
Trust levels всех участников организации. Admin-only (role=admin).

**Query params:** `limit` (default 50, max 200), `offset` (default 0).

**Response `200`:**
```json
{
  "levels": [
    {
      "id": "uuid",
      "user_id": "uuid",
      "organization_id": "uuid",
      "level": 3,
      "level_name": "Builder",
      "total_missions_completed": 35,
      "total_concepts_mastered": 18,
      "unlocked_areas": [],
      "level_up_at": "2026-03-05T12:00:00Z",
      "next_level": { "..." }
    }
  ]
}
```

**Response `403`:** Non-admin role.

---

### Daily Summary (1 endpoint)

#### GET /daily/me
Unified daily session summary. Authenticated.

**Query params:** `org_id` (required, UUID).

**Response `200`:**
```json
{
  "mission": {
    "id": "uuid",
    "status": "pending",
    "concept_name": "Authentication Middleware"
  },
  "trust_level": 2,
  "due_flashcards": 5,
  "streak_days": 7,
  "greeting": "Good morning! You have a 7-day streak."
}
```

`mission` может быть `null` если миссия ещё не создана на сегодня.

---

## RAG Service (`:8008`)

### Health

#### GET /health/live
Liveness probe. Всегда `{"status": "ok"}`.

#### GET /health/ready
Readiness probe. Проверяет PostgreSQL (pgvector) pool.

---

### Document Ingestion (3 endpoints)

#### POST /documents
Загрузка документа: chunking + embedding + сохранение в pgvector. Требует JWT (admin или teacher).

**Request:**
```json
{
  "org_id": "uuid",
  "source_type": "text",
  "source_path": "/docs/guide.md",
  "title": "Authentication Guide",
  "content": "Markdown content..."
}
```

`source_type`: `text`, `markdown`, `github`, `code`. Для `github`/`code` используется code chunker (split по def/class), для остальных — text chunker (split по параграфам/предложениям).

**Response `201`:**
```json
{
  "id": "uuid",
  "organization_id": "uuid",
  "source_type": "text",
  "source_path": "/docs/guide.md",
  "title": "Authentication Guide",
  "metadata": {},
  "created_at": "2026-03-05T00:00:00Z"
}
```

---

#### GET /documents
Список документов организации. Требует JWT.

**Query params:** `org_id` (required), `limit` (default 20, max 100), `offset` (default 0).

---

#### DELETE /documents/{id}
Удаление документа и его chunks (CASCADE). Требует JWT (admin only).

**Response `204`:** No Content.

---

### Search (1 endpoint)

#### POST /search
Семантический поиск по документам организации через pgvector cosine similarity. Требует JWT.

**Request:**
```json
{
  "query": "How does authentication work?",
  "org_id": "uuid",
  "limit": 5
}
```

`query` (required, min 1 char), `org_id` (required), `limit` (1–20, default 5).

**Response `200`:**
```json
{
  "query": "How does authentication work?",
  "results": [
    {
      "chunk_id": "uuid",
      "content": "...",
      "similarity": 0.92,
      "document_title": "Auth Guide",
      "source_type": "text",
      "source_path": "/docs/auth.md",
      "metadata": {}
    }
  ]
}
```

---

### Concepts (2 endpoints)

#### GET /concepts
Список концептов организации. Требует JWT (любая роль).

**Query params:** `org_id` (UUID, required).

**Response `200`:**
```json
[
  {
    "id": "uuid",
    "organization_id": "uuid",
    "name": "Dependency Injection",
    "description": "A design pattern for decoupling components",
    "source_document_id": "uuid",
    "created_at": "2026-03-05T00:00:00Z"
  }
]
```

---

#### POST /concepts/extract/{document_id}
Ручной запуск извлечения концептов из документа через LLM (Gemini Flash). Требует JWT + admin/teacher. Также вызывается автоматически при ingestion pipeline.

**Request body:**
```json
{
  "org_id": "uuid"
}
```

**Response `202`:**
```json
{
  "status": "accepted",
  "document_id": "uuid"
}
```

---

### Sources (1 endpoint)

#### POST /sources/github
Подключение GitHub репозитория как источника документов. Требует JWT + org admin.

**Request:**
```json
{
  "organization_id": "uuid",
  "repo_url": "https://github.com/acme/backend",
  "branch": "main",
  "file_patterns": ["*.md", "*.py", "*.rs"],
  "exclude_patterns": ["node_modules/**", ".git/**"]
}
```

**Response `202`:**
```json
{
  "job_id": "uuid",
  "status": "processing",
  "estimated_documents": 150
}
```

---

### Upload (2 endpoints)

#### POST /upload/markdown
Загрузка markdown файла. Требует JWT + org membership.

**Request:** multipart/form-data с файлом и `organization_id`.

**Response `201`:** Объект документа.

---

#### POST /upload/bulk
Массовая загрузка документов. Требует JWT + org admin.

**Request:** multipart/form-data с zip-архивом и `organization_id`.

**Response `202`:**
```json
{
  "job_id": "uuid",
  "status": "processing",
  "files_count": 25
}
```

---

### Knowledge Base Management (5 endpoints)

#### GET /kb/{org_id}/stats
Статистика knowledge base организации. Требует JWT (любая роль).

**Response `200`:**
```json
{
  "total_documents": 150,
  "total_chunks": 3200,
  "total_concepts": 85,
  "last_updated": "2026-03-05T00:00:00Z"
}
```

`last_updated` — `null` если документов нет.

---

#### GET /kb/{org_id}/sources
Список документов-источников knowledge base. Требует JWT (любая роль). Возвращает до 100 документов.

**Response `200`:**
```json
[
  {
    "id": "uuid",
    "organization_id": "uuid",
    "source_type": "text",
    "source_path": "/docs/guide.md",
    "title": "Authentication Guide",
    "metadata": {},
    "created_at": "2026-03-05T00:00:00Z"
  }
]
```

---

#### GET /kb/{org_id}/concepts
Граф концептов knowledge base (nodes + edges). Требует JWT (любая роль).

**Response `200`:**
```json
{
  "nodes": [
    {"id": "uuid", "name": "Dependency Injection", "description": "A design pattern"}
  ],
  "edges": [
    {"source": "uuid", "target": "uuid", "type": "related"}
  ]
}
```

---

#### POST /kb/{org_id}/search
Семантический поиск в knowledge base. Требует JWT (любая роль).

**Request:**
```json
{
  "query": "How does auth work?",
  "limit": 5
}
```

`query` (required, min 1 char), `limit` (1–20, default 5).

**Response `200`:**
```json
[
  {
    "chunk_id": "uuid",
    "content": "...",
    "similarity": 0.92,
    "document_title": "Auth Guide",
    "source_type": "text",
    "source_path": "/docs/auth.md",
    "metadata": {}
  }
]
```

---

#### POST /kb/{org_id}/refresh/{document_id}
Переиндексация документа (удаление chunks, перечанкинг, переэмбеддинг). Требует JWT + admin.

**Response `200`:**
```json
{
  "id": "uuid",
  "organization_id": "uuid",
  "source_type": "text",
  "source_path": "/docs/guide.md",
  "title": "Authentication Guide",
  "metadata": {},
  "created_at": "2026-03-05T00:00:00Z"
}
```

**`404`:** Document not found.

---

### Onboarding Templates (6 endpoints)

#### POST /templates
Создание шаблона онбординга. Требует JWT + org admin.

**Request:**
```json
{
  "organization_id": "uuid",
  "name": "Backend Engineer Onboarding",
  "description": "30-day onboarding for backend engineers",
  "target_role": "backend_engineer",
  "estimated_days": 30
}
```

**Response `201`:** Объект шаблона.

---

#### GET /templates
Список шаблонов организации. Требует JWT + org membership.

**Query params:** `organization_id` (required).

---

#### GET /templates/{id}
Шаблон с stages. Требует JWT + org membership.

---

#### POST /templates/{id}/stages
Добавление этапа в шаблон. Требует JWT + org admin.

**Request:**
```json
{
  "title": "Week 1: Development Environment",
  "description": "Setup and understand the dev environment",
  "order": 1,
  "estimated_days": 5,
  "concept_ids": ["uuid", "uuid"]
}
```

**Response `201`:** Объект stage.

---

#### PUT /templates/{id}/stages/{stage_id}
Обновление этапа. Требует JWT + org admin.

---

#### DELETE /templates/{id}/stages/{stage_id}
Удаление этапа. Требует JWT + org admin.

**Response `204`:** No Content.

---

## Notification Service (`:8005`)

### POST /notifications

Создание уведомления (internal/admin). Логирует в stdout (email stub).

**Request:**
```json
{
  "user_id": "uuid",
  "type": "mission_reminder",
  "title": "Daily Mission Available",
  "message": "Your daily mission is ready!"
}
```

**Response `201`:** Объект уведомления.

---

### GET /notifications/me

Уведомления текущего пользователя. Требует JWT.

**Query params:** `limit` (default 20), `offset` (default 0), `unread_only` (default false).

---

### PATCH /notifications/{id}/read

Отметить уведомление как прочитанное. Требует JWT (owner only).

**Response `200`:** Обновлённый объект уведомления.

---

### POST /streak-reminders/send

Массовая отправка streak reminders. Admin-only. Дедупликация по дню.

---

### POST /flashcard-reminders/send

Массовая отправка flashcard reminders. Admin-only. Дедупликация по дню.

---

### POST /flashcard-reminders/smart

FSRS-based smart reminders через Learning Service. Admin-only.

---

### POST /messages

Отправка прямого сообщения. Требует JWT. Лимит: 1–2000 символов.

**Request:**
```json
{
  "recipient_id": "uuid",
  "content": "Hello!"
}
```

**Response `201`:** Объект сообщения.

---

### GET /conversations/me

Список диалогов текущего пользователя. Требует JWT.

---

### GET /conversations/{id}/messages

Сообщения диалога. Требует JWT (participant only).

**Query params:** `limit` (default 50), `offset` (default 0).

---

### PATCH /messages/{id}/read

Отметить сообщение как прочитанное. Требует JWT (recipient only).

---

## Payment Service (`:8004`)

### POST /payments

Создание платежа (mock, всегда completed). Optional `coupon_code`. Student-only.

**Request:**
```json
{
  "course_id": "uuid",
  "amount": 29.99,
  "coupon_code": "SAVE20"    // optional
}
```

---

### GET /payments/{id}

Информация о платеже. Authenticated (owner or admin).

---

### GET /payments/me

Мои платежи. Authenticated.

**Query params:** `limit` (default 20), `offset` (default 0).

---

### GET /payments/{id}/invoice

Скачивание PDF invoice. Authenticated (owner or admin).

---

### POST /coupons

Создание купона. Teacher/admin.

**Request:**
```json
{
  "code": "SAVE20",
  "discount_percent": 20,
  "max_uses": 100,
  "expires_at": "2026-12-31T23:59:59Z"
}
```

---

### GET /coupons

Список купонов. Teacher/admin.

---

### POST /coupons/validate

Валидация купона. Authenticated.

---

### PATCH /coupons/{id}/deactivate

Деактивация купона. Teacher/admin (owner).

---

### POST /refunds

Запрос возврата. Authenticated (owner). 14-дневное окно, один на платёж.

---

### GET /refunds/me

Мои возвраты. Authenticated.

---

### GET /refunds

Все возвраты. Admin-only.

---

### PATCH /refunds/{id}/approve

Одобрение возврата. Admin-only. Payment status → `refunded`.

---

### PATCH /refunds/{id}/reject

Отклонение возврата. Admin-only.

---

### POST /gifts

Покупка подарка (курс). Authenticated.

**Request:**
```json
{
  "course_id": "uuid",
  "recipient_email": "friend@example.com",
  "message": "Happy learning!"
}
```

---

### GET /gifts/me/sent

Мои отправленные подарки. Authenticated.

---

### POST /gifts/redeem

Активация подарка по коду. Authenticated.

---

### GET /gifts/{gift_code}/info

Публичная информация о подарке (limited fields).

---

### GET /earnings/me/summary

Сводка доходов преподавателя. Teacher-only.

---

### GET /earnings/me

Детализация доходов. Teacher-only.

---

### POST /earnings/payouts

Запрос выплаты. Teacher-only.

---

### GET /earnings/payouts

Мои выплаты. Teacher-only.

---

### POST /org-subscriptions

Создание подписки организации. Требует JWT с `organization_id` claim.

**Request:**
```json
{
  "plan_tier": "pilot",           // "pilot" ($1000/mo, 20 seats) | "enterprise" ($10000/mo, 999 seats)
  "payment_method_id": "pm_xxx",
  "org_email": "org@example.com",
  "org_name": "Test Org"
}
```

**Response `201`:**
```json
{
  "id": "uuid",
  "organization_id": "uuid",
  "plan_tier": "pilot",
  "max_seats": 20,
  "current_seats": 0,
  "price_cents": 100000,
  "status": "active",
  "trial_ends_at": null,
  "current_period_start": "2026-03-06T00:00:00Z",
  "current_period_end": "2026-04-06T00:00:00Z",
  "created_at": "2026-03-06T00:00:00Z"
}
```

**Errors:** `409` (org already has subscription), `422` (invalid plan tier), `403` (no organization in JWT).

---

### GET /org-subscriptions/{org_id}

Информация о подписке организации. Требует JWT + organization_id match.

**Response `200`:** Same schema as POST response.

**Errors:** `403` (wrong org), `404` (no subscription found).

---

### POST /org-subscriptions/{org_id}/cancel

Отмена подписки организации. Требует JWT + organization_id match. Отменяет в Stripe немедленно.

**Response `200`:**
```json
{
  "id": "uuid",
  "organization_id": "uuid",
  "plan_tier": "pilot",
  "status": "canceled",
  ...
}
```

**Errors:** `403` (wrong org), `404` (not found), `400` (already canceled).

---

### POST /webhooks/stripe-org

Webhook для Stripe events связанных с org subscriptions. Публичный (verification via Stripe signature).

Handled events: `invoice.paid` (→ active), `invoice.payment_failed` (→ past_due), `customer.subscription.deleted` (→ canceled). Unknown subscriptions silently ignored (idempotent).

---

## Search Service (`:8010`) — Rust/Axum + tantivy

Full-text search service. Org-scoped document indexing with BM25 scoring. Called by RAG service and API Gateway.

### GET /health/live

**Response `200`:** `{"status": "ok"}`

### POST /index

Index a single document.

**Request Body:**
```json
{
  "id": "doc-uuid",
  "org_id": "org-uuid",
  "title": "Document title",
  "body": "Full text content for indexing",
  "source_type": "document",
  "source_path": "/docs/example.md"
}
```

**Response `201`:** `{"status": "indexed"}`

**Errors:** `500` (index error)

### POST /index/batch

Index multiple documents in a single request.

**Request Body:**
```json
{
  "documents": [
    {
      "id": "doc-1",
      "org_id": "org-uuid",
      "title": "First doc",
      "body": "Content",
      "source_type": "code",
      "source_path": "/src/main.rs"
    }
  ]
}
```

**Response `201`:** `{"status": "indexed", "indexed": 1}`

**Errors:** `500` (index error)

### POST /search

Search documents within an organization. BM25 scoring across title and body fields.

**Request Body:**
```json
{
  "query": "search terms",
  "org_id": "org-uuid",
  "limit": 10,
  "offset": 0
}
```

`limit` defaults to 10, `offset` defaults to 0.

**Response `200`:**
```json
{
  "results": [
    {
      "id": "doc-uuid",
      "title": "Document title",
      "snippet": "...matching <b>terms</b> highlighted...",
      "score": 5.23,
      "source_type": "document",
      "source_path": "/docs/example.md"
    }
  ],
  "total": 1
}
```

Empty query returns `{"results": [], "total": 0}`.

**Errors:** `400` (query parse error), `500` (search error)

### DELETE /index/{org_id}

Delete all indexed documents for an organization.

**Response `200`:** `{"status": "deleted"}`

**Errors:** `500` (index error)

---

## Dormant Services

### Course Service (`:8002`) — dormant

17 endpoints. CRUD courses + modules + lessons + reviews, ILIKE search, curriculum, categories, filtering/sorting, bundles, promotions, wishlist. Код сохранён, не развивается.

### Enrollment Service (`:8003`) — dormant

8 endpoints. POST /enrollments, GET /me, lesson progress, auto-completion, course enrollment count, recommendations. Код сохранён, не развивается.
