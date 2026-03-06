use std::sync::Arc;
use std::time::Duration;

use axum::extract::ws::{Message, WebSocket};
use axum::extract::{Query, State, WebSocketUpgrade};
use axum::http::StatusCode;
use axum::response::IntoResponse;
use axum::Json;
use futures::stream::StreamExt;
use serde::{Deserialize, Serialize};
use uuid::Uuid;

use crate::auth;
use crate::connection::ConnectionManager;
use crate::messages::{IncomingMessage, WsMessage};

/// Shared application state.
#[derive(Clone)]
pub struct AppState {
    pub manager: Arc<ConnectionManager>,
    pub jwt_secret: String,
    pub max_connections: usize,
    pub heartbeat_interval_secs: u64,
    pub heartbeat_timeout_secs: u64,
    pub max_message_size: usize,
}

#[derive(Deserialize)]
pub struct WsQuery {
    pub token: String,
}

/// GET /ws — WebSocket upgrade endpoint.
///
/// Validates JWT from query param (WebSocket can't use Authorization header).
/// Registers the connection and starts the message loop.
pub async fn ws_handler(
    ws: WebSocketUpgrade,
    Query(query): Query<WsQuery>,
    State(state): State<AppState>,
) -> impl IntoResponse {
    // Validate JWT before upgrading
    let claims = match auth::verify_token(&query.token, &state.jwt_secret) {
        Ok(c) => c,
        Err(_) => {
            return (StatusCode::UNAUTHORIZED, "invalid or expired token").into_response();
        }
    };

    // Check connection limit
    if state.manager.connection_count() >= state.max_connections {
        return (StatusCode::SERVICE_UNAVAILABLE, "connection limit reached").into_response();
    }

    let user_id = match Uuid::parse_str(&claims.sub) {
        Ok(id) => id,
        Err(_) => {
            return (StatusCode::BAD_REQUEST, "invalid user id in token").into_response();
        }
    };

    let org_id = claims
        .organization_id
        .as_deref()
        .and_then(|s| Uuid::parse_str(s).ok());

    ws.max_message_size(state.max_message_size)
        .on_upgrade(move |socket| handle_socket(socket, user_id, org_id, state))
}

/// Handle a single WebSocket connection after upgrade.
async fn handle_socket(socket: WebSocket, user_id: Uuid, org_id: Option<Uuid>, state: AppState) {
    let (sender, mut receiver) = socket.split();

    let conn_id = state.manager.subscribe(user_id, org_id, sender);

    let heartbeat_interval = Duration::from_secs(state.heartbeat_interval_secs);
    let heartbeat_timeout = Duration::from_secs(state.heartbeat_timeout_secs);

    // Spawn heartbeat task (first tick after heartbeat_interval, not immediately)
    let manager_clone = Arc::clone(&state.manager);
    let heartbeat_handle = tokio::spawn(async move {
        let start = tokio::time::Instant::now() + heartbeat_interval;
        let mut interval = tokio::time::interval_at(start, heartbeat_interval);
        loop {
            interval.tick().await;
            let ping_msg = WsMessage::Ping;
            if manager_clone.send_to_user(user_id, &ping_msg).await.is_err() {
                break;
            }
        }
    });

    // Message receive loop
    let mut last_pong = tokio::time::Instant::now();

    loop {
        let timeout = tokio::time::timeout(
            heartbeat_interval + heartbeat_timeout,
            receiver.next(),
        );

        match timeout.await {
            Ok(Some(Ok(msg))) => {
                match msg {
                    Message::Text(text) => {
                        // Try to parse as IncomingMessage
                        match serde_json::from_str::<IncomingMessage>(&text) {
                            Ok(IncomingMessage::Ping) => {
                                last_pong = tokio::time::Instant::now();
                                let pong = WsMessage::Pong;
                                let _ = state.manager.send_to_user(user_id, &pong).await;
                            }
                            Ok(IncomingMessage::ChatMessage { session_id, content }) => {
                                tracing::debug!(
                                    user_id = %user_id,
                                    session_id = %session_id,
                                    "Chat message received ({} chars)",
                                    content.len()
                                );
                                // Chat messages would be forwarded to the AI service
                                // via HTTP or message queue in production
                            }
                            Ok(IncomingMessage::Subscribe { channels }) => {
                                tracing::debug!(
                                    user_id = %user_id,
                                    channels = ?channels,
                                    "Subscribe request"
                                );
                                // Channel subscription handling for future use
                            }
                            Err(e) => {
                                tracing::warn!(
                                    user_id = %user_id,
                                    "Failed to parse message: {e}"
                                );
                            }
                        }
                    }
                    Message::Ping(_) => {
                        last_pong = tokio::time::Instant::now();
                        // axum auto-responds with Pong for protocol-level pings
                    }
                    Message::Pong(_) => {
                        last_pong = tokio::time::Instant::now();
                    }
                    Message::Close(_) => {
                        tracing::info!(user_id = %user_id, conn_id = %conn_id, "Client sent close");
                        break;
                    }
                    Message::Binary(_) => {
                        // Binary messages not supported
                        tracing::warn!(user_id = %user_id, "Binary message ignored");
                    }
                }
            }
            Ok(Some(Err(e))) => {
                tracing::warn!(user_id = %user_id, "WebSocket error: {e}");
                break;
            }
            Ok(None) => {
                // Stream ended
                tracing::info!(user_id = %user_id, "WebSocket stream ended");
                break;
            }
            Err(_) => {
                // Timeout — check if we got a recent pong
                if last_pong.elapsed() > heartbeat_interval + heartbeat_timeout {
                    tracing::info!(
                        user_id = %user_id,
                        conn_id = %conn_id,
                        "Heartbeat timeout, disconnecting"
                    );
                    break;
                }
            }
        }
    }

    // Cleanup
    heartbeat_handle.abort();
    state.manager.unsubscribe(conn_id);
}

