"""Integration tests – require running PostgreSQL and Qdrant.

Mark: @pytest.mark.integration
Run with: pytest -m integration
"""

from __future__ import annotations

import pytest


@pytest.mark.integration
async def test_postgres_connectivity() -> None:
    """Verify we can connect to PostgreSQL and execute a read-only query."""
    from app.core.config import settings
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine

    engine = create_async_engine(settings.database_url_async, pool_pre_ping=True)
    async with engine.connect() as conn:
        result = await conn.execute(text("SELECT 1"))
        assert result.scalar() == 1
    await engine.dispose()


@pytest.mark.integration
async def test_qdrant_connectivity() -> None:
    """Verify Qdrant is reachable and reports collections list."""
    from app.core.config import settings
    from qdrant_client import AsyncQdrantClient

    client = AsyncQdrantClient(host=settings.qdrant_host, port=settings.qdrant_port)
    collections = await client.get_collections()
    # Simply check the response is well-formed – do not assert collection count
    assert hasattr(collections, "collections")
    await client.close()


@pytest.mark.integration
async def test_health_endpoint() -> None:
    """End-to-end health endpoint test against running services."""
    from app import app
    from httpx import ASGITransport, AsyncClient

    async with (
        app.router.lifespan_context(app),
        AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client,
    ):
        response = await client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["services"]["postgres"]["ok"] is True
    assert data["services"]["qdrant"]["ok"] is True
    # Verify no secrets in response
    response_text = response.text
    assert "password" not in response_text.lower()
    assert "api_key" not in response_text.lower()
