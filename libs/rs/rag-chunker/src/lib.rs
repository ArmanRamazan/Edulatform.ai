#![deny(clippy::all)]

mod chunking;
mod markdown;
mod metadata;

use pyo3::prelude::*;

/// Split text into chunks of approximately `chunk_size` tokens with `overlap`.
/// Respects paragraph and sentence boundaries. Never splits mid-word.
#[pyfunction]
fn chunk_text(text: &str, chunk_size: usize, overlap: usize) -> Vec<String> {
    chunking::chunk_text(text, chunk_size, overlap)
}

/// Split code into chunks respecting function/class boundaries for the given language.
/// Supported languages: python, typescript, javascript, rust.
/// Falls back to line-based splitting for unknown languages.
#[pyfunction]
fn chunk_code(code: &str, chunk_size: usize, overlap: usize, language: &str) -> Vec<String> {
    chunking::chunk_code(code, chunk_size, overlap, language)
}

/// Approximate token count (words + punctuation).
#[pyfunction]
fn count_tokens(text: &str) -> usize {
    chunking::count_tokens(text)
}

/// Split markdown into chunks respecting heading structure and code blocks.
#[pyfunction]
fn chunk_markdown(md: &str, chunk_size: usize, overlap: usize) -> Vec<markdown::MarkdownChunk> {
    markdown::chunk_markdown(md, chunk_size, overlap)
}

/// Extract metadata from a chunk of text.
#[pyfunction]
#[pyo3(signature = (chunk, source_path, line_start=0, line_end=0))]
fn extract_chunk_metadata(
    chunk: &str,
    source_path: &str,
    line_start: usize,
    line_end: usize,
) -> metadata::ChunkMetadata {
    metadata::extract_chunk_metadata(chunk, source_path, line_start, line_end)
}

/// Python module exposed via pyo3.
#[pymodule]
fn rag_chunker(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(chunk_text, m)?)?;
    m.add_function(wrap_pyfunction!(chunk_code, m)?)?;
    m.add_function(wrap_pyfunction!(count_tokens, m)?)?;
    m.add_function(wrap_pyfunction!(chunk_markdown, m)?)?;
    m.add_function(wrap_pyfunction!(extract_chunk_metadata, m)?)?;
    m.add_class::<markdown::MarkdownChunk>()?;
    m.add_class::<metadata::ChunkMetadata>()?;
    Ok(())
}
