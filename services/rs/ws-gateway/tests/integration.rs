use std::sync::Arc;
use std::time::Duration;

use futures::{SinkExt, StreamExt};
use jsonwebtoken::{encode, EncodingKey, Header};
use serde::{Deserialize, Serialize};
use tokio::net::TcpListener;
use tokio_tungstenite::tungstenite;
use uuid::Uuid;
use ws_gateway::connection::ConnectionManager;
use ws_gateway::routes::AppState;

const JWT_SECRET: &str = "integration-test-secret";

#[derive(Debug, Clone, Serialize, Deserialize)]
struct TestClaims {
    sub: String,
    exp: usize,
    role: String,
    is_verified: bool,
    email_verified: bool,
    #[serde(skip_serializing_if = "Option::is_none")]
    organization_id: Option<String>,
}

fn make_jwt(user_id: &str, org_id: Option<&str>) -> String {
    let exp = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .expect("time")
        .as_secs() as usize
        + 3600;

    let claims = TestClaims {
        sub: user_id.into(),
        exp,
        role: "student".into(),
        is_verified: true,
        email_verified: true,
        organization_id: org_id.map(String::from),
    };

    encode(
        &Header::default(),
        &claims,
        &EncodingKey::from_secret(JWT_SECRET.as_bytes()),
    )
    .expect("encode jwt")
}

fn test_state() -> AppState {
    AppState {
        manager: Arc::new(ConnectionManager::new()),
        jwt_secret: JWT_SECRET.into(),
        max_connections: 100,
        heartbeat_interval_secs: 60, // Long interval so tests aren't affected
        heartbeat_timeout_secs: 10,
        max_message_size: 65_536,
    }
}

async fn start_server(state: AppState) -> String {
    let app = ws_gateway::create_router_with_state(state);
    let listener = TcpListener::bind("127.0.0.1:0").await.expect("bind");
    let addr = listener.local_addr().expect("addr");
    tokio::spawn(async move {
        axum::serve(listener, app).await.expect("serve");
    });
    format!("127.0.0.1:{}", addr.port())
}

#[tokio::test]
async fn test_ws_connect_with_valid_jwt() {
    let state = test_state();
    let manager = Arc::clone(&state.manager);
    let addr = start_server(state).await;

    let user_id = Uuid::new_v4();
    let token = make_jwt(&user_id.to_string(), None);

    let url = format!("ws://{addr}/ws?token={token}");
    let (ws, _resp) = tokio_tungstenite::connect_async(&url)
        .await
        .expect("connect");

    // Give server a moment to register the connection
    tokio::time::sleep(Duration::from_millis(50)).await;

    assert_eq!(manager.connection_count(), 1);
    assert_eq!(manager.users_online(), 1);

    drop(ws);
    tokio::time::sleep(Duration::from_millis(50)).await;
}

#[tokio::test]
async fn test_ws_invalid_jwt_rejected() {
    let state = test_state();
    let addr = start_server(state).await;

    let url = format!("ws://{addr}/ws?token=bad.jwt.token");
    let result = tokio_tungstenite::connect_async(&url).await;

    // Should fail — server responds with 401 before upgrade
    assert!(result.is_err());
}

