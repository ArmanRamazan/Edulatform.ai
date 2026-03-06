use std::env;

use crate::error::WsError;

#[derive(Debug, Clone)]
pub struct Config {
    pub port: u16,
    pub jwt_secret: String,
    pub max_connections: usize,
    pub heartbeat_interval_secs: u64,
    pub heartbeat_timeout_secs: u64,
    pub max_message_size: usize,
}

impl Config {
    pub fn from_env() -> Result<Self, WsError> {
        let _ = dotenvy::dotenv();

        let jwt_secret = env::var("JWT_SECRET")
            .map_err(|_| WsError::Config("JWT_SECRET is required".into()))?;

        Ok(Self {
            port: env::var("WS_PORT")
                .ok()
                .and_then(|v| v.parse().ok())
                .unwrap_or(8011),
            jwt_secret,
            max_connections: env::var("MAX_CONNECTIONS")
                .ok()
                .and_then(|v| v.parse().ok())
                .unwrap_or(10_000),
            heartbeat_interval_secs: env::var("HEARTBEAT_INTERVAL_SECS")
                .ok()
                .and_then(|v| v.parse().ok())
                .unwrap_or(30),
            heartbeat_timeout_secs: env::var("HEARTBEAT_TIMEOUT_SECS")
                .ok()
                .and_then(|v| v.parse().ok())
                .unwrap_or(10),
            max_message_size: env::var("MAX_MESSAGE_SIZE")
                .ok()
                .and_then(|v| v.parse().ok())
                .unwrap_or(65_536), // 64KB
        })
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::sync::Mutex;

    // Env var tests must run sequentially since env is shared process state.
    static ENV_LOCK: Mutex<()> = Mutex::new(());

    #[test]
    fn test_config_requires_jwt_secret_and_defaults() {
        let _lock = ENV_LOCK.lock().expect("lock");

        // First: missing JWT_SECRET should fail
        env::remove_var("JWT_SECRET");
        let result = Config::from_env();
        assert!(result.is_err());

        // Second: with JWT_SECRET set, defaults should apply
        env::set_var("JWT_SECRET", "test-secret-for-config");
        let config = Config::from_env().expect("config should load");
        assert_eq!(config.port, 8011);
        assert_eq!(config.max_connections, 10_000);
        assert_eq!(config.heartbeat_interval_secs, 30);
        assert_eq!(config.heartbeat_timeout_secs, 10);
        assert_eq!(config.max_message_size, 65_536);
        assert_eq!(config.jwt_secret, "test-secret-for-config");
        env::remove_var("JWT_SECRET");
    }
}
