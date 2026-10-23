"""Database persistence helpers for RAG preparation events and query measurements."""

from __future__ import annotations

import uuid
from datetime import datetime

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ExperimentRun, PreparationEvent, RequestMeasurement

logger = structlog.get_logger(__name__)


async def record_preparation_event(
    session: AsyncSession,
    *,
    run_id: uuid.UUID,
    document_version_id: uuid.UUID,
    strategy: str,
    consumer_id: str | None,
    status: str,
    is_reuse: bool,
    chunk_count: int | None,
    embedding_tokens_used: int | None,
    embedding_tokens_available: bool,
    duration_ms: float | None,
    estimated_cost_usd: float | None,
    qdrant_collection: str | None,
    error_message: str | None = None,
) -> PreparationEvent:
    """Insert a single preparation event record into PostgreSQL."""
    event = PreparationEvent(
        run_id=run_id,
        document_version_id=document_version_id,
        strategy=strategy,
        consumer_id=consumer_id,
        status=status,
        is_reuse=is_reuse,
        chunk_count=chunk_count,
        embedding_tokens_used=embedding_tokens_used,
        embedding_tokens_available=embedding_tokens_available,
        duration_ms=duration_ms,
        estimated_cost_usd=estimated_cost_usd,
        qdrant_collection=qdrant_collection,
        error_message=error_message,
    )
    session.add(event)
    await session.commit()
    await session.refresh(event)
    return event


async def record_request_measurement(
    session: AsyncSession,
    *,
    run_id: uuid.UUID,
    strategy: str,
    consumer_id: str | None,
    question_id: str,
    question_text: str,
    retrieved_chunk_ids: list[str] | None,
    retrieval_top_k: int | None,
    retrieval_duration_ms: float | None,
    answer_text: str | None,
    prompt_tokens: int | None,
    completion_tokens: int | None,
    generation_tokens_available: bool,
    generation_duration_ms: float | None,
    total_duration_ms: float | None,
    estimated_generation_cost_usd: float | None,
    estimated_retrieval_cost_usd: float | None,
    ground_truth_answer: str | None = None,
    recall_at_k: float | None = None,
    answer_correctness: float | None = None,
    answer_faithfulness: float | None = None,
    evaluation_notes: str | None = None,
    error_message: str | None = None,
) -> RequestMeasurement:
    """Insert a single request measurement record into PostgreSQL."""
    measurement = RequestMeasurement(
        run_id=run_id,
        strategy=strategy,
        consumer_id=consumer_id,
        question_id=question_id,
        question_text=question_text,
        retrieved_chunk_ids=retrieved_chunk_ids,
        retrieval_top_k=retrieval_top_k,
        retrieval_duration_ms=retrieval_duration_ms,
        answer_text=answer_text,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        generation_tokens_available=generation_tokens_available,
        generation_duration_ms=generation_duration_ms,
        total_duration_ms=total_duration_ms,
        estimated_generation_cost_usd=estimated_generation_cost_usd,
        estimated_retrieval_cost_usd=estimated_retrieval_cost_usd,
        ground_truth_answer=ground_truth_answer,
        recall_at_k=recall_at_k,
        answer_correctness=answer_correctness,
        answer_faithfulness=answer_faithfulness,
        evaluation_notes=evaluation_notes,
        error_message=error_message,
    )
    session.add(measurement)
    await session.commit()
    await session.refresh(measurement)
    return measurement


async def update_run_status(
    session: AsyncSession,
    run_id: uuid.UUID,
    status: str,
    error_message: str | None = None,
    finished: bool = False,
) -> None:
    """Update ExperimentRun status and timestamps."""
    run = await session.get(ExperimentRun, run_id)
    if run is not None:
        run.status = status
        if error_message:
            run.error_message = error_message
        if finished:
            run.finished_at = datetime.now()
        await session.commit()
