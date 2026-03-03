# 04 — Authentication Flow

> Последнее обновление: 2026-03-03
> Стадия: Phase 3.2 (Monetization backend — Stripe, subscriptions, earnings, payouts)

---

## Обзор

Аутентификация реализована через **JWT с shared secret**. Все 7 сервисов используют один и тот же `JWT_SECRET` для валидации токенов. Identity создаёт токены при register/login, остальные сервисы только валидируют.

```
┌─────────┐        ┌──────────┐        ┌──────────┐
│ Browser │        │ Identity │        │  Course  │
│         │        │  :8001   │        │  :8002   │
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
     │                  │   is_verified)    │
     │                  │                   │
     │  {access_token}  │                   │
     │◀─────────────────│                   │
     │                  │                   │
     │  POST /courses   │                   │
     │  Authorization:  │                   │
     │  Bearer <token>  │                   │
     │──────────────────┼──────────────────▶│
     │                  │                   │
     │                  │    JWT decode     │
     │                  │    (same secret)  │
     │                  │    Extract:       │
     │                  │    - user_id      │
     │                  │    - role         │
     │                  │    - is_verified  │
     │                  │                   │
     │                  │    Check:         │
     │                  │    role=teacher?  │
     │                  │    is_verified?   │
     │                  │                   │
     │  {course}        │                   │
     │◀─────────────────┼───────────────────│
```

---

## Регистрация

1. Пользователь отправляет `POST /register` с email, password, name и опционально role
2. Identity Service:
   - Проверяет уникальность email (409 Conflict если занят)
   - Хэширует пароль через `bcrypt.hashpw()` с `bcrypt.gensalt()`
   - Сохраняет пользователя в БД с `role` и `is_verified=false`
   - Создаёт JWT с extra_claims: `{role, is_verified}`
3. Возвращает `{access_token, refresh_token, token_type: "bearer"}`

---

## Логин

1. Пользователь отправляет `POST /login` с email и password
2. Identity Service:
   - Ищет пользователя по email (400 если не найден)
   - Проверяет пароль через `bcrypt.checkpw()`
   - Создаёт JWT с **текущими** значениями role и is_verified из БД
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

### Таблица refresh_tokens

