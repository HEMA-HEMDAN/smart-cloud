"""Unit tests for Independent and Shared RAG strategies using mock Qdrant and providers."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from app.embeddings.mock import MockEmbeddingProvider
from app.generation.mock import MockGenerationProvider
from app.rag.base import RAGRequest
from app.rag.independent.strategy import IndependentRAG
from app.rag.shared.strategy import SharedIntelligenceRAG


def create_mock_qdrant() -> MagicMock:
    """Create a mock Qdrant client tracking collections, points, and searches."""
    qdrant = MagicMock()
    collections_obj = MagicMock()
    collections_obj.collections = []
    qdrant.get_collections = AsyncMock(return_value=collections_obj)
    qdrant.create_collection = AsyncMock()
    qdrant.create_payload_index = AsyncMock()
    qdrant.upsert = AsyncMock()
    qdrant.set_payload = AsyncMock()

    # Search returns mock points
    mock_hit = MagicMock()
    mock_hit.id = "pt_1"
    mock_hit.score = 0.95
    mock_hit.payload = {
        "text": "Shared AI Intelligence reduces document preparation cost.",
        "chunk_id": "c_0",
        "document_id": "doc1",
        "version_hash": "v1",
        "authorized_consumers": ["c_00", "c_01"],
    }
    qdrant.search = AsyncMock(return_value=[mock_hit])
    return qdrant


@pytest.mark.unit
async def test_independent_rag_isolation() -> None:
    embedder = MockEmbeddingProvider()
    generator = MockGenerationProvider()
    qdrant = create_mock_qdrant()

    strat = IndependentRAG(embedder, generator, qdrant)

    col1 = strat.collection_name(run_id="run-1", consumer_id="c_00", repetition_index=0)
    col2 = strat.collection_name(run_id="run-1", consumer_id="c_01", repetition_index=0)

    # Invariant: independent collections must not collide across consumers
    assert col1 != col2
    assert "c_00" in col1
    assert "c_01" in col2

    text = "Independent preparation ensures total isolation between consumers."
    res1 = await strat.prepare_document("doc1", "v1", text, "run-1", "c_00")
    res2 = await strat.prepare_document("doc1", "v1", text, "run-1", "c_01")

    # Both must be full preparations (is_reuse = False)
    assert res1["is_reuse"] is False
    assert res2["is_reuse"] is False
    assert res1["collection"] == col1
    assert res2["collection"] == col2


@pytest.mark.unit
async def test_shared_rag_first_demand_and_reuse() -> None:
    embedder = MockEmbeddingProvider()
    generator = MockGenerationProvider()
    qdrant = create_mock_qdrant()

    strat = SharedIntelligenceRAG(embedder, generator, qdrant)

    col1 = strat.collection_name(run_id="run-1", repetition_index=0)
    col2 = strat.collection_name(run_id="run-1", repetition_index=0)
    # Same collection for shared strategy
    assert col1 == col2

    text = "First demand prepares intermediate vectors for subsequent authorized consumers."

    # Consumer 1: First demand preparation
    res1 = await strat.prepare_document("doc1", "v1", text, "run-1", "c_00", repetition_index=0)
    assert res1["is_reuse"] is False
    assert res1["embedding_tokens_used"] > 0
    assert qdrant.upsert.called

    # Consumer 2: Reuse of existing vectors
    res2 = await strat.prepare_document("doc1", "v1", text, "run-1", "c_01", repetition_index=0)
    assert res2["is_reuse"] is True
    assert res2["embedding_tokens_used"] == 0
    # set_payload must be called to authorize consumer 2
    assert qdrant.set_payload.called


@pytest.mark.unit
async def test_shared_rag_version_invalidation() -> None:
    embedder = MockEmbeddingProvider()
    generator = MockGenerationProvider()
    qdrant = create_mock_qdrant()

    strat = SharedIntelligenceRAG(embedder, generator, qdrant)
    text_v1 = "Version 1 of the institutional document."
    text_v2 = "Version 2 of the institutional document with revised guidelines."

    # Prepare v1
    res1 = await strat.prepare_document("doc1", "hash_v1", text_v1, "run-1", "c_00")
    assert res1["is_reuse"] is False

    # Document updated to v2: cannot reuse obsolete v1 vectors! Must re-prepare
    res2 = await strat.prepare_document("doc1", "hash_v2", text_v2, "run-1", "c_00")
    assert res2["is_reuse"] is False


@pytest.mark.unit
async def test_authorization_filter_in_shared_answer() -> None:
    embedder = MockEmbeddingProvider()
    generator = MockGenerationProvider()
    qdrant = create_mock_qdrant()

    strat = SharedIntelligenceRAG(embedder, generator, qdrant)
    req = RAGRequest(
        run_id="run-1",
        question_id="q1",
        question="What does the document state?",
        consumer_id="c_01",
    )

    result = await strat.answer(req)
    assert result.answer is not None
    assert qdrant.search.called

    # Verify that query_filter was passed to Qdrant search
    call_kwargs = qdrant.search.call_args.kwargs
    assert "query_filter" in call_kwargs
    filter_obj = call_kwargs["query_filter"]
    assert filter_obj is not None
