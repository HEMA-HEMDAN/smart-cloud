"""Gemini embedding provider using google-generativeai SDK.

Model: models/text-embedding-004 (dimension 768, task-type aware).
Model identifier is fully configurable via settings.
"""

from __future__ import annotations

import time
from typing import ClassVar

import structlog

from app.core.config import settings
from app.embeddings.base import (
    EmbeddingProvider,
    EmbeddingProviderError,
    EmbeddingResult,
)

logger = structlog.get_logger(__name__)

# Pricing (USD per 1M tokens) – record source/date in PricingAssumption table.
# Source: Google AI pricing page, 2024-11 snapshot.  Update before production.
_EMBEDDING_COST_PER_TOKEN = 0.0  # text-embedding-004 is currently free tier


class GeminiEmbeddingProvider(EmbeddingProvider):
    PROVIDER_NAME: ClassVar[str] = "gemini"

    def __init__(self) -> None:
        if not settings.gemini_api_key:
            raise EmbeddingProviderError(
                provider=self.PROVIDER_NAME,
                message="GEMINI_API_KEY is not configured.",
                retryable=False,
            )
        import google.generativeai as genai  # lazy import

        genai.configure(api_key=settings.gemini_api_key)  # type: ignore[attr-defined]
        self._genai = genai
        self._model = settings.gemini_embedding_model
        self._dim = settings.embedding_dimension
        logger.info(
            "embedding.provider.initialised",
            provider=self.PROVIDER_NAME,
            model=self._model,
            dimension=self._dim,
        )

    def model_id(self) -> str:
        return self._model

    def dimension(self) -> int:
        return self._dim

    async def embed(self, texts: list[str]) -> EmbeddingResult:
        if not texts:
            raise ValueError("texts must be non-empty")
        t0 = time.monotonic()
        try:
            task_type = "retrieval_document" if len(texts) > 1 else "retrieval_query"
            try:
                result = self._genai.embed_content(  # type: ignore[attr-defined]
                    model=self._model,
                    content=texts,
                    task_type=task_type,
                    output_dimensionality=self._dim,
                )
            except (TypeError, Exception) as call_err:
                # If output_dimensionality parameter is not supported by the model, retry without it
                err_msg = str(call_err).lower()
                if "output_dimensionality" in err_msg or "unexpected keyword" in err_msg:
                    result = self._genai.embed_content(  # type: ignore[attr-defined]
                        model=self._model,
                        content=texts,
                        task_type=task_type,
                    )
                else:
                    raise

            raw_embedding = result["embedding"]
            vectors: list[list[float]]
            if raw_embedding and isinstance(raw_embedding[0], float):
                vectors = [raw_embedding]
            else:
                vectors = raw_embedding  # type: ignore[assignment]
        except Exception as exc:
            raise EmbeddingProviderError(
                provider=self.PROVIDER_NAME,
                message=str(exc),
                retryable=True,
            ) from exc

        latency_ms = (time.monotonic() - t0) * 1000

        # Validate dimensions
        for v in vectors:
            self.validate_dimension(v)

        # Usage: google-generativeai SDK does not report token count for embeddings
        return EmbeddingResult(
            vectors=vectors,
            model_id=self._model,
            dimension=self._dim,
            tokens_used=None,
            tokens_available=False,
            latency_ms=round(latency_ms, 2),
            estimated_cost_usd=None,  # free-tier; set when pricing is known
            provider=self.PROVIDER_NAME,
        )
