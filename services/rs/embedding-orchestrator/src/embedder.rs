use std::sync::Arc;
use std::time::Duration;

use reqwest::Client;
use serde::{Deserialize, Serialize};
use tokio::sync::Semaphore;

use crate::config::Config;
use crate::error::EmbedError;

#[derive(Clone)]
pub struct EmbeddingService {
    client: Client,
    semaphore: Arc<Semaphore>,
    api_url: String,
    api_key: String,
    model: String,
    batch_size: usize,
}

#[derive(Serialize)]
struct EmbedRequest {
    model: String,
    content: EmbedContent,
}

#[derive(Serialize)]
struct EmbedContent {
    parts: Vec<EmbedPart>,
}

#[derive(Serialize)]
struct EmbedPart {
    text: String,
}

#[derive(Deserialize)]
struct EmbedResponse {
    embedding: Option<EmbedValues>,
}

#[derive(Deserialize)]
struct EmbedValues {
    values: Vec<f32>,
}

/// Result of a batch embedding request: either success with vector or failure with index.
pub struct BatchResult {
    pub embeddings: Vec<Vec<f32>>,
    pub failed: Vec<usize>,
}

impl EmbeddingService {
    pub fn new(config: &Config) -> Self {
        let client = Client::builder()
            .timeout(Duration::from_secs(config.request_timeout_secs))
            .pool_max_idle_per_host(config.max_concurrent_requests)
            .build()
            .expect("failed to build reqwest client");

        Self {
            client,
            semaphore: Arc::new(Semaphore::new(config.max_concurrent_requests)),
            api_url: config.embedding_api_url.clone(),
            api_key: config.embedding_api_key.clone(),
            model: config.embedding_model.clone(),
            batch_size: config.batch_size,
        }
    }

    /// Create an EmbeddingService with a custom reqwest::Client (for testing).
    #[cfg(test)]
    pub fn with_client(client: Client, config: &Config) -> Self {
        Self {
            client,
            semaphore: Arc::new(Semaphore::new(config.max_concurrent_requests)),
            api_url: config.embedding_api_url.clone(),
            api_key: config.embedding_api_key.clone(),
            model: config.embedding_model.clone(),
            batch_size: config.batch_size,
        }
    }

    pub async fn embed_single(&self, text: &str) -> Result<Vec<f32>, EmbedError> {
        if text.is_empty() {
            return Err(EmbedError::InvalidInput("text must not be empty".into()));
        }

        let _permit = self
            .semaphore
            .acquire()
            .await
            .map_err(|e| EmbedError::Api(format!("semaphore closed: {e}")))?;

        self.call_api(text).await
    }

    pub async fn embed_batch(&self, texts: Vec<String>) -> BatchResult {
        if texts.is_empty() {
            return BatchResult {
                embeddings: vec![],
                failed: vec![],
            };
        }

        let chunks: Vec<(usize, Vec<(usize, String)>)> = texts
            .into_iter()
            .enumerate()
            .collect::<Vec<_>>()
            .chunks(self.batch_size)
            .enumerate()
            .map(|(chunk_idx, chunk)| (chunk_idx, chunk.to_vec()))
            .collect();

        let mut handles = Vec::new();

        for (_chunk_idx, items) in chunks {
            for (global_idx, text) in items {
                let svc = self.clone();
                let handle =
                    tokio::spawn(async move { (global_idx, svc.embed_single_with_retry(&text).await) });
                handles.push(handle);
            }
        }

        let mut results: Vec<(usize, Result<Vec<f32>, EmbedError>)> =
            Vec::with_capacity(handles.len());

        for handle in handles {
            match handle.await {
                Ok(result) => results.push(result),
                Err(e) => {
                    tracing::error!("task panicked: {e}");
                }
            }
        }

        // Sort by original index to preserve order
        results.sort_by_key(|(idx, _)| *idx);

        let total = results.len();
        let mut embeddings = Vec::with_capacity(total);
        let mut failed = Vec::new();

        for (idx, result) in results {
            match result {
                Ok(embedding) => embeddings.push(embedding),
                Err(e) => {
                    tracing::warn!("embedding failed for index {idx}: {e}");
                    failed.push(idx);
                    // Push empty vec as placeholder to maintain alignment
                    embeddings.push(vec![]);
                }
            }
        }

        BatchResult { embeddings, failed }
    }

