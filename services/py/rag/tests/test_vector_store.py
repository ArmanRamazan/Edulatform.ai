from uuid import UUID, uuid4

import pytest

from app.repositories.vector_store import VectorPayload, VectorSearchResult, VectorStorePort
from app.repositories.stub_vector_store import StubVectorStore


ORG_A = uuid4()
ORG_B = uuid4()
DOC_1 = uuid4()
DOC_2 = uuid4()


def _payload(org_id: UUID = ORG_A, document_id: UUID = DOC_1, chunk_id: UUID | None = None) -> VectorPayload:
    return VectorPayload(
        chunk_id=chunk_id or uuid4(),
        document_id=document_id,
        org_id=org_id,
    )


def _unit_vector(dim: int, hot_index: int) -> list[float]:
    """Returns a unit vector with 1.0 at hot_index."""
    v = [0.0] * dim
    v[hot_index] = 1.0
    return v


class TestVectorSearchResult:
    def test_is_frozen_dataclass(self) -> None:
        chunk_id = uuid4()
        result = VectorSearchResult(chunk_id=chunk_id, score=0.9)
        assert result.chunk_id == chunk_id
        assert result.score == 0.9

    def test_immutable(self) -> None:
        result = VectorSearchResult(chunk_id=uuid4(), score=0.5)
        with pytest.raises(AttributeError):
            result.score = 1.0  # type: ignore[misc]


class TestVectorPayload:
    def test_is_frozen_dataclass(self) -> None:
        chunk_id = uuid4()
        doc_id = uuid4()
        org_id = uuid4()
        payload = VectorPayload(chunk_id=chunk_id, document_id=doc_id, org_id=org_id)
        assert payload.chunk_id == chunk_id
        assert payload.document_id == doc_id
        assert payload.org_id == org_id

    def test_immutable(self) -> None:
        payload = VectorPayload(chunk_id=uuid4(), document_id=uuid4(), org_id=uuid4())
        with pytest.raises(AttributeError):
            payload.org_id = uuid4()  # type: ignore[misc]


class TestStubVectorStoreImplementsABC:
    def test_stub_is_vector_store_port(self) -> None:
        store = StubVectorStore()
        assert isinstance(store, VectorStorePort)


class TestStubVectorStoreEnsureCollection:
    async def test_ensure_collection_is_idempotent(self) -> None:
        store = StubVectorStore()
        # Should not raise when called multiple times
        await store.ensure_collection(collection="test_col", vector_size=4)
        await store.ensure_collection(collection="test_col", vector_size=4)

    async def test_ensure_collection_different_names(self) -> None:
        store = StubVectorStore()
        await store.ensure_collection(collection="col_a", vector_size=4)
        await store.ensure_collection(collection="col_b", vector_size=8)


class TestStubVectorStoreUpsertAndSearch:
    async def test_upsert_and_search_returns_match(self) -> None:
        store = StubVectorStore()
        await store.ensure_collection("chunks", vector_size=4)

        chunk_id = uuid4()
        vec = _unit_vector(4, 0)  # [1, 0, 0, 0]
        payload = VectorPayload(chunk_id=chunk_id, document_id=DOC_1, org_id=ORG_A)

        await store.upsert(chunk_id=chunk_id, embedding=vec, payload=payload)

        results = await store.search(embedding=vec, org_id=ORG_A, limit=5)

        assert len(results) == 1
        assert results[0].chunk_id == chunk_id
        assert results[0].score == pytest.approx(1.0, abs=1e-6)

    async def test_search_returns_top_k_by_similarity(self) -> None:
        store = StubVectorStore()
        await store.ensure_collection("chunks", vector_size=4)

        # Insert 3 chunks — chunk at index 0 is most similar to query [1,0,0,0]
        ids = [uuid4(), uuid4(), uuid4()]
        vecs = [
            _unit_vector(4, 0),  # score=1.0
            _unit_vector(4, 1),  # score=0.0
            _unit_vector(4, 2),  # score=0.0
        ]
        for cid, vec in zip(ids, vecs):
            await store.upsert(
                chunk_id=cid,
                embedding=vec,
                payload=VectorPayload(chunk_id=cid, document_id=DOC_1, org_id=ORG_A),
            )

        query = _unit_vector(4, 0)
        results = await store.search(embedding=query, org_id=ORG_A, limit=2)

        assert len(results) == 2
        assert results[0].chunk_id == ids[0]
        assert results[0].score == pytest.approx(1.0, abs=1e-6)

    async def test_search_limits_results(self) -> None:
        store = StubVectorStore()
        await store.ensure_collection("chunks", vector_size=2)

        for _ in range(5):
            cid = uuid4()
            await store.upsert(
                chunk_id=cid,
                embedding=[1.0, 0.0],
                payload=VectorPayload(chunk_id=cid, document_id=DOC_1, org_id=ORG_A),
            )

        results = await store.search(embedding=[1.0, 0.0], org_id=ORG_A, limit=3)
        assert len(results) == 3


