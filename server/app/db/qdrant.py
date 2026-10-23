"""Qdrant client lifecycle management."""

from __future__ import annotations

from typing import Any

import structlog
from qdrant_client import AsyncQdrantClient

from app.core.config import settings

logger = structlog.get_logger(__name__)

_client: AsyncQdrantClient | None = None


def get_qdrant() -> AsyncQdrantClient:
    if _client is None:
        raise RuntimeError("Qdrant client not initialised.")
    return _client


async def init_qdrant() -> None:
    global _client
    kwargs: dict[str, Any] = {
        "host": settings.qdrant_host,
        "port": settings.qdrant_port,
        "grpc_port": settings.qdrant_grpc_port,
        "prefer_grpc": False,
    }
    if settings.qdrant_api_key:
        kwargs["api_key"] = settings.qdrant_api_key

    _client = AsyncQdrantClient(**kwargs)
    logger.info(
        "qdrant.client.created",
        host=settings.qdrant_host,
        port=settings.qdrant_port,
    )


async def close_qdrant() -> None:
    global _client
    if _client is not None:
        await _client.close()
        _client = None
        logger.info("qdrant.client.closed")
