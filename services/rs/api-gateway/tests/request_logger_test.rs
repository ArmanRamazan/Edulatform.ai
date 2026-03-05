use axum::http::StatusCode;
use tower::ServiceExt;

fn app() -> axum::Router {
    api_gateway::create_router_with_cors_and_logging(
        String::new(),
        vec!["http://localhost:3000".to_string()],
        3600,
    )
}

#[tokio::test]
async fn request_id_generated_if_missing() {
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

    let request_id = response
        .headers()
        .get("X-Request-Id")
        .expect("missing X-Request-Id header")
        .to_str()
        .unwrap();

    // Should be a valid UUID v4
    assert_eq!(request_id.len(), 36);
    assert!(uuid::Uuid::parse_str(request_id).is_ok());
}

#[tokio::test]
async fn request_id_passed_through_if_present() {
    let custom_id = "my-custom-request-id-12345";

    let response = app()
        .oneshot(
            axum::http::Request::builder()
                .uri("/health/live")
                .header("X-Request-Id", custom_id)
                .body(axum::body::Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();

    assert_eq!(response.status(), StatusCode::OK);

    let request_id = response
        .headers()
        .get("X-Request-Id")
        .expect("missing X-Request-Id header")
        .to_str()
        .unwrap();
    assert_eq!(request_id, custom_id);
}
