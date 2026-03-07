use std::collections::HashMap;
use std::sync::{Arc, Mutex};
use std::time::{SystemTime, UNIX_EPOCH};

use axum::body::Body;
use axum::http::{Method, Request, Response, StatusCode};
use axum::middleware::Next;
use serde_json::json;

/// Configuration for a rate limit window.
#[derive(Debug, Clone)]
pub struct RateConfig {
    pub max_requests: u32,
    pub window_secs: u32,
}

/// Backend trait for rate limit storage.
enum Backend {
    Redis(redis::Client),
    InMemory(Arc<Mutex<HashMap<String, u32>>>),
}

/// Sliding window rate limiter supporting Redis or in-memory backends.
///
/// Supports two distinct limit tiers:
/// - `auth_default`: applied to authenticated requests (keyed by user_id)
/// - `unauth_default`: applied to unauthenticated requests (keyed by IP)
///
/// Route-specific limits (e.g. /auth/register) override the defaults for all requests.
#[derive(Clone)]
pub struct RateLimiter {
    backend: Arc<Backend>,
    /// Default limit for authenticated users (100 req/min in production).
    auth_default: RateConfig,
    /// Default limit for unauthenticated users (20 req/min in production).
    unauth_default: RateConfig,
    route_limits: Vec<(Method, String, RateConfig)>,
}

impl RateLimiter {
    /// Create a rate limiter backed by Redis with separate auth/unauth defaults.
    pub fn redis(
        client: redis::Client,
        auth_default: RateConfig,
        unauth_default: RateConfig,
    ) -> Self {
        Self {
            backend: Arc::new(Backend::Redis(client)),
            auth_default,
            unauth_default,
            route_limits: default_route_limits(),
        }
    }

    /// Create an in-memory rate limiter using the same config for both auth and
    /// unauthenticated requests. Intended for use with `create_router_with_rate_limiter`
    /// (IP-only tests that don't need separate auth/unauth tiers).
    pub fn in_memory(default_config: RateConfig) -> Self {
        Self::in_memory_with_auth_config(default_config.clone(), default_config)
    }

    /// Create an in-memory rate limiter with explicit auth and unauth configs.
    ///
    /// - `auth_default`  — limit applied to authenticated requests (user_id key)
    /// - `unauth_default` — limit applied to unauthenticated requests (IP key)
    pub fn in_memory_with_auth_config(auth_default: RateConfig, unauth_default: RateConfig) -> Self {
        Self {
            backend: Arc::new(Backend::InMemory(Arc::new(Mutex::new(HashMap::new())))),
            auth_default,
            unauth_default,
            route_limits: default_route_limits(),
        }
    }

    /// Determine the applicable rate config for a request.
    ///
    /// Route-specific rules take priority; otherwise the auth/unauth default is used.
    fn config_for_route(&self, is_auth: bool, method: &Method, path: &str) -> &RateConfig {
        for (m, prefix, config) in &self.route_limits {
            if method == m && path.starts_with(prefix.as_str()) {
                return config;
            }
        }
        if is_auth {
            &self.auth_default
        } else {
            &self.unauth_default
        }
    }

    /// Resolve route group name used as part of the Redis/in-memory key.
    fn route_group(method: &Method, path: &str) -> &'static str {
        if method == Method::POST && path.starts_with("/auth/register") {
            return "auth_register";
        }
        if method == Method::POST && path.starts_with("/auth/login") {
            return "auth_login";
        }
        if method == Method::POST && path.starts_with("/ai/") {
            return "ai";
        }
        "default"
    }

    /// Increment the rate limit counter and return `(current_count, config)`.
    ///
    /// Key strategy:
    /// - Authenticated (`user_id = Some(uid)`): `rl:user:{uid}:{group}:{window_ts}`
    /// - Unauthenticated (`user_id = None`):   `rl:ip:{ip}:{group}:{window_ts}`
    ///
    /// Returns `Err(())` only in unreachable cases; Redis failures are handled by
    /// fail-open (returns `Ok((0, config))`).
    async fn check(
        &self,
        user_id: Option<&str>,
        ip: &str,
        method: &Method,
        path: &str,
    ) -> Result<(u32, &RateConfig), ()> {
        let is_auth = user_id.is_some();
        let config = self.config_for_route(is_auth, method, path);
        let group = Self::route_group(method, path);
        let window_ts = current_window_timestamp(config.window_secs);

        let key = match user_id {
            Some(uid) => format!("rl:user:{uid}:{group}:{window_ts}"),
            None => format!("rl:ip:{ip}:{group}:{window_ts}"),
        };

        let count = match self.backend.as_ref() {
            Backend::Redis(client) => {
                match redis_incr(client, &key, config.window_secs).await {
                    Ok(c) => c,
                    Err(_) => {
                        // Fail-open: allow request if Redis is down
                        tracing::warn!("Redis unavailable for rate limiting, allowing request");
                        return Ok((0, config));
                    }
                }
            }
            Backend::InMemory(store) => {
                let mut map = store.lock().unwrap();
                let counter = map.entry(key).or_insert(0);
                *counter += 1;
                *counter
            }
        };

        Ok((count, config))
    }
}

