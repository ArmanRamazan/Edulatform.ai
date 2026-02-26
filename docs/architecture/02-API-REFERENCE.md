# 02 — API Reference

> Последнее обновление: 2026-02-26
> Стадия: Phase 2.4 (Gamification — Streaks, XP, Badges)

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

**Errors:**
| Code | Причина |
|------|---------|
| 401 | Отсутствует или невалидный токен |

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

**Errors:**
| Code | Причина |
|------|---------|
| 401 | Невалидный, просроченный или повторно использованный refresh token |

> Token reuse detection: если revoked token используется повторно, вся token family отзывается.

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

**Errors:**
| Code | Причина |
|------|---------|
| 400 | Невалидный, просроченный или уже использованный токен |

---

### POST /resend-verification

Повторная отправка email-верификации. Требует JWT.

**Headers:** `Authorization: Bearer <token>`

**Response `204`:** No content.

**Errors:**
| Code | Причина |
|------|---------|
| 400 | Email уже подтверждён |
| 401 | Отсутствует или невалидный токен |

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

**Errors:**
| Code | Причина |
|------|---------|
| 400 | Невалидный, просроченный или уже использованный токен |

---

### Health Check Endpoints (все сервисы)

#### GET /health/live

Liveness probe. Всегда 200 если процесс жив.

**Response `200`:** `{"status": "ok"}`

#### GET /health/ready

Readiness probe. Проверяет PostgreSQL и Redis (если есть).

**Response `200`:** `{"status": "ok", "checks": {"postgres": "ok", "redis": "ok"}}`
**Response `503`:** `{"status": "degraded", "checks": {"postgres": "unavailable"}}`

---

### GET /admin/teachers/pending

Список преподавателей, ожидающих верификации. Только для `role=admin`.

**Headers:** `Authorization: Bearer <token>`

**Query params:**
| Параметр | Тип | Default | Описание |
|----------|-----|---------|----------|
| `limit` | int (1-100) | 50 | Количество записей |
| `offset` | int (≥0) | 0 | Смещение |

**Response `200`:**
```json
{
  "items": [
    {
      "id": "...",
      "email": "teacher@example.com",
      "name": "Ivan Petrov",
      "created_at": "2026-02-20T12:00:00+00:00"
    }
  ],
  "total": 5
}
```

**Errors:**
| Code | Причина |
|------|---------|
| 401 | Отсутствует или невалидный токен |
| 403 | `role != admin` — "Admin access required" |

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

**Errors:**
| Code | Причина |
|------|---------|
| 401 | Отсутствует или невалидный токен |
| 403 | `role != admin` — "Admin access required" |
| 404 | Пользователь не найден |
| 409 | Пользователь не является teacher / уже верифицирован |

---

## Course Service (`:8002`)

### GET /categories

Список всех категорий курсов. Публичный endpoint.

**Response `200`:**
```json
[
  {"id": "...", "name": "Programming", "slug": "programming"},
  {"id": "...", "name": "Design", "slug": "design"}
]
```

---

### GET /courses

Список курсов с пагинацией, фильтрацией и поиском. Публичный endpoint, не требует авторизации.

**Query params:**
| Параметр | Тип | Default | Описание |
|----------|-----|---------|----------|
| `q` | string | — | Поиск по title/description (ILIKE) |
| `category_id` | UUID | — | Фильтр по категории |
| `level` | string | — | Фильтр по уровню (beginner/intermediate/advanced) |
| `is_free` | bool | — | Фильтр по стоимости |
| `sort_by` | string | created_at | Сортировка: created_at, avg_rating, price |
| `limit` | int (1-100) | 20 | Количество записей |
| `offset` | int (≥0) | 0 | Смещение |

**Response `200`:**
```json
{
  "items": [
    {
      "id": "...",
      "teacher_id": "...",
      "title": "Python для начинающих",
      "description": "Основы Python...",
      "is_free": true,
      "price": null,
      "duration_minutes": 120,
      "level": "beginner",
      "avg_rating": 4.35,
      "review_count": 12,
      "category_id": "550e8400-e29b-41d4-a716-446655440001",
      "created_at": "2026-02-20T12:00:00+00:00"
    }
  ],
  "total": 42
}
```

---

### GET /courses/{course_id}

Детали одного курса. Публичный endpoint.

**Response `200`:** Объект `Course` (см. выше).

**Errors:**
| Code | Причина |
|------|---------|
| 404 | Курс не найден |

---

### POST /courses

Создание курса. Только для **verified teacher**.

**Headers:** `Authorization: Bearer <token>`

**Request:**
```json
{
  "title": "Python для начинающих",
  "description": "Основы Python",
  "is_free": true,
  "price": null,
  "duration_minutes": 120,
  "level": "beginner",
  "category_id": "550e8400-e29b-41d4-a716-446655440001"
}
```

