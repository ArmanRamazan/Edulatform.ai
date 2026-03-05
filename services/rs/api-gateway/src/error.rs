use axum::http::StatusCode;
use axum::response::{IntoResponse, Response};
use serde_json::json;

#[derive(Debug, thiserror::Error)]
pub enum GatewayError {
    #[error("configuration error: {0}")]
    Config(String),

    #[error("authentication error: {0}")]
    Auth(String),

    #[error("rate limit exceeded")]
    RateLimit,

    #[error("upstream service error: {0}")]
    Upstream(String),

    #[error("request timeout")]
    Timeout,
}

impl IntoResponse for GatewayError {
    fn into_response(self) -> Response {
        let (status, message) = match &self {
            GatewayError::Config(msg) => (StatusCode::INTERNAL_SERVER_ERROR, msg.clone()),
            GatewayError::Auth(msg) => (StatusCode::UNAUTHORIZED, msg.clone()),
            GatewayError::RateLimit => (StatusCode::TOO_MANY_REQUESTS, self.to_string()),
            GatewayError::Upstream(msg) => (StatusCode::BAD_GATEWAY, msg.clone()),
            GatewayError::Timeout => (StatusCode::GATEWAY_TIMEOUT, self.to_string()),
        };

        let body = json!({ "error": message });
        (status, axum::Json(body)).into_response()
    }
}
