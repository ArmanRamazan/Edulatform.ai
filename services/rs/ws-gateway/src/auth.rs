#![allow(clippy::module_name_repetitions)]

use jsonwebtoken::{decode, Algorithm, DecodingKey, Validation};
use serde::{Deserialize, Serialize};

use crate::error::WsError;

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
pub fn verify_token(token: &str, secret: &str) -> Result<Claims, WsError> {
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
        WsError::Auth(format!("invalid or expired token: {e}"))
    })?;

    Ok(token_data.claims)
}

#[cfg(test)]
mod tests {
    use super::*;
    use jsonwebtoken::{encode, EncodingKey, Header};

    fn make_token(secret: &str, exp: usize) -> String {
        let claims = Claims {
            sub: "user-123".into(),
            exp,
            role: "student".into(),
            is_verified: true,
            email_verified: true,
            organization_id: Some("org-abc".into()),
        };
        encode(
            &Header::default(),
            &claims,
            &EncodingKey::from_secret(secret.as_bytes()),
        )
        .expect("encode token")
    }

    #[test]
    fn test_verify_valid_token() {
        let secret = "test-secret";
        let exp = (chrono_now_secs() + 3600) as usize;
        let token = make_token(secret, exp);
        let claims = verify_token(&token, secret).expect("should verify");
        assert_eq!(claims.sub, "user-123");
        assert_eq!(claims.role, "student");
        assert_eq!(claims.organization_id.as_deref(), Some("org-abc"));
    }

    #[test]
    fn test_verify_invalid_secret() {
        let exp = (chrono_now_secs() + 3600) as usize;
        let token = make_token("correct-secret", exp);
        let result = verify_token(&token, "wrong-secret");
        assert!(result.is_err());
    }

    #[test]
    fn test_verify_expired_token() {
        let secret = "test-secret";
        let exp = (chrono_now_secs() - 3600) as usize;
        let token = make_token(secret, exp);
        let result = verify_token(&token, secret);
        assert!(result.is_err());
    }

    #[test]
    fn test_verify_garbage_token() {
        let result = verify_token("not.a.jwt", "secret");
        assert!(result.is_err());
    }

    fn chrono_now_secs() -> i64 {
        std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .expect("time")
            .as_secs() as i64
    }
}
