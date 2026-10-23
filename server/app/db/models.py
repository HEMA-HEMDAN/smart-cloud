"""Research experiment ORM models.

All research tables live in the 'research' schema to keep them isolated
from any future application tables in the 'public' schema.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

SCHEMA = "research"


# ──────────────────────────────────────────────────────────────────────────────
# Enumerations
# ──────────────────────────────────────────────────────────────────────────────


class RagStrategy(str):
    INDEPENDENT = "independent"
    SHARED = "shared"


class RunStatus(str):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class PrepStatus(str):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


# ──────────────────────────────────────────────────────────────────────────────
# Provider / pricing tables
# ──────────────────────────────────────────────────────────────────────────────


class ProviderConfig(Base):
    """Records the AI provider and model configuration used in an experiment."""

    __tablename__ = "provider_configs"
    __table_args__ = {"schema": SCHEMA}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    embedding_model: Mapped[str] = mapped_column(String(128), nullable=False)
    generation_model: Mapped[str] = mapped_column(String(128), nullable=False)
    embedding_dimension: Mapped[int] = mapped_column(Integer, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PricingAssumption(Base):
    """Stores pricing assumptions with source and date for reproducibility."""

    __tablename__ = "pricing_assumptions"
    __table_args__ = {"schema": SCHEMA}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    model: Mapped[str] = mapped_column(String(128), nullable=False)
    cost_per_input_token_usd: Mapped[float | None] = mapped_column(Float)
    cost_per_output_token_usd: Mapped[float | None] = mapped_column(Float)
    cost_per_embedding_token_usd: Mapped[float | None] = mapped_column(Float)
    source_url: Mapped[str | None] = mapped_column(String(512))
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)


# ──────────────────────────────────────────────────────────────────────────────
# Experiment configuration and runs
# ──────────────────────────────────────────────────────────────────────────────


class ExperimentConfig(Base):
    """Top-level experiment definition – shared across multiple runs."""

    __tablename__ = "experiment_configs"
    __table_args__ = {"schema": SCHEMA}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(256), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(Text)
    provider_config_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey(f"{SCHEMA}.provider_configs.id"), nullable=False
    )
    dataset_name: Mapped[str] = mapped_column(String(256), nullable=False)
    chunking_config: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    retrieval_config: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    workload_config: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    random_seed: Mapped[int | None] = mapped_column(Integer)
    repetitions: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    runs: Mapped[list[ExperimentRun]] = relationship(back_populates="config")


class ExperimentRun(Base):
    """One execution of an experiment configuration."""

    __tablename__ = "experiment_runs"
    __table_args__ = {"schema": SCHEMA}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    config_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(f"{SCHEMA}.experiment_configs.id"),
        nullable=False,
    )
    repetition_index: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(32), default=RunStatus.PENDING)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    config: Mapped[ExperimentConfig] = relationship(back_populates="runs")
    measurements: Mapped[list[RequestMeasurement]] = relationship(back_populates="run")


# ──────────────────────────────────────────────────────────────────────────────
# Documents
# ──────────────────────────────────────────────────────────────────────────────


class DocumentVersion(Base):
    """Tracks a specific version of a source document."""

    __tablename__ = "document_versions"
    __table_args__ = {"schema": SCHEMA}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id: Mapped[str] = mapped_column(String(512), nullable=False, index=True)
    version_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    title: Mapped[str | None] = mapped_column(String(512))
    source_path: Mapped[str | None] = mapped_column(String(1024))
    content_length_chars: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PreparationEvent(Base):
    """Records a document preparation attempt for a specific strategy."""

    __tablename__ = "preparation_events"
    __table_args__ = {"schema": SCHEMA}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(f"{SCHEMA}.experiment_runs.id"),
        nullable=False,
        index=True,
    )
    document_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(f"{SCHEMA}.document_versions.id"),
        nullable=False,
    )
    strategy: Mapped[str] = mapped_column(String(32), nullable=False)
    consumer_id: Mapped[str | None] = mapped_column(String(128))
    status: Mapped[str] = mapped_column(String(32), default=PrepStatus.PENDING)
    is_reuse: Mapped[bool] = mapped_column(Boolean, default=False)
    chunk_count: Mapped[int | None] = mapped_column(Integer)
    embedding_tokens_used: Mapped[int | None] = mapped_column(Integer)
    embedding_tokens_available: Mapped[bool] = mapped_column(Boolean, default=True)
    duration_ms: Mapped[float | None] = mapped_column(Float)
    estimated_cost_usd: Mapped[float | None] = mapped_column(Float)
    pricing_assumption_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey(f"{SCHEMA}.pricing_assumptions.id")
    )
    qdrant_collection: Mapped[str | None] = mapped_column(String(256))
    error_message: Mapped[str | None] = mapped_column(Text)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


# ──────────────────────────────────────────────────────────────────────────────
# Per-request measurements
# ──────────────────────────────────────────────────────────────────────────────


class RequestMeasurement(Base):
    """Raw measurement for a single question answered by one strategy."""

    __tablename__ = "request_measurements"
    __table_args__ = {"schema": SCHEMA}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(f"{SCHEMA}.experiment_runs.id"),
        nullable=False,
        index=True,
    )
    strategy: Mapped[str] = mapped_column(String(32), nullable=False)
    consumer_id: Mapped[str | None] = mapped_column(String(128))
    question_id: Mapped[str] = mapped_column(String(256), nullable=False)
    question_text: Mapped[str] = mapped_column(Text, nullable=False)

    # Retrieval
    retrieved_chunk_ids: Mapped[list[str] | None] = mapped_column(JSON)
    retrieval_top_k: Mapped[int | None] = mapped_column(Integer)
    retrieval_duration_ms: Mapped[float | None] = mapped_column(Float)

    # Generation
    answer_text: Mapped[str | None] = mapped_column(Text)
    prompt_tokens: Mapped[int | None] = mapped_column(Integer)
    completion_tokens: Mapped[int | None] = mapped_column(Integer)
    generation_tokens_available: Mapped[bool] = mapped_column(Boolean, default=True)
    generation_duration_ms: Mapped[float | None] = mapped_column(Float)
    total_duration_ms: Mapped[float | None] = mapped_column(Float)

    # Cost
    estimated_generation_cost_usd: Mapped[float | None] = mapped_column(Float)
    estimated_retrieval_cost_usd: Mapped[float | None] = mapped_column(Float)
    pricing_assumption_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey(f"{SCHEMA}.pricing_assumptions.id")
    )

    # Evaluation
    ground_truth_answer: Mapped[str | None] = mapped_column(Text)
    recall_at_k: Mapped[float | None] = mapped_column(Float)
    answer_correctness: Mapped[float | None] = mapped_column(Float)
    answer_faithfulness: Mapped[float | None] = mapped_column(Float)
    evaluation_notes: Mapped[str | None] = mapped_column(Text)

    # Error tracking
    error_message: Mapped[str | None] = mapped_column(Text)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)

    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    run: Mapped[ExperimentRun] = relationship(back_populates="measurements")
