"""Abstract embedding provider interface.

All providers must implement EmbeddingProvider.
Vectors from different providers/dimensions must never be mixed.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import ClassVar


@dataclass
class EmbeddingResult:
    """Result of embedding one or more texts."""

    vectors: list[list[float]]
    model_id: str
    dimension: int
    tokens_used: int | None  # None when provider does not report usage
    tokens_available: bool  # False means we estimated / not available
    latency_ms: float
    estimated_cost_usd: float | None = None
    provider: str = ""


@dataclass
class EmbeddingProviderError(Exception):
    """Raised when an embedding call fails after exhausting retries."""

    provider: str
    message: str
    retryable: bool = False

    def __str__(self) -> str:
        return f"[{self.provider}] {self.message}"


class EmbeddingProvider(ABC):
    """Interface that all embedding provider implementations must satisfy."""

    #: Human-readable provider name, e.g. "gemini", "openai"
    PROVIDER_NAME: ClassVar[str]

    @abstractmethod
    async def embed(self, texts: list[str]) -> EmbeddingResult:
        """Embed one or more texts and return vectors with usage metadata."""
        ...

    @abstractmethod
    def model_id(self) -> str:
        """Return the exact model identifier as sent to the provider API."""
        ...

    @abstractmethod
    def dimension(self) -> int:
        """Return the expected vector dimension for this model."""
        ...

    def validate_dimension(self, vector: list[float]) -> None:
        """Raise ValueError if the vector dimension does not match."""
        if len(vector) != self.dimension():
            raise ValueError(f"Expected dimension {self.dimension()}, got {len(vector)}")
