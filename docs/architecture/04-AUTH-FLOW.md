# 04 — Authentication Flow

> Последнее обновление: 2026-03-05
> Стадия: B2B Agentic Adaptive Learning Pivot

---

## Обзор

Аутентификация реализована через **JWT с shared secret**. Все активные сервисы (Identity, Payment, Notification, AI, Learning, RAG) используют один и тот же `JWT_SECRET` для валидации токенов. Identity создаёт токены при register/login, остальные сервисы только валидируют.

B2B pivot добавляет `organization_id` в JWT extra_claims для контекста активной организации, а также org membership проверки и Trust Level авторизацию.

```
┌─────────┐        ┌──────────┐        ┌──────────┐
│ Browser │        │ Identity │        │ Learning │
│         │        │  :8001   │        │  :8007   │
└────┬────┘        └────┬─────┘        └────┬─────┘
     │                  │                   │
     │  POST /register  │                   │
     │  {email,pass,    │                   │
     │   name,role}     │                   │
     │─────────────────▶│                   │
     │                  │                   │
     │                  │ bcrypt hash       │
     │                  │ INSERT user       │
     │                  │ JWT encode        │
     │                  │  (sub, role,      │
     │                  │   is_verified,    │
     │                  │   organization_id)│
     │                  │                   │
     │  {access_token,  │                   │
     │   refresh_token} │                   │
     │◀─────────────────│                   │
     │                  │                   │
     │  GET /missions/  │                   │
     │  today?org=X     │                   │
     │  Authorization:  │                   │
     │  Bearer <token>  │                   │
     │──────────────────┼──────────────────▶│
     │                  │                   │
     │                  │    JWT decode     │
     │                  │    (same secret)  │
     │                  │    Extract:       │
     │                  │    - user_id      │
     │                  │    - role         │
     │                  │    - org_id       │
     │                  │                   │
     │                  │    Check:         │
     │                  │    - org member?  │
     │                  │    - trust level? │
     │                  │                   │
     │  {mission}       │                   │
     │◀─────────────────┼───────────────────│
```

---

## Регистрация

1. Пользователь отправляет `POST /register` с email, password, name и опционально role
2. Identity Service:
   - Проверяет уникальность email (409 Conflict если занят)
   - Хэширует пароль через `bcrypt.hashpw()` с `bcrypt.gensalt()`
   - Генерирует реферальный код (REF-XXXXXXXX)
   - Сохраняет пользователя в БД с `role` и `is_verified=false`
   - Создаёт JWT с extra_claims: `{role, is_verified, email_verified}`
   - Создаёт refresh token (UUID, SHA-256 hash в БД)
3. Возвращает `{access_token, refresh_token, token_type: "bearer"}`

---

## Логин

1. Пользователь отправляет `POST /login` с email и password
2. Identity Service:
   - Ищет пользователя по email (400 если не найден)
   - Проверяет пароль через `bcrypt.checkpw()`
   - Создаёт JWT с **текущими** значениями из БД (role, is_verified, email_verified)
   - Если пользователь состоит в организации — добавляет `organization_id` в claims (последняя активная организация)
   - Создаёт refresh token (UUID-based, SHA-256 хэш в БД)
3. Возвращает `{access_token, refresh_token, token_type: "bearer"}`

---

## Refresh Token Flow

```
Client                    Identity Service               Database
  │                            │                            │
  │  POST /refresh             │                            │
  │  {refresh_token}           │                            │
  │───────────────────────────▶│                            │
  │                            │  SHA-256(token)            │
  │                            │  SELECT by hash            │
  │                            │───────────────────────────▶│
  │                            │◀───────────────────────────│
  │                            │                            │
  │                            │  Check: not revoked?       │
  │                            │  Check: not expired?       │
  │                            │                            │
  │                            │  Revoke entire family      │
  │                            │───────────────────────────▶│
  │                            │                            │
  │                            │  Create new refresh token  │
  │                            │  (same family_id)          │
  │                            │───────────────────────────▶│
  │                            │                            │
  │  {access_token,            │                            │
  │   refresh_token}           │                            │
  │◀───────────────────────────│                            │
```

### Token Rotation

- Каждый refresh создаёт **новый** refresh token и инвалидирует **все** предыдущие в той же family
- **Token reuse detection**: если revoked token используется повторно → вся family отзывается (compromised session)
- Refresh token TTL: 30 дней (настраивается через `REFRESH_TOKEN_TTL_DAYS`)

