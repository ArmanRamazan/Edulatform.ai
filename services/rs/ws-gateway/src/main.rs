#![deny(clippy::all)]

use tokio::net::TcpListener;
use tracing_subscriber::EnvFilter;
use ws_gateway::config::Config;

#[tokio::main]
async fn main() {
    tracing_subscriber::fmt()
        .with_env_filter(EnvFilter::try_from_default_env().unwrap_or_else(|_| "info".into()))
        .init();

    let config = Config::from_env().expect("failed to load config");

    let app = ws_gateway::create_router(&config);

    let addr = format!("0.0.0.0:{}", config.port);
    tracing::info!("WebSocket Gateway listening on {}", addr);
    tracing::info!(
        max_connections = config.max_connections,
        heartbeat_interval = config.heartbeat_interval_secs,
        heartbeat_timeout = config.heartbeat_timeout_secs,
        max_message_size = config.max_message_size,
        "Configuration loaded"
    );

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
