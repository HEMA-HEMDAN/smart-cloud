"""Results and measurements API for experiment runs."""

from __future__ import annotations

import io
import uuid
from typing import Any

import pandas as pd
from analysis.cost import compute_cost_summary
from analysis.latency import compute_latency_summary
from analysis.reuse import compute_reuse_summary
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ExperimentRun, PreparationEvent, RequestMeasurement
from app.db.session import get_session
from app.experiments.runner import get_run_progress

router = APIRouter()


class MeasurementOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    run_id: uuid.UUID
    strategy: str
    consumer_id: str | None
    question_id: str
    question_text: str
    retrieved_chunk_ids: list[str] | None
    retrieval_duration_ms: float | None
    answer_text: str | None
    prompt_tokens: int | None
    completion_tokens: int | None
    generation_duration_ms: float | None
    total_duration_ms: float | None
    estimated_generation_cost_usd: float | None
    ground_truth_answer: str | None
    recall_at_k: float | None
    answer_correctness: float | None
    error_message: str | None


class PreparationEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    run_id: uuid.UUID
    strategy: str
    consumer_id: str | None
    status: str
    is_reuse: bool
    chunk_count: int | None
    embedding_tokens_used: int | None
    duration_ms: float | None
    estimated_cost_usd: float | None
    qdrant_collection: str | None
    error_message: str | None


class ResultsSummaryOut(BaseModel):
    run_id: uuid.UUID
    status: str
    cost_summary: dict[str, Any]
    latency_summary: dict[str, Any]
    reuse_summary: dict[str, Any]
    quality_summary: dict[str, Any]
    security_violations: int
    total_measurements: int
    total_preparations: int
    note: str | None = None


@router.get("/progress/{run_id}")
async def get_progress(run_id: uuid.UUID) -> dict[str, Any]:
    """Get active in-memory progress for an executing run."""
    progress = get_run_progress(str(run_id))
    if progress is None:
        return {"run_id": str(run_id), "status": "unknown"}
    return progress


@router.get("/{run_id}/results", response_model=ResultsSummaryOut)
async def get_run_results(
    run_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
) -> ResultsSummaryOut:
    """Compute and return aggregated side-by-side A/B results for a run."""
    run = await session.get(ExperimentRun, run_id)
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")

    # Fetch request measurements
    meas_result = await session.execute(
        select(RequestMeasurement).where(RequestMeasurement.run_id == run_id)
    )
    measurements = list(meas_result.scalars().all())

    # Fetch preparation events
    prep_result = await session.execute(
        select(PreparationEvent).where(PreparationEvent.run_id == run_id)
    )
    prep_events = list(prep_result.scalars().all())

    if not measurements and not prep_events:
        return ResultsSummaryOut(
            run_id=run_id,
            status=run.status,
            cost_summary={"per_strategy": {}, "note": "No measurements recorded yet."},
            latency_summary={"per_strategy": {}, "note": "No latency data available."},
            reuse_summary={"note": "No preparation events recorded yet."},
            quality_summary={"note": "No evaluation data recorded."},
            security_violations=0,
            total_measurements=0,
            total_preparations=0,
            note="Awaiting run execution.",
        )

    # Convert to DataFrames for analysis modules
    meas_dicts = [
        {
            "run_id": str(m.run_id),
            "strategy": m.strategy,
            "consumer_id": m.consumer_id,
            "question_id": m.question_id,
            "total_duration_ms": m.total_duration_ms or 0.0,
            "retrieval_duration_ms": m.retrieval_duration_ms or 0.0,
            "generation_duration_ms": m.generation_duration_ms or 0.0,
            "estimated_cost_usd": m.estimated_generation_cost_usd,
            "recall_at_k": m.recall_at_k,
            "answer_correctness": m.answer_correctness,
        }
        for m in measurements
    ]
    meas_df = pd.DataFrame(meas_dicts)

    prep_dicts = [
        {
            "run_id": str(p.run_id),
            "strategy": p.strategy,
            "is_reuse": p.is_reuse,
            "duration_ms": p.duration_ms,
            "chunk_count": p.chunk_count,
            "estimated_cost_usd": p.estimated_cost_usd or 0.0,
        }
        for p in prep_events
    ]
    prep_df = pd.DataFrame(prep_dicts)

    cost_summary = compute_cost_summary(meas_df) if not meas_df.empty else {}
    latency_summary = compute_latency_summary(meas_df) if not meas_df.empty else {}
    reuse_summary = compute_reuse_summary(prep_df) if not prep_df.empty else {}

    # Augment cost summary with preparation costs
    if not prep_df.empty:
        prep_cost_by_strategy = (
            prep_df.groupby("strategy")["estimated_cost_usd"].sum().to_dict()
        )
        for strat, p_cost in prep_cost_by_strategy.items():
            if "per_strategy" in cost_summary and strat in cost_summary["per_strategy"]:
                cost_summary["per_strategy"][strat]["preparation_estimated_usd"] = float(p_cost)
                q_cost = cost_summary["per_strategy"][strat].get("total_estimated_usd") or 0.0
                total_w = round(q_cost + p_cost, 6)
                cost_summary["per_strategy"][strat]["total_workload_usd"] = total_w

    # Calculate quality metrics if available
    quality_summary: dict[str, Any] = {"per_strategy": {}}
    if not meas_df.empty and "recall_at_k" in meas_df.columns:
        for strat, group in meas_df.groupby("strategy"):
            valid_rec = group["recall_at_k"].dropna()
            valid_corr = group["answer_correctness"].dropna()
            quality_summary["per_strategy"][strat] = {
                "mean_recall_at_k": float(valid_rec.mean()) if len(valid_rec) > 0 else None,
                "mean_correctness": float(valid_corr.mean()) if len(valid_corr) > 0 else None,
                "evaluated_queries": int(len(valid_rec)),
            }

    progress = get_run_progress(str(run_id))
    sec_violations = progress.get("security_violations", 0) if progress else 0

    return ResultsSummaryOut(
        run_id=run_id,
        status=run.status,
        cost_summary=cost_summary,
        latency_summary=latency_summary,
        reuse_summary=reuse_summary,
        quality_summary=quality_summary,
        security_violations=sec_violations,
        total_measurements=len(measurements),
        total_preparations=len(prep_events),
    )


