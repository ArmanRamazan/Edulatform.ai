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
#[derive(Clone)]
pub struct RateLimiter {
    backend: Arc<Backend>,
    default_config: RateConfig,
    route_limits: Vec<(Method, String, RateConfig)>,
}

impl RateLimiter {
    /// Create a rate limiter backed by Redis.
    pub fn redis(client: redis::Client, default_config: RateConfig) -> Self {
        Self {
            backend: Arc::new(Backend::Redis(client)),
            default_config,
            route_limits: default_route_limits(),
        }
    }

    /// Create an in-memory rate limiter (for tests).
    pub fn in_memory(default_config: RateConfig) -> Self {
        Self {
            backend: Arc::new(Backend::InMemory(Arc::new(Mutex::new(HashMap::new())))),
            default_config,
            route_limits: default_route_limits(),
        }
    }

    /// Determine the rate config for a given request method and path.
    fn config_for_route(&self, method: &Method, path: &str) -> &RateConfig {
        for (m, prefix, config) in &self.route_limits {
            if method == m && path.starts_with(prefix.as_str()) {
                return config;
            }
        }
        &self.default_config
    }

    /// Resolve route group name for the Redis key.
    fn route_group(method: &Method, path: &str) -> String {
        // Match specific route groups
        if method == Method::POST && path.starts_with("/auth/register") {
            return "auth_register".to_string();
        }
        if method == Method::POST && path.starts_with("/auth/login") {
            return "auth_login".to_string();
        }
        if method == Method::POST && path.starts_with("/ai/") {
            return "ai".to_string();
        }
        "default".to_string()
    }

    /// Check rate limit and return (current_count, config) or error on Redis failure.
    async fn check(&self, ip: &str, method: &Method, path: &str) -> Result<(u32, &RateConfig), ()> {
        let config = self.config_for_route(method, path);
        let group = Self::route_group(method, path);
        let window_ts = current_window_timestamp(config.window_secs);
        let key = format!("rl:{}:{}:{}", ip, group, window_ts);

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

async fn redis_incr(client: &redis::Client, key: &str, window_secs: u32) -> Result<u32, redis::RedisError> {
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

/// Extract client IP from X-Forwarded-For header, falling back to peer address.
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

    // Fall back to peer address from connect info (not available in test oneshot)
    "unknown".to_string()
}

/// Axum middleware function for rate limiting.
pub async fn rate_limit_middleware(
    axum::extract::State(limiter): axum::extract::State<RateLimiter>,
    req: Request<Body>,
    next: Next,
) -> Response<Body> {
    let ip = extract_ip(&req);
    let method = req.method().clone();
    let path = req.uri().path().to_string();

    let (count, config) = match limiter.check(&ip, &method, &path).await {
        Ok(result) => result,
        Err(()) => {
            // Should not happen (check returns Ok on Redis failure too), but just in case
            return next.run(req).await;
        }
    };

    let max = config.max_requests;
    let window = config.window_secs;

    if count > max {
        tracing::info!(
            ip = %ip,
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
