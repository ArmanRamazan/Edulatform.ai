use pyo3::prelude::*;

use crate::chunking::{count_tokens, merge_to_chunks, paragraph_split};

#[pyclass(get_all)]
#[derive(Clone, Debug, PartialEq)]
pub struct MarkdownChunk {
    pub text: String,
    pub heading: Option<String>,
    pub level: u8,
}

#[pymethods]
impl MarkdownChunk {
    fn __repr__(&self) -> String {
        format!(
            "MarkdownChunk(heading={:?}, level={}, len={})",
            self.heading,
            self.level,
            self.text.len()
        )
    }
}

/// Split markdown into chunks respecting heading structure and code blocks.
pub fn chunk_markdown(md: &str, chunk_size: usize, overlap: usize) -> Vec<MarkdownChunk> {
    if md.trim().is_empty() {
        return Vec::new();
    }

    let sections = split_by_headings(md);
    let mut result = Vec::new();

    for section in sections {
        let token_count = count_tokens(&section.text);

        if token_count <= chunk_size {
            result.push(MarkdownChunk {
                text: section.text,
                heading: section.heading.clone(),
                level: section.level,
            });
        } else {
            // Section too large — split on paragraphs, preserving code blocks
            let sub_chunks =
                split_section_to_chunks(&section.text, chunk_size, overlap);
            for chunk_text in sub_chunks {
                result.push(MarkdownChunk {
                    text: chunk_text,
                    heading: section.heading.clone(),
                    level: section.level,
                });
            }
        }
    }

    result
}

struct Section {
    text: String,
    heading: Option<String>,
    level: u8,
}

/// Parse heading level from a line starting with #.
fn parse_heading(line: &str) -> Option<(u8, String)> {
    let trimmed = line.trim();
    if !trimmed.starts_with('#') {
        return None;
    }
    let level = trimmed.chars().take_while(|&c| c == '#').count();
    if level > 6 || level == 0 {
        return None;
    }
    let rest = trimmed[level..].trim();
    if rest.is_empty() {
        // Bare heading like "##" with no text — still a heading
        return Some((level as u8, String::new()));
    }
    Some((level as u8, rest.to_string()))
}

/// Split markdown text into sections by headings.
fn split_by_headings(md: &str) -> Vec<Section> {
    let mut sections = Vec::new();
    let mut current_lines: Vec<&str> = Vec::new();
    let mut current_heading: Option<String> = None;
    let mut current_level: u8 = 0;
    let mut in_code_block = false;

    for line in md.lines() {
        // Track code fence boundaries
        let trimmed = line.trim();
        if trimmed.starts_with("```") {
            in_code_block = !in_code_block;
            current_lines.push(line);
            continue;
        }

        if in_code_block {
            current_lines.push(line);
            continue;
        }

        if let Some((level, heading_text)) = parse_heading(line) {
            // Flush previous section
            if !current_lines.is_empty() {
                let text = current_lines.join("\n").trim().to_string();
                if !text.is_empty() {
                    sections.push(Section {
                        text,
                        heading: current_heading.take(),
                        level: current_level,
                    });
                }
                current_lines.clear();
            }
            current_heading = Some(heading_text);
            current_level = level;
            current_lines.push(line);
        } else {
            current_lines.push(line);
        }
    }

    // Flush remaining
    if !current_lines.is_empty() {
        let text = current_lines.join("\n").trim().to_string();
        if !text.is_empty() {
            sections.push(Section {
                text,
                heading: current_heading,
                level: current_level,
            });
        }
    }

    sections
}

/// Split a large section into smaller chunks by paragraphs,
/// keeping code blocks atomic (never splitting inside ```...```).
fn split_section_to_chunks(text: &str, chunk_size: usize, overlap: usize) -> Vec<String> {
    let segments = split_preserving_code_blocks(text);
    let refs: Vec<&str> = segments.iter().map(|s| s.as_str()).collect();
    merge_to_chunks(&refs, chunk_size, overlap)
}

