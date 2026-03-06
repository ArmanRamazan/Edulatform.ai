use axum::http::StatusCode;
use axum::response::{IntoResponse, Response};
use serde_json::json;

#[derive(Debug, thiserror::Error)]
pub enum EmbedError {
    #[error("config error: {0}")]
    Config(String),

    #[error("embedding API error: {0}")]
    Api(String),

    #[error("request error: {0}")]
    Request(#[from] reqwest::Error),

    #[error("invalid input: {0}")]
    InvalidInput(String),

    #[error("timeout: embedding API did not respond in time")]
    Timeout,
}

impl IntoResponse for EmbedError {
    fn into_response(self) -> Response {
        let (status, message) = match &self {
            EmbedError::Config(msg) => (StatusCode::INTERNAL_SERVER_ERROR, msg.clone()),
            EmbedError::Api(msg) => (StatusCode::BAD_GATEWAY, msg.clone()),
            EmbedError::Request(e) => (StatusCode::BAD_GATEWAY, e.to_string()),
            EmbedError::InvalidInput(msg) => (StatusCode::BAD_REQUEST, msg.clone()),
            EmbedError::Timeout => (StatusCode::GATEWAY_TIMEOUT, self.to_string()),
        };

        let body = json!({ "error": message });
        (status, axum::Json(body)).into_response()
    }
}
