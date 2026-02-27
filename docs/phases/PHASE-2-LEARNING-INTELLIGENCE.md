# Phase 2 — Learning Intelligence (10K → 100K MAU)

> **Цель:** превратить "видеокурсник" в платформу ускоренного обучения.
> Каждая фаза добавляет один evidence-based механизм повышения retention и completion.
>
> **Baseline (индустрия):** 13% completion rate, пассивное видео.
> **Target:** 40%+ completion, 60%+ 7-day retention.
>
> **Предусловие:** Phase 0–1 завершены — полный цикл обучения, 190 тестов (7 сервисов), 157 RPS.

---

## Бизнес-цели Phase 2

| Метрика | Целевое значение |
|---------|-----------------|
| MAU | 100 000 |
| Course completion rate | **40%+** (vs 13% baseline) |
| 7-day retention | **60%+** |
| DAU/MAU stickiness | **25%+** |
| Avg quiz score | 70%+ |
| Streak > 7 days | 30% of active users |
| AI cost per user | < $0.05/мес |

---

## Новые сервисы

| Сервис | Порт | Назначение | БД |
|--------|------|-----------|-----|
| AI Service | :8006 | LLM routing, quiz gen, summaries, tutor | Redis (stateless, no DB) |
| Learning Engine | :8007 | FSRS, quizzes, flashcards, concepts, gamification | learning-db (5438) |

---

## Milestone 2.0 — AI Service + Quiz Foundation

> От пассивного видео к активному обучению. Quiz после каждого урока.
> **Evidence:** Active recall → +25% retention.

| # | Задача | Статус |
|---|--------|--------|
| **Backend: AI Service** | | |
| 2.0.1 | Scaffold AI Service (FastAPI, Clean Architecture) | ✅ |
| 2.0.2 | Model router: task type → model tier (cheap/mid/expensive) | ✅ |
| 2.0.3 | Gemini Flash API client + error handling + retries | ✅ |
| 2.0.4 | Redis response cache (same lesson → same quiz for all) | ✅ |
| 2.0.5 | POST /ai/quiz/generate {lesson_id, content} → questions | ✅ |
| 2.0.6 | POST /ai/summary/generate {lesson_id, content} → summary | ✅ |
| **Backend: Learning Engine** | | |
| 2.0.7 | Scaffold Learning Engine (FastAPI, Clean Architecture) | ✅ |
| 2.0.8 | Quiz model: Quiz, Question (MCQ), Answer, Attempt | ✅ |
| 2.0.9 | POST /quizzes (create from AI output) | ✅ |
| 2.0.10 | POST /quizzes/:id/submit {answers} → score + feedback | ✅ |
| 2.0.11 | GET /quizzes/lesson/:lesson_id → quiz for this lesson | ✅ |
| **Frontend** | | |
| 2.0.12 | Quiz UI: after-lesson quiz flow (MCQ, submit, score) | ✅ |
| 2.0.13 | Summary block: collapsible summary above lesson content | ✅ |
| 2.0.14 | "Generate quiz" button for teacher (triggers AI) | 🔴 |
| **Infra** | | |
| 2.0.15 | Docker compose: ai-service + learning-engine + DBs | ✅ |
| 2.0.16 | Seed: quizzes for demo courses | 🔴 |
| **Tests** | | |
| 2.0.17 | AI Service tests: router, quiz gen, summary gen, cache | ✅ (21 тестов) |
| 2.0.18 | Learning Engine tests: quiz CRUD, submit, scoring | ✅ (12 тестов) |

