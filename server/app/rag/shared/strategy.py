"""Strategy B – Shared Intelligence RAG.

The first eligible consumer prepares a document once.
Subsequent authorized consumers reuse the shared vectors.

Authorization: every retrieval call checks consumer authorization against
the chunk payload. Cross-consumer leakage is a correctness failure, not
an acceptable trade-off.

INVARIANT: collection_name() does NOT include consumer_id – shared across all
authorized consumers for a given run.
"""

from __future__ import annotations

import time
import uuid
from typing import Any

import structlog
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchAny,
    PointStruct,
    VectorParams,
)

from app.embeddings.base import EmbeddingProvider
from app.generation.base import GenerationProvider, Message
from app.rag.base import RAGRequest, RAGResult, RAGStrategy, RetrievedChunk

logger = structlog.get_logger(__name__)


def _chunk_text(text: str, chunk_size: int = 512, overlap: int = 64) -> list[str]:
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunks.append(text[start:end])
        start += chunk_size - overlap
    return chunks


class SharedIntelligenceRAG(RAGStrategy):
    """Strategy B: shared preparation, per-consumer authorized retrieval."""

    STRATEGY_NAME = "shared"

    def __init__(
        self,
        embedding_provider: EmbeddingProvider,
        generation_provider: GenerationProvider,
        qdrant_client: Any,
    ) -> None:
        self._embedder = embedding_provider
        self._generator = generation_provider
        self._qdrant = qdrant_client
        # In-memory record of prepared documents within a run.
        # Production: store in DB PreparedDocument table.
        self._prepared: dict[str, set[str]] = {}  # run_id -> set[document_id]

    def collection_name(self, run_id: str, consumer_id: str | None = None) -> str:
        """Shared collection – NOT consumer-scoped."""
        return f"shared_{run_id}".replace("-", "_")

    async def prepare_document(
        self,
        document_id: str,
        version_hash: str,
        text: str,
        run_id: str,
        consumer_id: str,
    ) -> dict[str, Any]:
        """Prepare document once; subsequent calls record reuse."""
        t0 = time.monotonic()
        collection = self.collection_name(run_id)
        already_prepared = document_id in self._prepared.get(run_id, set())

        if already_prepared:
            duration_ms = (time.monotonic() - t0) * 1000
            logger.info(
                "preparation.reused",
                strategy=self.STRATEGY_NAME,
                document_id=document_id,
                consumer_id=consumer_id,
            )
            return {
                "strategy": self.STRATEGY_NAME,
                "collection": collection,
                "chunk_count": None,  # not re-counted
                "embedding_tokens_used": 0,
                "embedding_tokens_available": True,
                "duration_ms": round(duration_ms, 2),
                "is_reuse": True,
            }

        # First preparation
        chunks = _chunk_text(text)
        if not chunks:
            raise ValueError(f"Document {document_id} produced no chunks.")

        existing = await self._qdrant.get_collections()
        existing_names = {c.name for c in existing.collections}
        if collection not in existing_names:
            await self._qdrant.create_collection(
                collection_name=collection,
                vectors_config=VectorParams(
                    size=self._embedder.dimension(),
                    distance=Distance.COSINE,
                ),
            )
            logger.info(
                "qdrant.collection.created",
                collection=collection,
                strategy=self.STRATEGY_NAME,
            )

        embedding_result = await self._embedder.embed(chunks)
        points = [
            PointStruct(
                id=str(uuid.uuid4()),
                vector=vec,
                payload={
                    "document_id": document_id,
                    "version_hash": version_hash,
                    "run_id": run_id,
                    "chunk_index": i,
                    "text": chunk,
                    "strategy": self.STRATEGY_NAME,
                    # Authorization list – extended when consumers are added
                    "authorized_consumers": [consumer_id],
                },
            )
            for i, (chunk, vec) in enumerate(zip(chunks, embedding_result.vectors, strict=False))
        ]
        await self._qdrant.upsert(collection_name=collection, points=points)

        self._prepared.setdefault(run_id, set()).add(document_id)

        duration_ms = (time.monotonic() - t0) * 1000
        logger.info(
            "preparation.completed",
            strategy=self.STRATEGY_NAME,
            document_id=document_id,
            consumer_id=consumer_id,
            chunk_count=len(chunks),
            duration_ms=round(duration_ms, 2),
        )
        return {
            "strategy": self.STRATEGY_NAME,
            "collection": collection,
            "chunk_count": len(chunks),
            "embedding_tokens_used": embedding_result.tokens_used,
            "embedding_tokens_available": embedding_result.tokens_available,
            "duration_ms": round(duration_ms, 2),
            "is_reuse": False,
        }

    async def answer(self, request: RAGRequest) -> RAGResult:
        """Retrieve only from chunks authorized for this consumer."""
        total_t0 = time.monotonic()
        collection = self.collection_name(request.run_id)

        retrieval_t0 = time.monotonic()
        query_embedding = await self._embedder.embed([request.question])
        query_vec = query_embedding.vectors[0]

        # Authorization filter: only retrieve chunks the consumer is allowed to see
        auth_filter = Filter(
            must=[
                FieldCondition(
                    key="authorized_consumers",
                    match=MatchAny(any=[request.consumer_id]),
                )
            ]
        )

        hits = await self._qdrant.search(
            collection_name=collection,
            query_vector=query_vec,
            query_filter=auth_filter,
            limit=request.top_k,
        )
        retrieval_ms = (time.monotonic() - retrieval_t0) * 1000

        chunks = [
            RetrievedChunk(
                chunk_id=str(h.id),
                text=h.payload.get("text", ""),
                score=h.score,
                document_id=h.payload.get("document_id", ""),
                document_version_id=h.payload.get("version_hash", ""),
            )
            for h in hits
        ]

        context = "\n\n---\n\n".join(c.text for c in chunks)
        messages = [
            Message(
                role="system",
                content=(
                    "Answer the question using only the provided context. Be concise and factual."
                ),
            ),
            Message(role="user", content=f"Context:\n{context}\n\nQuestion: {request.question}"),
        ]

        gen_t0 = time.monotonic()
        gen_result = await self._generator.generate(messages)
        gen_ms = (time.monotonic() - gen_t0) * 1000
        total_ms = (time.monotonic() - total_t0) * 1000

        return RAGResult(
            run_id=request.run_id,
            question_id=request.question_id,
            strategy=self.STRATEGY_NAME,
            consumer_id=request.consumer_id,
            answer=gen_result.text,
            retrieved_chunks=chunks,
            retrieval_duration_ms=round(retrieval_ms, 2),
            generation_duration_ms=round(gen_ms, 2),
            total_duration_ms=round(total_ms, 2),
            prompt_tokens=gen_result.prompt_tokens,
            completion_tokens=gen_result.completion_tokens,
            tokens_available=gen_result.tokens_available,
            estimated_cost_usd=gen_result.estimated_cost_usd,
        )
