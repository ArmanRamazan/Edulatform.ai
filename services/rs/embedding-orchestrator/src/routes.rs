use std::sync::Arc;

use axum::extract::State;
use axum::http::StatusCode;
use axum::response::IntoResponse;
use axum::Json;
use serde::{Deserialize, Serialize};

use crate::embedder::EmbeddingService;

pub type AppState = Arc<EmbeddingService>;

#[derive(Deserialize)]
pub struct EmbedSingleRequest {
    pub text: String,
}

#[derive(Serialize)]
pub struct EmbedSingleResponse {
    pub embedding: Vec<f32>,
}

#[derive(Deserialize)]
pub struct EmbedBatchRequest {
    pub texts: Vec<String>,
}

#[derive(Serialize)]
pub struct EmbedBatchResponse {
    pub embeddings: Vec<Vec<f32>>,
    pub failed: Vec<usize>,
}

pub async fn embed_single(
    State(svc): State<AppState>,
    Json(body): Json<EmbedSingleRequest>,
) -> Result<Json<EmbedSingleResponse>, crate::error::EmbedError> {
    let embedding = svc.embed_single(&body.text).await?;
    Ok(Json(EmbedSingleResponse { embedding }))
}

pub async fn embed_batch(
    State(svc): State<AppState>,
    Json(body): Json<EmbedBatchRequest>,
) -> Json<EmbedBatchResponse> {
    let result = svc.embed_batch(body.texts).await;
    Json(EmbedBatchResponse {
        embeddings: result.embeddings,
        failed: result.failed,
    })
}

pub async fn health_live() -> impl IntoResponse {
    (StatusCode::OK, Json(serde_json::json!({ "status": "ok" })))
}

pub async fn health_ready(State(svc): State<AppState>) -> impl IntoResponse {
    match svc.check_health().await {
        Ok(()) => (
            StatusCode::OK,
            Json(serde_json::json!({ "status": "ready" })),
        ),
        Err(e) => (
            StatusCode::SERVICE_UNAVAILABLE,
            Json(serde_json::json!({ "status": "unavailable", "error": e.to_string() })),
        ),
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use axum::body::Body;
    use axum::http::Request;
    use axum::Router;
    use axum::routing::{get, post};
    use http_body_util::BodyExt;
    use tower::ServiceExt;
    use wiremock::matchers::{method, path};
    use wiremock::{Mock, MockServer, ResponseTemplate};

    use crate::config::Config;

    fn test_config(url: &str) -> Config {
        Config {
            port: 8009,
            embedding_api_url: url.to_string(),
            embedding_api_key: "test-key".into(),
            embedding_model: "text-embedding-004".into(),
            max_concurrent_requests: 5,
            batch_size: 100,
            request_timeout_secs: 10,
        }
    }

    fn create_app(svc: EmbeddingService) -> Router {
        let state: AppState = Arc::new(svc);
        Router::new()
            .route("/embed", post(embed_single))
            .route("/embed/batch", post(embed_batch))
            .route("/health/live", get(health_live))
            .route("/health/ready", get(health_ready))
            .with_state(state)
    }

    #[tokio::test]
    async fn test_embed_single_route() {
        let server = MockServer::start().await;
        let config = test_config(&server.uri());

        Mock::given(method("POST"))
            .and(path("/"))
            .respond_with(ResponseTemplate::new(200).set_body_json(serde_json::json!({
                "embedding": { "values": [0.1, 0.2, 0.3] }
            })))
            .mount(&server)
            .await;

        let svc = EmbeddingService::new(&config);
        let app = create_app(svc);

        let request = Request::builder()
            .method("POST")
            .uri("/embed")
            .header("content-type", "application/json")
            .body(Body::from(r#"{"text": "hello"}"#))
            .unwrap();

        let response = app.oneshot(request).await.unwrap();
        assert_eq!(response.status(), StatusCode::OK);

        let body = response.into_body().collect().await.unwrap().to_bytes();
        let json: serde_json::Value = serde_json::from_slice(&body).unwrap();
        assert_eq!(json["embedding"], serde_json::json!([0.1, 0.2, 0.3]));
    }

    #[tokio::test]
    async fn test_embed_batch_route() {
        let server = MockServer::start().await;
        let config = test_config(&server.uri());

        Mock::given(method("POST"))
            .and(path("/"))
            .respond_with(ResponseTemplate::new(200).set_body_json(serde_json::json!({
                "embedding": { "values": [1.0, 2.0] }
            })))
            .expect(2)
            .mount(&server)
            .await;

        let svc = EmbeddingService::new(&config);
        let app = create_app(svc);

        let request = Request::builder()
            .method("POST")
            .uri("/embed/batch")
            .header("content-type", "application/json")
            .body(Body::from(r#"{"texts": ["one", "two"]}"#))
            .unwrap();

        let response = app.oneshot(request).await.unwrap();
        assert_eq!(response.status(), StatusCode::OK);

        let body = response.into_body().collect().await.unwrap().to_bytes();
        let json: serde_json::Value = serde_json::from_slice(&body).unwrap();
        let embeddings = json["embeddings"].as_array().unwrap();
        assert_eq!(embeddings.len(), 2);
        assert!(json["failed"].as_array().unwrap().is_empty());
    }

    #[tokio::test]
    async fn test_health_live_route() {
        let config = test_config("http://localhost:1");
        let svc = EmbeddingService::new(&config);
        let app = create_app(svc);

        let request = Request::builder()
            .uri("/health/live")
            .body(Body::empty())
            .unwrap();

        let response = app.oneshot(request).await.unwrap();
        assert_eq!(response.status(), StatusCode::OK);
    }

    #[tokio::test]
    async fn test_health_ready_ok() {
        let server = MockServer::start().await;
        let config = test_config(&server.uri());

        Mock::given(method("POST"))
            .and(path("/"))
            .respond_with(ResponseTemplate::new(200).set_body_json(serde_json::json!({
                "embedding": { "values": [0.0] }
            })))
            .mount(&server)
            .await;

        let svc = EmbeddingService::new(&config);
        let app = create_app(svc);

        let request = Request::builder()
            .uri("/health/ready")
            .body(Body::empty())
            .unwrap();

        let response = app.oneshot(request).await.unwrap();
        assert_eq!(response.status(), StatusCode::OK);
    }

    #[tokio::test]
    async fn test_health_ready_unavailable() {
        // Point at a non-existent server
        let config = test_config("http://127.0.0.1:1");
        let svc = EmbeddingService::new(&config);
        let app = create_app(svc);

        let request = Request::builder()
            .uri("/health/ready")
            .body(Body::empty())
            .unwrap();

        let response = app.oneshot(request).await.unwrap();
        assert_eq!(response.status(), StatusCode::SERVICE_UNAVAILABLE);
    }
}
