use std::time::{Duration, Instant};

use axum::{
    body::Body,
    extract::State,
    http::{Request, Response, StatusCode, Uri},
};
use reqwest::Client;
use serde_json::json;

use crate::auth::Claims;

#[derive(Debug, Clone)]
pub struct RouteRule {
    pub prefix: String,
    pub upstream: String,
    pub strip_prefix: bool,
}

#[derive(Debug, Clone)]
pub struct ProxyService {
    client: Client,
    routes: Vec<RouteRule>,
}

/// Hop-by-hop headers that must not be forwarded.
const HOP_BY_HOP: &[&str] = &[
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailers",
    "transfer-encoding",
    "upgrade",
];

impl ProxyService {
    pub fn new(routes: Vec<RouteRule>) -> Self {
        let client = Client::builder()
            .timeout(Duration::from_secs(30))
            .pool_max_idle_per_host(32)
            .build()
            .expect("failed to build reqwest client");
        Self { client, routes }
    }

    pub fn match_route(&self, path: &str) -> Option<&RouteRule> {
        self.routes
            .iter()
            .find(|r| path == r.prefix || path.starts_with(&format!("{}/", r.prefix)))
    }

    fn build_upstream_url(&self, rule: &RouteRule, original_uri: &Uri) -> String {
        let path = original_uri.path();
        let upstream_path = if rule.strip_prefix {
            path.strip_prefix(&rule.prefix).unwrap_or(path)
        } else {
            path
        };

        let upstream_path = if upstream_path.is_empty() {
            "/"
        } else {
            upstream_path
        };

        match original_uri.query() {
            Some(q) => format!("{}{}?{}", rule.upstream, upstream_path, q),
            None => format!("{}{}", rule.upstream, upstream_path),
        }
    }
}

pub async fn proxy_handler(
    State(proxy): State<ProxyService>,
    req: Request<Body>,
) -> Response<Body> {
    let path = req.uri().path().to_string();
    let method = req.method().clone();

    let rule = match proxy.match_route(&path) {
        Some(r) => r.clone(),
        None => {
            let body = json!({ "error": "not found" }).to_string();
            return Response::builder()
                .status(StatusCode::NOT_FOUND)
                .header("Content-Type", "application/json")
                .body(Body::from(body))
                .expect("failed to build 404 response");
        }
    };

    let upstream_url = proxy.build_upstream_url(&rule, req.uri());
    let start = Instant::now();

    // Build upstream request
    let mut upstream_req = proxy
        .client
        .request(req.method().clone(), &upstream_url);

    // Forward headers (skip hop-by-hop and host)
    for (name, value) in req.headers() {
        let name_lower = name.as_str().to_lowercase();
        if name_lower == "host" || HOP_BY_HOP.contains(&name_lower.as_str()) {
            continue;
        }
        if let Ok(v) = reqwest::header::HeaderValue::from_bytes(value.as_bytes()) {
            upstream_req = upstream_req.header(name.as_str(), v);
        }
    }

    // Forward X-User-* headers from claims in extensions
    if let Some(claims) = req.extensions().get::<Claims>() {
        upstream_req = upstream_req.header("X-User-Id", &claims.sub);
        upstream_req = upstream_req.header("X-User-Role", &claims.role);
        upstream_req = upstream_req.header("X-User-Verified", claims.is_verified.to_string());
        if let Some(org_id) = &claims.organization_id {
            upstream_req = upstream_req.header("X-Organization-Id", org_id);
        }
    }

    // Forward body
    let body_bytes = match axum::body::to_bytes(req.into_body(), 10 * 1024 * 1024).await {
        Ok(b) => b,
        Err(e) => {
            tracing::error!("failed to read request body: {}", e);
            let body = json!({ "error": "failed to read request body" }).to_string();
            return Response::builder()
                .status(StatusCode::BAD_REQUEST)
                .header("Content-Type", "application/json")
                .body(Body::from(body))
                .expect("failed to build error response");
        }
    };

    if !body_bytes.is_empty() {
        upstream_req = upstream_req.body(body_bytes);
    }

    // Send request to upstream
    let upstream_resp = match upstream_req.send().await {
        Ok(resp) => resp,
        Err(e) => {
            let duration = start.elapsed();
            tracing::error!(
                method = %method,
                path = %path,
                upstream = %upstream_url,
                duration_ms = %duration.as_millis(),
                "upstream request failed: {}",
                e
            );

            let (status, msg) = if e.is_timeout() {
                (StatusCode::GATEWAY_TIMEOUT, "upstream timeout")
            } else {
                (StatusCode::BAD_GATEWAY, "upstream unavailable")
            };

            let body = json!({ "error": msg }).to_string();
            return Response::builder()
                .status(status)
                .header("Content-Type", "application/json")
                .body(Body::from(body))
                .expect("failed to build error response");
        }
    };

    let duration = start.elapsed();
    tracing::debug!(
        method = %method,
        path = %path,
        upstream = %upstream_url,
        duration_ms = %duration.as_millis(),
        status = %upstream_resp.status().as_u16(),
        "proxied request"
    );

    // Build response back to client
    let status = upstream_resp.status();
    let mut response_builder = Response::builder().status(status.as_u16());

    for (name, value) in upstream_resp.headers() {
        let name_lower = name.as_str().to_lowercase();
        if HOP_BY_HOP.contains(&name_lower.as_str()) {
            continue;
        }
        if let Ok(v) = axum::http::HeaderValue::from_bytes(value.as_bytes()) {
            response_builder = response_builder.header(name.as_str(), v);
        }
    }

    let resp_bytes = match upstream_resp.bytes().await {
        Ok(b) => b,
        Err(e) => {
            tracing::error!("failed to read upstream response: {}", e);
            let body = json!({ "error": "failed to read upstream response" }).to_string();
            return Response::builder()
                .status(StatusCode::BAD_GATEWAY)
                .header("Content-Type", "application/json")
                .body(Body::from(body))
                .expect("failed to build error response");
        }
    };

    response_builder
        .body(Body::from(resp_bytes))
        .expect("failed to build proxy response")
}