/// Split text into segments: paragraphs outside code blocks, and whole code blocks as atomic units.
fn split_preserving_code_blocks(text: &str) -> Vec<String> {
    let mut segments = Vec::new();
    let mut current_text = String::new();
    let mut code_block = String::new();
    let mut in_code_block = false;

    for line in text.lines() {
        let trimmed = line.trim();
        if trimmed.starts_with("```") {
            if in_code_block {
                // End of code block
                code_block.push_str(line);
                segments.push(code_block.clone());
                code_block.clear();
                in_code_block = false;
            } else {
                // Start of code block — flush current text first
                if !current_text.trim().is_empty() {
                    let paras = paragraph_split(&current_text);
                    for p in paras {
                        segments.push(p.to_string());
                    }
                }
                current_text.clear();
                in_code_block = true;
                code_block.push_str(line);
                code_block.push('\n');
            }
        } else if in_code_block {
            code_block.push_str(line);
            code_block.push('\n');
        } else {
            current_text.push_str(line);
            current_text.push('\n');
        }
    }

    // Flush remaining
    if in_code_block && !code_block.is_empty() {
        // Unclosed code block — treat as atomic
        segments.push(code_block);
    }
    if !current_text.trim().is_empty() {
        let paras = paragraph_split(&current_text);
        for p in paras {
            segments.push(p.to_string());
        }
    }

    segments
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_chunk_markdown_headings_preserved() {
        let md = "# Introduction\n\nSome intro text here.\n\n## Chapter One\n\nContent of chapter one.\n\n## Chapter Two\n\nContent of chapter two.\n";
        let chunks = chunk_markdown(md, 100, 0);

        assert!(!chunks.is_empty());

        // First chunk should have heading "Introduction"
        assert_eq!(chunks[0].heading.as_deref(), Some("Introduction"));
        assert_eq!(chunks[0].level, 1);

        // Should have sections for both chapters
        let headings: Vec<Option<&str>> =
            chunks.iter().map(|c| c.heading.as_deref()).collect();
        assert!(headings.contains(&Some("Chapter One")));
        assert!(headings.contains(&Some("Chapter Two")));
    }

    #[test]
    fn test_chunk_markdown_sections_split_correctly() {
        let md = "# Title\n\nParagraph one. Paragraph two. Paragraph three.\n\n## Section\n\nMore content here with many words to fill the chunk up beyond the limit so it splits.";
        let chunks = chunk_markdown(md, 5, 0);

        // With chunk_size=5, text should be split into multiple chunks
        assert!(
            chunks.len() > 1,
            "Should split into multiple chunks, got {}",
            chunks.len()
        );
    }

    #[test]
    fn test_markdown_code_blocks_not_split() {
        let md = "# Setup\n\nInstall:\n\n```python\ndef hello():\n    print('hello world')\n    print('this is a longer function')\n    return True\n```\n\nDone.";
        let chunks = chunk_markdown(md, 100, 0);

        // Find the chunk containing the code block
        let code_chunk = chunks.iter().find(|c| c.text.contains("```python"));
        assert!(code_chunk.is_some(), "Should have a chunk with code block");
        let code_chunk = code_chunk.unwrap();

        // The code block should be complete (has both opening and closing ```)
        let fence_count = code_chunk.text.matches("```").count();
        assert!(
            fence_count >= 2,
            "Code block should have opening and closing fences, got {}",
            fence_count
        );
    }

    #[test]
    fn test_chunk_markdown_no_heading_prefix() {
        let md = "Some text without any heading at all.\n\nAnother paragraph.";
        let chunks = chunk_markdown(md, 100, 0);

        assert_eq!(chunks.len(), 1);
        assert_eq!(chunks[0].heading, None);
        assert_eq!(chunks[0].level, 0);
    }

    #[test]
    fn test_chunk_markdown_empty() {
        let chunks = chunk_markdown("", 100, 0);
        assert!(chunks.is_empty());

        let chunks = chunk_markdown("   \n  \n  ", 100, 0);
        assert!(chunks.is_empty());
    }

    #[test]
    fn test_chunk_markdown_nested_headings() {
        let md = "# H1\n\nText.\n\n## H2\n\nText.\n\n### H3\n\nDeep text.";
        let chunks = chunk_markdown(md, 100, 0);

        let levels: Vec<u8> = chunks.iter().map(|c| c.level).collect();
        assert!(levels.contains(&1));
        assert!(levels.contains(&2));
        assert!(levels.contains(&3));
    }

    #[test]
    fn test_heading_inside_code_block_ignored() {
        let md = "# Real Heading\n\nText.\n\n```\n# This is a comment, not a heading\n## Also not a heading\n```\n\nMore text.";
        let chunks = chunk_markdown(md, 100, 0);

        // Should only detect the real heading, not the ones inside code block
        let heading_count = chunks
            .iter()
            .filter(|c| c.heading.is_some())
            .count();
        assert_eq!(heading_count, 1, "Only 1 real heading should be detected");
    }

    #[test]
    fn test_large_document_no_panic() {
        // Generate ~100KB markdown
        let mut md = String::with_capacity(110_000);
        md.push_str("# Large Document\n\n");
        for i in 0..500 {
            md.push_str(&format!("## Section {}\n\n", i));
            md.push_str("Lorem ipsum dolor sit amet, consectetur adipiscing elit. ");
            md.push_str("Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. ");
            md.push_str("Ut enim ad minim veniam.\n\n");
        }
        assert!(md.len() > 50_000);

        let chunks = chunk_markdown(&md, 50, 5);
        assert!(
            !chunks.is_empty(),
            "Large document should produce chunks"
        );
        for chunk in &chunks {
            assert!(!chunk.text.is_empty());
        }
    }
}