**DB Schema (learning-db :5438) — реализовано:**
```sql
CREATE TABLE quizzes (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    lesson_id   UUID NOT NULL UNIQUE,       -- один квиз на урок
    course_id   UUID NOT NULL,
    teacher_id  UUID NOT NULL,              -- кто создал
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE questions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    quiz_id         UUID NOT NULL REFERENCES quizzes(id) ON DELETE CASCADE,
    text            TEXT NOT NULL,
    options         JSONB NOT NULL,          -- ["option A", "option B", ...]
    correct_index   INT NOT NULL,
    explanation     TEXT,
    "order"         INT NOT NULL DEFAULT 0   -- SQL reserved word, quoted
);

CREATE TABLE quiz_attempts (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    quiz_id         UUID NOT NULL REFERENCES quizzes(id),
    student_id      UUID NOT NULL,
    answers         JSONB NOT NULL,          -- [0, 2, 1, ...] selected indexes
    score           FLOAT NOT NULL,          -- 0.0 to 1.0
    completed_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_questions_quiz_id ON questions(quiz_id);
CREATE INDEX idx_quiz_attempts_quiz_student ON quiz_attempts(quiz_id, student_id);
```

---

## Milestone 2.1 — Spaced Repetition + Flashcards

> Долгосрочное запоминание через FSRS-scheduled повторение.
> **Evidence:** Spaced repetition → +60% retention vs massed study.

| # | Задача | Статус |
|---|--------|--------|
| 2.1.1 | FSRS integration (py-fsrs v6.3.0 library) | ✅ |
| 2.1.2 | Flashcard model: Card, ReviewLog + migration | ✅ |
| 2.1.3 | Auto-generate cards from quiz mistakes + key concepts | 🔴 |
| 2.1.4 | POST /flashcards/:id/review {rating} → next_review | ✅ |
| 2.1.5 | GET /flashcards/due → cards due for review today | ✅ |
| 2.1.6 | Smart notifications: "Time to review!" (FSRS-scheduled) | 🔴 |
| 2.1.7 | Frontend: flashcard review page (flip card, rate: Again/Hard/Good/Easy) | ✅ |
| 2.1.8 | "Review due" badge in header | ✅ |
| 2.1.9 | Tests: FSRS scheduling, card CRUD, review flow | ✅ (11 тестов) |

**DB Schema:**
```sql
CREATE TABLE flashcards (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id UUID NOT NULL,
    course_id UUID NOT NULL,
    concept TEXT NOT NULL,           -- front
    answer TEXT NOT NULL,            -- back
    source_type VARCHAR(20),         -- quiz_mistake, key_concept, manual
    source_id UUID,
    -- FSRS state
    stability FLOAT DEFAULT 0,
    difficulty FLOAT DEFAULT 0,
    due TIMESTAMPTZ DEFAULT now(),
    last_review TIMESTAMPTZ,
    reps INT DEFAULT 0,
    lapses INT DEFAULT 0,
    state INT DEFAULT 0,            -- 0=New, 1=Learning, 2=Review, 3=Relearning
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE review_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    card_id UUID REFERENCES flashcards(id),
    rating INT NOT NULL,             -- 1=Again, 2=Hard, 3=Good, 4=Easy
    review_duration_ms INT,
    reviewed_at TIMESTAMPTZ DEFAULT now()
);
```

---

## Milestone 2.2 — Socratic AI Tutor ✅

> Глубокое понимание через диалог. AI не даёт ответ — ведёт к нему вопросами.
> **Evidence:** Socratic method → deeper conceptual understanding (Khanmigo model).

| # | Задача | Статус |
|---|--------|--------|
| 2.2.1 | POST /ai/tutor/chat {lesson_id, message, history} → response | ✅ |
| 2.2.2 | Socratic prompt template (system prompt + lesson context) | ✅ |
| 2.2.3 | Gemini Flash integration for tutor (with model routing) | ✅ |
| 2.2.4 | Conversation memory (session-scoped, Redis) | ✅ |
| 2.2.5 | Rate tutor response (POST /ai/tutor/feedback) | ✅ |
| 2.2.6 | Frontend: chat drawer on lesson page (TutorDrawer) | ✅ |
| 2.2.7 | AI credit tracking per user (10 chats/day, Redis counter) | ✅ |
| 2.2.8 | Tests: tutor prompt, conversation flow, credit tracking | ✅ (9 тестов) |

---

## Milestone 2.3 — Knowledge Graph + Adaptive Path ✅

