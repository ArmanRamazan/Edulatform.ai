# Identity Service

Port 8001 | DB port 5433 | Package: identity | 156 tests

## Domain

Auth (register/login), profiles, follows, referrals, organizations (multi-tenant).

## Services & Repos

- AuthService (UserRepo, TokenRepo, VerificationRepo, PasswordResetRepo)
- ProfileService (UserRepo)
- FollowService (FollowRepo, UserRepo)
- ReferralService (ReferralRepo, UserRepo)
- OrganizationService (OrganizationRepo)

## Routes

auth, admin, referrals, profiles, follows, organization_routes

## Migrations

001_users through 010_organizations (10 migration files)

## Key patterns

- JWT: `create_access_token()` with `extra_claims` (role, is_verified, organization_id)
- Password hashing: `bcrypt` directly (NOT passlib — incompatible with bcrypt>=4.1)
- Redis: used for rate limiting and caching
- Global service instances via lifespan + getter functions
- UNIQUE violations caught in repos via `asyncpg.UniqueViolationError` -> `ConflictError`

## Test command

```bash
cd services/py/identity && uv run --package identity pytest tests/ -v
```

## Security-critical

- JWT token generation/validation — verify claims carefully
- Password handling — bcrypt only, never plaintext
- Organization isolation — users only see their org's data
- Email verification and password reset flows
