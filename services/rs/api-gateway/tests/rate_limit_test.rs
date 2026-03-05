use axum::http::{Method, StatusCode};
use http_body_util::BodyExt;
use tower::ServiceExt;

use api_gateway::middleware::rate_limit::{RateConfig, RateLimiter};

fn test_limiter(max_requests: u32, window_secs: u32) -> RateLimiter {
    RateLimiter::in_memory(RateConfig {
        max_requests,
        window_secs,
    })
}

fn build_request(method: Method, uri: &str, forwarded_for: Option<&str>) -> axum::http::Request<axum::body::Body> {
    let mut builder = axum::http::Request::builder().method(method).uri(uri);
    if let Some(ip) = forwarded_for {
        builder = builder.header("X-Forwarded-For", ip);
    }
    builder.body(axum::body::Body::empty()).unwrap()
}

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