#[tokio::test]
async fn test_send_to_user_via_publish() {
    let state = test_state();
    let addr = start_server(state).await;

    let user_id = Uuid::new_v4();
    let token = make_jwt(&user_id.to_string(), None);

    let url = format!("ws://{addr}/ws?token={token}");
    let (mut ws, _) = tokio_tungstenite::connect_async(&url)
        .await
        .expect("connect");

    tokio::time::sleep(Duration::from_millis(50)).await;

    // Publish a notification via HTTP
    let client = reqwest::Client::new();
    let notification_id = Uuid::new_v4();
    let publish_body = serde_json::json!({
        "target": format!("user:{user_id}"),
        "message": {
            "type": "notification",
            "id": notification_id.to_string(),
            "notification_type": "mission_ready",
            "title": "New Mission",
            "body": "Your daily mission is ready"
        }
    });

    let resp = client
        .post(format!("http://{addr}/publish"))
        .json(&publish_body)
        .send()
        .await
        .expect("publish");
    assert_eq!(resp.status(), 200);

    // Read the message from WebSocket
    let msg = tokio::time::timeout(Duration::from_secs(2), ws.next())
        .await
        .expect("timeout")
        .expect("stream")
        .expect("message");

    if let tungstenite::Message::Text(text) = msg {
        let parsed: serde_json::Value = serde_json::from_str(&text).expect("json");
        assert_eq!(parsed["type"], "notification");
        assert_eq!(parsed["title"], "New Mission");
        assert_eq!(parsed["body"], "Your daily mission is ready");
    } else {
        panic!("expected text message, got {:?}", msg);
    }

    drop(ws);
}

#[tokio::test]
async fn test_multiple_connections_same_user() {
    let state = test_state();
    let manager = Arc::clone(&state.manager);
    let addr = start_server(state).await;

    let user_id = Uuid::new_v4();
    let token = make_jwt(&user_id.to_string(), None);
    let url = format!("ws://{addr}/ws?token={token}");

    // Two connections (two tabs)
    let (mut ws1, _) = tokio_tungstenite::connect_async(&url)
        .await
        .expect("connect1");
    let (mut ws2, _) = tokio_tungstenite::connect_async(&url)
        .await
        .expect("connect2");

    tokio::time::sleep(Duration::from_millis(50)).await;

    assert_eq!(manager.connection_count(), 2);
    assert_eq!(manager.users_online(), 1); // Same user

    // Publish a message — both tabs should receive it
    let client = reqwest::Client::new();
    let publish_body = serde_json::json!({
        "target": format!("user:{user_id}"),
        "message": { "type": "ping" }
    });

    client
        .post(format!("http://{addr}/publish"))
        .json(&publish_body)
        .send()
        .await
        .expect("publish");

    // Both should get the message
    let msg1 = tokio::time::timeout(Duration::from_secs(2), ws1.next())
        .await
        .expect("timeout1")
        .expect("stream1")
        .expect("msg1");

    let msg2 = tokio::time::timeout(Duration::from_secs(2), ws2.next())
        .await
        .expect("timeout2")
        .expect("stream2")
        .expect("msg2");

    assert!(matches!(msg1, tungstenite::Message::Text(_)));
    assert!(matches!(msg2, tungstenite::Message::Text(_)));

    drop(ws1);
    drop(ws2);
}

#[tokio::test]
async fn test_disconnect_cleanup() {
    let state = test_state();
    let manager = Arc::clone(&state.manager);
    let addr = start_server(state).await;

    let user_id = Uuid::new_v4();
    let token = make_jwt(&user_id.to_string(), None);
    let url = format!("ws://{addr}/ws?token={token}");

    let (ws, _) = tokio_tungstenite::connect_async(&url)
        .await
        .expect("connect");

    tokio::time::sleep(Duration::from_millis(50)).await;
    assert_eq!(manager.connection_count(), 1);

    // Close the connection
    drop(ws);

    // Give the server time to detect disconnect and clean up
    tokio::time::sleep(Duration::from_millis(200)).await;

    assert_eq!(manager.connection_count(), 0);
    assert_eq!(manager.users_online(), 0);
}

