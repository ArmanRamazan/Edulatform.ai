#![allow(clippy::unwrap_used)]

use axum::body::Body;
use axum::http::{Request, StatusCode};
use http_body_util::BodyExt;
use jsonwebtoken::{encode, EncodingKey, Header};
use serde::Serialize;
use tower::ServiceExt;

use api_gateway::proxy::{ProxyService, RouteRule};

const TEST_SECRET: &str = "test-jwt-secret-for-proxy-tests";

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

fn now_secs() -> u64 {
    std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .unwrap()
        .as_secs()
}

fn valid_claims() -> TestClaims {
    TestClaims {
        sub: "user-1".into(),
        exp: (now_secs() + 3600) as usize,
        role: "student".into(),
        is_verified: true,
        email_verified: true,
        organization_id: None,
    }
}

fn make_token(claims: &TestClaims) -> String {
    encode(
        &Header::default(),
        claims,
        &EncodingKey::from_secret(TEST_SECRET.as_bytes()),
    )
    .unwrap()
}

fn bearer(token: &str) -> String {
    format!("Bearer {}", token)
}

fn test_routes() -> Vec<RouteRule> {
    vec![
        RouteRule {
            prefix: "/auth".to_string(),
            upstream: "http://localhost:19001".to_string(),
            strip_prefix: false,
        },
        RouteRule {
            prefix: "/users".to_string(),
            upstream: "http://localhost:19001".to_string(),
            strip_prefix: false,
        },
        RouteRule {
            prefix: "/payments".to_string(),
            upstream: "http://localhost:19004".to_string(),
            strip_prefix: false,
        },
        RouteRule {
            prefix: "/quizzes".to_string(),
            upstream: "http://localhost:19007".to_string(),
            strip_prefix: false,
        },
        RouteRule {
            prefix: "/kb".to_string(),
            upstream: "http://localhost:19008".to_string(),
            strip_prefix: false,
        },
    ]
}

// --- Route matching tests ---

#[test]
fn match_route_auth() {
    let proxy = ProxyService::new(test_routes());
    let rule = proxy.match_route("/auth/login").unwrap();
    assert_eq!(rule.upstream, "http://localhost:19001");
}

#[test]
fn match_route_exact_prefix() {
    let proxy = ProxyService::new(test_routes());
    let rule = proxy.match_route("/users").unwrap();
    assert_eq!(rule.upstream, "http://localhost:19001");
}

#[test]
fn match_route_with_subpath() {
    let proxy = ProxyService::new(test_routes());
    let rule = proxy.match_route("/payments/123/refund").unwrap();
    assert_eq!(rule.upstream, "http://localhost:19004");
}

#[test]
fn match_route_returns_none_for_unknown() {
    let proxy = ProxyService::new(test_routes());
    assert!(proxy.match_route("/unknown").is_none());
}

#[test]
fn match_route_no_partial_prefix_match() {
    // "/kb" should NOT match "/kbsomething" (no slash separator)
    let proxy = ProxyService::new(test_routes());
    assert!(proxy.match_route("/kbsomething").is_none());
}

#[test]
fn match_route_learning_service() {
    let proxy = ProxyService::new(test_routes());
    let rule = proxy.match_route("/quizzes/42").unwrap();
    assert_eq!(rule.upstream, "http://localhost:19007");
}

#[test]
fn match_route_rag_service() {
    let proxy = ProxyService::new(test_routes());
    let rule = proxy.match_route("/kb/docs").unwrap();
    assert_eq!(rule.upstream, "http://localhost:19008");
}

// --- Proxy handler: 404 for unmatched routes ---

#[tokio::test]
async fn proxy_returns_404_for_unmatched_route() {
    let proxy = ProxyService::new(test_routes());
    let app = api_gateway::create_router_with_proxy(TEST_SECRET.to_string(), proxy);

    let token = make_token(&valid_claims());
    let req = Request::builder()
        .uri("/nonexistent-path")
        .header("Authorization", bearer(&token))
        .body(Body::empty())
        .unwrap();

    let response = app.oneshot(req).await.unwrap();
    assert_eq!(response.status(), StatusCode::NOT_FOUND);

    let body = response.into_body().collect().await.unwrap().to_bytes();
    let json: serde_json::Value = serde_json::from_slice(&body).unwrap();
    assert_eq!(json["error"], "not found");
}

