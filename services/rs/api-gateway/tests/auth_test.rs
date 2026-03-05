#![allow(clippy::unwrap_used)]

use axum::http::StatusCode;
use http_body_util::BodyExt;
use jsonwebtoken::{encode, EncodingKey, Header};
use serde::Serialize;
use tower::ServiceExt;

#[derive(Serialize)]
struct TestClaims {
    sub: String,
    exp: usize,
    role: String,
    is_verified: bool,
    email_verified: bool,
    #[serde(skip_serializing_if = "Option::is_none")]
    organization_id: Option<String>,
}

const TEST_SECRET: &str = "test-jwt-secret-for-unit-tests";

fn make_token(claims: &TestClaims) -> String {
    encode(
        &Header::default(),
        claims,
        &EncodingKey::from_secret(TEST_SECRET.as_bytes()),
    )
    .unwrap()
}

fn valid_claims() -> TestClaims {
    TestClaims {
        sub: "550e8400-e29b-41d4-a716-446655440000".into(),
        exp: (now_secs() + 3600) as usize,
        role: "student".into(),
        is_verified: false,
        email_verified: true,
        organization_id: None,
    }
}

fn now_secs() -> u64 {
    std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .unwrap()
        .as_secs()
}

fn app() -> axum::Router {
    api_gateway::create_router_with_secret(TEST_SECRET.to_string())
}

// ---------- verify_token unit tests ----------

#[test]
fn test_valid_jwt_passes_verification() {
    let claims = valid_claims();
    let token = make_token(&claims);
    let result = api_gateway::auth::verify_token(&token, TEST_SECRET);
    assert!(result.is_ok());
    let parsed = result.unwrap();
    assert_eq!(parsed.sub, "550e8400-e29b-41d4-a716-446655440000");
    assert_eq!(parsed.role, "student");
    assert!(!parsed.is_verified);
    assert!(parsed.email_verified);
    assert!(parsed.organization_id.is_none());
}

#[test]
fn test_expired_jwt_rejected() {
    let claims = TestClaims {
        exp: (now_secs().saturating_sub(100)) as usize,
        ..valid_claims()
    };
    let token = make_token(&claims);
    let result = api_gateway::auth::verify_token(&token, TEST_SECRET);
    assert!(result.is_err());
}

#[test]
fn test_invalid_signature_rejected() {
    let claims = valid_claims();
    let token = encode(
        &Header::default(),
        &claims,
        &EncodingKey::from_secret(b"wrong-secret"),
    )
    .unwrap();
    let result = api_gateway::auth::verify_token(&token, TEST_SECRET);
    assert!(result.is_err());
}

#[test]
fn test_claims_with_organization_id() {
    let claims = TestClaims {
        organization_id: Some("org-uuid-123".into()),
        ..valid_claims()
    };
    let token = make_token(&claims);
    let parsed = api_gateway::auth::verify_token(&token, TEST_SECRET).unwrap();
    assert_eq!(parsed.organization_id.as_deref(), Some("org-uuid-123"));
}

// ---------- middleware integration tests ----------