/// POST /publish — Internal API for Python services to push real-time updates.
#[derive(Debug, Deserialize)]
pub struct PublishRequest {
    pub target: String,
    pub message: WsMessage,
}

pub async fn publish_handler(
    State(state): State<AppState>,
    Json(payload): Json<PublishRequest>,
) -> impl IntoResponse {
    let (target_type, target_id_str) = match payload.target.split_once(':') {
        Some(pair) => pair,
        None => {
            return (
                StatusCode::BAD_REQUEST,
                Json(serde_json::json!({ "error": "target must be 'user:<uuid>' or 'org:<uuid>'" })),
            );
        }
    };

    let target_id = match Uuid::parse_str(target_id_str) {
        Ok(id) => id,
        Err(_) => {
            return (
                StatusCode::BAD_REQUEST,
                Json(serde_json::json!({ "error": "invalid UUID in target" })),
            );
        }
    };

    let result = match target_type {
        "user" => state.manager.send_to_user(target_id, &payload.message).await,
        "org" => state.manager.send_to_org(target_id, &payload.message).await,
        _ => {
            return (
                StatusCode::BAD_REQUEST,
                Json(serde_json::json!({ "error": "target type must be 'user' or 'org'" })),
            );
        }
    };

    match result {
        Ok(()) => (
            StatusCode::OK,
            Json(serde_json::json!({ "status": "sent" })),
        ),
        Err(e) => (
            StatusCode::INTERNAL_SERVER_ERROR,
            Json(serde_json::json!({ "error": e.to_string() })),
        ),
    }
}

/// GET /health/live — Liveness probe.
pub async fn health_live() -> Json<serde_json::Value> {
    Json(serde_json::json!({ "status": "ok" }))
}

/// GET /stats — Connection statistics.
#[derive(Serialize)]
pub struct StatsResponse {
    pub active_connections: usize,
    pub users_online: usize,
}

pub async fn stats_handler(State(state): State<AppState>) -> Json<StatsResponse> {
    Json(StatsResponse {
        active_connections: state.manager.connection_count(),
        users_online: state.manager.users_online(),
    })
}

#[cfg(test)]
mod tests {
    use super::*;
    use axum::body::Body;
    use axum::http::Request;
    use axum::routing::{get, post};
    use axum::Router;
    use http_body_util::BodyExt;
    use tower::util::ServiceExt;

    fn test_state() -> AppState {
        AppState {
            manager: Arc::new(ConnectionManager::new()),
            jwt_secret: "test-secret".into(),
            max_connections: 100,
            heartbeat_interval_secs: 30,
            heartbeat_timeout_secs: 10,
            max_message_size: 65_536,
        }
    }

    fn test_app(state: AppState) -> Router {
        Router::new()
            .route("/health/live", get(health_live))
            .route("/stats", get(stats_handler))
            .route("/publish", post(publish_handler))
            .route("/ws", get(ws_handler))
            .with_state(state)
    }

