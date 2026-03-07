#![allow(clippy::unwrap_used)]

use axum::http::{Method, StatusCode};
use http_body_util::BodyExt;
use jsonwebtoken::{encode, EncodingKey, Header};
use serde::Serialize;
use tower::ServiceExt;

use api_gateway::middleware::rate_limit::{RateConfig, RateLimiter};

// ---- helpers: unauthenticated (IP-only) requests ----

fn test_limiter(max_requests: u32, window_secs: u32) -> RateLimiter {
    RateLimiter::in_memory(RateConfig {
        max_requests,
        window_secs,
    })
}

fn build_request(
    method: Method,
    uri: &str,
    forwarded_for: Option<&str>,
) -> axum::http::Request<axum::body::Body> {
    let mut builder = axum::http::Request::builder().method(method).uri(uri);
    if let Some(ip) = forwarded_for {
        builder = builder.header("X-Forwarded-For", ip);
    }
    builder.body(axum::body::Body::empty()).unwrap()
}

// ---- helpers: authenticated (JWT) requests ----

const TEST_JWT_SECRET: &str = "test-rate-limit-jwt-secret-32chars!!";

#[derive(Serialize)]
struct TestJwtClaims {
    sub: String,
    exp: usize,
    role: String,
    is_verified: bool,
    email_verified: bool,
}

fn make_test_token(user_id: &str) -> String {
    let claims = TestJwtClaims {
        sub: user_id.to_string(),
        exp: (std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap()
            .as_secs()
            + 3600) as usize,
        role: "student".to_string(),
        is_verified: true,
        email_verified: true,
    };
    encode(
        &Header::default(),
        &claims,
        &EncodingKey::from_secret(TEST_JWT_SECRET.as_bytes()),
    )
    .unwrap()
}

fn build_auth_request(
    uri: &str,
    user_id: &str,
    ip: Option<&str>,
) -> axum::http::Request<axum::body::Body> {
    let token = make_test_token(user_id);
    let mut builder = axum::http::Request::builder()
        .method(Method::GET)
        .uri(uri)
        .header("Authorization", format!("Bearer {token}"));
    if let Some(ip_val) = ip {
        builder = builder.header("X-Forwarded-For", ip_val);
    }
    builder.body(axum::body::Body::empty()).unwrap()
}

fn test_limiter_with_auth(auth_max: u32, unauth_max: u32) -> RateLimiter {
    RateLimiter::in_memory_with_auth_config(
        RateConfig { max_requests: auth_max, window_secs: 60 },
        RateConfig { max_requests: unauth_max, window_secs: 60 },
    )
}

// ============================================================
// Existing tests — unauthenticated (IP-based), must keep passing
// ============================================================

#[tokio::test]
async fn request_under_limit_passes_with_headers() {
    let limiter = test_limiter(10, 60);
    let app = api_gateway::create_router_with_rate_limiter(limiter);

    let response = app
        .oneshot(build_request(Method::GET, "/health/live", Some("1.2.3.4")))
        .await
        .unwrap();

    assert_eq!(response.status(), StatusCode::OK);

    let limit = response
        .headers()
        .get("X-RateLimit-Limit")
        .expect("missing X-RateLimit-Limit header")
        .to_str()
        .unwrap();
    assert_eq!(limit, "10");

    let remaining = response
        .headers()
        .get("X-RateLimit-Remaining")
        .expect("missing X-RateLimit-Remaining header")
        .to_str()
        .unwrap()
        .parse::<u32>()
        .unwrap();
    assert_eq!(remaining, 9);

    assert!(response.headers().contains_key("X-RateLimit-Reset"));
}

#[tokio::test]
async fn request_at_limit_returns_429() {
    let limiter = test_limiter(2, 60);
    let app = api_gateway::create_router_with_rate_limiter(limiter);

    // First two requests should succeed
    for _ in 0..2 {
        let app_clone = app.clone();
        let response = app_clone
            .oneshot(build_request(Method::GET, "/health/live", Some("5.6.7.8")))
            .await
            .unwrap();
        assert_eq!(response.status(), StatusCode::OK);
    }

    // Third request should be rate limited
    let response = app
        .oneshot(build_request(Method::GET, "/health/live", Some("5.6.7.8")))
        .await
        .unwrap();

    assert_eq!(response.status(), StatusCode::TOO_MANY_REQUESTS);

    assert!(response.headers().contains_key("Retry-After"));

    let body = response.into_body().collect().await.unwrap().to_bytes();
    let json: serde_json::Value = serde_json::from_slice(&body).unwrap();
    assert_eq!(json["error"], "rate limit exceeded");
}

