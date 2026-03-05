#![deny(clippy::all)]

mod config;
mod error;
mod index;
mod routes;

use std::net::SocketAddr;
use std::path::Path;
use std::sync::Arc;

use axum::routing::{delete, get, post};
use axum::Router;
use tokio::net::TcpListener;
use tower_http::cors::CorsLayer;
use tower_http::trace::TraceLayer;
use tracing_subscriber::EnvFilter;

use crate::config::Config;
use crate::index::SearchIndex;

fn build_router(state: routes::AppState) -> Router {
    Router::new()
        .route("/health/live", get(routes::health_live))
        .route("/index", post(routes::index_document))
        .route("/index/batch", post(routes::batch_index))
        .route("/search", post(routes::search))
        .route("/index/{org_id}", delete(routes::delete_org))
        .layer(CorsLayer::permissive())
        .layer(TraceLayer::new_for_http())
        .with_state(state)
}

#[tokio::main]
async fn main() {
    let _ = dotenvy::dotenv();

    tracing_subscriber::fmt()
        .with_env_filter(
            EnvFilter::try_from_default_env().unwrap_or_else(|_| EnvFilter::new("info")),
        )
        .init();

    let config = Config::from_env();

    let search_index = SearchIndex::create_or_open(Path::new(&config.index_path))
        .expect("Failed to create or open search index");

    let state = Arc::new(search_index);
    let app = build_router(state);

    let addr = SocketAddr::from(([0, 0, 0, 0], config.port));
    tracing::info!("Search service listening on {}", addr);

    let listener = TcpListener::bind(addr)
        .await
        .expect("Failed to bind listener");

    axum::serve(listener, app)
        .with_graceful_shutdown(shutdown_signal())
        .await
        .expect("Server error");
}

async fn shutdown_signal() {
    tokio::signal::ctrl_c()
        .await
        .expect("Failed to install Ctrl+C handler");
    tracing::info!("Shutdown signal received");
}

#[cfg(test)]
mod tests {
    use super::*;
    use axum::body::Body;
    use axum::response::IntoResponse;
    use http_body_util::BodyExt;
    use routes::AppState;
    use tower::ServiceExt;

    fn setup_test_index() -> (tempfile::TempDir, AppState) {
        let dir = tempfile::TempDir::new().unwrap();
        let idx = SearchIndex::create_or_open(dir.path()).unwrap();
        (dir, Arc::new(idx))
    }

    fn make_app(state: AppState) -> Router {
        build_router(state)
    }

    async fn body_to_json(body: Body) -> serde_json::Value {
        let bytes = body.collect().await.unwrap().to_bytes();
        serde_json::from_slice(&bytes).unwrap()
    }

    #[tokio::test]
    async fn test_health_live() {
        let (_dir, state) = setup_test_index();
        let app = make_app(state);

        let req = axum::http::Request::builder()
            .method("GET")
            .uri("/health/live")
            .body(Body::empty())
            .unwrap();

        let resp = app.oneshot(req).await.unwrap();
        assert_eq!(resp.status(), 200);

        let json = body_to_json(resp.into_body()).await;
        assert_eq!(json["status"], "ok");
    }

    #[tokio::test]
    async fn test_index_and_search() {
        let (_dir, state) = setup_test_index();
        let app = make_app(state.clone());

        // Index a document
        let doc = serde_json::json!({
            "id": "doc-1",
            "org_id": "org-1",
            "title": "Introduction to Rust",
            "body": "Rust is a systems programming language focused on safety and performance",
            "source_type": "document",
            "source_path": "/docs/rust-intro.md"
        });

        let req = axum::http::Request::builder()
            .method("POST")
            .uri("/index")
            .header("content-type", "application/json")
            .body(Body::from(serde_json::to_string(&doc).unwrap()))
            .unwrap();

        let resp = app.oneshot(req).await.unwrap();
        assert_eq!(resp.status(), 201);

        // Search for it
        let app = make_app(state);
        let search_body = serde_json::json!({
            "query": "rust programming",
            "org_id": "org-1"
        });

        let req = axum::http::Request::builder()
            .method("POST")
            .uri("/search")
            .header("content-type", "application/json")
            .body(Body::from(serde_json::to_string(&search_body).unwrap()))
            .unwrap();

        let resp = app.oneshot(req).await.unwrap();
        assert_eq!(resp.status(), 200);

        let json = body_to_json(resp.into_body()).await;
        assert!(json["total"].as_u64().unwrap() > 0);
        assert_eq!(json["results"][0]["id"], "doc-1");
        assert_eq!(json["results"][0]["title"], "Introduction to Rust");
        assert_eq!(json["results"][0]["source_type"], "document");
    }

