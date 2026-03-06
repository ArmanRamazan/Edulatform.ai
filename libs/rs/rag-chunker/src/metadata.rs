use pyo3::prelude::*;

use crate::chunking::count_tokens;

#[pyclass(get_all)]
#[derive(Clone, Debug, PartialEq)]
pub struct ChunkMetadata {
    pub token_count: usize,
    pub language: Option<String>,
    pub has_code_block: bool,
    pub heading_context: Option<String>,
    pub line_start: usize,
    pub line_end: usize,
}

#[pymethods]
impl ChunkMetadata {
    fn __repr__(&self) -> String {
        format!(
            "ChunkMetadata(tokens={}, lang={:?}, code={}, heading={:?}, lines={}-{})",
            self.token_count,
            self.language,
            self.has_code_block,
            self.heading_context,
            self.line_start,
            self.line_end,
        )
    }
}

/// Detect language from file extension.
fn detect_language(source_path: &str) -> Option<String> {
    let ext = source_path.rsplit('.').next()?;
    match ext.to_lowercase().as_str() {
        "py" => Some("python".to_string()),
        "ts" | "tsx" => Some("typescript".to_string()),
        "js" | "jsx" => Some("javascript".to_string()),
        "rs" => Some("rust".to_string()),
        "md" => Some("markdown".to_string()),
        "yaml" | "yml" => Some("yaml".to_string()),
        "json" => Some("json".to_string()),
        "toml" => Some("toml".to_string()),
        "html" | "htm" => Some("html".to_string()),
        "css" => Some("css".to_string()),
        "sql" => Some("sql".to_string()),
        "sh" | "bash" => Some("shell".to_string()),
        _ => None,
    }
}

/// Extract the first heading (# ...) from the chunk text.
fn extract_heading(chunk: &str) -> Option<String> {
    for line in chunk.lines() {
        let trimmed = line.trim();
        if trimmed.starts_with('#') {
            let level = trimmed.chars().take_while(|&c| c == '#').count();
            if level > 0 && level <= 6 {
                let rest = trimmed[level..].trim();
                if !rest.is_empty() {
                    return Some(rest.to_string());
                }
            }
        }
    }
    None
}

/// Extract metadata from a chunk of text.
///
/// `line_start` and `line_end` are 1-based line numbers representing
/// where this chunk appears in the source document. Pass 0 for both
/// if the position is unknown.
pub fn extract_chunk_metadata(
    chunk: &str,
    source_path: &str,
    line_start: usize,
    line_end: usize,
) -> ChunkMetadata {
    let token_count = count_tokens(chunk);
    let language = detect_language(source_path);
    let has_code_block = chunk.contains("```");
    let heading_context = extract_heading(chunk);

    let line_end = if line_end == 0 && line_start == 0 {
        chunk.lines().count()
    } else {
        line_end
    };

    ChunkMetadata {
        token_count,
        language,
        has_code_block,
        heading_context,
        line_start,
        line_end,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_extract_metadata_python() {
        let chunk = "def hello():\n    print('world')\n";
        let meta = extract_chunk_metadata(chunk, "src/main.py", 1, 3);

        assert_eq!(meta.language.as_deref(), Some("python"));
        assert!(meta.token_count > 0);
        assert!(!meta.has_code_block);
        assert_eq!(meta.heading_context, None);
        assert_eq!(meta.line_start, 1);
        assert_eq!(meta.line_end, 3);
    }

    #[test]
    fn test_extract_metadata_typescript() {
        let chunk = "const x = 42;";
        let meta = extract_chunk_metadata(chunk, "app/index.tsx", 10, 10);

        assert_eq!(meta.language.as_deref(), Some("typescript"));
    }

    #[test]
    fn test_extract_metadata_markdown_with_code() {
        let chunk = "# Setup\n\n```python\nprint('hi')\n```\n";
        let meta = extract_chunk_metadata(chunk, "README.md", 0, 0);

        assert_eq!(meta.language.as_deref(), Some("markdown"));
        assert!(meta.has_code_block);
        assert_eq!(meta.heading_context.as_deref(), Some("Setup"));
        // line_end auto-calculated when 0,0
        assert_eq!(meta.line_end, 5);
    }

    #[test]
    fn test_extract_metadata_unknown_extension() {
        let chunk = "some data";
        let meta = extract_chunk_metadata(chunk, "file.xyz", 1, 1);

        assert_eq!(meta.language, None);
    }

    #[test]
    fn test_extract_metadata_no_extension() {
        let chunk = "some data";
        let meta = extract_chunk_metadata(chunk, "Makefile", 1, 1);

        assert_eq!(meta.language, None);
    }

    #[test]
    fn test_detect_language_all_supported() {
        assert_eq!(detect_language("f.py"), Some("python".to_string()));
        assert_eq!(detect_language("f.ts"), Some("typescript".to_string()));
        assert_eq!(detect_language("f.tsx"), Some("typescript".to_string()));
        assert_eq!(detect_language("f.js"), Some("javascript".to_string()));
        assert_eq!(detect_language("f.jsx"), Some("javascript".to_string()));
        assert_eq!(detect_language("f.rs"), Some("rust".to_string()));
        assert_eq!(detect_language("f.md"), Some("markdown".to_string()));
        assert_eq!(detect_language("f.yaml"), Some("yaml".to_string()));
        assert_eq!(detect_language("f.yml"), Some("yaml".to_string()));
        assert_eq!(detect_language("f.json"), Some("json".to_string()));
        assert_eq!(detect_language("f.toml"), Some("toml".to_string()));
        assert_eq!(detect_language("f.html"), Some("html".to_string()));
        assert_eq!(detect_language("f.css"), Some("css".to_string()));
        assert_eq!(detect_language("f.sql"), Some("sql".to_string()));
        assert_eq!(detect_language("f.sh"), Some("shell".to_string()));
    }

    #[test]
    fn test_token_count_accuracy() {
        let chunk = "Hello world foo bar baz";
        let meta = extract_chunk_metadata(chunk, "test.md", 1, 1);
        assert_eq!(meta.token_count, 5);
    }
}
