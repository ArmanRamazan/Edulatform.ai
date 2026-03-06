from unittest.mock import patch

from app.services.chunker import (
    chunk_text,
    chunk_code,
    chunk_markdown,
    count_tokens,
    RUST_CHUNKER,
    _py_chunk_text,
    _py_chunk_code,
)


class TestRustChunkerFlag:
    def test_flag_is_bool(self):
        assert isinstance(RUST_CHUNKER, bool)

    def test_python_fallback_functions_exist(self):
        assert callable(_py_chunk_text)
        assert callable(_py_chunk_code)


class TestChunkText:
    def test_short_text_single_chunk(self):
        text = "Hello world. This is a short paragraph."
        chunks = chunk_text(text, chunk_size=1000, overlap=200)
        assert len(chunks) == 1
        assert chunks[0] == text

    def test_empty_text(self):
        chunks = chunk_text("", chunk_size=1000, overlap=200)
        assert chunks == []

    def test_whitespace_only(self):
        chunks = chunk_text("   \n\n  ", chunk_size=1000, overlap=200)
        assert chunks == []

    def test_split_by_paragraphs(self):
        p1 = "First paragraph with some content."
        p2 = "Second paragraph with different content."
        text = f"{p1}\n\n{p2}"
        chunks = chunk_text(text, chunk_size=50, overlap=0)
        assert len(chunks) == 2
        assert chunks[0] == p1
        assert chunks[1] == p2

    def test_long_paragraph_split_by_sentences(self):
        s1 = "First sentence is here."
        s2 = "Second sentence is here."
        s3 = "Third sentence is here."
        text = f"{s1} {s2} {s3}"
        chunks = chunk_text(text, chunk_size=50, overlap=0)
        assert len(chunks) >= 2
        assert s1 in chunks[0]

    def test_overlap_applied(self):
        p1 = "A" * 100
        p2 = "B" * 100
        text = f"{p1}\n\n{p2}"
        chunks = chunk_text(text, chunk_size=120, overlap=20)
        assert len(chunks) == 2
        assert chunks[0] == p1
        # second chunk starts with overlap from first
        assert chunks[1].startswith(p1[-20:])
        assert chunks[1].endswith(p2)

    def test_multiple_paragraphs_aggregate_under_limit(self):
        paragraphs = ["Short." for _ in range(5)]
        text = "\n\n".join(paragraphs)
        chunks = chunk_text(text, chunk_size=1000, overlap=0)
        assert len(chunks) == 1

    def test_very_long_sentence_not_lost(self):
        long_sentence = "word " * 300  # ~1500 chars
        chunks = chunk_text(long_sentence.strip(), chunk_size=500, overlap=0)
        assert len(chunks) >= 1
        combined = "".join(chunks)
        # all words preserved
        assert combined.count("word") == 300


class TestChunkCode:
    def test_single_function(self):
        code = "def hello():\n    print('hello')\n"
        chunks = chunk_code(code, chunk_size=1500)
        assert len(chunks) == 1
        assert "def hello():" in chunks[0]

    def test_multiple_functions(self):
        code = "def foo():\n    pass\n\ndef bar():\n    pass\n"
        chunks = chunk_code(code, chunk_size=1500)
        assert len(chunks) == 2
        assert "def foo():" in chunks[0]
        assert "def bar():" in chunks[1]

    def test_class_definition(self):
        code = "class MyClass:\n    def method(self):\n        pass\n\ndef standalone():\n    pass\n"
        chunks = chunk_code(code, chunk_size=1500)
        assert len(chunks) == 2
        assert "class MyClass:" in chunks[0]
        assert "def standalone():" in chunks[1]

    def test_async_def(self):
        code = "async def fetch():\n    pass\n\nasync def process():\n    pass\n"
        chunks = chunk_code(code, chunk_size=1500)
        assert len(chunks) == 2
        assert "async def fetch():" in chunks[0]
        assert "async def process():" in chunks[1]

    def test_empty_code(self):
        chunks = chunk_code("", chunk_size=1500)
        assert chunks == []

    def test_code_with_imports_before_functions(self):
        code = "import os\nimport sys\n\ndef main():\n    pass\n"
        chunks = chunk_code(code, chunk_size=1500)
        assert len(chunks) >= 1
        # imports should be in first chunk
        assert "import os" in chunks[0]

    def test_large_function_kept_whole(self):
        body = "\n".join(f"    line_{i} = {i}" for i in range(50))
        code = f"def big():\n{body}\n"
        chunks = chunk_code(code, chunk_size=5000)
        assert len(chunks) == 1
        assert "def big():" in chunks[0]

    def test_language_param_accepted(self):
        code = "def foo():\n    pass\n"
        chunks = chunk_code(code, chunk_size=1500, language="python")
        assert len(chunks) >= 1
        assert "def foo():" in chunks[0]


class TestChunkMarkdown:
    def test_returns_list(self):
        result = chunk_markdown("# Hello\n\nSome text.", chunk_size=1000, overlap=0)
        assert isinstance(result, list)

    def test_empty_input(self):
        result = chunk_markdown("", chunk_size=1000, overlap=0)
        assert result == []

    def test_non_empty_produces_chunks(self):
        md = "# Title\n\nParagraph one.\n\n## Section\n\nParagraph two."
        result = chunk_markdown(md, chunk_size=1000, overlap=0)
        assert len(result) >= 1


class TestCountTokens:
    def test_returns_int(self):
        result = count_tokens("Hello world")
        assert isinstance(result, int)

    def test_empty_string(self):
        assert count_tokens("") == 0

    def test_positive_for_nonempty(self):
        assert count_tokens("Hello world, this is a test.") > 0


class TestOutputFormatConsistency:
    """Verify chunk functions return consistent formats regardless of backend."""

    def test_chunk_text_returns_list_of_str(self):
        chunks = chunk_text("Hello world. Another sentence.", chunk_size=100, overlap=0)
        assert isinstance(chunks, list)
        for c in chunks:
            assert isinstance(c, str)

    def test_chunk_code_returns_list_of_str(self):
        chunks = chunk_code("def foo():\n    pass\n", chunk_size=1500)
        assert isinstance(chunks, list)
        for c in chunks:
            assert isinstance(c, str)

    def test_python_fallback_matches_public_api(self):
        """Python fallback should produce same structure as public API."""
        text = "Para one.\n\nPara two.\n\nPara three."
        public = chunk_text(text, chunk_size=50, overlap=0)
        fallback = _py_chunk_text(text, chunk_size=50, overlap=0)
        # Both return list[str] with non-empty content
        assert isinstance(public, list)
        assert isinstance(fallback, list)
        for c in public:
            assert isinstance(c, str)
        for c in fallback:
            assert isinstance(c, str)