    async fn embed_single_with_retry(&self, text: &str) -> Result<Vec<f32>, EmbedError> {
        match self.embed_single(text).await {
            Ok(v) => Ok(v),
            Err(_first_err) => {
                tracing::info!("retrying embedding after failure");
                tokio::time::sleep(Duration::from_millis(500)).await;
                self.embed_single(text).await
            }
        }
    }

    async fn call_api(&self, text: &str) -> Result<Vec<f32>, EmbedError> {
        let url = format!(
            "{}?key={}",
            self.api_url.trim_end_matches('/'),
            self.api_key
        );

        let body = EmbedRequest {
            model: self.model.clone(),
            content: EmbedContent {
                parts: vec![EmbedPart {
                    text: text.to_string(),
                }],
            },
        };

        let response = self
            .client
            .post(&url)
            .json(&body)
            .send()
            .await
            .map_err(|e| {
                if e.is_timeout() {
                    EmbedError::Timeout
                } else {
                    EmbedError::Request(e)
                }
            })?;

        if !response.status().is_success() {
            let status = response.status();
            let body_text = response
                .text()
                .await
                .unwrap_or_else(|_| "unable to read body".into());
            return Err(EmbedError::Api(format!(
                "API returned {status}: {body_text}"
            )));
        }

        let embed_resp: EmbedResponse = response.json().await.map_err(|e| {
            EmbedError::Api(format!("failed to parse embedding response: {e}"))
        })?;

        embed_resp
            .embedding
            .map(|e| e.values)
            .ok_or_else(|| EmbedError::Api("response missing embedding field".into()))
    }

