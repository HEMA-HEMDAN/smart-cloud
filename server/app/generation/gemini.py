"""Gemini generation provider."""

from __future__ import annotations

import time
from typing import ClassVar

import structlog

from app.core.config import settings
from app.generation.base import (
    GenerationProvider,
    GenerationProviderError,
    GenerationResult,
    Message,
)

logger = structlog.get_logger(__name__)

# Approximate pricing – USD per 1M tokens (Gemini 1.5 Flash, 2024-11 snapshot).
# Update PricingAssumption record before production runs.
_INPUT_COST_PER_TOKEN = 0.075 / 1_000_000
_OUTPUT_COST_PER_TOKEN = 0.30 / 1_000_000


class GeminiGenerationProvider(GenerationProvider):
    PROVIDER_NAME: ClassVar[str] = "gemini"

    def __init__(self) -> None:
        if not settings.gemini_api_key:
            raise GenerationProviderError(
                provider=self.PROVIDER_NAME,
                message="GEMINI_API_KEY is not configured.",
                retryable=False,
            )
        import google.generativeai as genai

        genai.configure(api_key=settings.gemini_api_key)  # type: ignore[attr-defined]
        self._model_name = settings.gemini_generation_model
        self._genai = genai
        logger.info(
            "generation.provider.initialised",
            provider=self.PROVIDER_NAME,
            model=self._model_name,
        )

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
        try:
            model = self._genai.GenerativeModel(self._model_name)  # type: ignore[attr-defined]
            system_text = ""
            user_text = ""
            for msg in messages:
                if msg.role == "system":
                    system_text = msg.content
                elif msg.role == "user":
                    user_text = msg.content
            prompt = f"{system_text}\n\n{user_text}" if system_text else user_text
            response = model.generate_content(
                prompt,
                generation_config=self._genai.types.GenerationConfig(
                    temperature=temperature,
                    max_output_tokens=max_tokens,
                ),
            )
        except Exception as exc:
            raise GenerationProviderError(
                provider=self.PROVIDER_NAME,
                message=str(exc),
                retryable=True,
            ) from exc

        latency_ms = (time.monotonic() - t0) * 1000

        # Extract usage if available
        usage = getattr(response, "usage_metadata", None)
        prompt_tokens = getattr(usage, "prompt_token_count", None)
        completion_tokens = getattr(usage, "candidates_token_count", None)
        tokens_available = prompt_tokens is not None

        cost: float | None = None
        if tokens_available and prompt_tokens and completion_tokens:
            cost = (
                prompt_tokens * _INPUT_COST_PER_TOKEN + completion_tokens * _OUTPUT_COST_PER_TOKEN
            )

        return GenerationResult(
            text=response.text,
            model_id=self._model_name,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            tokens_available=tokens_available,
            latency_ms=round(latency_ms, 2),
            estimated_cost_usd=cost,
            provider=self.PROVIDER_NAME,
        )
