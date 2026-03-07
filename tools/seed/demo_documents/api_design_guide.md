# API Design Guide: Building Developer-Friendly APIs

## Introduction

An API is a contract between your system and its consumers. A well-designed API is intuitive, consistent, and stable — it makes the right thing easy and the wrong thing hard. A poorly designed API is a source of confusion, bugs, and frustration that haunts engineers for years. This guide covers the principles and conventions that produce APIs that developers love to use.

## REST Conventions

REST (Representational State Transfer) is an architectural style, not a protocol. The term is often misused. A truly RESTful API uses HTTP semantics correctly and models resources rather than remote procedure calls.

**Resources, not actions**: URIs identify resources, not operations. The HTTP method conveys the operation.

```
# Wrong: action in URI
POST /api/createUser
POST /api/deleteUser?id=123
GET  /api/getUserOrders?userId=456

# Correct: resource-oriented
POST   /api/users
DELETE /api/users/123
GET    /api/users/456/orders
```

**HTTP methods and their semantics**:
- `GET`: Retrieve a resource or collection. Must be safe (no side effects) and idempotent.
- `POST`: Create a resource or trigger an action. Not idempotent.
- `PUT`: Replace a resource entirely. Idempotent.
- `PATCH`: Partially update a resource. Should be idempotent.
- `DELETE`: Remove a resource. Idempotent.

**Naming conventions**: Use lowercase, hyphen-separated plural nouns for collections (`/users`, `/order-items`). Use IDs for specific resources (`/users/123`). Use nested paths for owned sub-resources (`/users/123/addresses`).

Avoid deep nesting beyond two levels. `/orgs/1/teams/2/members` is acceptable. `/orgs/1/teams/2/members/3/permissions/4` is a design smell — consider exposing permissions as a top-level resource.

## Versioning

APIs change. A versioning strategy is how you manage change without breaking existing consumers.

**URL versioning** is the most common and explicit approach: `/api/v1/users`, `/api/v2/users`. The version is visible in every request. Easy to route to different implementations. The downside: clients must update URLs when upgrading.

**Header versioning** uses an `Accept` or custom header: `Accept: application/vnd.myapi.v2+json`. Cleaner URLs, but the version is less visible and harder to test in browsers.

Whichever strategy you choose, apply it consistently. Document the deprecation policy clearly: which version is current, which is deprecated, when deprecated versions will be removed. Support at least one previous major version.

Semantic versioning applies to APIs: major version bumps (v1 → v2) are for breaking changes. Minor changes (new optional fields, new endpoints) should not require a version bump if they are additive and backward compatible.

## Pagination

Never return unbounded collections. Always paginate list endpoints.

**Cursor-based pagination** is the best approach for large, frequently-updated collections. A cursor encodes the position in the result set (typically an opaque base64-encoded value derived from a sort column):

```json
GET /api/users?limit=20&cursor=eyJpZCI6IjEwMCJ9

{
  "data": [...],
  "pagination": {
    "next_cursor": "eyJpZCI6IjEyMCJ9",
    "has_more": true
  }
}
```

Cursor pagination is stable — inserting or deleting records between pages does not cause items to be skipped or duplicated.

**Offset pagination** (`?page=2&per_page=20`) is simpler to implement and supports jumping to arbitrary pages, but becomes unreliable on live data because insertions shift offsets.

Always include `has_more` (or `next_cursor` being null as the sentinel). Clients should not have to guess whether there is another page.

Return consistent page sizes. Document the maximum allowed `limit`. Return 400 if the requested limit exceeds the maximum.

## Error Formats

A consistent error format makes APIs predictable. Clients should not need to handle a different error shape for every endpoint.

