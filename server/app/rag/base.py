"""Abstract RAG strategy interface.

Both Independent RAG and Shared Intelligence RAG implement this interface.
They share common abstractions for retrieval, generation, and measurement
but must not share prepared artifacts in a way that invalidates the baseline.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class RetrievedChunk:
    chunk_id: str
    text: str
    score: float
    document_id: str
    document_version_id: str


@dataclass
class RAGRequest:
    run_id: str
    question_id: str
    question: str
    consumer_id: str
    top_k: int = 5
    repetition_index: int = 0


@dataclass
class RAGResult:
    """Unified result from either strategy – captures all raw measurements."""

    run_id: str
    question_id: str
    strategy: str
    consumer_id: str
    answer: str
    retrieved_chunks: list[RetrievedChunk]

    # Timing (ms)
    retrieval_duration_ms: float
    generation_duration_ms: float
    total_duration_ms: float

    # Tokens
    prompt_tokens: int | None
    completion_tokens: int | None
    tokens_available: bool

    # Cost
    estimated_cost_usd: float | None

    # Errors
    error: str | None = None
    retry_count: int = 0


class RAGStrategy(ABC):
    """Base interface that Independent and Shared strategies must implement."""

    STRATEGY_NAME: str

    @abstractmethod
    async def prepare_document(
        self,
        document_id: str,
        version_hash: str,
        text: str,
        run_id: str,
        consumer_id: str,
        chunk_size: int = 512,
        chunk_overlap: int = 64,
        repetition_index: int = 0,
    ) -> dict[str, Any]:
        """
        Parse, chunk, embed, and store a document.

        Returns preparation metadata (chunk count, tokens used, duration, etc.).
        Raises an exception if preparation fails; never silently treats the
        document as prepared when it is not.
        """
        ...

    @abstractmethod
    async def answer(self, request: RAGRequest) -> RAGResult:
        """
        Retrieve relevant chunks and generate an answer.

        Must perform its own query embedding, retrieval, and generation.
        Must not access artifacts belonging to a different strategy's collection
        or a different consumer in the independent baseline.
        """
        ...

    @abstractmethod
    def collection_name(
        self,
        run_id: str,
        consumer_id: str | None = None,
        repetition_index: int = 0,
    ) -> str:
        """
        Return the Qdrant collection name used by this strategy.

        Independent strategy: includes consumer_id and repetition to ensure isolation.
        Shared strategy: uses a run-and-repetition scoped collection name.
        """
        ...
