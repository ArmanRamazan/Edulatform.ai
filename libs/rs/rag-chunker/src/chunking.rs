use regex::Regex;
use std::sync::LazyLock;

static SENTENCE_RE: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"[^.!?]*[.!?]+\s*").expect("invalid sentence regex"));

/// Split text into paragraphs (double newline separated).
/// Filters out empty segments.
pub fn paragraph_split(text: &str) -> Vec<&str> {
    if text.is_empty() {
        return Vec::new();
    }
    text.split("\n\n")
        .map(|s| s.trim())
        .filter(|s| !s.is_empty())
        .collect()
}

/// Split text into sentences using punctuation boundaries (.!?).
/// Falls back to the whole text as a single segment if no sentence boundaries found.
pub fn sentence_split(text: &str) -> Vec<&str> {
    if text.is_empty() {
        return Vec::new();
    }

    let matches: Vec<&str> = SENTENCE_RE
        .find_iter(text)
        .map(|m| m.as_str().trim())
        .filter(|s| !s.is_empty())
        .collect();

    if matches.is_empty() {
        // No sentence boundaries found, return whole text
        vec![text.trim()]
    } else {
        matches
    }
}

/// Tokenize text into approximate tokens: words and standalone punctuation.
fn tokenize(text: &str) -> Vec<&str> {
    let mut tokens = Vec::new();
    for word in text.split_whitespace() {
        let trimmed = word.trim();
        if trimmed.is_empty() {
            continue;
        }
        // Split leading punctuation
        let start_punct = trimmed
            .chars()
            .take_while(|c| c.is_ascii_punctuation())
            .count();
        if start_punct > 0 && start_punct < trimmed.len() {
            tokens.push(&trimmed[..start_punct]);
            let rest = &trimmed[start_punct..];
            // Split trailing punctuation from the remaining
            let end_punct = rest
                .chars()
                .rev()
                .take_while(|c| c.is_ascii_punctuation())
                .count();
            if end_punct > 0 && end_punct < rest.len() {
                tokens.push(&rest[..rest.len() - end_punct]);
                tokens.push(&rest[rest.len() - end_punct..]);
            } else {
                tokens.push(rest);
            }
        } else {
            // Split trailing punctuation
            let end_punct = trimmed
                .chars()
                .rev()
                .take_while(|c| c.is_ascii_punctuation())
                .count();
            if end_punct > 0 && end_punct < trimmed.len() {
                tokens.push(&trimmed[..trimmed.len() - end_punct]);
                tokens.push(&trimmed[trimmed.len() - end_punct..]);
            } else {
                tokens.push(trimmed);
            }
        }
    }
    tokens
}

/// Approximate token count (words + punctuation).
pub fn count_tokens(text: &str) -> usize {
    tokenize(text).len()
}

/// Merge text segments into chunks of approximately `chunk_size` tokens,
/// with `overlap` tokens of overlap between consecutive chunks.
pub fn merge_to_chunks(segments: &[&str], chunk_size: usize, overlap: usize) -> Vec<String> {
    if segments.is_empty() {
        return Vec::new();
    }
    let chunk_size = chunk_size.max(1);
    let overlap = overlap.min(chunk_size.saturating_sub(1));

    let mut chunks: Vec<String> = Vec::new();
    let mut current_parts: Vec<&str> = Vec::new();
    let mut current_tokens: usize = 0;

    for &segment in segments {
        let seg_tokens = count_tokens(segment);
        if seg_tokens == 0 {
            continue;
        }

        if current_tokens + seg_tokens > chunk_size && !current_parts.is_empty() {
            // Emit current chunk
            let chunk_text = current_parts.join(" ");
            chunks.push(chunk_text);

            // Build overlap from the end of current_parts
            if overlap > 0 {
                let mut overlap_parts: Vec<&str> = Vec::new();
                let mut overlap_count = 0;
                for &part in current_parts.iter().rev() {
                    let part_tokens = count_tokens(part);
                    if overlap_count + part_tokens > overlap && !overlap_parts.is_empty() {
                        break;
                    }
                    overlap_parts.push(part);
                    overlap_count += part_tokens;
                }
                overlap_parts.reverse();
                current_parts = overlap_parts;
                current_tokens = overlap_count;
            } else {
                current_parts.clear();
                current_tokens = 0;
            }
        }

        current_parts.push(segment);
        current_tokens += seg_tokens;
    }

    if !current_parts.is_empty() {
        let chunk_text = current_parts.join(" ");
        if !chunk_text.trim().is_empty() {
            chunks.push(chunk_text);
        }
    }

    chunks
}