**Response `201`:** Объект `Course`.

**Errors:**
| Code | Причина |
|------|---------|
| 401 | Отсутствует или невалидный токен |
| 403 | `role != teacher` — "Only teachers can create courses" |
| 403 | `is_verified == false` — "Only verified teachers can create courses" |
| 422 | Невалидные данные |

---

### GET /courses/my

Список курсов текущего преподавателя. Требует JWT (teacher).

**Headers:** `Authorization: Bearer <token>`

**Query params:** `limit`, `offset` (аналогично /courses).

**Response `200`:** Аналогично GET /courses.

---

### GET /courses/{course_id}/curriculum

Программа курса: модули с вложенными уроками. Публичный endpoint.

**Response `200`:**
```json
{
  "course": { "...": "Course object" },
  "modules": [
    {
      "id": "...",
      "course_id": "...",
      "title": "Введение",
      "order": 0,
      "created_at": "...",
      "lessons": [
        {
          "id": "...",
          "module_id": "...",
          "title": "Первый урок",
          "content": "...",
          "video_url": null,
          "duration_minutes": 30,
          "order": 0,
          "created_at": "..."
        }
      ]
    }
  ],
  "total_lessons": 15
}
```

---

### PUT /courses/{course_id}

Обновление курса. Только для **verified teacher** (owner check).

**Headers:** `Authorization: Bearer <token>`

**Request:** Все поля опциональны.
```json
{
  "title": "Новое название",
  "description": "Новое описание",
  "is_free": false,
  "price": 29.99,
  "duration_minutes": 180,
  "level": "intermediate"
}
```

**Response `200`:** Объект `Course`.

**Errors:**
| Code | Причина |
|------|---------|
| 403 | Не owner или не verified teacher |
| 404 | Курс не найден |

---

### POST /courses/{course_id}/modules

Создание модуля. Только для **verified teacher** (owner check).

**Headers:** `Authorization: Bearer <token>`

**Request:**
```json
{
  "title": "Введение",
  "order": 0
}
```

**Response `201`:** Объект `Module`.

---

### PUT /modules/{module_id}

Обновление модуля. Только для teacher (owner check).

**Headers:** `Authorization: Bearer <token>`

**Response `200`:** Объект `Module`.

---

### DELETE /modules/{module_id}

Удаление модуля (каскадное удаление уроков). Только для teacher (owner check).

**Headers:** `Authorization: Bearer <token>`

**Response `204`:** No content.

---

### POST /modules/{module_id}/lessons

Создание урока. Только для **verified teacher** (owner check через module→course).

**Headers:** `Authorization: Bearer <token>`

**Request:**
```json
{
  "title": "Первый урок",
  "content": "Содержимое урока в Markdown",
  "video_url": "https://youtube.com/embed/...",
  "duration_minutes": 30,
  "order": 0
}
```

**Response `201`:** Объект `Lesson`.

---

### GET /lessons/{lesson_id}

Содержимое урока. Публичный endpoint.

**Response `200`:** Объект `Lesson`.

---

### PUT /lessons/{lesson_id}

Обновление урока. Только для teacher (owner check).

**Headers:** `Authorization: Bearer <token>`

**Response `200`:** Объект `Lesson`.

---

### DELETE /lessons/{lesson_id}

Удаление урока. Только для teacher (owner check).

**Headers:** `Authorization: Bearer <token>`

**Response `204`:** No content.

---

### POST /reviews

Оставить отзыв на курс. Только для `role=student`. Один отзыв на курс.

**Headers:** `Authorization: Bearer <token>`

**Request:**
```json
{
  "course_id": "550e8400-e29b-41d4-a716-446655440000",
  "rating": 5,
  "comment": "Отличный курс!"
}
```

**Response `201`:** Объект `Review`.

**Errors:**
| Code | Причина |
|------|---------|
| 403 | `role != student` |
| 404 | Курс не найден |
| 409 | Уже оставлен отзыв на этот курс |

---

### GET /reviews/course/{course_id}

Отзывы на курс. Публичный endpoint.

**Query params:** `limit`, `offset`.

**Response `200`:**
```json
{
  "items": [
    {
      "id": "...",
      "student_id": "...",
      "course_id": "...",
      "rating": 5,
      "comment": "Отличный курс!",
      "created_at": "..."
    }
  ],
  "total": 12
}
```

---

## Enrollment Service (`:8003`)

### POST /enrollments

Записаться на курс. Только для `role=student`.

**Headers:** `Authorization: Bearer <token>`

**Request:**
```json
{
  "course_id": "550e8400-e29b-41d4-a716-446655440000",
  "payment_id": "660e8400-e29b-41d4-a716-446655440000",  // optional, для платных курсов
  "total_lessons": 15                                     // optional, для auto-completion
}
```

