from __future__ import annotations

import re


def chunk_text(
    text: str,
    chunk_size: int = 1000,
    overlap: int = 200,
) -> list[str]:
    text = text.strip()
    if not text:
        return []

    paragraphs = [p.strip() for p in re.split(r"\n\n+", text) if p.strip()]

    # Split large paragraphs into sentences
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


def chunk_code(code: str, chunk_size: int = 1500) -> list[str]:
    code = code.strip()
    if not code:
        return []

    # Split on top-level definitions (handle blank lines before def/class)
    parts = re.split(r"\n+(?=def |class |async def )", code)
    parts = [p.strip() for p in parts if p.strip()]

    if not parts:
        return []

    # First part might be preamble (imports). Check if it starts with a definition.
    _DEF_START = re.compile(r"^(def |class |async def )")
    chunks: list[str] = []
    preamble = ""

    for part in parts:
        if not _DEF_START.match(part):
            # Preamble (imports, module docstring) — attach to next definition
            preamble = part
        else:
            if preamble:
                chunk = preamble + "\n\n" + part
                preamble = ""
            else:
                chunk = part
            chunks.append(chunk)

    # If only preamble with no definitions
    if preamble and not chunks:
        chunks.append(preamble)

    return chunks
