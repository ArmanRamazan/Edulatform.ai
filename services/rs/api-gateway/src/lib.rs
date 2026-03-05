#![deny(clippy::all)]

pub mod auth;
pub mod config;
pub mod error;
pub mod middleware;
pub mod proxy;

use std::time::Duration;

use axum::http::StatusCode;
use axum::routing::{any, get};
use axum::{Json, Router};
use proxy::ProxyService;
use serde_json::{json, Value};
use tower_http::timeout::TimeoutLayer;
use tower_http::trace::TraceLayer;

async fn health_live() -> Json<Value> {
    Json(json!({ "status": "ok" }))
}

async fn health_ready() -> Json<Value> {
    Json(json!({ "status": "ready" }))
}

/// Create the application router with all routes and middleware.
///
/// Uses the default config for JWT secret (reads from env).
pub fn create_router() -> Router {
    let jwt_secret = std::env::var("JWT_SECRET").unwrap_or_default();
    create_router_with_secret(jwt_secret)
}

/// Create the application router with a specific JWT secret.
///
/// This is the primary constructor, used by tests and production code.
pub fn create_router_with_secret(jwt_secret: String) -> Router {
    let router = Router::new()
        .route("/health/live", get(health_live))
        .route("/health/ready", get(health_ready));

    middleware::apply_auth(router, jwt_secret)
        .layer(TimeoutLayer::with_status_code(
            StatusCode::GATEWAY_TIMEOUT,
            Duration::from_secs(30),
        ))
        .layer(TraceLayer::new_for_http())
}

/// Create the application router with proxy routing to upstream services.
///
/// This is the production constructor with full proxy support.
pub fn create_router_with_proxy(jwt_secret: String, proxy_service: ProxyService) -> Router {
    let router = Router::new()
        .route("/health/live", get(health_live))
        .route("/health/ready", get(health_ready))
        .fallback(any(proxy::proxy_handler).with_state(proxy_service));

    middleware::apply_auth(router, jwt_secret)
        .layer(TimeoutLayer::with_status_code(
            StatusCode::GATEWAY_TIMEOUT,
            Duration::from_secs(30),
        ))
        .layer(TraceLayer::new_for_http())
}

/// Create the application router with a specific rate limiter.
///
/// Used by rate limiting tests and production code when Redis is available.
pub fn create_router_with_rate_limiter(limiter: middleware::rate_limit::RateLimiter) -> Router {
    Router::new()
        .route("/health/live", get(health_live))
        .route("/health/ready", get(health_ready))
        .layer(axum::middleware::from_fn_with_state(
            limiter,
            middleware::rate_limit::rate_limit_middleware,
        ))
        .layer(TimeoutLayer::with_status_code(
            StatusCode::GATEWAY_TIMEOUT,
            Duration::from_secs(30),
        ))
        .layer(TraceLayer::new_for_http())
}
