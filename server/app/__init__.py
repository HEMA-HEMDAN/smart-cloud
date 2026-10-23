"""
Shared AI Intelligence – Research Backend
FastAPI application factory.
"""

from __future__ import annotations

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.logging import configure_logging
from app.db.session import db_lifespan

logger = structlog.get_logger(__name__)


def create_app() -> FastAPI:
    configure_logging()

    app = FastAPI(
        title="Shared AI Intelligence Research API",
        description=(
            "Backend for the Organization-Aware, Demand-Driven Shared AI Intelligence "
            "research experiment."
        ),
        version="0.1.0",
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
        lifespan=db_lifespan,
    )

    # CORS – allow local frontend only
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_router, prefix="/api/v1")

    return app


app = create_app()
