"""Abstract generation provider interface.

Provider calls must never be made from React/frontend.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import ClassVar


@dataclass
class Message:
    role: str  # "system" | "user" | "assistant"
    content: str


@dataclass
class GenerationResult:
    """Result of a single generation call."""

    text: str
    model_id: str
    prompt_tokens: int | None  # None when provider does not report
    completion_tokens: int | None
    tokens_available: bool  # False = usage was not reported
    latency_ms: float
    estimated_cost_usd: float | None
    provider: str


@dataclass
class GenerationProviderError(Exception):
    provider: str
    message: str
    retryable: bool = False

    def __str__(self) -> str:
        return f"[{self.provider}] {self.message}"


class GenerationProvider(ABC):
    PROVIDER_NAME: ClassVar[str]

    @abstractmethod
    async def generate(
        self,
        messages: list[Message],
        *,
        temperature: float = 0.0,
        max_tokens: int | None = None,
    ) -> GenerationResult:
        """Send messages and return a generated response with usage metadata."""
        ...

    @abstractmethod
    def model_id(self) -> str:
        """Return the exact model identifier sent to the provider."""
        ...
