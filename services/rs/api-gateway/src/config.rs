use std::env;

use crate::error::GatewayError;

#[derive(Debug, Clone)]
pub struct Config {
    pub port: u16,
    pub redis_url: String,
    pub jwt_secret: String,
    pub identity_url: String,
    pub ai_url: String,
    pub learning_url: String,
    pub rag_url: String,
    pub notification_url: String,
    pub payment_url: String,
}

impl Config {
    pub fn from_env() -> Result<Self, GatewayError> {
        let _ = dotenvy::dotenv();

        let jwt_secret = env::var("JWT_SECRET")
            .map_err(|_| GatewayError::Config("JWT_SECRET is required".into()))?;

        Ok(Self {
            port: env::var("GATEWAY_PORT")
                .ok()
                .and_then(|v| v.parse().ok())
                .unwrap_or(8080),
            redis_url: env::var("REDIS_URL")
                .unwrap_or_else(|_| "redis://localhost:6379".into()),
            jwt_secret,
            identity_url: env::var("IDENTITY_URL")
                .unwrap_or_else(|_| "http://localhost:8001".into()),
            ai_url: env::var("AI_URL")
                .unwrap_or_else(|_| "http://localhost:8006".into()),
            learning_url: env::var("LEARNING_URL")
                .unwrap_or_else(|_| "http://localhost:8007".into()),
            rag_url: env::var("RAG_URL")
                .unwrap_or_else(|_| "http://localhost:8008".into()),
            notification_url: env::var("NOTIFICATION_URL")
                .unwrap_or_else(|_| "http://localhost:8005".into()),
            payment_url: env::var("PAYMENT_URL")
                .unwrap_or_else(|_| "http://localhost:8004".into()),
        })
    }
}