#[tokio::test]
async fn test_client_sends_ping_gets_pong() {
    let state = test_state();
    let addr = start_server(state).await;

    let user_id = Uuid::new_v4();
    let token = make_jwt(&user_id.to_string(), None);
    let url = format!("ws://{addr}/ws?token={token}");

    let (mut ws, _) = tokio_tungstenite::connect_async(&url)
        .await
        .expect("connect");

    tokio::time::sleep(Duration::from_millis(50)).await;

    // Send application-level ping
    let ping_msg = serde_json::json!({"type": "ping"});
    ws.send(tungstenite::Message::Text(ping_msg.to_string().into()))
        .await
        .expect("send ping");

    // Should receive pong
    let msg = tokio::time::timeout(Duration::from_secs(2), ws.next())
        .await
        .expect("timeout")
        .expect("stream")
        .expect("message");

    if let tungstenite::Message::Text(text) = msg {
        let parsed: serde_json::Value = serde_json::from_str(&text).expect("json");
        assert_eq!(parsed["type"], "pong");
    } else {
        panic!("expected text message, got {:?}", msg);
    }

    drop(ws);
}

#[tokio::test]
async fn test_stats_endpoint() {
    let state = test_state();
    let addr = start_server(state).await;

    let user_id = Uuid::new_v4();
    let token = make_jwt(&user_id.to_string(), None);
    let url = format!("ws://{addr}/ws?token={token}");

    // Before connect
    let client = reqwest::Client::new();
    let resp = client
        .get(format!("http://{addr}/stats"))
        .send()
        .await
        .expect("stats");
    let stats: serde_json::Value = resp.json().await.expect("json");
    assert_eq!(stats["active_connections"], 0);
    assert_eq!(stats["users_online"], 0);

    // Connect
    let (_ws, _) = tokio_tungstenite::connect_async(&url)
        .await
        .expect("connect");

    tokio::time::sleep(Duration::from_millis(50)).await;

    let resp = client
        .get(format!("http://{addr}/stats"))
        .send()
        .await
        .expect("stats");
    let stats: serde_json::Value = resp.json().await.expect("json");
    assert_eq!(stats["active_connections"], 1);
    assert_eq!(stats["users_online"], 1);
}

#[tokio::test]
async fn test_publish_org_broadcast() {
    let state = test_state();
    let addr = start_server(state).await;

    let org_id = Uuid::new_v4();
    let user1 = Uuid::new_v4();
    let user2 = Uuid::new_v4();

    let token1 = make_jwt(&user1.to_string(), Some(&org_id.to_string()));
    let token2 = make_jwt(&user2.to_string(), Some(&org_id.to_string()));

    let (mut ws1, _) = tokio_tungstenite::connect_async(format!("ws://{addr}/ws?token={token1}"))
        .await
        .expect("connect1");
    let (mut ws2, _) = tokio_tungstenite::connect_async(format!("ws://{addr}/ws?token={token2}"))
        .await
        .expect("connect2");

    tokio::time::sleep(Duration::from_millis(50)).await;

    // Publish to org
    let client = reqwest::Client::new();
    let body = serde_json::json!({
        "target": format!("org:{org_id}"),
        "message": {
            "type": "notification",
            "id": Uuid::new_v4().to_string(),
            "notification_type": "org_update",
            "title": "Team Update",
            "body": "New docs available"
        }
    });

    let resp = client
        .post(format!("http://{addr}/publish"))
        .json(&body)
        .send()
        .await
        .expect("publish");
    assert_eq!(resp.status(), 200);

    // Both users should receive the message
    let msg1 = tokio::time::timeout(Duration::from_secs(2), ws1.next())
        .await
        .expect("timeout1")
        .expect("stream1")
        .expect("msg1");
    let msg2 = tokio::time::timeout(Duration::from_secs(2), ws2.next())
        .await
        .expect("timeout2")
        .expect("stream2")
        .expect("msg2");

    if let tungstenite::Message::Text(text) = msg1 {
        let parsed: serde_json::Value = serde_json::from_str(&text).expect("json");
        assert_eq!(parsed["title"], "Team Update");
    } else {
        panic!("expected text message for user1");
    }

    if let tungstenite::Message::Text(text) = msg2 {
        let parsed: serde_json::Value = serde_json::from_str(&text).expect("json");
        assert_eq!(parsed["title"], "Team Update");
    } else {
        panic!("expected text message for user2");
    }

    drop(ws1);
    drop(ws2);
}
