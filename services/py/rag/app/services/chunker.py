from __future__ import annotations

import logging
import re

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Python fallback implementations
# ---------------------------------------------------------------------------

def _py_chunk_text(
    text: str,
    chunk_size: int = 1000,
    overlap: int = 200,
) -> list[str]:
    text = text.strip()
    if not text:
        return []

    paragraphs = [p.strip() for p in re.split(r"\n\n+", text) if p.strip()]

    pieces: list[str] = []
    for para in paragraphs:
        if len(para) <= chunk_size:
            pieces.append(para)
        else:
            sentences = re.split(r"(?<=[.!?])\s+", para)
            for s in sentences:
                pieces.append(s)

    if not pieces:
        return []

    chunks: list[str] = []
    current = pieces[0]

    for piece in pieces[1:]:
        candidate = current + "\n\n" + piece
        if len(candidate) <= chunk_size:
            current = candidate
        else:
            chunks.append(current)
            if overlap > 0 and len(current) > overlap:
                prefix = current[-overlap:]
            else:
                prefix = ""
            current = prefix + piece if prefix else piece
    chunks.append(current)

    return chunks


def _py_chunk_code(code: str, chunk_size: int = 1500) -> list[str]:
    code = code.strip()
    if not code:
        return []

    parts = re.split(r"\n+(?=def |class |async def )", code)
    parts = [p.strip() for p in parts if p.strip()]

    if not parts:
        return []

    _DEF_START = re.compile(r"^(def |class |async def )")
    chunks: list[str] = []
    preamble = ""

    for part in parts:
        if not _DEF_START.match(part):
            preamble = part
        else:
            if preamble:
                chunk = preamble + "\n\n" + part
                preamble = ""
            else:
                chunk = part
            chunks.append(chunk)

    if preamble and not chunks:
        chunks.append(preamble)

    return chunks


def _py_chunk_markdown(
    md: str,
    chunk_size: int = 1000,
    overlap: int = 0,
) -> list[str]:
    """Fallback: treat markdown as plain text."""
    return _py_chunk_text(md, chunk_size, overlap)


def _py_count_tokens(text: str) -> int:
    """Approximate token count: split on whitespace + punctuation."""
    if not text:
        return 0
    tokens = re.findall(r"\w+|[^\w\s]", text)
    return len(tokens)


# ---------------------------------------------------------------------------
# Try loading Rust FFI chunker
# ---------------------------------------------------------------------------

try:
    from rag_chunker import (
        chunk_text as _rs_chunk_text,
        chunk_code as _rs_chunk_code,
        chunk_markdown as _rs_chunk_markdown,
        count_tokens as _rs_count_tokens,
    )
    RUST_CHUNKER = True
    logger.info("rag_chunker: using Rust FFI backend")
except ImportError:
    RUST_CHUNKER = False
    logger.info("rag_chunker: Rust crate not available, using Python fallback")


# ---------------------------------------------------------------------------
# Public API — delegates to Rust or Python
# ---------------------------------------------------------------------------

def chunk_text(
    text: str,
    chunk_size: int = 1000,
    overlap: int = 200,
) -> list[str]:
    if RUST_CHUNKER:
        return _rs_chunk_text(text, chunk_size, overlap)
    return _py_chunk_text(text, chunk_size, overlap)


def chunk_code(
    code: str,
    chunk_size: int = 1500,
    overlap: int = 0,
    language: str = "python",
) -> list[str]:
    if RUST_CHUNKER:
        return _rs_chunk_code(code, chunk_size, overlap, language)
    return _py_chunk_code(code, chunk_size)


def chunk_markdown(
    md: str,
    chunk_size: int = 1000,
    overlap: int = 0,
) -> list:
    if RUST_CHUNKER:
        return _rs_chunk_markdown(md, chunk_size, overlap)
    return _py_chunk_markdown(md, chunk_size, overlap)


def count_tokens(text: str) -> int:
    if RUST_CHUNKER:
        return _rs_count_tokens(text)
    return _py_count_tokens(text)
