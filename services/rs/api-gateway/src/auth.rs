#![allow(clippy::module_name_repetitions)]

use jsonwebtoken::{decode, DecodingKey, Validation, Algorithm};
use serde::{Deserialize, Serialize};

use crate::error::GatewayError;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Claims {
    pub sub: String,
    pub exp: usize,
    pub role: String,
    pub is_verified: bool,
    pub email_verified: bool,
    #[serde(default)]
    pub organization_id: Option<String>,
}

/// Verify and decode a JWT token using HS256.
///
/// Returns the decoded claims on success, or an auth error on failure.
/// Expiration is validated by the jsonwebtoken crate.
pub fn verify_token(token: &str, secret: &str) -> Result<Claims, GatewayError> {
    let mut validation = Validation::new(Algorithm::HS256);
    validation.validate_exp = true;
    validation.set_required_spec_claims(&["sub", "exp"]);

    let token_data = decode::<Claims>(
        token,
        &DecodingKey::from_secret(secret.as_bytes()),
        &validation,
    )
    .map_err(|e| {
        tracing::warn!("JWT verification failed: {}", e);
        GatewayError::Auth("invalid or expired token".into())
    })?;

    Ok(token_data.claims)
}