@router.get("/{run_id}/measurements", response_model=list[MeasurementOut])
async def list_measurements(
    run_id: uuid.UUID,
    strategy: str | None = None,
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_session),
) -> list[MeasurementOut]:
    """List paginated request measurements for a run."""
    stmt = (
        select(RequestMeasurement)
        .where(RequestMeasurement.run_id == run_id)
        .order_by(RequestMeasurement.occurred_at.asc())
        .offset(offset)
        .limit(limit)
    )
    if strategy:
        stmt = stmt.where(RequestMeasurement.strategy == strategy)

    result = await session.execute(stmt)
    rows = list(result.scalars().all())
    return [MeasurementOut.model_validate(r) for r in rows]


@router.get("/{run_id}/preparation-events", response_model=list[PreparationEventOut])
async def list_preparation_events(
    run_id: uuid.UUID,
    strategy: str | None = None,
    session: AsyncSession = Depends(get_session),
) -> list[PreparationEventOut]:
    """List all preparation events for a run."""
    stmt = (
        select(PreparationEvent)
        .where(PreparationEvent.run_id == run_id)
        .order_by(PreparationEvent.occurred_at.asc())
    )
    if strategy:
        stmt = stmt.where(PreparationEvent.strategy == strategy)

    result = await session.execute(stmt)
    rows = list(result.scalars().all())
    return [PreparationEventOut.model_validate(r) for r in rows]


@router.get("/{run_id}/export")
async def export_measurements(
    run_id: uuid.UUID,
    format: str = Query(default="csv", pattern="^(csv|jsonl)$"),
    session: AsyncSession = Depends(get_session),
) -> Response:
    """Export raw measurements as CSV or JSONL for offline statistical analysis."""
    result = await session.execute(
        select(RequestMeasurement)
        .where(RequestMeasurement.run_id == run_id)
        .order_by(RequestMeasurement.occurred_at.asc())
    )
    rows = list(result.scalars().all())

    records = [
        {
            "run_id": str(r.run_id),
            "strategy": r.strategy,
            "consumer_id": r.consumer_id,
            "question_id": r.question_id,
            "retrieval_duration_ms": r.retrieval_duration_ms,
            "generation_duration_ms": r.generation_duration_ms,
            "total_duration_ms": r.total_duration_ms,
            "prompt_tokens": r.prompt_tokens,
            "completion_tokens": r.completion_tokens,
            "estimated_cost_usd": r.estimated_generation_cost_usd,
            "recall_at_k": r.recall_at_k,
            "answer_correctness": r.answer_correctness,
            "error_message": r.error_message,
        }
        for r in rows
    ]

    df = pd.DataFrame(records)

    if format == "jsonl":
        output = df.to_json(orient="records", lines=True)
        filename = f"run_{run_id}_measurements.jsonl"
        return Response(
            content=output or "",
            media_type="application/x-ndjson",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )

    csv_buf = io.StringIO()
    df.to_csv(csv_buf, index=False)
    filename_csv = f"run_{run_id}_measurements.csv"
    return Response(
        content=csv_buf.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename_csv}"},
    )
