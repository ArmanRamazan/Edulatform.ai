#![deny(clippy::all)]

pub mod config;
pub mod error;

use std::time::Duration;

use axum::{routing::get, Json, Router};
use serde_json::{json, Value};
use axum::http::StatusCode;
use tower_http::timeout::TimeoutLayer;
use tower_http::trace::TraceLayer;

async fn health_live() -> Json<Value> {
    Json(json!({ "status": "ok" }))
}

async fn health_ready() -> Json<Value> {
    Json(json!({ "status": "ready" }))
}

/// Create the application router with all routes and middleware.
pub fn create_router() -> Router {
    Router::new()
        .route("/health/live", get(health_live))
        .route("/health/ready", get(health_ready))
        .layer(TimeoutLayer::with_status_code(StatusCode::GATEWAY_TIMEOUT, Duration::from_secs(30)))
        .layer(TraceLayer::new_for_http())
}
