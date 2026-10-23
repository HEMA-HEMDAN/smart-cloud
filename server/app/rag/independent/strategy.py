"""Strategy A – Independent RAG baseline.

Each simulated consumer independently prepares its own documents.
Prepared artifacts (chunks, vectors) are stored in a consumer-scoped Qdrant
collection. No artifact sharing between consumers is permitted.

INVARIANT: collection_name() includes run_id, repetition_index, and consumer_id
so that two consumers working on the same document never share vectors.
"""

from __future__ import annotations

import time
import uuid
from typing import Any

import structlog
from qdrant_client.models import (
    Distance,
    PointStruct,
    VectorParams,
)

from app.documents.extractor import chunk_document_text
from app.embeddings.base import EmbeddingProvider
from app.generation.base import GenerationProvider, Message
from app.rag.base import RAGRequest, RAGResult, RAGStrategy, RetrievedChunk

logger = structlog.get_logger(__name__)


class IndependentRAG(RAGStrategy):
    """Strategy A: each consumer prepares and queries its own isolated index."""

    STRATEGY_NAME = "independent"

    def __init__(
        self,
        embedding_provider: EmbeddingProvider,
        generation_provider: GenerationProvider,
        qdrant_client: Any,
    ) -> None:
        self._embedder = embedding_provider
        self._generator = generation_provider
        self._qdrant = qdrant_client

    def collection_name(
        self,
        run_id: str,
        consumer_id: str | None = None,
        repetition_index: int = 0,
    ) -> str:
        """Collection is scoped to run, repetition index, and consumer – never shared."""
        safe_run = run_id.replace("-", "")[:8]
        cid = consumer_id or "default"
        # Qdrant collection name cannot contain hyphens
        return f"ind_{safe_run}_rep{repetition_index}_{cid}".replace("-", "_")

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
        """Chunk, embed, and index the document for this specific consumer."""
        t0 = time.monotonic()
        collection = self.collection_name(run_id, consumer_id, repetition_index)

        chunks = chunk_document_text(text, chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        if not chunks:
            raise ValueError(f"Document {document_id} produced no chunks.")

        # Ensure collection exists
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

        chunk_texts = [c["text"] for c in chunks]
        embedding_result = await self._embedder.embed(chunk_texts)

        points = [
            PointStruct(
                id=str(uuid.uuid4()),
                vector=vec,
                payload={
                    "document_id": document_id,
                    "version_hash": version_hash,
                    "consumer_id": consumer_id,
                    "run_id": run_id,
                    "chunk_id": chunk["chunk_id"],
                    "chunk_index": chunk["chunk_index"],
                    "text": chunk["text"],
                    "strategy": self.STRATEGY_NAME,
                },
            )
            for chunk, vec in zip(chunks, embedding_result.vectors, strict=False)
        ]
        await self._qdrant.upsert(collection_name=collection, points=points)

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
        total_t0 = time.monotonic()
        collection = self.collection_name(
            request.run_id, request.consumer_id, request.repetition_index
        )

        # Embed query
        retrieval_t0 = time.monotonic()
        query_embedding = await self._embedder.embed([request.question])
        query_vec = query_embedding.vectors[0]

        # Retrieve
        try:
            if hasattr(self._qdrant, "query_points"):
                response = await self._qdrant.query_points(
                    collection_name=collection,
                    query=query_vec,
                    limit=request.top_k,
                )
                hits = response.points if hasattr(response, "points") else response
            elif hasattr(self._qdrant, "search"):
                hits = await self._qdrant.search(
                    collection_name=collection,
                    query_vector=query_vec,
                    limit=request.top_k,
                )
            else:
                hits = []
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