**Response `201`:**
```json
{
  "id": "...",
  "student_id": "...",
  "course_id": "...",
  "payment_id": null,
  "status": "enrolled",
  "total_lessons": 15,
  "enrolled_at": "2026-02-20T12:00:00+00:00"
}
```

**Errors:**
| Code | Причина |
|------|---------|
| 401 | Отсутствует или невалидный токен |
| 403 | `role != student` — "Only students can enroll in courses" |
| 409 | Уже записан на курс (UNIQUE constraint) |
| 422 | Невалидные данные |

---

### GET /enrollments/me

Мои записи на курсы. Требует JWT.

**Headers:** `Authorization: Bearer <token>`

**Query params:**
| Параметр | Тип | Default | Описание |
|----------|-----|---------|----------|
| `limit` | int (1-100) | 20 | Количество записей |
| `offset` | int (≥0) | 0 | Смещение |

**Response `200`:**
```json
{
  "items": [{ "id": "...", "student_id": "...", "course_id": "...", "payment_id": null, "status": "enrolled", "enrolled_at": "..." }],
  "total": 5
}
```

---

### GET /enrollments/course/{course_id}/count

Количество записей на курс. Публичный endpoint.

**Response `200`:**
```json
{
  "course_id": "...",
  "count": 42
}
```

---

### POST /progress/lessons/{lesson_id}/complete

Отметить урок как пройденный. Только для `role=student`.

**Headers:** `Authorization: Bearer <token>`

