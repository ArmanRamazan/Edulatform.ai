"""Tests for seed_rag_documents — RAG documents, chunks, concepts, and relationships."""
import math
import uuid
from unittest.mock import AsyncMock, call

import pytest

from seed import (
    DEMO_DOC_IDS,
    DEMO_ORG_ID,
    _random_embedding,
    _split_into_chunks,
    seed_rag_documents,
)

# ---------------------------------------------------------------------------
# Unit tests: _split_into_chunks helper
# ---------------------------------------------------------------------------


def test_split_into_chunks_produces_non_empty_chunks():
    content = " ".join(["word"] * 500)
    chunks = _split_into_chunks(content, target_words=200)
    assert len(chunks) > 0
    assert all(c.strip() for c in chunks)


def test_split_into_chunks_respects_target_words():
    content = " ".join([f"word{i}" for i in range(600)])
    chunks = _split_into_chunks(content, target_words=200)
    # With 600 words and target 200, expect 3 chunks
    assert len(chunks) == 3


def test_split_into_chunks_covers_all_words():
    words = [f"w{i}" for i in range(450)]
    content = " ".join(words)
    chunks = _split_into_chunks(content, target_words=200)
    reconstructed = " ".join(chunks)
    assert reconstructed == content


def test_split_into_chunks_handles_empty_string():
    chunks = _split_into_chunks("", target_words=200)
    assert chunks == []


def test_split_into_chunks_two_thousand_word_doc_yields_ten_chunks():
    content = " ".join(["word"] * 2000)
    chunks = _split_into_chunks(content, target_words=200)
    assert len(chunks) == 10


# ---------------------------------------------------------------------------
# Unit tests: _random_embedding helper
# ---------------------------------------------------------------------------


def test_random_embedding_has_correct_dimension():
    vec = _random_embedding()
    assert len(vec) == 768


def test_random_embedding_is_unit_length():
    vec = _random_embedding()
    magnitude = math.sqrt(sum(v * v for v in vec))
    assert abs(magnitude - 1.0) < 1e-6


def test_random_embedding_values_are_floats():
    vec = _random_embedding()
    assert all(isinstance(v, float) for v in vec)


def test_random_embedding_produces_different_vectors_each_call():
    vec1 = _random_embedding()
    vec2 = _random_embedding()
    assert vec1 != vec2


# ---------------------------------------------------------------------------
# Structural: DEMO_DOC_IDS constant
# ---------------------------------------------------------------------------


def test_demo_doc_ids_has_five_documents():
    assert len(DEMO_DOC_IDS) == 5


def test_demo_doc_ids_contains_expected_slugs():
    expected = {
        "python_best_practices",
        "rust_ownership",
        "typescript_patterns",
        "system_design",
        "api_design_guide",
    }
    assert set(DEMO_DOC_IDS.keys()) == expected


def test_demo_doc_ids_are_fixed_uuids():
    """All document IDs must be deterministic for idempotency."""
    for slug, doc_id in DEMO_DOC_IDS.items():
        # Must be parseable as UUID
        parsed = uuid.UUID(doc_id)
        assert str(parsed) == doc_id.lower(), f"Invalid UUID for {slug}"


# ---------------------------------------------------------------------------
# Idempotency: skips when already seeded
# ---------------------------------------------------------------------------


async def test_seed_rag_documents_skips_when_already_seeded():
    rag_pool = AsyncMock()
    first_doc_id = next(iter(DEMO_DOC_IDS.values()))
    rag_pool.fetchval.return_value = first_doc_id  # already exists

    await seed_rag_documents(rag_pool)

    rag_pool.execute.assert_not_called()


# ---------------------------------------------------------------------------
# Happy path helpers
# ---------------------------------------------------------------------------


def _make_rag_pool(concept_count: int = 47) -> AsyncMock:
    """Return a rag_pool mock configured for a fresh DB."""
    rag_pool = AsyncMock()
    concept_uuids = [str(uuid.uuid4()) for _ in range(concept_count)]
    # First call: existence check → None (not seeded)
    # Remaining calls: concept INSERT...RETURNING id
    rag_pool.fetchval.side_effect = [None] + concept_uuids
    return rag_pool


# ---------------------------------------------------------------------------
# Happy path: documents
# ---------------------------------------------------------------------------


async def test_seed_rag_documents_inserts_five_documents():
    rag_pool = _make_rag_pool()

    await seed_rag_documents(rag_pool)

    doc_calls = [
        c for c in rag_pool.execute.call_args_list
        if "INSERT INTO documents" in str(c.args[0])
    ]
    assert len(doc_calls) == 5, (
        f"Expected 5 document INSERTs, got {len(doc_calls)}"
    )


