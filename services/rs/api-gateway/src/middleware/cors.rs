use axum::http::{HeaderName, HeaderValue, Method};
use tower_http::cors::CorsLayer;

pub fn cors_layer(allowed_origins: &[String], max_age_secs: u64) -> CorsLayer {
    let origins: Vec<HeaderValue> = allowed_origins
        .iter()
        .filter_map(|o| o.parse().ok())
        .collect();

    CorsLayer::new()
        .allow_origin(origins)
        .allow_methods([
            Method::GET,
            Method::POST,
            Method::PUT,
            Method::PATCH,
            Method::DELETE,
            Method::OPTIONS,
        ])
        .allow_headers([
            HeaderName::from_static("authorization"),
            HeaderName::from_static("content-type"),
            HeaderName::from_static("x-request-id"),
        ])
        .expose_headers([
            HeaderName::from_static("x-ratelimit-limit"),
            HeaderName::from_static("x-ratelimit-remaining"),
            HeaderName::from_static("x-ratelimit-reset"),
        ])
        .max_age(std::time::Duration::from_secs(max_age_secs))
}
