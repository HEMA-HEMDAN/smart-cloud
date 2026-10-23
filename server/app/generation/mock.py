"""Deterministic mock generation provider for offline testing and benchmark runs."""

from __future__ import annotations

import time
from typing import ClassVar

from app.generation.base import (
    GenerationProvider,
    GenerationResult,
    Message,
)


class MockGenerationProvider(GenerationProvider):
    """Zero-cost, offline mock generator producing deterministic factual answers."""

    PROVIDER_NAME: ClassVar[str] = "mock"

    def __init__(self, model_name: str = "mock-gemini-1.5-flash") -> None:
        self._model_name = model_name

    def model_id(self) -> str:
        return self._model_name

    async def generate(
        self,
        messages: list[Message],
        *,
        temperature: float = 0.0,
        max_tokens: int | None = None,
    ) -> GenerationResult:
        t0 = time.monotonic()

        prompt_str = " ".join(m.content for m in messages)
        prompt_tokens = max(1, len(prompt_str) // 4)

        # Extract context and user question
        user_msg = next((m.content for m in messages if m.role == "user"), "")

        # Extract answer snippet from context if present
        context = ""
        if "Context:\n" in user_msg:
            parts = user_msg.split("Context:\n", 1)[1]
            if "\n\nQuestion:" in parts:
                context = parts.split("\n\nQuestion:")[0]

        if context.strip():
            # Return first sentence or concise extract from context
            first_line = context.strip().split("\n")[0][:200]
            answer_text = f"Based on the provided context: {first_line}"
        else:
            answer_text = "No evidence found in context to answer the question."

        completion_tokens = max(1, len(answer_text) // 4)
        latency_ms = (time.monotonic() - t0) * 1000

        return GenerationResult(
            text=answer_text,
            model_id=self._model_name,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            tokens_available=True,
            latency_ms=round(latency_ms, 2),
            estimated_cost_usd=0.0,
            provider=self.PROVIDER_NAME,
        )
