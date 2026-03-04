from app.services.chunker import chunk_text, chunk_code


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