async def test_seed_rag_documents_uses_correct_org_id():
    rag_pool = _make_rag_pool()

    await seed_rag_documents(rag_pool)

    doc_calls = [
        c for c in rag_pool.execute.call_args_list
        if "INSERT INTO documents" in str(c.args[0])
    ]
    for c in doc_calls:
        assert DEMO_ORG_ID in str(c.args), "Each document must belong to demo org"


async def test_seed_rag_documents_uses_fixed_document_ids():
    rag_pool = _make_rag_pool()

    await seed_rag_documents(rag_pool)

    doc_calls = [
        c for c in rag_pool.execute.call_args_list
        if "INSERT INTO documents" in str(c.args[0])
    ]
    inserted_ids = {str(c.args[1]) for c in doc_calls}
    expected_ids = set(DEMO_DOC_IDS.values())
    assert inserted_ids == expected_ids, "Document IDs must match DEMO_DOC_IDS"


async def test_seed_rag_documents_source_type_is_file():
    rag_pool = _make_rag_pool()

    await seed_rag_documents(rag_pool)

    doc_calls = [
        c for c in rag_pool.execute.call_args_list
        if "INSERT INTO documents" in str(c.args[0])
    ]
    for c in doc_calls:
        assert "file" in str(c.args), "source_type must be 'file'"


# ---------------------------------------------------------------------------
# Happy path: chunks
# ---------------------------------------------------------------------------


async def test_seed_rag_documents_inserts_chunks_for_each_document():
    rag_pool = _make_rag_pool()

    await seed_rag_documents(rag_pool)

    chunk_calls = [
        c for c in rag_pool.execute.call_args_list
        if "INSERT INTO chunks" in str(c.args[0])
    ]
    # 5 documents × at least 5 chunks each = at least 25 total
    assert len(chunk_calls) >= 25, (
        f"Expected at least 25 chunk INSERTs, got {len(chunk_calls)}"
    )


async def test_seed_rag_documents_chunks_have_embeddings():
    rag_pool = _make_rag_pool()

    await seed_rag_documents(rag_pool)

    chunk_calls = [
        c for c in rag_pool.execute.call_args_list
        if "INSERT INTO chunks" in str(c.args[0])
    ]
    for c in chunk_calls:
        # The embedding arg is a string "[x,y,z,...]"
        embedding_arg = str(c.args[4])
        assert embedding_arg.startswith("[") and embedding_arg.endswith("]"), (
            "Embedding must be a vector literal"
        )


# ---------------------------------------------------------------------------
# Happy path: concepts
# ---------------------------------------------------------------------------


async def test_seed_rag_documents_inserts_47_concepts():
    rag_pool = _make_rag_pool(concept_count=47)

    await seed_rag_documents(rag_pool)

    # fetchval: 1 existence check + 47 concept upserts = 48 total
    assert rag_pool.fetchval.call_count == 48, (
        f"Expected 48 fetchval calls (1 check + 47 concepts), "
        f"got {rag_pool.fetchval.call_count}"
    )


async def test_seed_rag_documents_concepts_belong_to_demo_org():
    rag_pool = _make_rag_pool()

    await seed_rag_documents(rag_pool)

    concept_calls = [
        c for c in rag_pool.fetchval.call_args_list
        if "INSERT INTO org_concepts" in str(c.args[0])
    ]
    for c in concept_calls:
        assert DEMO_ORG_ID in str(c.args), (
            "Every concept must belong to the demo org"
        )


async def test_seed_rag_documents_concept_names_are_non_empty():
    rag_pool = _make_rag_pool()

    await seed_rag_documents(rag_pool)

    concept_calls = [
        c for c in rag_pool.fetchval.call_args_list
        if "INSERT INTO org_concepts" in str(c.args[0])
    ]
    for c in concept_calls:
        name = c.args[2]  # $2 = name
        assert isinstance(name, str) and len(name) > 0, "Concept name must be non-empty"


# ---------------------------------------------------------------------------
# Happy path: prerequisite relationships
# ---------------------------------------------------------------------------


async def test_seed_rag_documents_inserts_prerequisite_relationships():
    rag_pool = _make_rag_pool()

    await seed_rag_documents(rag_pool)

    rel_calls = [
        c for c in rag_pool.execute.call_args_list
        if "INSERT INTO concept_relationships" in str(c.args[0])
    ]
    assert len(rel_calls) > 0, "Expected at least one prerequisite relationship"


async def test_seed_rag_documents_relationships_use_prerequisite_type():
    rag_pool = _make_rag_pool()

    await seed_rag_documents(rag_pool)

    rel_calls = [
        c for c in rag_pool.execute.call_args_list
        if "INSERT INTO concept_relationships" in str(c.args[0])
    ]
    for c in rel_calls:
        assert "prerequisite" in str(c.args), (
            "Relationship type must be 'prerequisite'"
        )