#[tokio::test]
async fn different_ips_have_independent_limits() {
    let limiter = test_limiter(1, 60);
    let app = api_gateway::create_router_with_rate_limiter(limiter);

    // IP A uses its one request
    let response = app
        .clone()
        .oneshot(build_request(Method::GET, "/health/live", Some("10.0.0.1")))
        .await
        .unwrap();
    assert_eq!(response.status(), StatusCode::OK);

    // IP B should still be able to make a request
    let response = app
        .oneshot(build_request(Method::GET, "/health/live", Some("10.0.0.2")))
        .await
        .unwrap();
    assert_eq!(response.status(), StatusCode::OK);
}

#[tokio::test]
async fn route_specific_limits_apply() {
    // Default limit is 100 but login is 10 and register is 5
    let limiter = RateLimiter::in_memory(RateConfig {
        max_requests: 100,
        window_secs: 60,
    });
    let app = api_gateway::create_router_with_rate_limiter(limiter);

    // POST /auth/register should use the 5/min limit
    let response = app
        .clone()
        .oneshot(build_request(Method::POST, "/auth/register", Some("20.0.0.1")))
        .await
        .unwrap();

    // The route may 404, but the rate limit headers should reflect the route-specific limit
    let limit = response
        .headers()
        .get("X-RateLimit-Limit")
        .expect("missing X-RateLimit-Limit header")
        .to_str()
        .unwrap();
    assert_eq!(limit, "5");

    // POST /auth/login should use the 10/min limit
    let response = app
        .clone()
        .oneshot(build_request(Method::POST, "/auth/login", Some("20.0.0.2")))
        .await
        .unwrap();

    let limit = response
        .headers()
        .get("X-RateLimit-Limit")
        .expect("missing X-RateLimit-Limit header")
        .to_str()
        .unwrap();
    assert_eq!(limit, "10");

    // POST /ai/chat should use the 30/min limit
    let response = app
        .clone()
        .oneshot(build_request(Method::POST, "/ai/chat", Some("20.0.0.3")))
        .await
        .unwrap();

    let limit = response
        .headers()
        .get("X-RateLimit-Limit")
        .expect("missing X-RateLimit-Limit header")
        .to_str()
        .unwrap();
    assert_eq!(limit, "30");

    // GET /health/live should use the default 100/min limit
    let response = app
        .oneshot(build_request(Method::GET, "/health/live", Some("20.0.0.4")))
        .await
        .unwrap();

    let limit = response
        .headers()
        .get("X-RateLimit-Limit")
        .expect("missing X-RateLimit-Limit header")
        .to_str()
        .unwrap();
    assert_eq!(limit, "100");
}

#[tokio::test]
async fn remaining_decrements_correctly() {
    let limiter = test_limiter(5, 60);
    let app = api_gateway::create_router_with_rate_limiter(limiter);

    for expected_remaining in (1..=4).rev() {
        let response = app
            .clone()
            .oneshot(build_request(Method::GET, "/health/live", Some("30.0.0.1")))
            .await
            .unwrap();
        assert_eq!(response.status(), StatusCode::OK);

        let remaining: u32 = response
            .headers()
            .get("X-RateLimit-Remaining")
            .unwrap()
            .to_str()
            .unwrap()
            .parse()
            .unwrap();
        assert_eq!(remaining, expected_remaining);
    }
}

// ============================================================
// New tests — authenticated (user_id-based) rate limiting
// ============================================================

