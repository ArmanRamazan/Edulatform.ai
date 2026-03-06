# 04 — Authentication & Authorization

> Последнее обновление: 2026-03-06

## JWT Token Structure

```json
{
  "sub": "550e8400-e29b-41d4-a716-446655440000",
  "iat": 1709712000,
  "exp": 1709715600,
  "role": "student",
  "is_verified": true,
  "email_verified": true,
  "organization_id": "660e8400-e29b-41d4-a716-446655440000",
  "subscription_tier": "pro"
}
```

| Claim | Type | Description |
|-------|------|-------------|
| `sub` | UUID | User ID |
| `role` | string | `student` / `teacher` / `admin` |
| `is_verified` | bool | Admin-verified (for teachers) |
| `email_verified` | bool | Email confirmed |
| `organization_id` | UUID? | Active org (B2B, optional) |
| `subscription_tier` | string? | `free` / `student` / `pro` / `enterprise` |

Algorithm: **HS256**. Secret: `JWT_SECRET` env var.

## Token Lifecycle

```
Registration
  → email_verifications record created
  → access_token (1h) + refresh_token (30d) returned
  → refresh_token stored in DB

Login
  → verify password (bcrypt)
  → new access_token + refresh_token
  → old refresh_token NOT invalidated (multiple devices)

Token Refresh
  → validate refresh_token exists in DB and not expired
  → issue new access_token + refresh_token
  → delete old refresh_token from DB (rotation)

Logout
  → delete refresh_token from DB
```

## Authentication Flow

```
Client                   API Gateway              Identity Service
  │                         │                          │
  │  POST /auth/login       │                          │
  │────────────────────────>│                          │
  │                         │  proxy to :8001          │
  │                         │─────────────────────────>│
  │                         │                          │ verify password
  │                         │                          │ create tokens
  │                         │  { access, refresh }     │
  │                         │<─────────────────────────│
  │  { access, refresh }    │                          │
  │<────────────────────────│                          │
  │                         │                          │
  │  GET /courses           │                          │
  │  Authorization: Bearer  │                          │
  │────────────────────────>│                          │
  │                         │ validate JWT             │
  │                         │ extract claims           │
  │                         │ proxy to course:8002     │
  │                         │──────────> Course Service │
  │                         │                          │
```

## Role-Based Access

### student (default)
- Register, login, manage profile
- Enroll in courses, track progress
- Take quizzes, use flashcards, earn XP/badges
- Complete missions, participate in discussions
- Join study groups, view leaderboard
- Use AI tutor and coach

### teacher (requires admin verification)
- All student permissions
- Create/edit courses, modules, lessons
- Create bundles, promotions, coupons
- View teacher analytics, earnings
- Pin/unpin discussion comments
- Generate AI course outlines and lessons

### admin
- All teacher permissions
- Verify/unverify teachers
- Manage refunds (approve/reject)
- Send bulk reminders (streak, flashcard)
- Issue certificates
- Configure LLM settings per org
- View all users, all refunds

## B2B Multi-Tenancy

### Organization Model

```
Organization
  ├── owner (user who created)
  ├── admins (manage members)
  └── members (learn within org)
```

### Data Isolation

- `organization_id` in JWT extra_claims when user selects active org
- Services filter queries by `organization_id` where applicable:
  - **learning**: missions, trust levels scoped to org
  - **rag**: documents, chunks, concepts scoped to org
  - **ai**: unified search filters by org, LLM config per org
  - **payment**: org subscriptions per organization

### Org Subscription Tiers

| Tier | Max Seats | Features |
|------|-----------|----------|
| pilot | 5 | Basic KB, 10 missions/day |
| starter | 25 | Full KB, unlimited missions |
| growth | 100 | Custom LLM config, analytics |
| enterprise | unlimited | Dedicated support, SLA |

## Password Security

- Hashing: **bcrypt** (cost factor 12)
- No password stored in plain text
- Password reset via time-limited token (email)
- No `passlib` — direct `bcrypt` library usage

## Email Verification

1. On registration → `email_verifications` record with UUID token
2. Verification link sent via email
3. `POST /auth/verify-email` with token → sets `email_verified = true`
4. Resend available via `POST /auth/resend-verification`

## Security Headers

- API gateway sets CORS headers based on `ALLOWED_ORIGINS` env
- All SQL queries use parameterized statements (`$1, $2, ...`)
- PII masked in structured logs
- No secrets in code or config files — env vars only