    #[tokio::test]
    async fn test_org_isolation() {
        let (_dir, state) = setup_test_index();

        // Index docs for two different orgs
        let doc_org1 = index::SearchDocument {
            id: "doc-org1".to_string(),
            org_id: "org-1".to_string(),
            title: "Org 1 document about databases".to_string(),
            body: "PostgreSQL is a powerful relational database".to_string(),
            source_type: "document".to_string(),
            source_path: "/docs/db.md".to_string(),
        };

        let doc_org2 = index::SearchDocument {
            id: "doc-org2".to_string(),
            org_id: "org-2".to_string(),
            title: "Org 2 document about databases".to_string(),
            body: "MySQL is another popular relational database".to_string(),
            source_type: "document".to_string(),
            source_path: "/docs/db2.md".to_string(),
        };

        state.add_document(&doc_org1).unwrap();
        state.add_document(&doc_org2).unwrap();
        state.commit().unwrap();

        // Search as org-1 should only find org-1 docs
        let results = state.search("database", "org-1", 10, 0).unwrap();
        assert_eq!(results.total, 1);
        assert_eq!(results.results[0].id, "doc-org1");

        // Search as org-2 should only find org-2 docs
        let results = state.search("database", "org-2", 10, 0).unwrap();
        assert_eq!(results.total, 1);
        assert_eq!(results.results[0].id, "doc-org2");
    }

    #[tokio::test]
    async fn test_batch_index() {
        let (_dir, state) = setup_test_index();
        let app = make_app(state.clone());

        let batch = serde_json::json!({
            "documents": [
                {
                    "id": "batch-1",
                    "org_id": "org-1",
                    "title": "First batch document",
                    "body": "Content about microservices architecture patterns",
                    "source_type": "code",
                    "source_path": "/src/main.rs"
                },
                {
                    "id": "batch-2",
                    "org_id": "org-1",
                    "title": "Second batch document",
                    "body": "Content about microservices deployment strategies",
                    "source_type": "code",
                    "source_path": "/src/deploy.rs"
                },
                {
                    "id": "batch-3",
                    "org_id": "org-1",
                    "title": "Third batch document",
                    "body": "Content about testing microservices",
                    "source_type": "document",
                    "source_path": "/docs/testing.md"
                }
            ]
        });

        let req = axum::http::Request::builder()
            .method("POST")
            .uri("/index/batch")
            .header("content-type", "application/json")
            .body(Body::from(serde_json::to_string(&batch).unwrap()))
            .unwrap();

        let resp = app.oneshot(req).await.unwrap();
        assert_eq!(resp.status(), 201);

        let json = body_to_json(resp.into_body()).await;
        assert_eq!(json["indexed"], 3);

        // Search for the batch-indexed docs
        let results = state.search("microservices", "org-1", 10, 0).unwrap();
        assert_eq!(results.total, 3);
    }

    #[tokio::test]
    async fn test_empty_query() {
        let (_dir, state) = setup_test_index();
        let app = make_app(state);

        let search_body = serde_json::json!({
            "query": "",
            "org_id": "org-1"
        });

        let req = axum::http::Request::builder()
            .method("POST")
            .uri("/search")
            .header("content-type", "application/json")
            .body(Body::from(serde_json::to_string(&search_body).unwrap()))
            .unwrap();

        let resp = app.oneshot(req).await.unwrap();
        assert_eq!(resp.status(), 200);

        let json = body_to_json(resp.into_body()).await;
        assert_eq!(json["total"], 0);
        assert_eq!(json["results"].as_array().unwrap().len(), 0);
    }