    #[tokio::test]
    async fn test_health_live() {
        let app = test_app(test_state());
        let req = Request::builder()
            .uri("/health/live")
            .body(Body::empty())
            .expect("request");

        let resp = app.oneshot(req).await.expect("response");
        assert_eq!(resp.status(), StatusCode::OK);

        let body = resp.into_body().collect().await.expect("body").to_bytes();
        let json: serde_json::Value = serde_json::from_slice(&body).expect("json");
        assert_eq!(json["status"], "ok");
    }

    #[tokio::test]
    async fn test_stats_empty() {
        let app = test_app(test_state());
        let req = Request::builder()
            .uri("/stats")
            .body(Body::empty())
            .expect("request");

        let resp = app.oneshot(req).await.expect("response");
        assert_eq!(resp.status(), StatusCode::OK);

        let body = resp.into_body().collect().await.expect("body").to_bytes();
        let json: serde_json::Value = serde_json::from_slice(&body).expect("json");
        assert_eq!(json["active_connections"], 0);
        assert_eq!(json["users_online"], 0);
    }

    #[tokio::test]
    async fn test_ws_missing_token() {
        let app = test_app(test_state());
        let req = Request::builder()
            .uri("/ws")
            .body(Body::empty())
            .expect("request");

        let resp = app.oneshot(req).await.expect("response");
        // Missing query param returns 400 (axum query extraction failure)
        assert_eq!(resp.status(), StatusCode::BAD_REQUEST);
    }

    #[tokio::test]
    async fn test_ws_no_upgrade_header() {
        // Without proper WebSocket upgrade headers, axum returns 426 Upgrade Required.
        // Real JWT rejection is tested via integration tests with actual WebSocket clients.
        let app = test_app(test_state());
        let req = Request::builder()
            .uri("/ws?token=invalid.jwt.token")
            .body(Body::empty())
            .expect("request");

        let resp = app.oneshot(req).await.expect("response");
        // axum requires WebSocket upgrade headers; without them → 400 or 426
        assert!(
            resp.status() == StatusCode::BAD_REQUEST
                || resp.status() == StatusCode::UPGRADE_REQUIRED
        );
    }

    #[tokio::test]
    async fn test_publish_invalid_target() {
        let app = test_app(test_state());
        let body = serde_json::json!({
            "target": "invalid",
            "message": { "type": "ping" }
        });

        let req = Request::builder()
            .method("POST")
            .uri("/publish")
            .header("content-type", "application/json")
            .body(Body::from(serde_json::to_string(&body).expect("json")))
            .expect("request");

        let resp = app.oneshot(req).await.expect("response");
        assert_eq!(resp.status(), StatusCode::BAD_REQUEST);
    }

    #[tokio::test]
    async fn test_publish_invalid_uuid() {
        let app = test_app(test_state());
        let body = serde_json::json!({
            "target": "user:not-a-uuid",
            "message": { "type": "ping" }
        });

        let req = Request::builder()
            .method("POST")
            .uri("/publish")
            .header("content-type", "application/json")
            .body(Body::from(serde_json::to_string(&body).expect("json")))
            .expect("request");

        let resp = app.oneshot(req).await.expect("response");
        assert_eq!(resp.status(), StatusCode::BAD_REQUEST);
    }

    #[tokio::test]
    async fn test_publish_valid_user_target_no_connections() {
        let app = test_app(test_state());
        let user_id = Uuid::new_v4();
        let body = serde_json::json!({
            "target": format!("user:{user_id}"),
            "message": { "type": "ping" }
        });

        let req = Request::builder()
            .method("POST")
            .uri("/publish")
            .header("content-type", "application/json")
            .body(Body::from(serde_json::to_string(&body).expect("json")))
            .expect("request");

        let resp = app.oneshot(req).await.expect("response");
        assert_eq!(resp.status(), StatusCode::OK);
    }

    #[tokio::test]
    async fn test_publish_invalid_target_type() {
        let app = test_app(test_state());
        let body = serde_json::json!({
            "target": format!("group:{}", Uuid::new_v4()),
            "message": { "type": "ping" }
        });

        let req = Request::builder()
            .method("POST")
            .uri("/publish")
            .header("content-type", "application/json")
            .body(Body::from(serde_json::to_string(&body).expect("json")))
            .expect("request");

        let resp = app.oneshot(req).await.expect("response");
        assert_eq!(resp.status(), StatusCode::BAD_REQUEST);
    }
}