### Logout

`POST /logout` с `{refresh_token}` → отзывает всю token family.

---

## JWT Claims

| Claim | Source | Описание |
|-------|--------|----------|
| `sub` | `user.id` (UUID → string) | Идентификатор пользователя |
| `iat` | `datetime.now(UTC)` | Время выпуска токена |
| `exp` | `iat + 3600s` | Время истечения |
| `role` | `user.role` | `"student"`, `"teacher"` или `"admin"` |
| `is_verified` | `user.is_verified` | Статус верификации преподавателя |
| `email_verified` | `user.email_verified` | Подтверждён ли email |
| `organization_id` | active org context | ID активной организации (NEW, nullable) |

### Organization Context в JWT (NEW)

Когда пользователь выбирает активную организацию (или логинится и у него есть организация), `organization_id` добавляется в JWT extra_claims. Это позволяет всем сервисам знать контекст организации без дополнительных запросов к Identity.

```python
extra_claims = {
    "role": user.role,
    "is_verified": user.is_verified,
    "email_verified": user.email_verified,
    "organization_id": str(active_org_id) if active_org_id else None,
}
```

Если пользователь не состоит ни в одной организации — `organization_id` отсутствует в claims (None).

---

## Авторизация в сервисах

Все сервисы **не обращаются к Identity Service**. Вся авторизация происходит через JWT claims:

1. Route layer извлекает `Authorization: Bearer <token>` из header
2. Декодирует JWT тем же `JWT_SECRET` (env var)
3. Извлекает claims: `user_id` (sub), `role`, `is_verified`, `organization_id`
4. Передаёт claims в service layer

### Identity Service

**Admin-only (role=admin):**
- `PATCH /admin/users/{id}/verify` — верификация teacher

**Org owner/admin:**
- `POST /organizations/{id}/members` — добавление участника
- `DELETE /organizations/{id}/members/{user_id}` — удаление участника

**Org membership required:**
- `GET /organizations/{id}` — информация об организации
- `GET /organizations/{id}/members` — список участников

---

### AI Service

**Authenticated (любая роль):**
- `POST /ai/quiz/generate`, `POST /ai/summary/generate`
- `POST /ai/tutor/chat`, `POST /ai/tutor/feedback`
- `GET /ai/credits/me`

**Teacher/admin only:**
- `POST /ai/course/outline`, `POST /ai/lesson/generate`
- `POST /ai/moderate`

**Authenticated + org membership (NEW):**
- `POST /ai/strategist/plan-path` — планирование пути
- `POST /ai/strategist/next-concept` — следующий концепт
- `POST /ai/strategist/adapt` — адаптация пути
- `POST /ai/designer/mission` — генерация миссии
- `POST /ai/designer/recap` — recap после миссии
- `POST /ai/coach/start`, `POST /ai/coach/chat`, `POST /ai/coach/end` — guided session
- `GET /ai/mission/daily` — ежедневная миссия
- `GET /ai/memory/{user_id}` — agent memory (admin или owner)
- `POST /ai/memory/{user_id}` — обновление memory (admin/internal)

---

### Learning Engine

**Teacher-only (role=teacher + is_verified):**
- `POST /quizzes`, concept management, `PATCH /discussions/{id}/pin`, `PATCH /discussions/{id}/mark-answer`

**Student-only:**
- `POST /quizzes/{id}/submit`, flashcard CRUD, pre-tests

**Authenticated (любая роль):**
- GET endpoints для quizzes, concepts, streaks, leaderboard, discussions, XP, badges, velocity, activity

**Authenticated + org membership (NEW):**
- `GET /missions/today` — сегодняшняя миссия
- `POST /missions/{id}/start`, `POST /missions/{id}/complete` — управление миссией
- `GET /missions/me`, `GET /missions/streak` — история и streak
- `GET /trust-level/me` — свой trust level
- `GET /trust-level/org/{org_id}` — trust levels организации (org admin)
- `GET /daily/me` — ежедневная сводка

---

### RAG Service (NEW)

**Authenticated + org membership:**
- `GET /documents`, `POST /search`, `GET /concepts`
- `GET /kb/{org_id}/stats`, `GET /kb/{org_id}/sources`, `GET /kb/{org_id}/concepts`
- `POST /kb/{org_id}/search`
- `GET /templates`, `GET /templates/{id}`