    #[tokio::test]
    async fn test_delete_org() {
        let (_dir, state) = setup_test_index();

        // Index docs for two orgs
        let doc1 = index::SearchDocument {
            id: "del-1".to_string(),
            org_id: "org-delete".to_string(),
            title: "Document to delete about algorithms".to_string(),
            body: "Sorting algorithms are fundamental to computer science".to_string(),
            source_type: "document".to_string(),
            source_path: "/docs/algo.md".to_string(),
        };

        let doc2 = index::SearchDocument {
            id: "del-2".to_string(),
            org_id: "org-delete".to_string(),
            title: "Another doc to delete about algorithms".to_string(),
            body: "Graph algorithms include BFS and DFS".to_string(),
            source_type: "document".to_string(),
            source_path: "/docs/graph.md".to_string(),
        };

        let doc_keep = index::SearchDocument {
            id: "keep-1".to_string(),
            org_id: "org-keep".to_string(),
            title: "Document to keep about algorithms".to_string(),
            body: "Dynamic programming algorithms solve optimization problems".to_string(),
            source_type: "document".to_string(),
            source_path: "/docs/dp.md".to_string(),
        };

        state.add_document(&doc1).unwrap();
        state.add_document(&doc2).unwrap();
        state.add_document(&doc_keep).unwrap();
        state.commit().unwrap();

        // Verify all docs exist
        let results = state.search("algorithms", "org-delete", 10, 0).unwrap();
        assert_eq!(results.total, 2);

        let results = state.search("algorithms", "org-keep", 10, 0).unwrap();
        assert_eq!(results.total, 1);

        // Delete org-delete via HTTP
        let app = make_app(Arc::clone(&state));
        let req = axum::http::Request::builder()
            .method("DELETE")
            .uri("/index/org-delete")
            .body(Body::empty())
            .unwrap();

        let resp = app.oneshot(req).await.unwrap();
        assert_eq!(resp.status(), 200);

        // org-delete should have no docs
        let results = state.search("algorithms", "org-delete", 10, 0).unwrap();
        assert_eq!(results.total, 0);

        // org-keep should still have its doc
        let results = state.search("algorithms", "org-keep", 10, 0).unwrap();
        assert_eq!(results.total, 1);
        assert_eq!(results.results[0].id, "keep-1");
    }

    #[tokio::test]
    async fn test_search_with_limit_and_offset() {
        let (_dir, state) = setup_test_index();

        for i in 0..5 {
            let doc = index::SearchDocument {
                id: format!("page-{i}"),
                org_id: "org-page".to_string(),
                title: format!("Document {i} about pagination"),
                body: "Pagination is an important feature for search results".to_string(),
                source_type: "document".to_string(),
                source_path: format!("/docs/page-{i}.md"),
            };
            state.add_document(&doc).unwrap();
        }
        state.commit().unwrap();

        // Limit to 2 results
        let results = state.search("pagination", "org-page", 2, 0).unwrap();
        assert_eq!(results.results.len(), 2);

        // Offset by 3, should get at most 2
        let results = state.search("pagination", "org-page", 10, 3).unwrap();
        assert_eq!(results.results.len(), 2);
    }

    #[tokio::test]
    async fn test_search_error_response() {
        let error = error::SearchError::QueryError("bad query".to_string());
        let response = error.into_response();
        assert_eq!(response.status(), 400);
    }

    #[tokio::test]
    async fn test_not_found_error_response() {
        let error = error::SearchError::NotFound;
        let response = error.into_response();
        assert_eq!(response.status(), 404);
    }

    #[tokio::test]
    async fn test_index_error_response() {
        let error = error::SearchError::IndexError("disk full".to_string());
        let response = error.into_response();
        assert_eq!(response.status(), 500);
    }
}
