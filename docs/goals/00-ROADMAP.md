# KnowledgeOS — Roadmap

> B2B AI-powered knowledge platform для онбординга инженеров.

## Completed Phases

### Phase 0 — Foundation
- 5 core сервисов (identity, course, enrollment, payment, notification)
- Clean Architecture, JWT auth, Docker infra
- 621 тест

### Phase 1 — Launch Optimization
- Bundles, promotions, wishlist, coupons, refunds, gifts
- Teacher earnings, direct messaging, referrals
- Seller app (teacher dashboard)
- ~400 доп. тестов

### Phase 2 — Learning Intelligence
- AI service (Gemini Flash): quiz/summary/outline generation, tutor chat
- Learning service: flashcards FSRS, knowledge graph, gamification (XP, badges, streaks, leaderboard)
- Discussions, study groups, pretests, velocity, certificates
- 529 доп. тестов

### Phase 3 — B2B Growth
- Organizations, multi-tenancy, org subscriptions (Stripe)
- RAG service: pgvector, GitHub adapter, concept extraction
- Tri-agent coaching (Strategist → Designer → Coach), missions
- Unified search, per-org LLM config, trust levels
- Search service (Rust/tantivy), rag-chunker (Rust/PyO3)
- Buyer app: Dark Knowledge theme, dashboard, concept hub, smart search
- ~330 доп. тестов

**Итого: 10 сервисов, 1343 теста, 2 frontend apps.**

## Next — Phase 4: Scale & Enterprise (not started)

- Multi-region (K8s), ClickHouse analytics
- WebSocket real-time, OAuth/Social login
- MCP Server, video transcoding
- Custom ML models
