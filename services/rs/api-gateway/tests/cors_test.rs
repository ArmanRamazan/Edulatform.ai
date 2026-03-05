use axum::http::{Method, StatusCode};
use tower::ServiceExt;

fn app() -> axum::Router {
    api_gateway::create_router_with_cors_and_logging(
        String::new(),
        vec!["http://localhost:3000".to_string(), "http://localhost:3001".to_string()],
        3600,
    )
}

#[tokio::test]
async fn cors_preflight_returns_correct_headers() {
    let response = app()
        .oneshot(
            axum::http::Request::builder()
                .method(Method::OPTIONS)
                .uri("/health/live")
                .header("Origin", "http://localhost:3000")
                .header("Access-Control-Request-Method", "GET")
                .header("Access-Control-Request-Headers", "Authorization,Content-Type")
                .body(axum::body::Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();

    assert_eq!(response.status(), StatusCode::OK);

    let headers = response.headers();
    let allow_origin = headers
        .get("Access-Control-Allow-Origin")
        .expect("missing Access-Control-Allow-Origin")
        .to_str()
        .unwrap();
    assert_eq!(allow_origin, "http://localhost:3000");

    let allow_methods = headers
        .get("Access-Control-Allow-Methods")
        .expect("missing Access-Control-Allow-Methods")
        .to_str()
        .unwrap();
    for method in &["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"] {
        assert!(
            allow_methods.contains(method),
            "missing method {} in {}",
            method,
            allow_methods
        );
    }

    let max_age = headers
        .get("Access-Control-Max-Age")
        .expect("missing Access-Control-Max-Age")
        .to_str()
        .unwrap();
    assert_eq!(max_age, "3600");
}

#[tokio::test]
async fn cors_expose_headers_on_actual_request() {
    let response = app()
        .oneshot(
            axum::http::Request::builder()
                .method(Method::GET)
                .uri("/health/live")
                .header("Origin", "http://localhost:3000")
                .body(axum::body::Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();

    assert_eq!(response.status(), StatusCode::OK);

    let expose = response
        .headers()
        .get("Access-Control-Expose-Headers")
        .expect("missing Access-Control-Expose-Headers")
        .to_str()
        .unwrap();
    assert!(expose.contains("x-ratelimit-limit"));
    assert!(expose.contains("x-ratelimit-remaining"));
    assert!(expose.contains("x-ratelimit-reset"));
}

#[tokio::test]
async fn cors_rejects_disallowed_origin() {
    let response = app()
        .oneshot(
            axum::http::Request::builder()
                .method(Method::OPTIONS)
                .uri("/health/live")
                .header("Origin", "http://evil.com")
                .header("Access-Control-Request-Method", "GET")
                .body(axum::body::Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();

    // tower-http CorsLayer returns 200 but without CORS headers for disallowed origins
    assert!(response
        .headers()
        .get("Access-Control-Allow-Origin")
        .is_none());
}
