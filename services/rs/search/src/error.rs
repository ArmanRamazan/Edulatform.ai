use axum::http::StatusCode;
use axum::response::{IntoResponse, Response};
use serde_json::json;

#[derive(Debug, thiserror::Error)]
#[allow(dead_code)]
pub enum SearchError {
    #[error("Index error: {0}")]
    IndexError(String),

    #[error("Query error: {0}")]
    QueryError(String),

    #[error("Not found")]
    NotFound,
}

impl IntoResponse for SearchError {
    fn into_response(self) -> Response {
        let (status, message) = match &self {
            SearchError::IndexError(msg) => (StatusCode::INTERNAL_SERVER_ERROR, msg.clone()),
            SearchError::QueryError(msg) => (StatusCode::BAD_REQUEST, msg.clone()),
            SearchError::NotFound => (StatusCode::NOT_FOUND, "Not found".to_string()),
        };

        let body = json!({
            "error": message,
        });

        (status, axum::Json(body)).into_response()
    }
}