    /// Check if the embedding API is reachable (for health checks).
    pub async fn check_health(&self) -> Result<(), EmbedError> {
        let url = format!(
            "{}?key={}",
            self.api_url.trim_end_matches('/'),
            self.api_key
        );

        let body = EmbedRequest {
            model: self.model.clone(),
            content: EmbedContent {
                parts: vec![EmbedPart {
                    text: "health check".to_string(),
                }],
            },
        };

        let response = self
            .client
            .post(&url)
            .json(&body)
            .send()
            .await
            .map_err(|e| EmbedError::Api(format!("health check failed: {e}")))?;

        if response.status().is_success() {
            Ok(())
        } else {
            Err(EmbedError::Api(format!(
                "health check returned {}",
                response.status()
            )))
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use wiremock::matchers::{method, path};
    use wiremock::{Mock, MockServer, ResponseTemplate};

    fn test_config(url: &str) -> Config {
        Config {
            port: 8009,
            embedding_api_url: url.to_string(),
            embedding_api_key: "test-key".into(),
            embedding_model: "text-embedding-004".into(),
            max_concurrent_requests: 5,
            batch_size: 2,
            request_timeout_secs: 10,
        }
    }

    fn mock_embed_response(values: Vec<f32>) -> serde_json::Value {
        serde_json::json!({
            "embedding": {
                "values": values
            }
        })
    }

    #[tokio::test]
    async fn test_embed_single() {
        let server = MockServer::start().await;
        let config = test_config(&server.uri());

        Mock::given(method("POST"))
            .and(path("/"))
            .respond_with(
                ResponseTemplate::new(200).set_body_json(mock_embed_response(vec![0.1, 0.2, 0.3])),
            )
            .mount(&server)
            .await;

        let svc = EmbeddingService::new(&config);
        let result = svc.embed_single("hello world").await;
        assert!(result.is_ok());
        let embedding = result.unwrap();
        assert_eq!(embedding, vec![0.1, 0.2, 0.3]);
    }

    #[tokio::test]
    async fn test_embed_single_empty_text() {
        let config = test_config("http://localhost:1");
        let svc = EmbeddingService::new(&config);
        let result = svc.embed_single("").await;
        assert!(result.is_err());
        assert!(matches!(result.unwrap_err(), EmbedError::InvalidInput(_)));
    }

    #[tokio::test]
    async fn test_embed_batch() {
        let server = MockServer::start().await;
        let config = test_config(&server.uri());

        // Each call returns a different embedding based on the request
        Mock::given(method("POST"))
            .and(path("/"))
            .respond_with(
                ResponseTemplate::new(200)
                    .set_body_json(mock_embed_response(vec![0.1, 0.2, 0.3])),
            )
            .expect(3)
            .mount(&server)
            .await;

        let svc = EmbeddingService::new(&config);
        let texts = vec![
            "text one".to_string(),
            "text two".to_string(),
            "text three".to_string(),
        ];

        let result = svc.embed_batch(texts).await;
        assert!(result.failed.is_empty());
        assert_eq!(result.embeddings.len(), 3);
        // All should return the same mock embedding
        for emb in &result.embeddings {
            assert_eq!(emb, &vec![0.1, 0.2, 0.3]);
        }
    }

    #[tokio::test]
    async fn test_embed_batch_empty() {
        let config = test_config("http://localhost:1");
        let svc = EmbeddingService::new(&config);
        let result = svc.embed_batch(vec![]).await;
        assert!(result.embeddings.is_empty());
        assert!(result.failed.is_empty());
    }

    #[tokio::test]
    async fn test_concurrent_limit() {
        let server = MockServer::start().await;
        // Max 2 concurrent requests
        let config = Config {
            max_concurrent_requests: 2,
            batch_size: 10,
            ..test_config(&server.uri())
        };

        // Respond with a 200ms delay to observe concurrency
        Mock::given(method("POST"))
            .and(path("/"))
            .respond_with(
                ResponseTemplate::new(200)
                    .set_body_json(mock_embed_response(vec![1.0]))
                    .set_delay(Duration::from_millis(100)),
            )
            .expect(4)
            .mount(&server)
            .await;

        let svc = EmbeddingService::new(&config);
        let texts: Vec<String> = (0..4).map(|i| format!("text {i}")).collect();

        let start = tokio::time::Instant::now();
        let result = svc.embed_batch(texts).await;
        let elapsed = start.elapsed();

        assert!(result.failed.is_empty());
        assert_eq!(result.embeddings.len(), 4);

        // With 4 requests, max 2 concurrent, each taking 100ms:
        // minimum ~200ms (2 batches of 2). Should be > 150ms at least.
        assert!(
            elapsed >= Duration::from_millis(150),
            "should be limited by semaphore, took {elapsed:?}"
        );
    }

    #[tokio::test]
    async fn test_retry_on_failure() {
        let server = MockServer::start().await;
        let config = test_config(&server.uri());

        // First call fails, second succeeds
        Mock::given(method("POST"))
            .and(path("/"))
            .respond_with(ResponseTemplate::new(500).set_body_string("server error"))
            .up_to_n_times(1)
            .mount(&server)
            .await;

        Mock::given(method("POST"))
            .and(path("/"))
            .respond_with(
                ResponseTemplate::new(200)
                    .set_body_json(mock_embed_response(vec![0.5, 0.6])),
            )
            .mount(&server)
            .await;

        let svc = EmbeddingService::new(&config);
        // Use batch to trigger retry logic
        let result = svc.embed_batch(vec!["retry text".to_string()]).await;
        assert!(result.failed.is_empty());
        assert_eq!(result.embeddings.len(), 1);
        assert_eq!(result.embeddings[0], vec![0.5, 0.6]);
    }

    #[tokio::test]
    async fn test_partial_failure() {
        let server = MockServer::start().await;
        let config = test_config(&server.uri());

        // Always fail — both original and retry will get 500
        Mock::given(method("POST"))
            .and(path("/"))
            .respond_with(ResponseTemplate::new(500).set_body_string("always fails"))
            .mount(&server)
            .await;

        let svc = EmbeddingService::new(&config);
        let texts = vec!["fail text".to_string()];
        let result = svc.embed_batch(texts).await;

        assert_eq!(result.failed.len(), 1);
        assert_eq!(result.failed[0], 0);
    }
}
