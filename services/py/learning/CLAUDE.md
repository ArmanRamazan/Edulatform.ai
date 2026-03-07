# Learning Service

Port 8007 | DB port 5438 | Package: learning | 272 tests (largest service)

## Domain

55+ endpoints across 16 route modules. The core learning engine.

## Services & Repos (16 pairs)

QuizService, FlashcardService, ConceptService, StreakService,
LeaderboardService, DiscussionService, XpService, BadgeService,
PretestService, VelocityService, ActivityService, StudyGroupService,
CertificateService, TrustLevelService, MissionService, DailyService

Plus ReviewGenerator (used by MissionService for flashcard reviews).

## Routes

quizzes, flashcards, concepts, streaks, leaderboard, discussions,
xp, badges, pretests, velocity, activity, study_groups,
certificates, internal_certificates, trust_levels, missions, daily_routes

## Migrations

001_quizzes through 015_missions (15 migration files)

## Key patterns

- FSRS algorithm: scheduling flashcard reviews in FlashcardService
- Concepts: knowledge graph nodes, linked to courses/lessons
- ActivityService: injected into many services for activity feed tracking
- MissionService: calls AI service (8006) via httpx for mission generation
- DailyService: aggregates missions + trust + flashcards + streaks
- Internal certificates route: service-to-service endpoint (no user auth)
- Largest test suite — always run full suite before committing

## Test command

```bash
cd services/py/learning && uv run --package learning pytest tests/ -v
```