// --- Proxy handler: upstream unavailable returns 502 ---

#[tokio::test]
async fn proxy_returns_502_when_upstream_unavailable() {
    // Use a port that nothing listens on
    let routes = vec![RouteRule {
        prefix: "/test-svc".to_string(),
        upstream: "http://127.0.0.1:19999".to_string(),
        strip_prefix: false,
    }];
    let proxy = ProxyService::new(routes);
    let app = api_gateway::create_router_with_proxy(TEST_SECRET.to_string(), proxy);

    let token = make_token(&valid_claims());
    let req = Request::builder()
        .uri("/test-svc/hello")
        .header("Authorization", bearer(&token))
        .body(Body::empty())
        .unwrap();

    let response = app.oneshot(req).await.unwrap();
    assert_eq!(response.status(), StatusCode::BAD_GATEWAY);
}

// --- Proxy handler: proxies to real mock server ---

#[tokio::test]
async fn proxy_forwards_to_upstream_and_returns_response() {
    // Start a mini Axum server as mock upstream
    let mock_app = axum::Router::new().route(
        "/users/me",
        axum::routing::get(|| async {
            axum::Json(serde_json::json!({ "id": "user-1", "name": "Alice" }))
        }),
    );

    let listener = tokio::net::TcpListener::bind("127.0.0.1:0").await.unwrap();
    let mock_addr = listener.local_addr().unwrap();
    tokio::spawn(async move {
        axum::serve(listener, mock_app).await.unwrap();
    });

    let routes = vec![RouteRule {
        prefix: "/users".to_string(),
        upstream: format!("http://{}", mock_addr),
        strip_prefix: false,
    }];

    let proxy = ProxyService::new(routes);
    let app = api_gateway::create_router_with_proxy(TEST_SECRET.to_string(), proxy);

    let token = make_token(&valid_claims());
    let req = Request::builder()
        .uri("/users/me")
        .header("Authorization", bearer(&token))
        .body(Body::empty())
        .unwrap();

    let response = app.oneshot(req).await.unwrap();
    assert_eq!(response.status(), StatusCode::OK);

    let body = response.into_body().collect().await.unwrap().to_bytes();
    let json: serde_json::Value = serde_json::from_slice(&body).unwrap();
    assert_eq!(json["id"], "user-1");
    assert_eq!(json["name"], "Alice");
}

// --- Proxy handler: X-User-* headers forwarded to upstream ---

#[tokio::test]
async fn proxy_forwards_x_user_headers_to_upstream() {
    // Mock upstream that echoes back X-User-* headers
    let mock_app = axum::Router::new().route(
        "/users/profile",
        axum::routing::get(|headers: axum::http::HeaderMap| async move {
            let user_id = headers
                .get("X-User-Id")
                .map(|v| v.to_str().unwrap_or(""))
                .unwrap_or("");
            let role = headers
                .get("X-User-Role")
                .map(|v| v.to_str().unwrap_or(""))
                .unwrap_or("");
            let verified = headers
                .get("X-User-Verified")
                .map(|v| v.to_str().unwrap_or(""))
                .unwrap_or("");
            axum::Json(serde_json::json!({
                "user_id": user_id,
                "role": role,
                "verified": verified,
            }))
        }),
    );

    let listener = tokio::net::TcpListener::bind("127.0.0.1:0").await.unwrap();
    let mock_addr = listener.local_addr().unwrap();
    tokio::spawn(async move {
        axum::serve(listener, mock_app).await.unwrap();
    });

    let routes = vec![RouteRule {
        prefix: "/users".to_string(),
        upstream: format!("http://{}", mock_addr),
        strip_prefix: false,
    }];

    let proxy = ProxyService::new(routes);
    let app = api_gateway::create_router_with_proxy(TEST_SECRET.to_string(), proxy);

    let token = make_token(&valid_claims());
    let req = Request::builder()
        .uri("/users/profile")
        .header("Authorization", bearer(&token))
        .body(Body::empty())
        .unwrap();

    let response = app.oneshot(req).await.unwrap();
    assert_eq!(response.status(), StatusCode::OK);

    let body = response.into_body().collect().await.unwrap().to_bytes();
    let json: serde_json::Value = serde_json::from_slice(&body).unwrap();
    assert_eq!(json["user_id"], "user-1");
    assert_eq!(json["role"], "student");
    assert_eq!(json["verified"], "true");
}

