#![deny(clippy::all)]

pub mod auth;
pub mod config;
pub mod connection;
pub mod error;
pub mod messages;
pub mod routes;

use std::sync::Arc;

use axum::routing::{get, post};
use axum::Router;
use tower_http::trace::TraceLayer;

use crate::config::Config;
use crate::connection::ConnectionManager;
use crate::routes::AppState;

/// Create the application router with all routes.
///
/// Used by both production main and tests.
pub fn create_router(config: &Config) -> Router {
    let state = AppState {
        manager: Arc::new(ConnectionManager::new()),
        jwt_secret: config.jwt_secret.clone(),
        max_connections: config.max_connections,
        heartbeat_interval_secs: config.heartbeat_interval_secs,
        heartbeat_timeout_secs: config.heartbeat_timeout_secs,
        max_message_size: config.max_message_size,
    };

    create_router_with_state(state)
}

/// Create the application router with a specific state.
///
/// Allows tests to inject a custom ConnectionManager.
pub fn create_router_with_state(state: AppState) -> Router {
    Router::new()
        .route("/ws", get(routes::ws_handler))
        .route("/publish", post(routes::publish_handler))
        .route("/health/live", get(routes::health_live))
        .route("/stats", get(routes::stats_handler))
        .with_state(state)
        .layer(TraceLayer::new_for_http())
}
