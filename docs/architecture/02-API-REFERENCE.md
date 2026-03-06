# 02 — API Reference

> Последнее обновление: 2026-03-06

Все endpoints доступны через api-gateway (port 8000). Auth = `Authorization: Bearer <jwt>`.

---

## Identity Service (port 8001)

### Authentication

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/auth/register` | — | Register (email, password, name, role) → TokenPair |
| POST | `/auth/login` | — | Login (email, password) → TokenPair |
| POST | `/auth/refresh` | — | Refresh (refresh_token) → TokenPair |
| POST | `/auth/logout` | — | Logout (refresh_token) → 204 |
| GET | `/auth/me` | required | Current user → User |
| POST | `/auth/verify-email` | — | Verify email (token) → User |
| POST | `/auth/resend-verification` | required | Resend verification → 204 |
| POST | `/auth/forgot-password` | — | Request reset (email) → 204 |
| POST | `/auth/reset-password` | — | Reset password (token, new_password) → 204 |

### Profiles

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/users/{user_id}/profile` | — | Public profile |
| GET | `/users/{user_id}/stats` | — | User stats (followers, courses) |
| PATCH | `/users/me/visibility` | required | Set profile visibility (is_public) |

### Follows

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/follow/{user_id}` | required | Follow user → 201 |
| DELETE | `/follow/{user_id}` | required | Unfollow → 204 |
| GET | `/followers/me` | required | My followers (paginated) |
| GET | `/following/me` | required | My following (paginated) |
| GET | `/users/{user_id}/followers/count` | — | Follower stats |

### Referrals

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/referral/me` | required | My referral stats |
| POST | `/referral/apply` | required | Apply referral code |
| POST | `/referral/complete` | required | Complete referral (referee_id) |

### Organizations

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/organizations` | required | Create org (name, slug) → 201 |
| GET | `/organizations/me` | required | My organizations |
| GET | `/organizations/{org_id}` | required | Get organization |
| POST | `/organizations/{org_id}/members` | required | Add member (user_id, role) → 201 |
| DELETE | `/organizations/{org_id}/members/{user_id}` | required | Remove member → 204 |
| GET | `/organizations/{org_id}/members` | required | List members (paginated) |

### Admin

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/admin/teachers/pending` | admin | Pending teacher verifications |
| PATCH | `/admin/users/{user_id}/verify` | admin | Verify teacher |

---

## Course Service (port 8002)

### Courses

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/courses` | — | List courses (q, category_id, level, is_free, sort_by, limit, offset, cursor) |
| GET | `/courses/my` | required | My courses (teacher) |
| POST | `/courses` | teacher | Create course → 201 |
| GET | `/courses/{course_id}` | — | Get course |
| GET | `/courses/{course_id}/curriculum` | — | Full curriculum (modules + lessons) |
| PUT | `/courses/{course_id}` | teacher | Update course |

### Modules

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/courses/{course_id}/modules` | teacher | Create module → 201 |
| PUT | `/modules/{module_id}` | teacher | Update module |
| DELETE | `/modules/{module_id}` | teacher | Delete module → 204 |

### Lessons

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/modules/{module_id}/lessons` | teacher | Create lesson → 201 |
| GET | `/lessons/{lesson_id}` | — | Get lesson |
| PUT | `/lessons/{lesson_id}` | teacher | Update lesson |
| DELETE | `/lessons/{lesson_id}` | teacher | Delete lesson → 204 |

### Reviews

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/reviews` | required | Create review (course_id, rating, comment) → 201 |
| GET | `/reviews/course/{course_id}` | — | Course reviews (paginated) |

### Bundles

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/bundles` | teacher | Create bundle → 201 |
| GET | `/bundles` | — | List bundles (teacher_id filter) |
| GET | `/bundles/{bundle_id}` | — | Get bundle |
| PUT | `/bundles/{bundle_id}` | teacher | Update bundle |
| DELETE | `/bundles/{bundle_id}` | teacher | Delete bundle → 204 |

### Promotions

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/courses/{course_id}/promotions` | teacher | Create promotion → 201 |
| GET | `/courses/{course_id}/promotions` | — | List promotions |
| DELETE | `/promotions/{promotion_id}` | teacher | Delete promotion → 204 |

