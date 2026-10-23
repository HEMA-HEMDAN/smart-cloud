"""Unit tests – run without any external services."""

from __future__ import annotations

import pandas as pd
import pytest
from analysis.compare import compare_strategies
from analysis.cost import breakeven_consumers, compute_cost_summary
from analysis.latency import compute_latency_summary
from analysis.reuse import compute_reuse_summary

# ── Fixtures ──────────────────────────────────────────────────────────────────
# These are SYNTHETIC test records. They are not real experiment results.

SYNTHETIC_MEASUREMENTS = pd.DataFrame(
    [
        {
            "run_id": "test-run-1",
            "strategy": "independent",
            "question_id": "q1",
            "total_duration_ms": 1200.0,
            "estimated_cost_usd": 0.002,
        },
        {
            "run_id": "test-run-1",
            "strategy": "independent",
            "question_id": "q2",
            "total_duration_ms": 1100.0,
            "estimated_cost_usd": 0.0018,
        },
        {
            "run_id": "test-run-1",
            "strategy": "shared",
            "question_id": "q1",
            "total_duration_ms": 900.0,
            "estimated_cost_usd": 0.0015,
        },
        {
            "run_id": "test-run-1",
            "strategy": "shared",
            "question_id": "q2",
            "total_duration_ms": 850.0,
            "estimated_cost_usd": None,
        },
    ]
)

SYNTHETIC_PREP_EVENTS = pd.DataFrame(
    [
        {"run_id": "test-run-1", "strategy": "shared", "document_id": "doc1", "is_reuse": False},
        {"run_id": "test-run-1", "strategy": "shared", "document_id": "doc1", "is_reuse": True},
        {"run_id": "test-run-1", "strategy": "shared", "document_id": "doc1", "is_reuse": True},
    ]
)


# ── Cost tests ────────────────────────────────────────────────────────────────


@pytest.mark.unit
def test_cost_summary_structure() -> None:
    result = compute_cost_summary(SYNTHETIC_MEASUREMENTS)
    assert "per_strategy" in result
    assert "independent" in result["per_strategy"]
    assert "shared" in result["per_strategy"]


@pytest.mark.unit
def test_cost_summary_partial_missing() -> None:
    result = compute_cost_summary(SYNTHETIC_MEASUREMENTS)
    assert "note" in result
    # shared has one None cost – note should mention missing data
    assert "1 of 4" in result["note"] or "partial" in result["note"].lower()


@pytest.mark.unit
def test_breakeven_basic() -> None:
    # With c_p=1.0, c_m=0, breakeven = 1
    assert breakeven_consumers(c_p=1.0, c_m=0.0) == pytest.approx(1.0)


@pytest.mark.unit
def test_breakeven_with_maintenance() -> None:
    # c_p=1.0, c_m=1.0 -> N* = 2
    assert breakeven_consumers(c_p=1.0, c_m=1.0) == pytest.approx(2.0)


@pytest.mark.unit
def test_breakeven_invalid_cp() -> None:
    with pytest.raises(ValueError):
        breakeven_consumers(c_p=0.0)


# ── Latency tests ─────────────────────────────────────────────────────────────


@pytest.mark.unit
def test_latency_summary_keys() -> None:
    result = compute_latency_summary(SYNTHETIC_MEASUREMENTS)
    ind = result["per_strategy"]["independent"]
    assert "median_ms" in ind
    assert "p95_ms" in ind
    assert ind["n"] == 2


@pytest.mark.unit
def test_latency_shared_has_data() -> None:
    result = compute_latency_summary(SYNTHETIC_MEASUREMENTS)
    shared = result["per_strategy"]["shared"]
    assert shared["median_ms"] == pytest.approx(875.0)


# ── Reuse tests ───────────────────────────────────────────────────────────────


@pytest.mark.unit
def test_reuse_rate() -> None:
    result = compute_reuse_summary(SYNTHETIC_PREP_EVENTS)
    assert result["total_preparation_events"] == 3
    assert result["reuses"] == 2
    assert result["reuse_rate"] == pytest.approx(2 / 3)


@pytest.mark.unit
def test_reuse_no_shared_data() -> None:
    empty = pd.DataFrame(columns=["strategy", "is_reuse", "run_id"])
    result = compute_reuse_summary(empty)
    assert "note" in result


# ── Compare tests ─────────────────────────────────────────────────────────────


@pytest.mark.unit
def test_compare_both_strategies() -> None:
    result = compare_strategies(SYNTHETIC_MEASUREMENTS)
    assert "cost" in result
    assert "latency" in result
    assert "conclusion" in result


@pytest.mark.unit
def test_compare_missing_strategy() -> None:
    only_ind = SYNTHETIC_MEASUREMENTS[SYNTHETIC_MEASUREMENTS["strategy"] == "independent"]
    result = compare_strategies(only_ind)
    assert "Available strategies" in result["conclusion"]


# ── Embedding interface tests ─────────────────────────────────────────────────


@pytest.mark.unit
def test_embedding_dimension_validation() -> None:
    from app.embeddings.base import EmbeddingProvider

    class FakeProvider(EmbeddingProvider):
        PROVIDER_NAME = "fake"

        def model_id(self) -> str:
            return "fake-model"

        def dimension(self) -> int:
            return 3

        async def embed(self, texts): ...  # type: ignore

    provider = FakeProvider()
    with pytest.raises(ValueError, match="dimension"):
        provider.validate_dimension([1.0, 2.0])  # wrong size


@pytest.mark.unit
def test_embedding_dimension_ok() -> None:
    from app.embeddings.base import EmbeddingProvider

    class FakeProvider(EmbeddingProvider):
        PROVIDER_NAME = "fake"

        def model_id(self) -> str:
            return "fake-model"

        def dimension(self) -> int:
            return 3

        async def embed(self, texts): ...  # type: ignore

    provider = FakeProvider()
    provider.validate_dimension([1.0, 2.0, 3.0])  # should not raise


# ── RAG strategy isolation test ───────────────────────────────────────────────


@pytest.mark.unit
def test_independent_collection_is_consumer_scoped() -> None:
    from app.rag.independent.strategy import IndependentRAG

    class FakeEmbedder:
        def dimension(self) -> int:
            return 768

        def model_id(self) -> str:
            return "fake"

    class FakeGen:
        pass

    class FakeQdrant:
        pass

    strategy = IndependentRAG(FakeEmbedder(), FakeGen(), FakeQdrant())  # type: ignore
    c1 = strategy.collection_name("run1", "consumer_a")
    c2 = strategy.collection_name("run1", "consumer_b")
    assert c1 != c2, "Independent strategy must produce different collections per consumer"


@pytest.mark.unit
def test_shared_collection_not_consumer_scoped() -> None:
    from app.rag.shared.strategy import SharedIntelligenceRAG

    class FakeEmbedder:
        def dimension(self) -> int:
            return 768

        def model_id(self) -> str:
            return "fake"

    class FakeGen:
        pass

    class FakeQdrant:
        pass

    strategy = SharedIntelligenceRAG(FakeEmbedder(), FakeGen(), FakeQdrant())  # type: ignore
    c1 = strategy.collection_name("run1", "consumer_a")
    c2 = strategy.collection_name("run1", "consumer_b")
    assert c1 == c2, "Shared strategy must use the same collection for all consumers"
