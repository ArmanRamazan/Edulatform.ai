#![deny(clippy::all)]

use api_gateway::config::Config;
use api_gateway::middleware::rate_limit::{RateConfig, RateLimiter};
use api_gateway::proxy::{self, ProxyService};
use api_gateway::create_router_with_proxy_and_limiter;
use tokio::net::TcpListener;
use tracing_subscriber::EnvFilter;

#[tokio::main]
async fn main() {
    tracing_subscriber::fmt()
        .with_env_filter(EnvFilter::try_from_default_env().unwrap_or_else(|_| "info".into()))
        .init();

    let config = Config::from_env().expect("failed to load config");

    let redis_client = redis::Client::open(config.redis_url.clone())
        .expect("failed to create Redis client");

    let rate_limiter = RateLimiter::redis(
        redis_client,
        RateConfig { max_requests: 100, window_secs: 60 }, // authenticated: 100 req/min per user
        RateConfig { max_requests: 20, window_secs: 60 },  // unauthenticated: 20 req/min per IP
    );

    let routes = proxy::default_routes(&config);
    let proxy_service = ProxyService::new(routes);
    let app = create_router_with_proxy_and_limiter(
        config.jwt_secret.clone(),
        proxy_service,
        rate_limiter,
    );

    let addr = format!("0.0.0.0:{}", config.port);
    tracing::info!("API Gateway listening on {}", addr);

    let listener = TcpListener::bind(&addr)
        .await
        .expect("failed to bind address");

    axum::serve(listener, app)
        .with_graceful_shutdown(shutdown_signal())
        .await
        .expect("server error");
}

async fn shutdown_signal() {
    let ctrl_c = tokio::signal::ctrl_c();

    #[cfg(unix)]
    {
        let mut sigterm =
            tokio::signal::unix::signal(tokio::signal::unix::SignalKind::terminate())
                .expect("failed to install SIGTERM handler");
        tokio::select! {
            _ = ctrl_c => { tracing::info!("received SIGINT, shutting down"); }
            _ = sigterm.recv() => { tracing::info!("received SIGTERM, shutting down"); }
        }
    }

    #[cfg(not(unix))]
    {
        ctrl_c.await.expect("failed to listen for ctrl_c");
        tracing::info!("received SIGINT, shutting down");
    }
}
