# Phase 2 — Learning Intelligence [COMPLETED, pre-pivot]

> **Эра:** B2C Course Marketplace (до пивота на B2B Agentic Onboarding)
>
> **Статус:** ✅ ЗАВЕРШЕНА. AI и Learning компоненты переиспользуются в B2B Tri-Agent System.
>
> **Цель:** превратить платформу в AI-powered learning engine с active recall, spaced repetition, knowledge graph и gamification.

---

## Построенные сервисы

### AI Service (:8006) — переиспользуется

- ✅ Gemini 2.0 Flash Lite через httpx
- ✅ Model router: task type → model tier
- ✅ Redis response cache + conversation memory
- ✅ Quiz generation (POST /ai/quiz/generate)
- ✅ Summary generation (POST /ai/summary/generate)
- ✅ Socratic AI tutor (POST /ai/tutor/chat, POST /ai/tutor/feedback)
- ✅ Course outline generation (POST /ai/course/outline) — teacher/admin
- ✅ Lesson content generation (POST /ai/lesson/generate) — teacher/admin
- ✅ Personalized study plans (POST /ai/study-plan)
- ✅ Content moderation (POST /ai/moderate) — teacher/admin
- ✅ Plan-based credit system (free: 10/day, student: 100/day, pro: unlimited)
- ✅ 116 тестов

**Переиспользование в B2B:** AI Service становится основой для Coach Agent (Socratic tutor), Designer Agent (content generation) и Strategist Agent (study plans). Credit system адаптируется под B2B тарификацию.

### Learning Engine (:8007) — переиспользуется

- ✅ Quizzes: CRUD, submit, scoring (4 endpoints)
- ✅ FSRS Flashcards: spaced repetition, review scheduling (4 endpoints)
- ✅ Knowledge Graph: concepts, edges, mastery tracking (7 endpoints)
- ✅ Streaks: daily activity counter (2 endpoints)
- ✅ Leaderboard: per-course, opt-in (5 endpoints)
- ✅ Discussions: threaded, pinning, teacher answers (8 endpoints)
- ✅ XP system: lesson +10, quiz +20, flashcard +5 (1 endpoint)
- ✅ Badges: first_enrollment, streak_7, quiz_ace, mastery_100 (1 endpoint)
- ✅ Adaptive pre-test: concept-based difficulty (3 endpoints)
- ✅ Learning velocity tracking (1 endpoint)
- ✅ Activity feed (2 endpoints)
- ✅ Study groups (6 endpoints)
- ✅ 175 тестов, 44 endpoints

**Переиспользование в B2B:** Knowledge graph → company tech stack mapping. FSRS → spaced review missions. XP/Badges/Streaks → Trust Level progression. Quizzes → mission assessment.

### Notification Service (:8005) — переиспользуется

- ✅ In-app notifications, email via Resend API
- ✅ Streak-at-risk reminders, flashcard-due reminders
- ✅ Smart FSRS-based reminders via Learning Service
- ✅ Direct messaging (conversations, messages)
- ✅ 57 тестов

---

## DB Schemas (learning-db :5438)

Таблицы quizzes, questions, quiz_attempts, flashcards, review_logs, concepts, concept_edges, concept_mastery, streaks, leaderboard_entries, discussions, xp_events, badges, user_badges, pretests, pretest_answers, activity_events, study_groups, study_group_members.

---

## Метрики при завершении

- 2 новых сервиса (AI + Learning), 1 обновлен (Notification)
- 734 тестов по 7 сервисам
- 95+ endpoints
- AI cost < $0.05/user/мес

---

## Примечание

Phase 2 дала AI и Learning инфраструктуру, которая является ядром B2B Agentic Onboarding. Tri-Agent System (Sprint 18) строится поверх AI Service. Mission Engine (Sprint 19) строится поверх Learning Engine.