### Wishlist

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/wishlist` | required | Add to wishlist → 201 |
| DELETE | `/wishlist/{course_id}` | required | Remove → 204 |
| GET | `/wishlist/me` | required | My wishlist (paginated) |
| GET | `/wishlist/check/{course_id}` | required | Check if wishlisted |

### Categories & Analytics

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/categories` | — | All categories |
| GET | `/analytics/teacher` | teacher | Teacher analytics summary |

---

## Enrollment Service (port 8003)

### Enrollments

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/enrollments` | required | Enroll (course_id, payment_id, total_lessons) → 201 |
| GET | `/enrollments/me` | required | My enrollments (paginated) |
| GET | `/enrollments/course/{course_id}/count` | — | Enrollment count |

### Progress

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/progress/lessons/{lesson_id}/complete` | required | Complete lesson → 201 |
| GET | `/progress/courses/{course_id}` | required | Course progress |
| GET | `/progress/courses/{course_id}/lessons` | required | Completed lesson IDs |

### Recommendations

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/recommendations/courses/{course_id}` | — | Related courses (limit=5) |
| GET | `/recommendations/me` | required | Personal recommendations (limit=10) |

---

## Payment Service (port 8004)

### Payments

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/payments` | required | Create payment (course_id, amount, coupon_code) → 201 |
| GET | `/payments/me` | required | My payments (paginated) |
| GET | `/payments/{payment_id}` | required | Get payment |
| GET | `/payments/{payment_id}/invoice` | required | Download invoice (PDF) |

### Coupons

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/coupons` | teacher | Create coupon → 201 |
| GET | `/coupons` | teacher | List coupons (paginated) |
| POST | `/coupons/validate` | required | Validate coupon (code, course_id, amount) |
| PATCH | `/coupons/{coupon_id}/deactivate` | teacher | Deactivate → 204 |

### Earnings

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/earnings/me/summary` | teacher | Earnings summary |
| GET | `/earnings/me` | teacher | Earnings history (paginated) |
| POST | `/earnings/payouts` | teacher | Request payout → 201 |
| GET | `/earnings/payouts` | teacher | Payout history (paginated) |

### Refunds

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/refunds` | required | Request refund (payment_id, reason) → 201 |
| GET | `/refunds/me` | required | My refunds (paginated) |
| GET | `/refunds` | admin | All refunds (status filter) |
| PATCH | `/refunds/{refund_id}/approve` | admin | Approve refund |
| PATCH | `/refunds/{refund_id}/reject` | admin | Reject refund (reason) |

### Gifts

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/gifts` | required | Send gift (course_id, recipient_email, message) → 201 |
| GET | `/gifts/me/sent` | required | My sent gifts (paginated) |
| POST | `/gifts/redeem` | required | Redeem gift (gift_code) |
| GET | `/gifts/{gift_code}/info` | — | Gift info |

### Organization Subscriptions

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/org-subscriptions` | required | Create org subscription (plan_tier, payment_method_id) → 201 |
| GET | `/org-subscriptions/{org_id}` | required | Get subscription |
| POST | `/org-subscriptions/{org_id}/cancel` | required | Cancel subscription |
| POST | `/webhooks/stripe-org` | — | Stripe webhook handler |

---

## Notification Service (port 8005)

### Notifications

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/notifications` | required | Create notification → 201 |
| GET | `/notifications/me` | required | My notifications (paginated) |
| PATCH | `/notifications/{notification_id}/read` | required | Mark as read |

### Reminders

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/notifications/streak-reminders/send` | admin | Send streak reminders (user_ids) |
| POST | `/notifications/flashcard-reminders/send` | admin | Send flashcard reminders (items) |
| POST | `/notifications/flashcard-reminders/smart` | admin | Smart flashcard reminders |

### Messaging

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/messages` | required | Send message (recipient_id, content) → 201 |
| GET | `/conversations/me` | required | My conversations (paginated) |
| GET | `/conversations/{conversation_id}/messages` | required | Conversation messages (paginated) |
| PATCH | `/messages/{message_id}/read` | required | Mark message read → 204 |

---

## AI Service (port 8006)