```sql
CREATE TABLE refresh_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash VARCHAR(255) NOT NULL UNIQUE,
    family_id UUID NOT NULL,
    is_revoked BOOLEAN NOT NULL DEFAULT false,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

---

## Авторизация в сервисах

Все 7 сервисов **не обращаются к Identity Service**. Вся авторизация происходит через JWT claims:

1. Route layer извлекает `Authorization: Bearer <token>` из header
2. Декодирует JWT тем же `JWT_SECRET` (env var)
3. Извлекает claims: `user_id` (sub), `role`, `is_verified`
4. Передаёт claims в service layer

### Identity Service

**Admin-only (role=admin):**
- `GET /admin/teachers/pending` — список unverified teachers
- `PATCH /admin/users/{id}/verify` — верификация teacher

### Course Service

**Teacher-only (role=teacher + is_verified + owner check):**
- `POST /courses` — создание курса
- `PUT /courses/{id}` — редактирование курса
- `POST /courses/{id}/modules`, `PUT /modules/{id}`, `DELETE /modules/{id}` — управление модулями
- `POST /modules/{id}/lessons`, `PUT /lessons/{id}`, `DELETE /lessons/{id}` — управление уроками

**Student-only (role=student):**
- `POST /reviews` — отзыв на курс

**Публичные** (без авторизации):
- `GET /courses`, `GET /courses/{id}`, `GET /courses/{id}/curriculum`
- `GET /lessons/{id}`, `GET /reviews/course/{id}`

### Enrollment Service

**Student-only (role=student):**
- `POST /enrollments` — запись на курс
- `POST /progress/lessons/{id}/complete` — отметка прогресса

**Authenticated (любая роль):**
- `GET /enrollments/me`, `GET /progress/courses/{id}`, `GET /progress/courses/{id}/lessons`

**Публичные:**
- `GET /enrollments/course/{id}/count`

### Payment Service

**Student-only:** `POST /payments`
**Authenticated:** `GET /payments/{id}`, `GET /payments/me`
**Teacher-only:** `GET /earnings/me/summary`, `GET /earnings/me`, `POST /earnings/payouts`, `GET /earnings/payouts`

### Notification Service

**Authenticated:** `POST /notifications`, `GET /notifications/me`, `PATCH /notifications/{id}/read`
**Admin-only:** `POST /streak-reminders/send`, `POST /flashcard-reminders/send`

### AI Service

**Authenticated (любая роль):**
- `POST /ai/quiz/generate` — генерация квиза из содержания урока
- `POST /ai/summary/generate` — генерация краткого содержания
- `POST /ai/tutor/chat` — Socratic AI-тьютор (чат по уроку, лимит 10/день)
- `POST /ai/tutor/feedback` — оценка ответа тьютора (thumbs up/down)
- `GET /ai/credits/me` — баланс кредитов текущего пользователя

### Learning Engine

**Teacher-only (role=teacher + is_verified):**
- `POST /quizzes` — создание квиза для урока

**Student-only (role=student):**
- `POST /quizzes/{id}/submit` — сдача квиза
- `GET /quizzes/{id}/attempts/me` — мои попытки
- `POST /flashcards` — создание карточки
- `GET /flashcards/due` — карточки к повторению
- `POST /flashcards/{id}/review` — повторение карточки
- `DELETE /flashcards/{id}` — удаление карточки

**Authenticated (любая роль):**
- `GET /quizzes/lesson/{id}` — получение квиза для урока
- `GET /concepts/course/{id}` — граф концептов курса
- `GET /concepts/course/{id}/mastery` — мастерство по концептам
- `GET /streaks/me` — текущий streak пользователя
- `GET /leaderboard` — общий рейтинг
- `GET /leaderboard/course/{id}` — рейтинг по курсу
- `GET /discussions/lesson/{id}` — обсуждения урока
- `POST /discussions` — создание комментария
- `POST /discussions/{id}/upvote` — голосование
- `GET /xp/me` — XP текущего пользователя
- `GET /badges/me` — значки текущего пользователя

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

---

## Верификация преподавателей

Верификация выполняется через Admin API:

1. Преподаватель регистрируется с `role=teacher` → получает `is_verified=false`
2. Администратор (`role=admin`) открывает панель `/admin/teachers` → видит список unverified teachers
3. Администратор нажимает "Одобрить" → `PATCH /admin/users/{id}/verify`
4. Identity Service обновляет `is_verified=true` в БД
5. Преподаватель **перелогинивается** → получает новый JWT с `is_verified=true` → может создавать курсы

**Admin endpoints (Identity Service):**
- `GET /admin/teachers/pending` — список unverified teachers (admin only)
- `PATCH /admin/users/{user_id}/verify` — верифицировать teacher (admin only)

**Seed admin:** `admin@eduplatform.com` / `password123` (создаётся в seed скрипте)

---

## Email Verification Flow

1. При регистрации Identity Service создаёт `email_verification_token` (raw token → SHA-256 hash в БД, TTL 24h)
2. Raw token логируется `[EMAIL_VERIFY] url=.../verify-email?token=...` (stub, без реальной отправки)
3. Пользователь переходит по ссылке → `POST /verify-email {token}`
4. Identity Service: SHA-256(token) → найти в БД → проверить expiry/used → mark used → set `email_verified=true`
5. Новый JWT включает `email_verified: true`

**Resend:** `POST /resend-verification` (authenticated) → удаляет старые токены, создаёт новый.

**Frontend:** баннер "Подтвердите email" в Header, если `email_verified === false`.

---

## Forgot Password Flow

1. Пользователь отправляет `POST /forgot-password {email}`
2. Identity Service **всегда** возвращает 204 (не раскрывает существование email)
3. Если email существует: проверяет rate limit (3/hour per user), создаёт `password_reset_token` (TTL 1h), логирует `[PASSWORD_RESET]`
4. Пользователь переходит по ссылке → `POST /reset-password {token, new_password}`
5. Identity Service: validate token → update password (bcrypt) → revoke all refresh tokens
6. Пользователь перелогинивается с новым паролем

---

## Хранение токена на клиенте

Фронтенд хранит токен в `localStorage`:
- `token` — JWT access token
- `user` — JSON объект текущего пользователя (кэш)

При logout — оба ключа удаляются.

---

## Ограничения

| Ограничение | Причина | Когда появится |
|-------------|---------|---------------|
| ~~Нет refresh token~~ | ~~YAGNI для MVP~~ | ✅ Phase 1.2 — refresh token rotation |
| ~~Нет blacklist токенов~~ | ~~Нет Redis кэша~~ | ✅ Phase 1.2 — revoke family via DB |
| Shared secret (HS256) | Простота, 7 сервисов | Phase 3 (RSA/JWKS при gateway) |
| ~~Manual verification~~ | ~~Нет admin panel~~ | ✅ Admin panel реализован |
| localStorage | Простота | Cookie httpOnly при production |
| Email stub (логирование) | Нет SMTP | Phase 2 (реальная отправка через email service) |