/// Build the default route rules from a Config.
pub fn default_routes(config: &crate::config::Config) -> Vec<RouteRule> {
    let identity = &config.identity_url;
    let payment = &config.payment_url;
    let notification = &config.notification_url;
    let ai = &config.ai_url;
    let learning = &config.learning_url;
    let rag = &config.rag_url;

    vec![
        // Identity service
        rule("/auth", identity),
        rule("/me", identity),
        rule("/users", identity),
        rule("/organizations", identity),
        rule("/follow", identity),
        rule("/referral", identity),
        // Payment service
        rule("/payments", payment),
        rule("/subscriptions", payment),
        rule("/coupons", payment),
        rule("/earnings", payment),
        rule("/gifts", payment),
        rule("/org-subscriptions", payment),
        // Notification service
        rule("/notifications", notification),
        rule("/conversations", notification),
        rule("/messages", notification),
        rule("/streak-reminders", notification),
        rule("/flashcard-reminders", notification),
        // AI service
        rule("/ai", ai),
        // Learning service
        rule("/quizzes", learning),
        rule("/flashcards", learning),
        rule("/concepts", learning),
        rule("/missions", learning),
        rule("/trust-level", learning),
        rule("/daily", learning),
        rule("/streaks", learning),
        rule("/leaderboard", learning),
        rule("/discussions", learning),
        rule("/xp", learning),
        rule("/badges", learning),
        rule("/pretests", learning),
        rule("/velocity", learning),
        rule("/activity", learning),
        rule("/study-groups", learning),
        // RAG service
        rule("/kb", rag),
        rule("/sources", rag),
        rule("/upload", rag),
        rule("/templates", rag),
    ]
}

fn rule(prefix: &str, upstream: &str) -> RouteRule {
    RouteRule {
        prefix: prefix.to_string(),
        upstream: upstream.to_string(),
        strip_prefix: false,
    }
}
