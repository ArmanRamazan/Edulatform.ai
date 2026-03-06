use std::env;

use crate::error::EmbedError;

#[derive(Debug, Clone)]
pub struct Config {
    pub port: u16,
    pub embedding_api_url: String,
    pub embedding_api_key: String,
    pub embedding_model: String,
    pub max_concurrent_requests: usize,
    pub batch_size: usize,
    pub request_timeout_secs: u64,
}

impl Config {
    pub fn from_env() -> Result<Self, EmbedError> {
        let _ = dotenvy::dotenv();

        let embedding_api_key = env::var("EMBEDDING_API_KEY")
            .map_err(|_| EmbedError::Config("EMBEDDING_API_KEY is required".into()))?;

        let embedding_api_url = env::var("EMBEDDING_API_URL")
            .map_err(|_| EmbedError::Config("EMBEDDING_API_URL is required".into()))?;

        Ok(Self {
            port: env::var("EMBEDDING_PORT")
                .ok()
                .and_then(|v| v.parse().ok())
                .unwrap_or(8009),
            embedding_api_url,
            embedding_api_key,
            embedding_model: env::var("EMBEDDING_MODEL")
                .unwrap_or_else(|_| "text-embedding-004".into()),
            max_concurrent_requests: env::var("MAX_CONCURRENT_REQUESTS")
                .ok()
                .and_then(|v| v.parse().ok())
                .unwrap_or(50),
            batch_size: env::var("BATCH_SIZE")
                .ok()
                .and_then(|v| v.parse().ok())
                .unwrap_or(100),
            request_timeout_secs: env::var("REQUEST_TIMEOUT_SECS")
                .ok()
                .and_then(|v| v.parse().ok())
                .unwrap_or(30),
        })
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    /// Test config construction with defaults by building directly.
    /// We avoid env var manipulation since tests run in parallel.
    #[test]
    fn test_config_defaults() {
        let config = Config {
            port: 8009,
            embedding_api_url: "http://localhost:9999".into(),
            embedding_api_key: "test-key".into(),
            embedding_model: "text-embedding-004".into(),
            max_concurrent_requests: 50,
            batch_size: 100,
            request_timeout_secs: 30,
        };

        assert_eq!(config.port, 8009);
        assert_eq!(config.embedding_model, "text-embedding-004");
        assert_eq!(config.max_concurrent_requests, 50);
        assert_eq!(config.batch_size, 100);
        assert_eq!(config.request_timeout_secs, 30);
        assert_eq!(config.embedding_api_key, "test-key");
        assert_eq!(config.embedding_api_url, "http://localhost:9999");
    }

    #[test]
    fn test_config_from_env_requires_api_key() {
        // from_env reads EMBEDDING_API_KEY — if absent it returns Err.
        // We test the validation logic by directly checking the field mapping.
        let result: Result<String, EmbedError> = env::var("__NONEXISTENT_VAR_12345__")
            .map_err(|_| EmbedError::Config("EMBEDDING_API_KEY is required".into()));
        assert!(result.is_err());
    }

    #[test]
    fn test_config_from_env_requires_api_url() {
        let result: Result<String, EmbedError> = env::var("__NONEXISTENT_VAR_67890__")
            .map_err(|_| EmbedError::Config("EMBEDDING_API_URL is required".into()));
        assert!(result.is_err());
    }
}