> Персонализация. Пропускай изученное, фокусируйся на пробелах.
> **Evidence:** Squirrel AI knowledge graph → TIME Best Invention 2025.

| # | Задача | Статус |
|---|--------|--------|
| 2.3.1 | Concept model: knowledge points per course | ✅ |
| 2.3.2 | Concept edges: prerequisite, related, extends | ✅ |
| 2.3.3 | Concept mastery tracking per student (0.0 → 1.0) | ✅ |
| 2.3.4 | Adaptive pre-test: diagnostic → skip known material | ⏭️ YAGNI |
| 2.3.5 | Learning Velocity Dashboard: concepts/hour, trend | ⏭️ YAGNI |
| 2.3.6 | Teacher UI: concept CRUD + prerequisites | ✅ |
| 2.3.7 | Frontend: mastery progress visualization | ✅ |
| 2.3.8 | Quiz submit auto-updates concept mastery (score × 0.3) | ✅ |
| 2.3.9 | Tests: concept CRUD, mastery, quiz integration | ✅ (14 тестов) |

**DB Schema — реализовано:**
```sql
CREATE TABLE concepts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    course_id UUID NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    lesson_id UUID,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE concept_edges (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id UUID REFERENCES concepts(id) ON DELETE CASCADE,
    target_id UUID REFERENCES concepts(id) ON DELETE CASCADE,
    relation VARCHAR(50) NOT NULL,  -- prerequisite, related, extends
    weight FLOAT DEFAULT 1.0
);

CREATE TABLE concept_mastery (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id UUID NOT NULL,
    concept_id UUID REFERENCES concepts(id) ON DELETE CASCADE,
    mastery_level FLOAT DEFAULT 0.0,
    last_reviewed_at TIMESTAMPTZ,
    next_review_at TIMESTAMPTZ,
    review_count INT DEFAULT 0,
    UNIQUE(student_id, concept_id)
);
```

---

## Milestone 2.4 — Gamification + Community

> Мотивация и привычка. Completion rate до 96% с gamification + community.
> **Evidence:** Gamification → +30% completion, community → +30-40% completion.

| # | Задача | Статус |
|---|--------|--------|
| 2.4.1 | XP system: events → points (lesson +10, quiz +20, flashcard +5) | ✅ |
| 2.4.2 | Streaks: daily activity counter (midnight reset) | ✅ |
| 2.4.3 | Badges: first course, 7-day streak, quiz ace, 100% mastery | ✅ |
| 2.4.4 | Leaderboard per course (opt-in) | ✅ |
| 2.4.5 | Course discussions: comments per lesson, upvotes | ✅ |
| 2.4.6 | Frontend: XP counter in header, streak flame, badge shelf | ✅ |
| 2.4.7 | Streak at risk notification (23:00 if no activity) | ✅ |
| 2.4.8 | Tests: XP calculation, streak logic, badge unlock | ✅ (xp: 11, streak: 9, badge: 15 = 35 тестов) |

---

## Milestone 2.5 — MVP Polish + Demo Ready

> Продукт готов к показу пользователям и инвесторам.

| # | Задача | Статус |
|---|--------|--------|
| 2.5.1 | Onboarding: guided first course experience | 🔴 |
| 2.5.2 | Landing page: value proposition, screenshots/demo | 🔴 |
| 2.5.3 | Responsive mobile web | 🔴 |
| 2.5.4 | Update demo script (show AI features in browser) | ✅ |
| 2.5.5 | Seed: courses with quizzes, flashcards, concepts, XP | ✅ |
| 2.5.6 | Bug fixes, UI polish, error states | 🔴 |

---

## Критерии завершения Phase 2

- [ ] AI Service работает: quizzes, summaries, tutor
- [ ] FSRS flashcards с расписанием повторений
- [ ] Knowledge graph visualization для min 3 courses
- [ ] Gamification (XP, streaks, badges) в UI
- [ ] Course completion rate > 40% в тестовой группе
- [ ] 7-day retention > 60%
- [ ] Можно провести live demo для пользователей/инвесторов
- [ ] AI cost < $0.05/user/мес