A good error response includes a machine-readable code, a human-readable message, and optional detail for debugging:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Request validation failed",
    "details": [
      {
        "field": "email",
        "message": "must be a valid email address"
      },
      {
        "field": "age",
        "message": "must be at least 18"
      }
    ]
  }
}
```

Map HTTP status codes correctly:
- `400 Bad Request`: The client sent invalid data.
- `401 Unauthorized`: Authentication is required or failed.
- `403 Forbidden`: Authenticated but not authorized for this action.
- `404 Not Found`: The resource does not exist.
- `409 Conflict`: The request conflicts with existing state (duplicate, version mismatch).
- `422 Unprocessable Entity`: Syntactically valid but semantically incorrect (business rule violation).
- `429 Too Many Requests`: Rate limit exceeded.
- `500 Internal Server Error`: Unexpected server failure (never expose stack traces to clients).

Use `code` strings (not just status codes) so clients can distinguish between different 400-class errors programmatically.

## Authentication

Authentication verifies identity. Authorization verifies permission. Design your API to make both explicit and auditable.

**JWT (JSON Web Tokens)** are the standard for stateless authentication in APIs. A JWT contains claims (user ID, role, expiry) signed by the server. The client includes it in every request via the `Authorization: Bearer <token>` header.

Design JWTs to contain the minimum required claims. Avoid including sensitive data — JWTs are base64-encoded, not encrypted. Include `sub` (subject/user ID), `exp` (expiry), `iat` (issued at), and any role or permission claims needed to authorize requests without a database lookup.

Short expiry times (15 minutes to 1 hour) for access tokens with longer-lived refresh tokens (7-30 days) is the standard pattern. Refresh tokens are single-use and invalidated after each use (rotation).

**API keys** are appropriate for server-to-server communication. Generate cryptographically random keys (at least 256 bits). Store only the hash (bcrypt or SHA-256). Include a prefix for easy identification in logs: `sk_live_...` for production, `sk_test_...` for test.

## Idempotency

An idempotent operation produces the same result whether applied once or multiple times. Idempotency is critical for APIs that process payments, send notifications, or perform any action with real-world side effects.

Implement idempotency via idempotency keys. The client generates a unique key (UUID) and includes it in the request header:

```http
POST /api/payments
Idempotency-Key: 550e8400-e29b-41d4-a716-446655440000
```

The server stores the result of the first request keyed by the idempotency key. On retry, it returns the stored result without re-executing the operation. Use Redis with a short TTL (24 hours) for the idempotency store.

```python
async def process_payment(idempotency_key: str, request: PaymentRequest) -> PaymentResult:
    cached = await redis.get(f"idem:{idempotency_key}")
    if cached:
        return PaymentResult.parse_raw(cached)

    result = await payment_gateway.charge(request)
    await redis.setex(f"idem:{idempotency_key}", 86400, result.json())
    return result
```

Communicate idempotency semantics in your documentation. Tell clients which endpoints support idempotency keys and which are naturally idempotent (GET, PUT, DELETE).

## Rate Limiting for APIs

Rate limiting protects your API from abuse and ensures fair usage. Communicate limits clearly.

Include rate limit information in response headers:

```http
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 982
X-RateLimit-Reset: 1640995200
Retry-After: 60
```

Different endpoints may have different limits. Authentication endpoints should be tightly rate-limited (5-10 requests per minute per IP) to prevent credential stuffing. Read endpoints can be more generous. Write endpoints sit in between.

Provide per-user, per-organization, and per-IP limits. Enterprise customers may have elevated limits. Communicate limit tiers in your developer documentation.

## Documentation and OpenAPI

An undocumented API is an unusable API. Documentation is not optional — it is part of the API contract.

Use OpenAPI (formerly Swagger) to describe your API. It is machine-readable and can be used to generate SDKs, interactive documentation (Swagger UI, Redoc), and mock servers.

In FastAPI, OpenAPI schemas are generated automatically from Pydantic models and route signatures. Annotate thoroughly:

```python
@router.post(
    "/users",
    response_model=UserResponse,
    status_code=201,
    summary="Create a user",
    description="Create a new user account. Returns the created user with its assigned ID.",
    responses={
        409: {"description": "Email already registered"},
        422: {"description": "Validation error"},
    },
)
async def create_user(body: CreateUserRequest) -> UserResponse:
    ...
```

Include examples in your Pydantic models:

```python
class CreateUserRequest(BaseModel):
    email: str = Field(..., example="alice@example.com")
    name: str = Field(..., example="Alice Smith", min_length=2, max_length=100)
    password: str = Field(..., min_length=8, example="secretpassword")
```

Maintain a changelog. Every breaking change must be documented with a migration guide. Every new feature must be documented before or at release, never after.
