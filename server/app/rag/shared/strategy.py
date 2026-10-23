"""Strategy B – Shared Intelligence RAG.

The first eligible consumer prepares a document once into a shared collection.
Subsequent authorized consumers reuse the shared vectors.

Authorization: every retrieval call checks consumer authorization against
the chunk payload ('authorized_consumers' field). Cross-consumer leakage
is a correctness failure, not an acceptable trade-off.

INVARIANT: collection_name() does NOT include consumer_id – it is shared across all
authorized consumers for a given run and repetition.
"""

from __future__ import annotations

import contextlib
import time
import uuid
from typing import Any

import structlog
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchAny,
    PayloadSchemaType,
    PointStruct,
    VectorParams,
)

from app.documents.extractor import chunk_document_text
from app.embeddings.base import EmbeddingProvider
from app.generation.base import GenerationProvider, Message
from app.rag.base import RAGRequest, RAGResult, RAGStrategy, RetrievedChunk

logger = structlog.get_logger(__name__)


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
        # Key: (collection_name, document_id) -> version_hash
        self._prepared_versions: dict[tuple[str, str], str] = {}
        # Key: (collection_name, document_id) -> set of consumer_ids
        self._authorized_consumers: dict[tuple[str, str], set[str]] = {}
        # Key: (collection_name, document_id) -> list of point_ids (UUID strings)
        self._doc_points: dict[tuple[str, str], list[str]] = {}

    def collection_name(
        self,
        run_id: str,
        consumer_id: str | None = None,
        repetition_index: int = 0,
    ) -> str:
        """Shared collection scoped to run and repetition – NOT consumer-scoped."""
        safe_run = run_id.replace("-", "")[:8]
        return f"shared_{safe_run}_rep{repetition_index}".replace("-", "_")

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
        Prepare document once on first demand; subsequent consumers reuse artifacts.

        When reused, the new consumer is added to 'authorized_consumers' in point payloads.
        """
        t0 = time.monotonic()
        collection = self.collection_name(
            run_id=run_id, repetition_index=repetition_index
        )
        doc_key = (collection, document_id)

        # Check if already prepared with matching version
        existing_version = self._prepared_versions.get(doc_key)
        if existing_version is not None and existing_version == version_hash:
            # REUSE EVENT: add consumer to authorized list for this document
            self._authorized_consumers.setdefault(doc_key, set()).add(consumer_id)
            all_authorized = sorted(self._authorized_consumers[doc_key])

            # Update point payloads in Qdrant to authorize new consumer
            point_ids = self._doc_points.get(doc_key, [])
            if point_ids:
                try:
                    await self._qdrant.set_payload(
                        collection_name=collection,
                        payload={"authorized_consumers": all_authorized},
                        points=point_ids,
                    )
                except Exception as exc:
                    logger.warning(
                        "qdrant.set_payload.warning",
                        collection=collection,
                        error=str(exc),
                    )

            duration_ms = (time.monotonic() - t0) * 1000
            logger.info(
                "preparation.reused",
                strategy=self.STRATEGY_NAME,
                document_id=document_id,
                consumer_id=consumer_id,
                authorized_count=len(all_authorized),
                duration_ms=round(duration_ms, 2),
            )
            return {
                "strategy": self.STRATEGY_NAME,
                "collection": collection,
                "chunk_count": len(point_ids),
                "embedding_tokens_used": 0,
                "embedding_tokens_available": True,
                "duration_ms": round(duration_ms, 2),
                "is_reuse": True,
            }

        # FIRST PREPARATION (or re-preparation due to version update)
        chunks = chunk_document_text(text, chunk_size=chunk_size, chunk_overlap=chunk_overlap)
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
            # Create payload index for fast authorized_consumers filtering
            with contextlib.suppress(Exception):
                await self._qdrant.create_payload_index(
                    collection_name=collection,
                    field_name="authorized_consumers",
                    field_schema=PayloadSchemaType.KEYWORD,
                )

            logger.info(
                "qdrant.collection.created",
                collection=collection,
                strategy=self.STRATEGY_NAME,
            )

        chunk_texts = [c["text"] for c in chunks]
        embedding_result = await self._embedder.embed(chunk_texts)

        new_point_ids: list[str] = [str(uuid.uuid4()) for _ in chunks]
        points = [
            PointStruct(
                id=pid,
                vector=vec,
                payload={
                    "document_id": document_id,
                    "version_hash": version_hash,
                    "run_id": run_id,
                    "chunk_id": chunk["chunk_id"],
                    "chunk_index": chunk["chunk_index"],
                    "text": chunk["text"],
                    "strategy": self.STRATEGY_NAME,
                    "authorized_consumers": [consumer_id],
                },
            )
            for pid, chunk, vec in zip(
                new_point_ids, chunks, embedding_result.vectors, strict=False
            )
        ]
        await self._qdrant.upsert(collection_name=collection, points=points)

        # Track state
        self._prepared_versions[doc_key] = version_hash
        self._authorized_consumers[doc_key] = {consumer_id}
        self._doc_points[doc_key] = new_point_ids

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
        collection = self.collection_name(
            run_id=request.run_id, repetition_index=request.repetition_index
        )

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

        try:
            hits = await self._qdrant.search(
                collection_name=collection,
                query_vector=query_vec,
                query_filter=auth_filter,
                limit=request.top_k,
            )
        except Exception as exc:
            logger.error("retrieval.failed", collection=collection, error=str(exc))
            hits = []

        retrieval_ms = (time.monotonic() - retrieval_t0) * 1000

        chunks = [
            RetrievedChunk(
                chunk_id=str(h.payload.get("chunk_id", h.id)),
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