#[tokio::test]
async fn test_public_health_routes_without_auth_pass() {
    let response = app()
        .oneshot(
            axum::http::Request::builder()
                .uri("/health/live")
                .body(axum::body::Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();

    assert_eq!(response.status(), StatusCode::OK);
}

#[tokio::test]
async fn test_public_auth_routes_without_auth_pass() {
    // POST /auth/login should be public — returns 404 (no upstream handler)
    // but NOT 401 (auth middleware must skip it)
    let response = app()
        .oneshot(
            axum::http::Request::builder()
                .method("POST")
                .uri("/auth/login")
                .body(axum::body::Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();

    assert_ne!(response.status(), StatusCode::UNAUTHORIZED);
}

#[tokio::test]
async fn test_protected_route_without_auth_returns_401() {
    let response = app()
        .oneshot(
            axum::http::Request::builder()
                .uri("/api/courses")
                .body(axum::body::Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();

    assert_eq!(response.status(), StatusCode::UNAUTHORIZED);

    let body = response.into_body().collect().await.unwrap().to_bytes();
    let json: serde_json::Value = serde_json::from_slice(&body).unwrap();
    assert!(json["error"].as_str().is_some());
}

#[tokio::test]
async fn test_protected_route_with_valid_jwt_passes() {
    let claims = valid_claims();
    let token = make_token(&claims);

    let response = app()
        .oneshot(
            axum::http::Request::builder()
                .uri("/api/courses")
                .header("Authorization", format!("Bearer {}", token))
                .body(axum::body::Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();

    // Should NOT be 401 (will be 404 since no upstream handler, but auth passed)
    assert_ne!(response.status(), StatusCode::UNAUTHORIZED);
}

#[tokio::test]
async fn test_protected_route_with_expired_jwt_returns_401() {
    let claims = TestClaims {
        exp: (now_secs().saturating_sub(100)) as usize,
        ..valid_claims()
    };
    let token = make_token(&claims);

    let response = app()
        .oneshot(
            axum::http::Request::builder()
                .uri("/api/courses")
                .header("Authorization", format!("Bearer {}", token))
                .body(axum::body::Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();

    assert_eq!(response.status(), StatusCode::UNAUTHORIZED);
}

#[tokio::test]
async fn test_protected_route_with_invalid_signature_returns_401() {
    let claims = valid_claims();
    let token = encode(
        &Header::default(),
        &claims,
        &EncodingKey::from_secret(b"wrong-secret"),
    )
    .unwrap();

    let response = app()
        .oneshot(
            axum::http::Request::builder()
                .uri("/api/courses")
                .header("Authorization", format!("Bearer {}", token))
                .body(axum::body::Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();

    assert_eq!(response.status(), StatusCode::UNAUTHORIZED);
}

#[tokio::test]
async fn test_x_user_headers_set_correctly() {
    let claims = TestClaims {
        organization_id: Some("org-abc-123".into()),
        ..valid_claims()
    };
    let token = make_token(&claims);

    // Build a test router with echo handler + auth middleware
    use axum::{routing::get, Json, Router};
    use serde_json::{json, Value};

    async fn echo_headers(headers: axum::http::HeaderMap) -> Json<Value> {
        Json(json!({
            "x_user_id": headers.get("X-User-Id").and_then(|v| v.to_str().ok()),
            "x_user_role": headers.get("X-User-Role").and_then(|v| v.to_str().ok()),
            "x_user_verified": headers.get("X-User-Verified").and_then(|v| v.to_str().ok()),
            "x_organization_id": headers.get("X-Organization-Id").and_then(|v| v.to_str().ok()),
        }))
    }

    let router = Router::new().route("/api/echo", get(echo_headers));
    let router = api_gateway::middleware::apply_auth(router, TEST_SECRET.to_string());

    let response = router
        .oneshot(
            axum::http::Request::builder()
                .uri("/api/echo")
                .header("Authorization", format!("Bearer {}", token))
                .body(axum::body::Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();

    assert_eq!(response.status(), StatusCode::OK);

    let body = response.into_body().collect().await.unwrap().to_bytes();
    let json: serde_json::Value = serde_json::from_slice(&body).unwrap();

    assert_eq!(
        json["x_user_id"].as_str().unwrap(),
        "550e8400-e29b-41d4-a716-446655440000"
    );
    assert_eq!(json["x_user_role"].as_str().unwrap(), "student");
    assert_eq!(json["x_user_verified"].as_str().unwrap(), "false");
    assert_eq!(json["x_organization_id"].as_str().unwrap(), "org-abc-123");
}

#[tokio::test]
async fn test_x_organization_id_absent_when_null() {
    let claims = valid_claims(); // organization_id is None
    let token = make_token(&claims);

    use axum::{routing::get, Json, Router};
    use serde_json::{json, Value};

    async fn echo_org(headers: axum::http::HeaderMap) -> Json<Value> {
        Json(json!({
            "has_org_header": headers.get("X-Organization-Id").is_some(),
        }))
    }

    let router = Router::new().route("/api/echo-org", get(echo_org));
    let router = api_gateway::middleware::apply_auth(router, TEST_SECRET.to_string());

    let response = router
        .oneshot(
            axum::http::Request::builder()
                .uri("/api/echo-org")
                .header("Authorization", format!("Bearer {}", token))
                .body(axum::body::Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();

    assert_eq!(response.status(), StatusCode::OK);

    let body = response.into_body().collect().await.unwrap().to_bytes();
    let json: serde_json::Value = serde_json::from_slice(&body).unwrap();

    assert!(!json["has_org_header"].as_bool().unwrap());
}
