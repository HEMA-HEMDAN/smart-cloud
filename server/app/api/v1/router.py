"""API v1 router – aggregates all sub-routers."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.documents import router as documents_router
from app.api.v1.experiments import router as experiments_router
from app.api.v1.health import router as health_router
from app.api.v1.results import router as results_router

api_router = APIRouter()

api_router.include_router(health_router, prefix="/health", tags=["health"])
api_router.include_router(documents_router, prefix="/documents", tags=["documents"])
api_router.include_router(experiments_router, prefix="/experiments", tags=["experiments"])
api_router.include_router(results_router, prefix="/results", tags=["results"])