// --- Proxy handler: POST body forwarded ---

#[tokio::test]
async fn proxy_forwards_post_body_to_upstream() {
    let mock_app = axum::Router::new().route(
        "/auth/register",
        axum::routing::post(
            |body: axum::Json<serde_json::Value>| async move { axum::Json(body.0) },
        ),
    );

    let listener = tokio::net::TcpListener::bind("127.0.0.1:0").await.unwrap();
    let mock_addr = listener.local_addr().unwrap();
    tokio::spawn(async move {
        axum::serve(listener, mock_app).await.unwrap();
    });

    let routes = vec![RouteRule {
        prefix: "/auth".to_string(),
        upstream: format!("http://{}", mock_addr),
        strip_prefix: false,
    }];

    let proxy = ProxyService::new(routes);
    // /auth/register is a public route — no JWT needed
    let app = api_gateway::create_router_with_proxy(TEST_SECRET.to_string(), proxy);

    let payload = serde_json::json!({ "email": "test@example.com", "password": "secret123" });
    let req = Request::builder()
        .method("POST")
        .uri("/auth/register")
        .header("Content-Type", "application/json")
        .body(Body::from(serde_json::to_string(&payload).unwrap()))
        .unwrap();

    let response = app.oneshot(req).await.unwrap();
    assert_eq!(response.status(), StatusCode::OK);

    let body = response.into_body().collect().await.unwrap().to_bytes();
    let json: serde_json::Value = serde_json::from_slice(&body).unwrap();
    assert_eq!(json["email"], "test@example.com");
}

// --- Proxy handler: query params preserved ---

#[tokio::test]
async fn proxy_preserves_query_params() {
    let mock_app = axum::Router::new().route(
        "/users/search",
        axum::routing::get(|uri: axum::http::Uri| async move {
            let query = uri.query().unwrap_or("");
            axum::Json(serde_json::json!({ "query": query }))
        }),
    );

    let listener = tokio::net::TcpListener::bind("127.0.0.1:0").await.unwrap();
    let mock_addr = listener.local_addr().unwrap();
    tokio::spawn(async move {
        axum::serve(listener, mock_app).await.unwrap();
    });

    let routes = vec![RouteRule {
        prefix: "/users".to_string(),
        upstream: format!("http://{}", mock_addr),
        strip_prefix: false,
    }];

    let proxy = ProxyService::new(routes);
    let app = api_gateway::create_router_with_proxy(TEST_SECRET.to_string(), proxy);

    let token = make_token(&valid_claims());
    let req = Request::builder()
        .uri("/users/search?q=alice&limit=10")
        .header("Authorization", bearer(&token))
        .body(Body::empty())
        .unwrap();

    let response = app.oneshot(req).await.unwrap();
    assert_eq!(response.status(), StatusCode::OK);

    let body = response.into_body().collect().await.unwrap().to_bytes();
    let json: serde_json::Value = serde_json::from_slice(&body).unwrap();
    assert_eq!(json["query"], "q=alice&limit=10");
}

// --- Default route mapping completeness ---

