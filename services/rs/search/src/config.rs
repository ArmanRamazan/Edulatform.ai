use std::env;

pub struct Config {
    pub port: u16,
    pub index_path: String,
}

impl Config {
    pub fn from_env() -> Self {
        Self {
            port: env::var("SEARCH_PORT")
                .ok()
                .and_then(|v| v.parse().ok())
                .unwrap_or(8010),
            index_path: env::var("INDEX_PATH").unwrap_or_else(|_| "./data/index".to_string()),
        }
    }
}
