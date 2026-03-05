use std::path::Path;

use serde::{Deserialize, Serialize};
use tantivy::collector::TopDocs;
use tantivy::directory::MmapDirectory;
use tantivy::query::{BooleanQuery, Occur, QueryParser, TermQuery};
use tantivy::schema::{
    Field, IndexRecordOption, Schema, TextFieldIndexing, TextOptions, Value, STORED, STRING, TEXT,
};
use tantivy::{DateTime, Index, IndexReader, IndexWriter, ReloadPolicy, Term};

use crate::error::SearchError;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SearchDocument {
    pub id: String,
    pub org_id: String,
    pub title: String,
    pub body: String,
    pub source_type: String,
    pub source_path: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SearchResult {
    pub id: String,
    pub title: String,
    pub snippet: String,
    pub score: f32,
    pub source_type: String,
    pub source_path: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SearchResults {
    pub results: Vec<SearchResult>,
    pub total: usize,
}

pub struct SchemaFields {
    pub id: Field,
    pub org_id: Field,
    pub title: Field,
    pub body: Field,
    pub source_type: Field,
    pub source_path: Field,
    pub created_at: Field,
}

pub struct SearchIndex {
    index: Index,
    reader: IndexReader,
    writer: std::sync::Mutex<IndexWriter>,
    fields: SchemaFields,
    #[allow(dead_code)]
    schema: Schema,
}

impl SearchIndex {
    pub fn create_or_open(path: &Path) -> Result<Self, SearchError> {
        let mut schema_builder = Schema::builder();

        let id = schema_builder.add_text_field("id", STRING | STORED);
        let org_id = schema_builder.add_text_field("org_id", STRING);

        let title_indexing = TextFieldIndexing::default()
            .set_tokenizer("default")
            .set_index_option(IndexRecordOption::WithFreqsAndPositions);
        let title_options = TextOptions::default()
            .set_indexing_options(title_indexing)
            .set_stored();
        let title = schema_builder.add_text_field("title", title_options);

        let body = schema_builder.add_text_field("body", TEXT);
        let source_type = schema_builder.add_text_field("source_type", STRING | STORED);
        let source_path = schema_builder.add_text_field("source_path", STRING | STORED);
        let created_at = schema_builder.add_date_field("created_at", STORED);

        let schema = schema_builder.build();

        std::fs::create_dir_all(path).map_err(|e| {
            SearchError::IndexError(format!("Failed to create index directory: {e}"))
        })?;

        let mmap_dir = MmapDirectory::open(path).map_err(|e| {
            SearchError::IndexError(format!("Failed to open mmap directory: {e}"))
        })?;

        let index = if Index::exists(&mmap_dir).map_err(|e| {
            SearchError::IndexError(format!("Failed to check index existence: {e}"))
        })? {
            Index::open_in_dir(path)
                .map_err(|e| SearchError::IndexError(format!("Failed to open index: {e}")))?
        } else {
            Index::create_in_dir(path, schema.clone())
                .map_err(|e| SearchError::IndexError(format!("Failed to create index: {e}")))?
        };

        let writer = index
            .writer(50_000_000)
            .map_err(|e| SearchError::IndexError(format!("Failed to create writer: {e}")))?;

        let reader = index
            .reader_builder()
            .reload_policy(ReloadPolicy::OnCommitWithDelay)
            .try_into()
            .map_err(|e| SearchError::IndexError(format!("Failed to create reader: {e}")))?;

        let fields = SchemaFields {
            id,
            org_id,
            title,
            body,
            source_type,
            source_path,
            created_at,
        };

        Ok(Self {
            index,
            reader,
            writer: std::sync::Mutex::new(writer),
            fields,
            schema,
        })
    }

    pub fn add_document(&self, doc: &SearchDocument) -> Result<(), SearchError> {
        let writer = self
            .writer
            .lock()
            .map_err(|e| SearchError::IndexError(format!("Writer lock poisoned: {e}")))?;

        let mut tantivy_doc = tantivy::TantivyDocument::new();
        tantivy_doc.add_text(self.fields.id, &doc.id);
        tantivy_doc.add_text(self.fields.org_id, &doc.org_id);
        tantivy_doc.add_text(self.fields.title, &doc.title);
        tantivy_doc.add_text(self.fields.body, &doc.body);
        tantivy_doc.add_text(self.fields.source_type, &doc.source_type);
        tantivy_doc.add_text(self.fields.source_path, &doc.source_path);
        tantivy_doc.add_date(self.fields.created_at, DateTime::from_timestamp_secs(0));

        writer
            .add_document(tantivy_doc)
            .map_err(|e| SearchError::IndexError(format!("Failed to add document: {e}")))?;

        Ok(())
    }

    pub fn add_documents_batch(&self, docs: &[SearchDocument]) -> Result<usize, SearchError> {
        let writer = self
            .writer
            .lock()
            .map_err(|e| SearchError::IndexError(format!("Writer lock poisoned: {e}")))?;

        let mut count = 0;
        for doc in docs {
            let mut tantivy_doc = tantivy::TantivyDocument::new();
            tantivy_doc.add_text(self.fields.id, &doc.id);
            tantivy_doc.add_text(self.fields.org_id, &doc.org_id);
            tantivy_doc.add_text(self.fields.title, &doc.title);
            tantivy_doc.add_text(self.fields.body, &doc.body);
            tantivy_doc.add_text(self.fields.source_type, &doc.source_type);
            tantivy_doc.add_text(self.fields.source_path, &doc.source_path);
            tantivy_doc.add_date(self.fields.created_at, DateTime::from_timestamp_secs(0));

            writer
                .add_document(tantivy_doc)
                .map_err(|e| SearchError::IndexError(format!("Failed to add document: {e}")))?;
            count += 1;
        }

        Ok(count)
    }

    pub fn commit(&self) -> Result<(), SearchError> {
        let mut writer = self
            .writer
            .lock()
            .map_err(|e| SearchError::IndexError(format!("Writer lock poisoned: {e}")))?;

        writer
            .commit()
            .map_err(|e| SearchError::IndexError(format!("Failed to commit: {e}")))?;

        self.reader
            .reload()
            .map_err(|e| SearchError::IndexError(format!("Failed to reload reader: {e}")))?;

        Ok(())
    }

    pub fn delete_by_org(&self, org_id: &str) -> Result<(), SearchError> {
        let mut writer = self
            .writer
            .lock()
            .map_err(|e| SearchError::IndexError(format!("Writer lock poisoned: {e}")))?;

        let term = Term::from_field_text(self.fields.org_id, org_id);
        writer.delete_term(term);

        writer
            .commit()
            .map_err(|e| SearchError::IndexError(format!("Failed to commit delete: {e}")))?;

        self.reader
            .reload()
            .map_err(|e| SearchError::IndexError(format!("Failed to reload reader: {e}")))?;

        Ok(())
    }

    pub fn search(
        &self,
        query_str: &str,
        org_id: &str,
        limit: usize,
        offset: usize,
    ) -> Result<SearchResults, SearchError> {
        if query_str.trim().is_empty() {
            return Ok(SearchResults {
                results: Vec::new(),
                total: 0,
            });
        }

        let searcher = self.reader.searcher();

        let query_parser =
            QueryParser::for_index(&self.index, vec![self.fields.title, self.fields.body]);

        let text_query = query_parser.parse_query(query_str).map_err(|e| {
            SearchError::QueryError(format!("Failed to parse query '{query_str}': {e}"))
        })?;

        let org_term = Term::from_field_text(self.fields.org_id, org_id);
        let org_query = TermQuery::new(org_term, IndexRecordOption::Basic);

        let combined_query = BooleanQuery::new(vec![
            (Occur::Must, Box::new(org_query)),
            (Occur::Must, text_query),
        ]);

        let top_docs = searcher
            .search(&combined_query, &TopDocs::with_limit(limit + offset))
            .map_err(|e| SearchError::QueryError(format!("Search failed: {e}")))?;

        let total = top_docs.len();

        let results: Vec<SearchResult> = top_docs
            .into_iter()
            .skip(offset)
            .take(limit)
            .filter_map(|(score, doc_address)| {
                let doc: tantivy::TantivyDocument = searcher.doc(doc_address).ok()?;
                let id = self.get_text_field(&doc, self.fields.id)?;
                let title = self.get_text_field(&doc, self.fields.title)?;
                let source_type = self.get_text_field(&doc, self.fields.source_type)?;
                let source_path = self.get_text_field(&doc, self.fields.source_path)?;

                let snippet = self.generate_snippet(&searcher, &combined_query, doc_address);

                Some(SearchResult {
                    id,
                    title,
                    snippet,
                    score,
                    source_type,
                    source_path,
                })
            })
            .collect();

        Ok(SearchResults { results, total })
    }

    fn get_text_field(&self, doc: &tantivy::TantivyDocument, field: Field) -> Option<String> {
        doc.get_first(field)
            .and_then(|v| v.as_str())
            .map(|s| s.to_string())
    }

    fn generate_snippet(
        &self,
        searcher: &tantivy::Searcher,
        query: &BooleanQuery,
        doc_address: tantivy::DocAddress,
    ) -> String {
        let snippet_generator =
            tantivy::SnippetGenerator::create(searcher, query, self.fields.body);

        match snippet_generator {
            Ok(generator) => {
                let doc: Result<tantivy::TantivyDocument, _> = searcher.doc(doc_address);
                match doc {
                    Ok(d) => {
                        let snippet = generator.snippet_from_doc(&d);
                        let html = snippet.to_html();
                        if html.is_empty() {
                            self.get_text_field(&d, self.fields.title)
                                .unwrap_or_default()
                        } else {
                            html
                        }
                    }
                    Err(_) => String::new(),
                }
            }
            Err(_) => String::new(),
        }
    }

    #[cfg(test)]
    pub fn schema(&self) -> &Schema {
        &self.schema
    }
}
