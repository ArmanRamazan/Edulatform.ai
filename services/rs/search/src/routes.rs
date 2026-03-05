use std::sync::Arc;

use axum::extract::{Path, State};
use axum::http::StatusCode;
use axum::response::IntoResponse;
use axum::Json;
use serde::{Deserialize, Serialize};

use crate::error::SearchError;
use crate::index::{SearchDocument, SearchIndex, SearchResults};

pub type AppState = Arc<SearchIndex>;

#[derive(Debug, Deserialize)]
pub struct IndexDocumentRequest {
    pub id: String,
    pub org_id: String,
    pub title: String,
    pub body: String,
    pub source_type: String,
    pub source_path: String,
}

#[derive(Debug, Deserialize)]
pub struct BatchIndexRequest {
    pub documents: Vec<IndexDocumentRequest>,
}

#[derive(Debug, Deserialize)]
pub struct SearchRequest {
    pub query: String,
    pub org_id: String,
    pub limit: Option<usize>,
    pub offset: Option<usize>,
}

#[derive(Debug, Serialize)]
pub struct IndexResponse {
    pub status: String,
}

#[derive(Debug, Serialize)]
pub struct BatchIndexResponse {
    pub status: String,
    pub indexed: usize,
}

#[derive(Debug, Serialize)]
pub struct DeleteResponse {
    pub status: String,
}

pub async fn health_live() -> impl IntoResponse {
    (StatusCode::OK, Json(serde_json::json!({"status": "ok"})))
}

pub async fn index_document(
    State(state): State<AppState>,
    Json(req): Json<IndexDocumentRequest>,
) -> Result<impl IntoResponse, SearchError> {
    let doc = SearchDocument {
        id: req.id,
        org_id: req.org_id,
        title: req.title,
        body: req.body,
        source_type: req.source_type,
        source_path: req.source_path,
    };

    state.add_document(&doc)?;
    state.commit()?;

    Ok((
        StatusCode::CREATED,
        Json(IndexResponse {
            status: "indexed".to_string(),
        }),
    ))
}

pub async fn batch_index(
    State(state): State<AppState>,
    Json(req): Json<BatchIndexRequest>,
) -> Result<impl IntoResponse, SearchError> {
    let docs: Vec<SearchDocument> = req
        .documents
        .into_iter()
        .map(|r| SearchDocument {
            id: r.id,
            org_id: r.org_id,
            title: r.title,
            body: r.body,
            source_type: r.source_type,
            source_path: r.source_path,
        })
        .collect();

    let count = state.add_documents_batch(&docs)?;
    state.commit()?;

    Ok((
        StatusCode::CREATED,
        Json(BatchIndexResponse {
            status: "indexed".to_string(),
            indexed: count,
        }),
    ))
}

pub async fn search(
    State(state): State<AppState>,
    Json(req): Json<SearchRequest>,
) -> Result<Json<SearchResults>, SearchError> {
    let limit = req.limit.unwrap_or(10);
    let offset = req.offset.unwrap_or(0);

    let results = state.search(&req.query, &req.org_id, limit, offset)?;
    Ok(Json(results))
}

pub async fn delete_org(
    State(state): State<AppState>,
    Path(org_id): Path<String>,
) -> Result<Json<DeleteResponse>, SearchError> {
    state.delete_by_org(&org_id)?;
    Ok(Json(DeleteResponse {
        status: "deleted".to_string(),
    }))
}
