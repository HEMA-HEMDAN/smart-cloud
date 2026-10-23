"""Application configuration loaded from environment variables.

Never print or log secrets – values are masked in __repr__.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── PostgreSQL ───────────────────────────────────────────────────────────
    db_name: str = Field(default="", description="PostgreSQL database name")
    db_user: str = Field(default="", description="PostgreSQL user")
    db_password: str = Field(default="", description="PostgreSQL password")
    db_host: str = Field(default="localhost")
    db_port: int = Field(default=5432)

    # Derived – built in validator, never read directly from env
    database_url: str = ""
    database_url_async: str = ""

    # ── Qdrant ───────────────────────────────────────────────────────────────
    qdrant_host: str = Field(default="localhost")
    qdrant_port: int = Field(default=6333)
    qdrant_grpc_port: int = Field(default=6334)
    qdrant_api_key: str | None = Field(default=None)

    # ── AI providers ─────────────────────────────────────────────────────────
    gemini_api_key: str | None = Field(default=None)
    gemini_embedding_model: str = Field(default="models/text-embedding-004")
    gemini_generation_model: str = Field(default="models/gemini-1.5-flash")
    embedding_dimension: int = Field(default=768)

    # ── Application ──────────────────────────────────────────────────────────
    environment: str = Field(default="development")
    log_level: str = Field(default="INFO")
    cors_origins: list[str] = Field(default=["http://localhost:5173", "http://127.0.0.1:5173"])

    # ── Research experiment defaults ─────────────────────────────────────────
    research_schema: str = Field(default="research")
    qdrant_collection_independent: str = Field(default="research_independent_rag")
    qdrant_collection_shared: str = Field(default="research_shared_intelligence")

    @model_validator(mode="after")
    def build_database_urls(self) -> Settings:
        base = (
            f"postgresql://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )
        self.database_url = base
        self.database_url_async = base.replace("postgresql://", "postgresql+asyncpg://")
        return self

    def safe_summary(self) -> dict[str, Any]:
        """Return non-secret configuration values safe for logging and health endpoints."""
        return {
            "environment": self.environment,
            "db_host": self.db_host,
            "db_port": self.db_port,
            "db_name": self.db_name,
            "qdrant_host": self.qdrant_host,
            "qdrant_port": self.qdrant_port,
            "gemini_embedding_model": self.gemini_embedding_model,
            "gemini_generation_model": self.gemini_generation_model,
            "embedding_dimension": self.embedding_dimension,
            "research_schema": self.research_schema,
            "qdrant_collection_independent": self.qdrant_collection_independent,
            "qdrant_collection_shared": self.qdrant_collection_shared,
            "gemini_configured": self.gemini_api_key is not None,
        }


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