**Authenticated + org admin:**
- `POST /documents`, `DELETE /documents/{id}`
- `POST /concepts/extract/{document_id}`
- `POST /sources/github`
- `POST /upload/markdown`, `POST /upload/bulk`
- `POST /kb/{org_id}/refresh/{document_id}`
- `POST /templates`, `POST /templates/{id}/stages`
- `PUT /templates/{id}/stages/{stage_id}`, `DELETE /templates/{id}/stages/{stage_id}`

---

### Payment Service

**Student-only:** `POST /payments`
**Authenticated:** `GET /payments/{id}`, `GET /payments/me`
**Teacher-only:** earnings, payouts
**Admin-only:** refund management
**Org owner/admin (NEW):** `POST /org-subscriptions`, `POST /org-subscriptions/{org_id}/cancel`
**Org membership (NEW):** `GET /org-subscriptions/{org_id}`

---

### Notification Service

**Authenticated:** `POST /notifications`, `GET /notifications/me`, `PATCH /{id}/read`, messages
**Admin-only:** streak/flashcard reminders

---

## Organization Membership Check (NEW)

Для endpoints с `org membership required`, middleware проверяет:

```python
# In route layer:
async def require_org_membership(
    user_id: UUID,
    organization_id: UUID,
    # Identity DB не читается — проверка через JWT claim или query param
) -> None:
    # Option 1: organization_id from JWT claims (fast, no DB call)
    # Option 2: API call to Identity /organizations/{org_id}/members check
    pass
```

В текущей реализации `organization_id` передаётся как query parameter или в request body, и сервис доверяет JWT claim `organization_id`. Для критических операций (admin actions) выполняется дополнительная проверка.

---

## Trust Level Authorization (NEW)

Некоторые ресурсы и действия гейтятся Trust Level:

| Trust Level | Доступные действия |
|-------------|-------------------|
| 0 (Observer) | Только чтение документации, просмотр KB |
| 1 (Learner) | Миссии, квизы, flashcards |
| 2 (Contributor) | Дискуссии, study groups |
| 3 (Practitioner) | Реальные задачи из кодовой базы, code review миссии |
| 4 (Specialist) | Менторинг, advanced topics |
| 5 (Expert) | Создание контента, управление KB |

Trust Level проверяется в service layer:

```python
# In service layer:
async def check_trust_level(
    user_id: UUID,
    organization_id: UUID,
    required_level: int,
    trust_repo: TrustLevelRepository,
) -> None:
    trust = await trust_repo.get(user_id, organization_id)
    if trust.level < required_level:
        raise ForbiddenError(f"Trust level {required_level} required, current: {trust.level}")
```

---

## Верификация преподавателей

1. Преподаватель регистрируется с `role=teacher` → получает `is_verified=false`
2. Администратор (`role=admin`) → `PATCH /admin/users/{id}/verify`
3. Identity Service обновляет `is_verified=true` в БД
4. Преподаватель перелогинивается → получает новый JWT с `is_verified=true`

---

## Email Verification Flow

1. При регистрации Identity Service создаёт `email_verification_token` (raw token → SHA-256 hash в БД, TTL 24h)
2. Raw token логируется `[EMAIL_VERIFY] url=.../verify-email?token=...` (stub)
3. `POST /verify-email {token}` → Identity Service: SHA-256(token) → найти → проверить → mark used → set `email_verified=true`
4. Новый JWT включает `email_verified: true`

---

## Forgot Password Flow

1. `POST /forgot-password {email}` → всегда 204 (не раскрывает существование email)
2. Если email существует: rate limit (3/hour), создаёт `password_reset_token` (TTL 1h), логирует `[PASSWORD_RESET]`
3. `POST /reset-password {token, new_password}` → validate token → update password (bcrypt) → revoke all refresh tokens
4. Пользователь перелогинивается с новым паролем

---

## Хранение токена на клиенте

Фронтенд хранит токен в `localStorage`:
- `token` — JWT access token
- `user` — JSON объект текущего пользователя (кэш)
- `activeOrganization` — ID активной организации (NEW)

При logout — все ключи удаляются.

---

## Ограничения

| Ограничение | Причина | Когда появится |
|-------------|---------|---------------|
| Shared secret (HS256) | Простота, все сервисы | По необходимости (RSA/JWKS при gateway) |
| localStorage | Простота | Cookie httpOnly при production |
| Email stub (логирование) | Нет SMTP | По необходимости |
| Org membership check via JWT | Не real-time (если удалили из org, JWT ещё валиден до exp) | По необходимости (Redis blacklist) |