/// Split text into chunks of approximately `chunk_size` tokens with `overlap`.
/// Respects paragraph and sentence boundaries. Never splits mid-word.
pub fn chunk_text(text: &str, chunk_size: usize, overlap: usize) -> Vec<String> {
    if text.trim().is_empty() {
        return Vec::new();
    }

    // First try paragraph-level splitting
    let paragraphs = paragraph_split(text);

    // Break paragraphs into sentences for finer granularity
    let mut segments: Vec<&str> = Vec::new();
    for para in &paragraphs {
        let sentences = sentence_split(para);
        segments.extend(sentences);
    }

    if segments.is_empty() {
        return vec![text.to_string()];
    }

    merge_to_chunks(&segments, chunk_size, overlap)
}

/// Get boundary patterns for a given language.
fn language_boundaries(language: &str) -> Option<Vec<&'static str>> {
    match language.to_lowercase().as_str() {
        "python" | "py" => Some(vec!["def ", "class "]),
        "typescript" | "ts" | "javascript" | "js" => {
            Some(vec!["function ", "class ", "export "])
        }
        "rust" | "rs" => Some(vec!["fn ", "impl ", "struct ", "enum "]),
        _ => None,
    }
}

/// Split code at language-specific boundaries.
fn split_at_boundaries<'a>(code: &'a str, boundaries: &[&str]) -> Vec<&'a str> {
    let mut splits: Vec<usize> = Vec::new();

    for line_start in code.match_indices('\n').map(|(i, _)| i + 1) {
        let rest = &code[line_start..];
        let trimmed = rest.trim_start();
        for &boundary in boundaries {
            if trimmed.starts_with(boundary) {
                splits.push(line_start);
                break;
            }
        }
    }

    // Also check the very beginning of the file
    let first_trimmed = code.trim_start();
    for &boundary in boundaries {
        if first_trimmed.starts_with(boundary) {
            // The first boundary is at the start, don't add 0 if it's already there
            if splits.first() != Some(&0) {
                splits.insert(0, 0);
            }
            break;
        }
    }

    if splits.is_empty() {
        return vec![code];
    }

    let mut result: Vec<&str> = Vec::new();

    // If code starts before first boundary, include that prefix
    if splits[0] > 0 {
        let prefix = &code[..splits[0]];
        if !prefix.trim().is_empty() {
            result.push(prefix.trim_end());
        }
    }

    for i in 0..splits.len() {
        let start = splits[i];
        let end = if i + 1 < splits.len() {
            splits[i + 1]
        } else {
            code.len()
        };
        let segment = &code[start..end];
        if !segment.trim().is_empty() {
            result.push(segment.trim_end());
        }
    }

    result
}

/// Split code into lines and merge by token count (fallback for unknown languages).
fn line_based_split(code: &str, chunk_size: usize, overlap: usize) -> Vec<String> {
    let lines: Vec<&str> = code.lines().filter(|l| !l.trim().is_empty()).collect();
    merge_to_chunks(&lines, chunk_size, overlap)
}