**Request:**
```json
{
  "course_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**Response `201`:**
```json
{
  "id": "...",
  "lesson_id": "...",
  "course_id": "...",
  "completed_at": "2026-02-20T12:00:00+00:00"
}
```

**Errors:**
| Code | Причина |
|------|---------|
| 403 | `role != student` |
| 409 | Урок уже пройден |

---

### GET /progress/courses/{course_id}

Прогресс студента по курсу. Требует JWT.

**Headers:** `Authorization: Bearer <token>`

**Query params:**
| Параметр | Тип | Описание |
|----------|-----|----------|
| `total_lessons` | int | Общее количество уроков в курсе |

**Response `200`:**
```json
{
  "course_id": "...",
  "completed_lessons": 8,
  "total_lessons": 15,
  "percentage": 53.3
}
```

---

### GET /progress/courses/{course_id}/lessons

Список пройденных уроков. Требует JWT.

**Headers:** `Authorization: Bearer <token>`

**Response `200`:**
```json
{
  "course_id": "...",
  "completed_lesson_ids": ["uuid1", "uuid2", "..."]
}
```

---

## Payment Service (`:8004`)

### POST /payments

Mock оплата курса. Всегда возвращает `status=completed`. Только для `role=student`.

**Headers:** `Authorization: Bearer <token>`

**Request:**
```json
{
  "course_id": "550e8400-e29b-41d4-a716-446655440000",
  "amount": 49.99
}
```

**Response `201`:**
```json
{
  "id": "...",
  "student_id": "...",
  "course_id": "...",
  "amount": "49.99",
  "status": "completed",
  "created_at": "2026-02-20T12:00:00+00:00"
}
```

**Errors:**
| Code | Причина |
|------|---------|
| 401 | Отсутствует или невалидный токен |
| 403 | `role != student` — "Only students can make payments" |
| 422 | Невалидные данные (amount <= 0) |

---

### GET /payments/{id}

Статус оплаты. Требует JWT.

**Headers:** `Authorization: Bearer <token>`

**Response `200`:** Объект `Payment`.

**Errors:**
| Code | Причина |
|------|---------|
| 404 | Оплата не найдена |

---

### GET /payments/me

Мои оплаты. Требует JWT.

**Headers:** `Authorization: Bearer <token>`

**Query params:** `limit`, `offset` (аналогично другим /me endpoints).

**Response `200`:**
```json
{
  "items": [{ "id": "...", "student_id": "...", "course_id": "...", "amount": "49.99", "status": "completed", "created_at": "..." }],
  "total": 3
}
```

---

## Notification Service (`:8005`)

### POST /notifications

Создать уведомление. Логирует `[NOTIFICATION]` в stdout. Требует JWT.

**Headers:** `Authorization: Bearer <token>`

**Request:**
```json
{
  "type": "enrollment",
  "title": "Вы записались на курс: Python 101",
  "body": "Бесплатная запись"
}
```

**Response `201`:**
```json
{
  "id": "...",
  "user_id": "...",
  "type": "enrollment",
  "title": "...",
  "body": "...",
  "is_read": false,
  "created_at": "2026-02-20T12:00:00+00:00"
}
```

---

### GET /notifications/me

Мои уведомления. Требует JWT.

**Headers:** `Authorization: Bearer <token>`

**Query params:** `limit`, `offset`.

**Response `200`:**
```json
{
  "items": [{ "id": "...", "user_id": "...", "type": "enrollment", "title": "...", "body": "...", "is_read": false, "created_at": "..." }],
  "total": 10
}
```

---

### PATCH /notifications/{id}/read

Пометить уведомление как прочитанное. Требует JWT. Проверяет, что уведомление принадлежит текущему пользователю.

**Headers:** `Authorization: Bearer <token>`

**Response `200`:** Объект `Notification` с `is_read: true`.

**Errors:**
| Code | Причина |
|------|---------|
| 404 | Уведомление не найдено или не принадлежит пользователю |

---

## AI Service (`:8006`)

### POST /ai/quiz/generate

Генерация квиза из содержания урока через Gemini Flash. Требует JWT.

**Headers:** `Authorization: Bearer <token>`

**Request:**
```json
{
  "lesson_id": "550e8400-e29b-41d4-a716-446655440000",
  "content": "Текст урока (min 10, max 50000 символов)"
}
```

**Response `200`:**
```json
{
  "lesson_id": "...",
  "questions": [
    {
      "text": "Вопрос?",
      "options": ["A", "B", "C", "D"],
      "correct_index": 1,
      "explanation": "Объяснение"
    }
  ],
  "model_used": "gemini-2.0-flash-lite",
  "cached": false
}
```

---

### POST /ai/summary/generate

Генерация краткого содержания урока. Требует JWT.

**Headers:** `Authorization: Bearer <token>`

**Request:**
```json
{
  "lesson_id": "550e8400-e29b-41d4-a716-446655440000",
  "content": "Текст урока (min 10, max 50000 символов)"
}
```

**Response `200`:**
```json
{
  "lesson_id": "...",
  "summary": "Краткое содержание...",
  "model_used": "gemini-2.0-flash-lite",
  "cached": true
}
```

---

### POST /ai/tutor/chat

Сократический AI-тьютор. Отправка сообщения в контексте урока. AI не даёт прямых ответов — задаёт наводящие вопросы. Требует JWT.

**Headers:** `Authorization: Bearer <token>`

**Request:**
```json
{
  "lesson_id": "550e8400-e29b-41d4-a716-446655440000",
  "message": "Что такое переменная?",
  "lesson_content": "Текст урока (min 10, max 50000 символов)",
  "session_id": null
}
```

> `session_id` — `null` для нового диалога, строка для продолжения существующего.

**Response `200`:**
```json
{
  "session_id": "uuid-строка",
  "message": "Хороший вопрос! Как ты думаешь, что происходит когда ты присваиваешь значение имени?",
  "model_used": "gemini-2.0-flash-lite",
  "credits_remaining": 9
}
```

**Errors:**
| Code | Причина |
|------|---------|
| 401 | Отсутствует или невалидный токен |
| 403 | Дневной лимит чатов исчерпан (10/день) |

---

### POST /ai/tutor/feedback

Оценка ответа тьютора (thumbs up/down). Требует JWT.

**Headers:** `Authorization: Bearer <token>`

**Request:**
```json
{
  "session_id": "uuid-строка",
  "message_index": 1,
  "rating": 1
}
```

> `rating`: -1 (плохо), 0 (нейтрально), 1 (хорошо)

**Response `200`:**
```json
{
  "status": "ok"
}
```

**Errors:**
| Code | Причина |
|------|---------|
| 400 | Невалидный message_index |
| 401 | Отсутствует или невалидный токен |
| 404 | Сессия не найдена |

---

## Learning Engine Service (`:8007`)

### POST /quizzes

Создать квиз для урока из результата AI-генерации. Только для **verified teacher** (owner check по `teacher_id`).

**Headers:** `Authorization: Bearer <token>`

**Request:**
```json
{
  "lesson_id": "550e8400-e29b-41d4-a716-446655440000",
  "course_id": "660e8400-e29b-41d4-a716-446655440000",
  "questions": [
    {
      "text": "Что такое переменная?",
      "options": ["Значение", "Именованная ячейка памяти", "Функция", "Тип данных"],
      "correct_index": 1,
      "explanation": "Переменная — именованная область памяти для хранения данных.",
      "order": 0
    }
  ]
}
```

**Response `201`:**
```json
{
  "id": "...",
  "lesson_id": "...",
  "course_id": "...",
  "teacher_id": "...",
  "created_at": "2026-02-25T12:00:00+00:00",
  "questions": [
    {
      "id": "...",
      "quiz_id": "...",
      "text": "Что такое переменная?",
      "options": ["Значение", "Именованная ячейка памяти", "Функция", "Тип данных"],
      "order": 0
    }
  ]
}
```

> Поле `correct_index` и `explanation` не возвращаются в ответе — только при сабмите.

**Errors:**
| Code | Причина |
|------|---------|
| 401 | Отсутствует или невалидный токен |
| 403 | `role != teacher` или `is_verified == false` |
| 409 | Квиз для этого урока уже существует (UNIQUE constraint на `lesson_id`) |
| 422 | Невалидные данные |

---

### GET /quizzes/lesson/{lesson_id}

Получить квиз для урока. Требует JWT. Правильные ответы (`correct_index`, `explanation`) не возвращаются студентам.

**Headers:** `Authorization: Bearer <token>`

**Response `200`:**
```json
{
  "id": "...",
  "lesson_id": "...",
  "course_id": "...",
  "teacher_id": "...",
  "created_at": "2026-02-25T12:00:00+00:00",
  "questions": [
    {
      "id": "...",
      "quiz_id": "...",
      "text": "Что такое переменная?",
      "options": ["Значение", "Именованная ячейка памяти", "Функция", "Тип данных"],
      "order": 0
    }
  ]
}
```

**Errors:**
| Code | Причина |
|------|---------|
| 401 | Отсутствует или невалидный токен |
| 404 | Квиз для урока не найден |

---

### POST /quizzes/{quiz_id}/submit

Сдать квиз. Только для `role=student`. Возвращает оценку и обратную связь по каждому вопросу.

**Headers:** `Authorization: Bearer <token>`

**Request:**
```json
{
  "answers": [1, 0, 2]
}
```

> `answers` — массив выбранных индексов (`int`) по порядку вопросов.

**Response `201`:**
```json
{
  "id": "...",
  "quiz_id": "...",
  "student_id": "...",
  "score": 0.67,
  "answers": [1, 0, 2],
  "completed_at": "2026-02-25T12:00:00+00:00",
  "feedback": [
    {
      "question_id": "...",
      "correct": true,
      "correct_index": 1,
      "explanation": "Переменная — именованная область памяти для хранения данных."
    }
  ]
}
```

> `score` — доля правильных ответов (0.0–1.0).

**Errors:**
| Code | Причина |
|------|---------|
| 401 | Отсутствует или невалидный токен |
| 403 | `role != student` |
| 404 | Квиз не найден |
| 422 | Количество ответов не совпадает с количеством вопросов |

---

### GET /quizzes/{quiz_id}/attempts/me

Список попыток текущего студента по квизу. Только для `role=student`.

**Headers:** `Authorization: Bearer <token>`

**Response `200`:**
```json
[
  {
    "id": "...",
    "quiz_id": "...",
    "student_id": "...",
    "score": 0.67,
    "answers": [1, 0, 2],
    "completed_at": "2026-02-25T12:00:00+00:00"
  }
]
```

**Errors:**
| Code | Причина |
|------|---------|
| 401 | Отсутствует или невалидный токен |
| 403 | `role != student` |

### POST /flashcards

Создать флешкарту. Только для `role=student`.

**Headers:** `Authorization: Bearer <token>`

**Request:**
```json
{
  "course_id": "660e8400-e29b-41d4-a716-446655440000",
  "concept": "Что такое FSRS?",
  "answer": "Free Spaced Repetition Scheduler — алгоритм для оптимального повторения",
  "source_type": "manual",
  "source_id": null
}
```

**Response `201`:**
```json
{
  "id": "...",
  "course_id": "...",
  "concept": "Что такое FSRS?",
  "answer": "Free Spaced Repetition Scheduler...",
  "source_type": "manual",
  "stability": 0.0,
  "difficulty": 0.0,
  "due": "2026-02-25T12:00:00+00:00",
  "state": 0,
  "reps": 0,
  "lapses": 0,
  "created_at": "2026-02-25T12:00:00+00:00"
}
```

**Errors:**
| Code | Причина |
|------|---------|
| 401 | Отсутствует или невалидный токен |
| 403 | `role != student` |
| 422 | Невалидные данные |

---

### GET /flashcards/due

Карточки, которые нужно повторить сейчас (`due <= now()`). Только для `role=student`.

**Headers:** `Authorization: Bearer <token>`

**Query params:** `limit` (default 20), `offset` (default 0)

**Response `200`:**
```json
{
  "items": [
    {
      "id": "...",
      "course_id": "...",
      "concept": "Что такое FSRS?",
      "answer": "Free Spaced Repetition Scheduler...",
      "source_type": "manual",
      "stability": 4.93,
      "difficulty": 5.31,
      "due": "2026-02-25T12:00:00+00:00",
      "state": 2,
      "reps": 3,
      "lapses": 0,
      "created_at": "2026-02-20T10:00:00+00:00"
    }
  ],
  "total": 5
}
```

---

### POST /flashcards/{card_id}/review

Повторить карточку. FSRS рассчитывает следующую дату повторения. Только для `role=student`, только свои карточки.

**Headers:** `Authorization: Bearer <token>`

**Request:**
```json
{
  "rating": 3,
  "review_duration_ms": 5200
}
```

> `rating`: 1=Again, 2=Hard, 3=Good, 4=Easy

**Response `200`:**
```json
{
  "card_id": "...",
  "rating": 3,
  "new_stability": 4.93,
  "new_difficulty": 5.31,
  "next_due": "2026-03-02T12:00:00+00:00",
  "new_state": 2
}
```

**Errors:**
| Code | Причина |
|------|---------|
| 401 | Отсутствует или невалидный токен |
| 403 | `role != student` или не ваша карточка |
| 404 | Карточка не найдена |

---

### DELETE /flashcards/{card_id}

Удалить флешкарту. Только для `role=student`, только свои.

**Headers:** `Authorization: Bearer <token>`

**Response `204`:** Нет тела.

**Errors:**
| Code | Причина |
|------|---------|
| 401 | Отсутствует или невалидный токен |
| 403 | `role != student` |
| 404 | Карточка не найдена или не ваша |

---

### POST /concepts

Создать concept (знание) для курса. Только для **verified teacher**.

**Headers:** `Authorization: Bearer <token>`

**Request:**
```json
{
  "course_id": "660e8400-e29b-41d4-a716-446655440000",
  "name": "Variables",
  "description": "Understanding variables and assignment",
  "lesson_id": null,
  "parent_id": null,
  "order": 0
}
```

**Response `201`:**
```json
{
  "id": "...",
  "course_id": "...",
  "lesson_id": null,
  "name": "Variables",
  "description": "Understanding variables and assignment",
  "parent_id": null,
  "order": 0,
  "created_at": "2026-02-25T12:00:00+00:00"
}
```

**Errors:**
| Code | Причина |
|------|---------|
| 401 | Отсутствует или невалидный токен |
| 403 | `role != teacher` или `is_verified == false` |
| 409 | Concept с таким именем уже существует в курсе (UNIQUE constraint) |

---

### PUT /concepts/{concept_id}

Обновить concept. Только для **verified teacher**.

**Headers:** `Authorization: Bearer <token>`

**Request:** Все поля опциональны.
```json
{
  "name": "Updated Name",
  "description": "New description",
  "lesson_id": "550e8400-e29b-41d4-a716-446655440000",
  "parent_id": null,
  "order": 1
}
```

**Response `200`:** Объект `Concept`.

**Errors:**
| Code | Причина |
|------|---------|
| 403 | Не verified teacher |
| 404 | Concept не найден |

---

### DELETE /concepts/{concept_id}

Удалить concept. Только для **verified teacher**.

**Headers:** `Authorization: Bearer <token>`

**Response `204`:** No content.

**Errors:**
| Code | Причина |
|------|---------|
| 403 | Не verified teacher |
| 404 | Concept не найден |

---

### POST /concepts/{concept_id}/prerequisites

Добавить prerequisite связь между concepts (в рамках одного курса). Только для **verified teacher**.

**Headers:** `Authorization: Bearer <token>`

**Request:**
```json
{
  "prerequisite_id": "770e8400-e29b-41d4-a716-446655440000"
}
```

**Response `201`:** `{"status": "ok"}`

**Errors:**
| Code | Причина |
|------|---------|
| 403 | Не verified teacher или concepts из разных курсов |
| 404 | Concept или prerequisite не найден |

---

### DELETE /concepts/{concept_id}/prerequisites/{prerequisite_id}

Удалить prerequisite связь. Только для **verified teacher**.

**Headers:** `Authorization: Bearer <token>`

**Response `204`:** No content.

---

### GET /concepts/course/{course_id}

Knowledge graph курса: все concepts с prerequisite связями. Требует JWT.

**Headers:** `Authorization: Bearer <token>`

**Response `200`:**
```json
{
  "course_id": "...",
  "concepts": [
    {
      "id": "...",
      "course_id": "...",
      "lesson_id": null,
      "name": "Variables",
      "description": "...",
      "parent_id": null,
      "order": 0,
      "created_at": "...",
      "prerequisites": []
    },
    {
      "id": "...",
      "course_id": "...",
      "lesson_id": null,
      "name": "Functions",
      "description": "...",
      "parent_id": null,
      "order": 1,
      "created_at": "...",
      "prerequisites": ["<variables-concept-id>"]
    }
  ]
}
```

---

### GET /concepts/mastery/course/{course_id}

Mastery студента по concepts курса. Требует JWT.

**Headers:** `Authorization: Bearer <token>`

**Response `200`:**
```json
{
  "course_id": "...",
  "items": [
    {
      "concept_id": "...",
      "name": "Variables",
      "mastery": 0.75
    }
  ]
}
```

> `mastery` — значение 0.0–1.0. Обновляется автоматически при сдаче квиза (score × 0.3).

---

### POST /streaks/activity

Записать ежедневную активность. Требует JWT (любая роль). При первом вызове создаёт streak. Повторный вызов в тот же день — no-op. Consecutive day — инкремент. Gap >1 дня — сброс до 1.

**Headers:** `Authorization: Bearer <token>`

**Response `200`:**
```json
{
  "current_streak": 3,
  "longest_streak": 7,
  "last_activity_date": "2026-02-26",
  "active_today": true
}
```

**Errors:**
| Code | Причина |
|------|---------|
| 401 | Отсутствует или невалидный токен |

---

### GET /streaks/me

Текущий streak пользователя. Требует JWT. Если streak прерван (last_activity > вчера), `current_streak` возвращается как 0.

**Headers:** `Authorization: Bearer <token>`

**Response `200`:**
```json
{
  "current_streak": 3,
  "longest_streak": 7,
  "last_activity_date": "2026-02-26",
  "active_today": true
}
```

> Если у пользователя нет записи — возвращает `current_streak: 0, longest_streak: 0, last_activity_date: null, active_today: false`.

**Errors:**
| Code | Причина |
|------|---------|
| 401 | Отсутствует или невалидный токен |

---

### Leaderboard

Opt-in рейтинг студентов внутри курса. Студент должен сначала opt-in в курс, чтобы участвовать.

#### `POST /leaderboards/courses/{course_id}/opt-in`

Подписаться на leaderboard курса. Идемпотентно — повторный opt-in сохраняет score.

**Headers:** `Authorization: Bearer <token>`

**Response `200`:**
```json
{
  "course_id": "uuid",
  "opted_in": true,
  "score": 0
}
```

#### `DELETE /leaderboards/courses/{course_id}/opt-in`

Отписаться от leaderboard курса. Score сохраняется.

**Headers:** `Authorization: Bearer <token>`

**Response `200`:**
```json
{
  "course_id": "uuid",
  "opted_in": false,
  "score": 150
}
```

**Errors:**
| Code | Причина |
|------|---------|
| 404 | Запись не найдена (не был opt-in) |

#### `GET /leaderboards/courses/{course_id}`

Получить рейтинг курса (только opted-in пользователи).

**Headers:** `Authorization: Bearer <token>`

**Query:** `limit` (1-100, default 20), `offset` (>=0, default 0)

**Response `200`:**
```json
{
  "course_id": "uuid",
  "entries": [
    { "student_id": "uuid", "score": 200, "rank": 1 },
    { "student_id": "uuid", "score": 150, "rank": 2 }
  ],
  "total": 42
}
```

#### `GET /leaderboards/courses/{course_id}/me`

Получить свою позицию в рейтинге курса.

**Headers:** `Authorization: Bearer <token>`

**Response `200`:**
```json
{
  "course_id": "uuid",
  "score": 150,
  "rank": 3,
  "opted_in": true
}
```

> Если opted_in=false, rank=0 (не участвует в рейтинге, но score сохранён).

**Errors:**
| Code | Причина |
|------|---------|
| 404 | Запись не найдена |

#### `POST /leaderboards/courses/{course_id}/score`

Добавить баллы в leaderboard (для XP system и других сервисов).

**Headers:** `Authorization: Bearer <token>`

**Body:**
```json
{
  "points": 20
}
```

**Response `200`:**
```json
{
  "course_id": "uuid",
  "opted_in": true,
  "score": 170
}
```

**Errors:**
| Code | Причина |
|------|---------|
| 404 | Запись не найдена (не был opt-in) |

---

### POST /discussions/comments

Создать комментарий к уроку (поддерживает ответы на комментарии).

**Headers:** `Authorization: Bearer <token>`

**Request Body:**
```json
{
  "lesson_id": "uuid",
  "course_id": "uuid",
  "content": "Great explanation!",
  "parent_id": "uuid | null"
}
```

**Response (201):**
```json
{
  "id": "uuid",
  "lesson_id": "uuid",
  "course_id": "uuid",
  "user_id": "uuid",
  "content": "Great explanation!",
  "parent_id": null,
  "upvote_count": 0,
  "created_at": "2025-01-01T00:00:00Z",
  "updated_at": "2025-01-01T00:00:00Z"
}
```

**Errors:**
| Code | Причина |
|------|---------|
| 404 | parent_id указан, но комментарий не найден |

---

### GET /discussions/lessons/{lesson_id}/comments

Список комментариев к уроку (пагинация).

**Headers:** `Authorization: Bearer <token>`

**Query:** `?limit=20&offset=0`

**Response (200):**
```json
{
  "comments": [
    {
      "id": "uuid",
      "lesson_id": "uuid",
      "course_id": "uuid",
      "user_id": "uuid",
      "content": "Great explanation!",
      "parent_id": null,
      "upvote_count": 3,
      "created_at": "2025-01-01T00:00:00Z",
      "updated_at": "2025-01-01T00:00:00Z"
    }
  ],
  "total": 42
}
```

---

### PATCH /discussions/comments/{comment_id}

Редактировать свой комментарий.

**Headers:** `Authorization: Bearer <token>`

**Request Body:**
```json
{
  "content": "Updated text"
}
```

**Response (200):** CommentResponse (см. POST)

**Errors:**
| Code | Причина |
|------|---------|
| 403 | Попытка редактировать чужой комментарий |
| 404 | Комментарий не найден |

---

### DELETE /discussions/comments/{comment_id}

Удалить свой комментарий (каскадно удаляет ответы).

**Headers:** `Authorization: Bearer <token>`

**Response:** `204 No Content`

**Errors:**
| Code | Причина |
|------|---------|
| 403 | Попытка удалить чужой комментарий |
| 404 | Комментарий не найден |

---

### POST /discussions/comments/{comment_id}/upvote

Toggle upvote на комментарий. Повторный вызов — снимает upvote.

**Headers:** `Authorization: Bearer <token>`

**Response (200):**
```json
{
  "comment_id": "uuid",
  "upvoted": true,
  "upvote_count": 4
}
```

**Errors:**
| Code | Причина |
|------|---------|
| 404 | Комментарий не найден |

### GET /xp/me

Получить XP-саммари текущего пользователя. Общее количество XP и история событий.

**Headers:** `Authorization: Bearer <token>`

**Query params:** `limit` (int, default 20), `offset` (int, default 0)

**Response (200):**
```json
{
  "total_xp": 75,
  "events": [
    {
      "action": "lesson_complete",
      "points": 10,
      "course_id": "uuid | null",
      "created_at": "2026-02-26T12:00:00+00:00"
    }
  ]
}
```

> XP начисления: `lesson_complete` = 10, `quiz_submit` = 20, `flashcard_review` = 5.

**Errors:**
| Code | Причина |
|------|---------|
| 401 | Отсутствует или невалидный токен |

---

### GET /badges/me

Получить все бейджи текущего пользователя.

**Headers:** `Authorization: Bearer <token>`

**Response (200):**
```json
{
  "badges": [
    {
      "badge_type": "streak_7",
      "description": "Maintain a 7-day streak",
      "unlocked_at": "2026-02-26T12:00:00+00:00"
    }
  ],
  "total": 1
}
```

> Типы бейджей: `first_enrollment`, `streak_7`, `quiz_ace`, `mastery_100`.

**Errors:**
| Code | Причина |
|------|---------|
| 401 | Отсутствует или невалидный токен |

---

## JWT Token Format

```json
{
  "sub": "550e8400-e29b-41d4-a716-446655440000",
  "iat": 1740000000,
  "exp": 1740003600,
  "role": "teacher",
  "is_verified": true,
  "email_verified": true
}
```

| Claim | Тип | Описание |
|-------|-----|----------|
| `sub` | UUID string | User ID |
| `iat` | int | Issued at (unix timestamp) |
| `exp` | int | Expiration (iat + 3600 сек) |
| `role` | string | `"student"`, `"teacher"` или `"admin"` |
| `is_verified` | bool | Верифицирован ли преподаватель |
| `email_verified` | bool | Подтверждён ли email |

- Алгоритм: **HS256**
- Shared secret: `JWT_SECRET` env var (одинаковый для всех сервисов)
- TTL: 1 час (3600 секунд)
- Все 7 сервисов валидируют JWT самостоятельно, без обращения к Identity

---

## Frontend Proxy (Next.js Rewrites)

Фронтенд проксирует запросы к API через Next.js rewrites:

| Frontend path | Backend destination |
|---------------|-------------------|
| `/api/identity/*` | `http://localhost:8001/*` |
| `/api/course/*` | `http://localhost:8002/*` |
| `/api/enrollment/*` | `http://localhost:8003/*` |
| `/api/payment/*` | `http://localhost:8004/*` |
| `/api/notification/*` | `http://localhost:8005/*` |
| `/api/ai/*` | `http://localhost:8006/*` |
| `/api/learning/*` | `http://localhost:8007/*` |

---

## Error Response Format

Все ошибки возвращаются в едином формате:

```json
{
  "detail": "Описание ошибки"
}
```