/// Two different users from the same IP must have independent rate limit counters.
/// Once user-A exhausts their limit, user-B (same IP) is unaffected.
///
/// Uses `/me` — a protected (non-public) path so that the auth middleware runs
/// and inserts Claims into request extensions before the rate limiter fires.
#[tokio::test]
async fn authenticated_users_keyed_by_user_id_not_ip() {
    // auth limit = 1 req/window so we can exhaust it with a single request
    let limiter = test_limiter_with_auth(1, 100);
    let app = api_gateway::create_router_with_rate_limiter_and_jwt(
        limiter,
        TEST_JWT_SECRET.to_string(),
    );

    // User A (first request) — allowed (count=1, limit=1)
    let resp = app
        .clone()
        .oneshot(build_auth_request("/me", "user-uuid-aaa", Some("1.2.3.4")))
        .await
        .unwrap();
    assert_ne!(resp.status(), StatusCode::TOO_MANY_REQUESTS, "user A first request should be allowed");

    // User B from the SAME IP — must still pass (different user_id = different bucket)
    let resp = app
        .clone()
        .oneshot(build_auth_request("/me", "user-uuid-bbb", Some("1.2.3.4")))
        .await
        .unwrap();
    assert_ne!(resp.status(), StatusCode::TOO_MANY_REQUESTS, "user B should be unaffected by user A's limit");

    // User A again — limit already exhausted, must get 429
    let resp = app
        .clone()
        .oneshot(build_auth_request("/me", "user-uuid-aaa", Some("1.2.3.4")))
        .await
        .unwrap();
    assert_eq!(resp.status(), StatusCode::TOO_MANY_REQUESTS, "user A second request must be rate limited");
}

/// The X-RateLimit-Limit response header for an authenticated request must equal
/// the auth config value (100), not the unauth config value (20).
#[tokio::test]
async fn authenticated_request_uses_auth_config_limit() {
    let limiter = test_limiter_with_auth(100, 20);
    let app = api_gateway::create_router_with_rate_limiter_and_jwt(
        limiter,
        TEST_JWT_SECRET.to_string(),
    );

    // /me is a protected path — auth middleware sets Claims, rate limiter uses user_id key
    let resp = app
        .clone()
        .oneshot(build_auth_request("/me", "user-uuid-ccc", Some("9.9.9.9")))
        .await
        .unwrap();

    assert_ne!(resp.status(), StatusCode::TOO_MANY_REQUESTS);
    let limit = resp
        .headers()
        .get("X-RateLimit-Limit")
        .expect("missing X-RateLimit-Limit")
        .to_str()
        .unwrap();
    assert_eq!(limit, "100");
}

/// The X-RateLimit-Limit response header for an unauthenticated request must equal
/// the unauth config value (20), not the auth config value (100).
#[tokio::test]
async fn unauthenticated_request_uses_unauth_config_limit() {
    let limiter = test_limiter_with_auth(100, 20);
    let app = api_gateway::create_router_with_rate_limiter_and_jwt(
        limiter,
        TEST_JWT_SECRET.to_string(),
    );

    // /health/live is a public path — no Claims in extensions → IP-based rate limiting
    let resp = app
        .clone()
        .oneshot(build_request(Method::GET, "/health/live", Some("8.8.8.8")))
        .await
        .unwrap();

    assert_ne!(resp.status(), StatusCode::TOO_MANY_REQUESTS);
    let limit = resp
        .headers()
        .get("X-RateLimit-Limit")
        .expect("missing X-RateLimit-Limit")
        .to_str()
        .unwrap();
    assert_eq!(limit, "20");
}

/// When an authenticated user exceeds their per-user limit, the 429 response must
/// include a Retry-After header and a JSON error body.
#[tokio::test]
async fn authenticated_user_gets_429_with_retry_after_when_limit_exceeded() {
    let limiter = test_limiter_with_auth(1, 100);
    let app = api_gateway::create_router_with_rate_limiter_and_jwt(
        limiter,
        TEST_JWT_SECRET.to_string(),
    );

    // First request consumes the single allowed slot (count = 1 = limit)
    let _ = app
        .clone()
        .oneshot(build_auth_request("/me", "user-uuid-ddd", None))
        .await
        .unwrap();

    // Second request must be rejected (count = 2 > limit = 1)
    let resp = app
        .clone()
        .oneshot(build_auth_request("/me", "user-uuid-ddd", None))
        .await
        .unwrap();

    assert_eq!(resp.status(), StatusCode::TOO_MANY_REQUESTS);
    assert!(resp.headers().contains_key("Retry-After"));

    let body = resp.into_body().collect().await.unwrap().to_bytes();
    let json: serde_json::Value = serde_json::from_slice(&body).unwrap();
    assert_eq!(json["error"], "rate limit exceeded");
}