fn default_route_limits() -> Vec<(Method, String, RateConfig)> {
    vec![
        (
            Method::POST,
            "/auth/register".to_string(),
            RateConfig {
                max_requests: 5,
                window_secs: 60,
            },
        ),
        (
            Method::POST,
            "/auth/login".to_string(),
            RateConfig {
                max_requests: 10,
                window_secs: 60,
            },
        ),
        (
            Method::POST,
            "/ai/".to_string(),
            RateConfig {
                max_requests: 30,
                window_secs: 60,
            },
        ),
    ]
}

fn current_window_timestamp(window_secs: u32) -> u64 {
    let now = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .expect("time went backwards")
        .as_secs();
    now / u64::from(window_secs)
}

fn reset_timestamp(window_secs: u32) -> u64 {
    let window_ts = current_window_timestamp(window_secs);
    (window_ts + 1) * u64::from(window_secs)
}

async fn redis_incr(
    client: &redis::Client,
    key: &str,
    window_secs: u32,
) -> Result<u32, redis::RedisError> {
    use redis::AsyncCommands;
    let mut conn = client.get_multiplexed_async_connection().await?;
    let count: u32 = redis::cmd("INCR")
        .arg(key)
        .query_async(&mut conn)
        .await?;
    if count == 1 {
        let _: () = conn.expire(key, i64::from(window_secs)).await?;
    }
    Ok(count)
}

/// Extract client IP from X-Forwarded-For header, falling back to "unknown".
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
    // Peer address from connect info is not available in test oneshot
    "unknown".to_string()
}

/// Axum middleware function for rate limiting.
///
/// Checks `req.extensions()` for decoded JWT `Claims` (inserted by the auth
/// middleware when it runs as an outer layer).  If claims are present the
/// request is considered authenticated and the per-user bucket is used;
/// otherwise the per-IP bucket is used.
pub async fn rate_limit_middleware(
    axum::extract::State(limiter): axum::extract::State<RateLimiter>,
    req: Request<Body>,
    next: Next,
) -> Response<Body> {
    // Extract user_id from JWT claims if auth middleware already ran
    let user_id = req
        .extensions()
        .get::<crate::auth::Claims>()
        .map(|c| c.sub.clone());

    let ip = extract_ip(&req);
    let method = req.method().clone();
    let path = req.uri().path().to_string();

    let (count, config) = match limiter.check(user_id.as_deref(), &ip, &method, &path).await {
        Ok(result) => result,
        Err(()) => return next.run(req).await,
    };

    let max = config.max_requests;
    let window = config.window_secs;

    if count > max {
        tracing::info!(
            ip = %ip,
            user_id = ?user_id,
            path = %path,
            limit = max,
            "rate limit exceeded"
        );

        let reset = reset_timestamp(window);
        let retry_after = reset.saturating_sub(
            SystemTime::now()
                .duration_since(UNIX_EPOCH)
                .expect("time went backwards")
                .as_secs(),
        );

        let body = serde_json::to_string(&json!({"error": "rate limit exceeded"}))
            .unwrap_or_default();

        Response::builder()
            .status(StatusCode::TOO_MANY_REQUESTS)
            .header("Content-Type", "application/json")
            .header("X-RateLimit-Limit", max.to_string())
            .header("X-RateLimit-Remaining", "0")
            .header("X-RateLimit-Reset", reset.to_string())
            .header("Retry-After", retry_after.to_string())
            .body(Body::from(body))
            .unwrap()
    } else {
        let remaining = max - count;
        let reset = reset_timestamp(window);

        let mut response = next.run(req).await;

        let headers = response.headers_mut();
        headers.insert("X-RateLimit-Limit", max.to_string().parse().unwrap());
        headers.insert(
            "X-RateLimit-Remaining",
            remaining.to_string().parse().unwrap(),
        );
        headers.insert("X-RateLimit-Reset", reset.to_string().parse().unwrap());

        response
    }
}