### Credits

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/ai/credits/me` | required | Credit balance and tier |

### Generation

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/ai/quiz/generate` | required | Generate quiz (lesson_id, content) |
| POST | `/ai/summary/generate` | required | Generate summary (lesson_id, content) |
| POST | `/ai/course/outline` | teacher | Generate course outline (topic, level) |
| POST | `/ai/lesson/generate` | teacher | Generate lesson content (topic, level) |
| POST | `/ai/study-plan` | required | Generate study plan (course_id, learning_style) |
| POST | `/ai/tutor/chat` | required | Tutor chat (lesson_id, message, session_id) |
| POST | `/ai/tutor/feedback` | required | Rate tutor session |
| POST | `/ai/content/moderate` | required | Moderate content |

### Coach (Tri-Agent)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/ai/coach/start` | required | Start coach session (mission_id, personality) |
| POST | `/ai/coach/chat` | required | Send message (session_id, message) |
| POST | `/ai/coach/end` | required | End session (session_id) → summary |
| GET | `/ai/coach/stream/{session_id}?message=` | required | Stream coach reply as SSE tokens (text/event-stream) |

### Missions

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/ai/mission/daily` | required | Get daily mission (org_id) |
| POST | `/ai/mission/complete` | required | Complete mission (session_id, org_id, concept_id) |

### Unified Search

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/ai/search/unified` | required | Query router: internal RAG + external Gemini |

### LLM Config

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/ai/config/llm/{org_id}` | admin | Get org LLM config |
| PUT | `/ai/config/llm/{org_id}` | admin | Update org LLM config |
| POST | `/ai/config/llm/{org_id}/test` | admin | Test LLM connection |

---

## Learning Service (port 8007)

### Quizzes

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/quizzes` | teacher | Create quiz (lesson_id, questions) → 201 |
| GET | `/quizzes/lesson/{lesson_id}` | required | Get quiz for lesson |
| POST | `/quizzes/{quiz_id}/submit` | required | Submit answers |
| GET | `/quizzes/{quiz_id}/attempts/me` | required | My attempts |

### Flashcards (FSRS)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/flashcards` | required | Create flashcard → 201 |
| GET | `/flashcards/due` | required | Due cards (paginated) |
| POST | `/flashcards/{card_id}/review` | required | Review card (rating) |
| DELETE | `/flashcards/{card_id}` | required | Delete card → 204 |

### Concepts (Knowledge Graph)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/concepts` | teacher | Create concept → 201 |
| PUT | `/concepts/{concept_id}` | teacher | Update concept |
| DELETE | `/concepts/{concept_id}` | teacher | Delete concept → 204 |
| POST | `/concepts/{concept_id}/prerequisites` | teacher | Add prerequisite → 201 |
| DELETE | `/concepts/{concept_id}/prerequisites/{prerequisite_id}` | teacher | Remove prerequisite → 204 |
| GET | `/concepts/course/{course_id}` | required | Course knowledge graph |
| GET | `/concepts/mastery/course/{course_id}` | required | Mastery data per concept |

### Missions

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/missions/today` | required | Today's mission |
| POST | `/missions/{mission_id}/start` | required | Start mission |
| POST | `/missions/{mission_id}/complete` | required | Complete mission |
| GET | `/missions/me` | required | My missions |
| GET | `/missions/streak` | required | Mission streak |

### Streaks

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/streaks/activity` | required | Record activity |
| GET | `/streaks/me` | required | My streak |
| GET | `/streaks/at-risk` | admin | At-risk users |

### Leaderboard

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/leaderboard/courses/{course_id}/opt-in` | required | Opt in |
| DELETE | `/leaderboard/courses/{course_id}/opt-in` | required | Opt out |
| GET | `/leaderboard/courses/{course_id}` | required | Rankings (limit=100) |
| GET | `/leaderboard/courses/{course_id}/me` | required | My rank |
| POST | `/leaderboard/courses/{course_id}/score` | required | Update score |

### Discussions

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/discussions/comments` | required | Create comment → 201 |
| GET | `/discussions/lessons/{lesson_id}/comments` | required | Threaded comments |
| PATCH | `/discussions/comments/{comment_id}` | required | Edit comment |
| DELETE | `/discussions/comments/{comment_id}` | required | Delete comment → 204 |
| POST | `/discussions/comments/{comment_id}/upvote` | required | Upvote |
| POST | `/discussions/comments/{comment_id}/flag` | required | Flag |
| PATCH | `/discussions/comments/{comment_id}/pin` | teacher | Pin comment |
| PATCH | `/discussions/comments/{comment_id}/unpin` | teacher | Unpin comment |

