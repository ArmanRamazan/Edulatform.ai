#[derive(Debug, thiserror::Error)]
pub enum WsError {
    #[error("authentication failed: {0}")]
    Auth(String),

    #[error("configuration error: {0}")]
    Config(String),

    #[error("connection error: {0}")]
    Connection(String),

    #[error("message error: {0}")]
    Message(String),
}