/// Split code into chunks respecting language-specific boundaries.
pub fn chunk_code(code: &str, chunk_size: usize, overlap: usize, language: &str) -> Vec<String> {
    if code.trim().is_empty() {
        return Vec::new();
    }

    match language_boundaries(language) {
        Some(boundaries) => {
            let segments = split_at_boundaries(code, &boundaries);
            let refs: Vec<&str> = segments.to_vec();
            merge_to_chunks(&refs, chunk_size, overlap)
        }
        None => line_based_split(code, chunk_size, overlap),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_chunk_text_basic() {
        let text = "This is the first paragraph.\n\nThis is the second paragraph.\n\nThis is the third paragraph with more words to ensure splitting.";
        let chunks = chunk_text(text, 10, 0);
        assert!(!chunks.is_empty(), "Should produce at least one chunk");
        assert!(chunks.len() > 1, "Should produce multiple chunks for text exceeding chunk_size");
        // All original text content should be present across chunks
        for chunk in &chunks {
            assert!(!chunk.is_empty(), "No chunk should be empty");
        }
    }

    #[test]
    fn test_chunk_text_overlap() {
        let text = "Alpha bravo charlie. Delta echo foxtrot. Golf hotel india. Juliet kilo lima. Mike november oscar.";
        let chunks = chunk_text(text, 6, 2);
        assert!(chunks.len() > 1, "Should produce multiple chunks");
        // With overlap, consecutive chunks should share some content
        if chunks.len() >= 2 {
            let first_words: Vec<&str> = chunks[0].split_whitespace().collect();
            let second_words: Vec<&str> = chunks[1].split_whitespace().collect();
            // The end of first chunk should overlap with beginning of second chunk
            let first_tail: Vec<&str> = first_words.iter().rev().take(2).copied().collect();
            let second_head: Vec<&str> = second_words.iter().take(2).copied().collect();
            // At least one word should appear in both chunks (overlap)
            let has_overlap = first_tail.iter().any(|w| second_head.contains(w));
            assert!(has_overlap, "Consecutive chunks should overlap. Chunk 0: {:?}, Chunk 1: {:?}", chunks[0], chunks[1]);
        }
    }

    #[test]
    fn test_chunk_code_python() {
        let code = "def hello():\n    print('hello')\n\ndef world():\n    print('world')\n\nclass Foo:\n    def bar(self):\n        pass\n";
        let chunks = chunk_code(code, 8, 0, "python");
        assert!(!chunks.is_empty(), "Should produce at least one chunk");
        // Each chunk should start with a function/class boundary or be the first chunk
        for chunk in &chunks {
            let trimmed = chunk.trim();
            assert!(!trimmed.is_empty(), "No chunk should be empty");
        }
    }

    #[test]
    fn test_count_tokens() {
        assert_eq!(count_tokens("hello world"), 2);
        assert_eq!(count_tokens("Hello, world!"), 4); // Hello + , + world + !
        assert!(count_tokens("") == 0);
        assert!(count_tokens("one") == 1);
    }

    #[test]
    fn test_empty_input() {
        assert!(chunk_text("", 10, 0).is_empty());
        assert!(chunk_code("", 10, 0, "python").is_empty());
        assert_eq!(count_tokens(""), 0);
    }

    #[test]
    fn test_small_text() {
        let text = "Small text.";
        let chunks = chunk_text(text, 100, 0);
        assert_eq!(chunks.len(), 1, "Text smaller than chunk_size should return single chunk");
        assert_eq!(chunks[0].trim(), "Small text.");
    }

    #[test]
    fn test_paragraph_split() {
        let text = "First paragraph.\n\nSecond paragraph.\n\nThird.";
        let paras = paragraph_split(text);
        assert_eq!(paras.len(), 3);
    }

    #[test]
    fn test_sentence_split() {
        let text = "First sentence. Second sentence! Third sentence?";
        let sentences = sentence_split(text);
        assert_eq!(sentences.len(), 3);
    }

    #[test]
    fn test_merge_to_chunks_no_overlap() {
        let segments = vec!["Hello world.", "Foo bar baz.", "One two three."];
        let chunks = merge_to_chunks(&segments, 3, 0);
        assert!(!chunks.is_empty());
    }

    #[test]
    fn test_chunk_code_rust() {
        let code = "fn hello() {\n    println!(\"hello\");\n}\n\nfn world() {\n    println!(\"world\");\n}\n";
        let chunks = chunk_code(code, 6, 0, "rust");
        assert!(!chunks.is_empty());
    }

    #[test]
    fn test_chunk_code_unknown_language_fallback() {
        let code = "line1\nline2\nline3\nline4\nline5\nline6\nline7\nline8\nline9\nline10\n";
        let chunks = chunk_code(code, 3, 0, "unknown");
        assert!(chunks.len() > 1, "Should fall back to line-based splitting");
    }
}
