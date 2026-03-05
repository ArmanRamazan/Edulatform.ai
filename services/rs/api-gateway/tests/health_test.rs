use axum::http::StatusCode;
use http_body_util::BodyExt;
use tower::ServiceExt;

fn app() -> axum::Router {
    api_gateway::create_router()
}

#[tokio::test]
async fn health_live_returns_200_ok() {
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

    let body = response.into_body().collect().await.unwrap().to_bytes();
    let json: serde_json::Value = serde_json::from_slice(&body).unwrap();
    assert_eq!(json["status"], "ok");
}

#[tokio::test]
async fn health_ready_returns_200() {
    let response = app()
        .oneshot(
            axum::http::Request::builder()
                .uri("/health/ready")
                .body(axum::body::Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();

    assert_eq!(response.status(), StatusCode::OK);

    let body = response.into_body().collect().await.unwrap().to_bytes();
    let json: serde_json::Value = serde_json::from_slice(&body).unwrap();
    assert_eq!(json["status"], "ready");
}

#[tokio::test]
async fn unknown_route_returns_404() {
    let response = app()
        .oneshot(
            axum::http::Request::builder()
                .uri("/nonexistent")
                .body(axum::body::Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();

    assert_eq!(response.status(), StatusCode::NOT_FOUND);
}
