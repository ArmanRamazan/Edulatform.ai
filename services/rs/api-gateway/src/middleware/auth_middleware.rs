use axum::{
    body::Body,
    extract::State,
    http::{HeaderValue, Request, Response, StatusCode},
    middleware::{self, Next},
    Router,
};
use serde_json::json;

use crate::auth;

/// Routes that do not require JWT authentication.
const PUBLIC_PREFIXES: &[&str] = &[
    "/health/",
    "/auth/register",
    "/auth/login",
    "/auth/forgot-password",
];

fn is_public_route(path: &str) -> bool {
    PUBLIC_PREFIXES
        .iter()
        .any(|prefix| path.starts_with(prefix))
}

/// Apply JWT auth middleware to a router using `from_fn_with_state`.
///
/// Public routes bypass authentication.
/// Protected routes require a valid `Authorization: Bearer <token>` header.
/// On success, X-User-* headers are set for upstream Python services.
pub fn apply_auth(router: Router, jwt_secret: String) -> Router {
    router.layer(middleware::from_fn_with_state(
        jwt_secret,
        auth_middleware_fn,
    ))
}

async fn auth_middleware_fn(
    State(jwt_secret): State<String>,
    mut req: Request<Body>,
    next: Next,
) -> Response<Body> {
    let path = req.uri().path().to_string();

    // Skip auth for public routes
    if is_public_route(&path) {
        return next.run(req).await;
    }

    // Extract Bearer token
    let auth_header = req
        .headers()
        .get("Authorization")
        .and_then(|v| v.to_str().ok());

    let token = match auth_header {
        Some(header) if header.starts_with("Bearer ") => &header[7..],
        _ => {
            tracing::warn!("missing or malformed Authorization header for {}", path);
            return unauthorized_response("missing or invalid authorization header");
        }
    };

    // Verify token
    let claims = match auth::verify_token(token, &jwt_secret) {
        Ok(claims) => claims,
        Err(_) => {
            return unauthorized_response("invalid or expired token");
        }
    };

    // Store claims in extensions for downstream handlers
    req.extensions_mut().insert(claims.clone());

    // Set X-User-* headers for upstream Python services
    let headers = req.headers_mut();

    if let Ok(val) = HeaderValue::from_str(&claims.sub) {
        headers.insert("X-User-Id", val);
    }
    if let Ok(val) = HeaderValue::from_str(&claims.role) {
        headers.insert("X-User-Role", val);
    }
    if let Ok(val) = HeaderValue::from_str(&claims.is_verified.to_string()) {
        headers.insert("X-User-Verified", val);
    }
    if let Some(org_id) = &claims.organization_id {
        if let Ok(val) = HeaderValue::from_str(org_id) {
            headers.insert("X-Organization-Id", val);
        }
    }

    next.run(req).await
}

fn unauthorized_response(message: &str) -> Response<Body> {
    let body = json!({ "error": message }).to_string();
    Response::builder()
        .status(StatusCode::UNAUTHORIZED)
        .header("Content-Type", "application/json")
        .body(Body::from(body))
        .expect("failed to build unauthorized response")
}
