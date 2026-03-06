#![deny(clippy::all)]

pub mod config;
pub mod embedder;
pub mod error;
pub mod routes;

use std::sync::Arc;

use axum::routing::{get, post};
use axum::Router;

use crate::embedder::EmbeddingService;
use crate::routes::AppState;

pub fn create_router(svc: EmbeddingService) -> Router {
    let state: AppState = Arc::new(svc);

    Router::new()
        .route("/embed", post(routes::embed_single))
        .route("/embed/batch", post(routes::embed_batch))
        .route("/health/live", get(routes::health_live))
        .route("/health/ready", get(routes::health_ready))
        .with_state(state)
}
