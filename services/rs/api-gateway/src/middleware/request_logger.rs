use std::time::Instant;

use axum::body::Body;
use axum::http::{HeaderValue, Request, Response};
use axum::middleware::Next;

use crate::auth::Claims;

pub async fn request_logger_middleware(
    mut req: Request<Body>,
    next: Next,
) -> Response<Body> {
    let request_id = req
        .headers()
        .get("X-Request-Id")
        .and_then(|v| v.to_str().ok())
        .map(String::from)
        .unwrap_or_else(|| uuid::Uuid::new_v4().to_string());

    if let Ok(val) = HeaderValue::from_str(&request_id) {
        req.headers_mut().insert("X-Request-Id", val);
    }

    let method = req.method().clone();
    let path = req.uri().path().to_string();
    let ip = extract_ip(&req);

    let user_id = req
        .extensions()
        .get::<Claims>()
        .map(|c| c.sub.clone());

    let start = Instant::now();
    let mut response = next.run(req).await;
    let duration_ms = start.elapsed().as_millis();

    let status = response.status().as_u16();

    if let Ok(val) = HeaderValue::from_str(&request_id) {
        response.headers_mut().insert("X-Request-Id", val);
    }

    let log_fields = serde_json::json!({
        "method": method.as_str(),
        "path": path,
        "status": status,
        "duration_ms": duration_ms,
        "user_id": user_id,
        "ip": ip,
        "request_id": request_id,
    });

    if status >= 500 {
        tracing::error!(target: "request", "{}", log_fields);
    } else if status >= 400 {
        tracing::warn!(target: "request", "{}", log_fields);
    } else {
        tracing::info!(target: "request", "{}", log_fields);
    }

    response
}

fn extract_ip(req: &Request<Body>) -> String {
    if let Some(forwarded) = req.headers().get("X-Forwarded-For") {
        if let Ok(val) = forwarded.to_str() {
            if let Some(first_ip) = val.split(',').next() {
                let trimmed = first_ip.trim();
                if !trimmed.is_empty() {
                    return trimmed.to_string();
                }
            }
        }
    }
    "unknown".to_string()
}