#[test]
fn default_routes_cover_all_services() {
    let config = api_gateway::config::Config {
        port: 8080,
        redis_url: "redis://localhost".to_string(),
        jwt_secret: "secret".to_string(),
        identity_url: "http://identity:8001".to_string(),
        payment_url: "http://payment:8004".to_string(),
        notification_url: "http://notification:8005".to_string(),
        ai_url: "http://ai:8006".to_string(),
        learning_url: "http://learning:8007".to_string(),
        rag_url: "http://rag:8008".to_string(),
        cors_origins: vec!["http://localhost:3000".to_string()],
        cors_max_age: 3600,
    };

    let routes = api_gateway::proxy::default_routes(&config);
    let proxy = ProxyService::new(routes);

    // Identity
    assert_eq!(proxy.match_route("/auth/login").unwrap().upstream, "http://identity:8001");
    assert_eq!(proxy.match_route("/me").unwrap().upstream, "http://identity:8001");
    assert_eq!(proxy.match_route("/users/1").unwrap().upstream, "http://identity:8001");
    assert_eq!(proxy.match_route("/organizations/1").unwrap().upstream, "http://identity:8001");
    assert_eq!(proxy.match_route("/follow/1").unwrap().upstream, "http://identity:8001");
    assert_eq!(proxy.match_route("/referral/code").unwrap().upstream, "http://identity:8001");

    // Payment
    assert_eq!(proxy.match_route("/payments/1").unwrap().upstream, "http://payment:8004");
    assert_eq!(proxy.match_route("/subscriptions/1").unwrap().upstream, "http://payment:8004");
    assert_eq!(proxy.match_route("/coupons/abc").unwrap().upstream, "http://payment:8004");
    assert_eq!(proxy.match_route("/earnings/1").unwrap().upstream, "http://payment:8004");
    assert_eq!(proxy.match_route("/gifts/1").unwrap().upstream, "http://payment:8004");
    assert_eq!(proxy.match_route("/org-subscriptions/1").unwrap().upstream, "http://payment:8004");

    // Notification
    assert_eq!(proxy.match_route("/notifications/1").unwrap().upstream, "http://notification:8005");
    assert_eq!(proxy.match_route("/conversations/1").unwrap().upstream, "http://notification:8005");
    assert_eq!(proxy.match_route("/messages/1").unwrap().upstream, "http://notification:8005");

    // AI
    assert_eq!(proxy.match_route("/ai/chat").unwrap().upstream, "http://ai:8006");

    // Learning
    assert_eq!(proxy.match_route("/quizzes/1").unwrap().upstream, "http://learning:8007");
    assert_eq!(proxy.match_route("/flashcards/1").unwrap().upstream, "http://learning:8007");
    assert_eq!(proxy.match_route("/concepts/1").unwrap().upstream, "http://learning:8007");
    assert_eq!(proxy.match_route("/missions/1").unwrap().upstream, "http://learning:8007");
    assert_eq!(proxy.match_route("/trust-level/1").unwrap().upstream, "http://learning:8007");
    assert_eq!(proxy.match_route("/daily/summary").unwrap().upstream, "http://learning:8007");
    assert_eq!(proxy.match_route("/streaks/1").unwrap().upstream, "http://learning:8007");
    assert_eq!(proxy.match_route("/leaderboard/1").unwrap().upstream, "http://learning:8007");
    assert_eq!(proxy.match_route("/discussions/1").unwrap().upstream, "http://learning:8007");
    assert_eq!(proxy.match_route("/xp/1").unwrap().upstream, "http://learning:8007");
    assert_eq!(proxy.match_route("/badges/1").unwrap().upstream, "http://learning:8007");
    assert_eq!(proxy.match_route("/pretests/1").unwrap().upstream, "http://learning:8007");
    assert_eq!(proxy.match_route("/velocity/1").unwrap().upstream, "http://learning:8007");
    assert_eq!(proxy.match_route("/activity/1").unwrap().upstream, "http://learning:8007");
    assert_eq!(proxy.match_route("/study-groups/1").unwrap().upstream, "http://learning:8007");

    // RAG
    assert_eq!(proxy.match_route("/kb/1").unwrap().upstream, "http://rag:8008");
    assert_eq!(proxy.match_route("/sources/1").unwrap().upstream, "http://rag:8008");
    assert_eq!(proxy.match_route("/upload/file").unwrap().upstream, "http://rag:8008");
    assert_eq!(proxy.match_route("/templates/1").unwrap().upstream, "http://rag:8008");

    // Unknown → None
    assert!(proxy.match_route("/unknown").is_none());
}
