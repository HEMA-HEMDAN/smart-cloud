"""API v1 router – aggregates all sub-routers."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.experiments import router as experiments_router
from app.api.v1.health import router as health_router

api_router = APIRouter()

api_router.include_router(health_router, prefix="/health", tags=["health"])
api_router.include_router(experiments_router, prefix="/experiments", tags=["experiments"])