class TestStubVectorStoreFilterByOrg:
    async def test_search_filters_by_org_id(self) -> None:
        store = StubVectorStore()
        await store.ensure_collection("chunks", vector_size=4)

        vec = _unit_vector(4, 0)

        # Chunk belonging to ORG_A
        cid_a = uuid4()
        await store.upsert(
            chunk_id=cid_a,
            embedding=vec,
            payload=VectorPayload(chunk_id=cid_a, document_id=DOC_1, org_id=ORG_A),
        )

        # Chunk belonging to ORG_B
        cid_b = uuid4()
        await store.upsert(
            chunk_id=cid_b,
            embedding=vec,
            payload=VectorPayload(chunk_id=cid_b, document_id=DOC_2, org_id=ORG_B),
        )

        results_a = await store.search(embedding=vec, org_id=ORG_A, limit=10)
        results_b = await store.search(embedding=vec, org_id=ORG_B, limit=10)

        org_a_ids = {r.chunk_id for r in results_a}
        org_b_ids = {r.chunk_id for r in results_b}

        assert cid_a in org_a_ids
        assert cid_b not in org_a_ids
        assert cid_b in org_b_ids
        assert cid_a not in org_b_ids

    async def test_search_returns_empty_for_unknown_org(self) -> None:
        store = StubVectorStore()
        await store.ensure_collection("chunks", vector_size=4)

        cid = uuid4()
        await store.upsert(
            chunk_id=cid,
            embedding=_unit_vector(4, 0),
            payload=VectorPayload(chunk_id=cid, document_id=DOC_1, org_id=ORG_A),
        )

        results = await store.search(embedding=_unit_vector(4, 0), org_id=uuid4(), limit=10)
        assert results == []


class TestStubVectorStoreDelete:
    async def test_delete_removes_chunk(self) -> None:
        store = StubVectorStore()
        await store.ensure_collection("chunks", vector_size=4)

        cid = uuid4()
        vec = _unit_vector(4, 0)
        payload = VectorPayload(chunk_id=cid, document_id=DOC_1, org_id=ORG_A)

        await store.upsert(chunk_id=cid, embedding=vec, payload=payload)
        await store.delete(chunk_id=cid)

        results = await store.search(embedding=vec, org_id=ORG_A, limit=10)
        assert all(r.chunk_id != cid for r in results)

    async def test_delete_nonexistent_chunk_is_noop(self) -> None:
        store = StubVectorStore()
        await store.ensure_collection("chunks", vector_size=4)
        # Should not raise
        await store.delete(chunk_id=uuid4())

    async def test_delete_only_removes_target_chunk(self) -> None:
        store = StubVectorStore()
        await store.ensure_collection("chunks", vector_size=4)

        vec = _unit_vector(4, 0)
        cid_keep = uuid4()
        cid_del = uuid4()

        for cid in (cid_keep, cid_del):
            await store.upsert(
                chunk_id=cid,
                embedding=vec,
                payload=VectorPayload(chunk_id=cid, document_id=DOC_1, org_id=ORG_A),
            )

        await store.delete(chunk_id=cid_del)

        results = await store.search(embedding=vec, org_id=ORG_A, limit=10)
        ids = {r.chunk_id for r in results}
        assert cid_keep in ids
        assert cid_del not in ids


class TestStubVectorStoreDeleteByDocument:
    async def test_delete_by_document_removes_all_chunks(self) -> None:
        store = StubVectorStore()
        await store.ensure_collection("chunks", vector_size=4)

        vec = _unit_vector(4, 0)
        doc_chunks = [uuid4(), uuid4(), uuid4()]
        other_cid = uuid4()

        for cid in doc_chunks:
            await store.upsert(
                chunk_id=cid,
                embedding=vec,
                payload=VectorPayload(chunk_id=cid, document_id=DOC_1, org_id=ORG_A),
            )
        await store.upsert(
            chunk_id=other_cid,
            embedding=vec,
            payload=VectorPayload(chunk_id=other_cid, document_id=DOC_2, org_id=ORG_A),
        )

        await store.delete_by_document(document_id=DOC_1)

        results = await store.search(embedding=vec, org_id=ORG_A, limit=10)
        ids = {r.chunk_id for r in results}

        for cid in doc_chunks:
            assert cid not in ids
        assert other_cid in ids

    async def test_delete_by_document_nonexistent_is_noop(self) -> None:
        store = StubVectorStore()
        await store.ensure_collection("chunks", vector_size=4)
        # Should not raise
        await store.delete_by_document(document_id=uuid4())

    async def test_upsert_overwrites_existing_chunk(self) -> None:
        store = StubVectorStore()
        await store.ensure_collection("chunks", vector_size=4)

        cid = uuid4()
        vec_a = _unit_vector(4, 0)
        vec_b = _unit_vector(4, 1)
        payload = VectorPayload(chunk_id=cid, document_id=DOC_1, org_id=ORG_A)

        await store.upsert(chunk_id=cid, embedding=vec_a, payload=payload)
        await store.upsert(chunk_id=cid, embedding=vec_b, payload=payload)

        # Search for vec_b — should find the chunk with high score
        results = await store.search(embedding=vec_b, org_id=ORG_A, limit=10)
        chunk = next(r for r in results if r.chunk_id == cid)
        assert chunk.score == pytest.approx(1.0, abs=1e-6)

        # Search for vec_a — should have low score (chunk was overwritten)
        results_a = await store.search(embedding=vec_a, org_id=ORG_A, limit=10)
        chunk_a = next(r for r in results_a if r.chunk_id == cid)
        assert chunk_a.score == pytest.approx(0.0, abs=1e-6)