### Study Groups

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/study-groups` | required | Create group → 201 |
| GET | `/study-groups/course/{course_id}` | required | Course groups |
| POST | `/study-groups/{group_id}/join` | required | Join → 201 |
| DELETE | `/study-groups/{group_id}/leave` | required | Leave → 204 |
| GET | `/study-groups/{group_id}/members` | required | Group members |
| GET | `/study-groups/me` | required | My groups |

### Other

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/xp/me` | required | XP summary |
| GET | `/badges/me` | required | My badges |
| POST | `/certificates/issue` | admin | Issue certificate → 201 |
| GET | `/certificates/me` | required | My certificates |
| GET | `/certificates/{certificate_id}` | required | Get certificate |
| POST | `/pretests/course/{course_id}/start` | required | Start pretest → 201 |
| POST | `/pretests/{pretest_id}/answer` | required | Answer question |
| GET | `/pretests/course/{course_id}/results` | required | Pretest results |
| GET | `/trust-level/me` | required | My trust level |
| GET | `/trust-level/org/{org_id}` | required | Org trust levels |
| GET | `/velocity/me` | required | Learning velocity |
| GET | `/activity/me` | required | My activity feed |
| GET | `/activity/feed` | required | Global activity feed |
| GET | `/daily/me` | required | Daily summary |

---

## RAG Service (port 8008)

### Documents

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/documents` | required | Ingest document (content, source_type, source_path, metadata) → 201 |
| GET | `/documents` | required | List documents (org_id) |
| DELETE | `/documents/{document_id}` | required | Delete document → 204 |

### GitHub Adapter

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/sources/github` | required | Ingest from GitHub (repo_url, file_pattern, org_id) |

### Search

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/search` | required | Semantic search (query, org_id, limit) |

### Knowledge Base

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/kb/{org_id}/stats` | required | KB stats (documents, chunks, concepts) |
| GET | `/kb/{org_id}/sources` | required | KB sources |
| GET | `/kb/{org_id}/concepts` | required | KB concepts |
| POST | `/kb/{org_id}/search` | required | Semantic search within org |
| POST | `/kb/{org_id}/refresh/{document_id}` | required | Refresh document |

### Concept Extraction

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/concepts` | required | List concepts (org_id) |
| POST | `/concepts/extract/{document_id}` | required | Extract concepts (async) → 202 |

---

## Search Service (Rust, port 9000)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/health/live` | — | Health check |
| POST | `/index` | — | Index document (doc_id, org_id, text, metadata) |
| POST | `/index/batch` | — | Batch index documents |
| POST | `/search` | — | Full-text search (query, org_id, limit) |
| DELETE | `/index/{org_id}` | — | Delete org index |

---

## API Gateway (Rust, port 8000)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/health/live` | — | Liveness probe |
| GET | `/health/ready` | — | Readiness probe |

Route prefix → upstream mapping:

```
/auth, /me, /users, /organizations, /follow, /referral  →  identity:8001
/courses, /modules, /lessons, /reviews, /bundles,
  /promotions, /wishlist, /categories, /analytics        →  course:8002
/enrollments, /progress, /recommendations                →  enrollment:8003
/payments, /coupons, /earnings, /refunds, /gifts,
  /org-subscriptions, /webhooks/stripe-org               →  payment:8004
/notifications, /conversations, /messages,
  /streak-reminders, /flashcard-reminders                →  notification:8005
/ai                                                      →  ai:8006
/quizzes, /flashcards, /concepts, /missions,
  /streaks, /leaderboard, /discussions, /study-groups,
  /xp, /badges, /certificates, /pretests, /trust-level,
  /velocity, /activity, /daily                           →  learning:8007
/documents, /search, /kb, /sources, /concepts            →  rag:8008
```
