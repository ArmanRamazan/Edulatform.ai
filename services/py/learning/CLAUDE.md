# Learning Service

Port 8007 | DB port 5438 | Package: learning | 277 tests

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
- MissionService: fetches mastery locally → POSTs to AI with mastery in body (push model)
  Avoids circular HTTP dependency (Learning → AI → Learning)
- MissionService applies mastery_delta locally after mission completion via ConceptService
- ConceptService.apply_mastery_delta — delta applied per concept after AI coach session
- DailyService: aggregates missions + trust + flashcards + streaks
- Internal certificates route: service-to-service endpoint (no user auth)

## Test command

```bash
cd services/py/learning && uv run --package learning pytest tests/ -v
```
