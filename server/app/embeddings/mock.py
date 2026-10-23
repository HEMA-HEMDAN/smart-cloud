"""Deterministic mock embedding provider for local testing and benchmark runs."""

from __future__ import annotations

import hashlib
import math
import time
from typing import ClassVar

from app.embeddings.base import EmbeddingProvider, EmbeddingResult


def _text_to_deterministic_vector(text: str, dimension: int = 768) -> list[float]:
    """Generate a deterministic unit-length vector from text using SHA-256 seeding."""
    vec: list[float] = []
    hasher = hashlib.sha256()
    hasher.update(text.encode("utf-8"))
    digest = hasher.digest()

    for i in range(dimension):
        # Deterministic pseudo-random float between -1.0 and 1.0
        byte_val = digest[i % len(digest)]
        val = math.sin((i + 1) * (byte_val + 1))
        vec.append(val)

    # Normalize to unit length
    norm = math.sqrt(sum(v * v for v in vec))
    if norm > 0:
        vec = [v / norm for v in vec]
    return vec


class MockEmbeddingProvider(EmbeddingProvider):
    """Zero-cost, offline mock embedding provider for repeatable tests."""

    PROVIDER_NAME: ClassVar[str] = "mock"

    def __init__(
        self,
        model_name: str = "mock-text-embedding-004",
        dim: int = 768,
    ) -> None:
        self._model = model_name
        self._dim = dim

    def model_id(self) -> str:
        return self._model

    def dimension(self) -> int:
        return self._dim

    async def embed(self, texts: list[str]) -> EmbeddingResult:
        if not texts:
            raise ValueError("texts must be non-empty")

        t0 = time.monotonic()
        vectors = [_text_to_deterministic_vector(t, self._dim) for t in texts]
        latency_ms = (time.monotonic() - t0) * 1000

        total_tokens = sum(max(1, len(t) // 4) for t in texts)

        return EmbeddingResult(
            vectors=vectors,
            model_id=self._model,
            dimension=self._dim,
            tokens_used=total_tokens,
            tokens_available=True,
            latency_ms=round(latency_ms, 2),
            estimated_cost_usd=0.0,
            provider=self.PROVIDER_NAME,
        )
