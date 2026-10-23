"""Health-check endpoints.

Reports application, PostgreSQL, and Qdrant status.
Never exposes secret values in responses.
"""

from __future__ import annotations

import time
from typing import Any

import structlog
from fastapi import APIRouter, status
from pydantic import BaseModel
from sqlalchemy import text

from app.core.config import settings
from app.db.qdrant import get_qdrant
from app.db.session import get_session_factory

logger = structlog.get_logger(__name__)
router = APIRouter()


class ServiceStatus(BaseModel):
    ok: bool
    detail: str | None = None
    latency_ms: float | None = None


class HealthResponse(BaseModel):
    status: str  # "healthy" | "degraded" | "unhealthy"
    version: str
    environment: str
    services: dict[str, ServiceStatus]
    config_summary: dict[str, Any]


async def _check_postgres() -> ServiceStatus:
    t0 = time.monotonic()
    try:
        factory = get_session_factory()
        async with factory() as session:
            await session.execute(text("SELECT 1"))
        return ServiceStatus(
            ok=True,
            latency_ms=round((time.monotonic() - t0) * 1000, 2),
        )
    except Exception as exc:
        logger.warning("health.postgres.failed", error=str(exc))
        return ServiceStatus(ok=False, detail="connection failed")


async def _check_qdrant() -> ServiceStatus:
    t0 = time.monotonic()
    try:
        client = get_qdrant()
        collections = await client.get_collections()
        return ServiceStatus(
            ok=True,
            latency_ms=round((time.monotonic() - t0) * 1000, 2),
            detail=f"{len(collections.collections)} collections",
        )
    except Exception as exc:
        logger.warning("health.qdrant.failed", error=str(exc))
        return ServiceStatus(ok=False, detail="connection failed")


@router.get(
    "",
    response_model=HealthResponse,
    summary="Application health check",
)
async def health() -> HealthResponse:
    pg = await _check_postgres()
    qd = await _check_qdrant()

    all_ok = pg.ok and qd.ok
    overall = "healthy" if all_ok else ("degraded" if pg.ok or qd.ok else "unhealthy")

    return HealthResponse(
        status=overall,
        version="0.1.0",
        environment=settings.environment,
        services={"postgres": pg, "qdrant": qd},
        config_summary=settings.safe_summary(),
    )


@router.get(
    "/live",
    status_code=status.HTTP_200_OK,
    summary="Liveness probe – returns 200 if the process is running",
)
async def liveness() -> dict[str, str]:
    return {"status": "alive"}


@router.get(
    "/ready",
    summary="Readiness probe – returns 200 only when all services are reachable",
)
async def readiness() -> dict[str, str]:
    pg = await _check_postgres()
    qd = await _check_qdrant()
    if not (pg.ok and qd.ok):
        from fastapi import HTTPException

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="One or more backing services are unavailable",
        )
    return {"status": "ready"}
