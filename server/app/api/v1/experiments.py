"""Experiments API – CRUD for experiment configs and runs."""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime
from typing import Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.models import ExperimentConfig, ExperimentRun, ProviderConfig, RunStatus
from app.db.session import get_session, get_session_factory
from app.experiments.runner import ACTIVE_RUN_TASKS, cancel_active_run, execute_experiment_run

logger = structlog.get_logger(__name__)
router = APIRouter()


# ── Schemas ──────────────────────────────────────────────────────────────────


class ExperimentConfigCreate(BaseModel):
    name: str
    description: str | None = None
    provider_config_id: uuid.UUID | None = None
    dataset_name: str
    chunking_config: dict[str, Any]
    retrieval_config: dict[str, Any]
    workload_config: dict[str, Any]
    random_seed: int | None = None
    repetitions: int = 1


class ExperimentConfigOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: str | None
    dataset_name: str
    repetitions: int
    created_at: datetime


class ExperimentRunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    config_id: uuid.UUID
    repetition_index: int
    status: str
    started_at: datetime | None
    finished_at: datetime | None
    error_message: str | None
    created_at: datetime


async def _get_or_create_default_provider(
    session: AsyncSession,
    requested_id: uuid.UUID | None = None,
) -> ProviderConfig:
    if requested_id and requested_id != uuid.UUID(int=0):
        provider = await session.get(ProviderConfig, requested_id)
        if provider is not None:
            return provider

    result = await session.execute(
        select(ProviderConfig).order_by(ProviderConfig.created_at.asc()).limit(1)
    )
    provider = result.scalar_one_or_none()
    if provider is None:
        provider = ProviderConfig(
            provider="gemini",
            embedding_model=settings.gemini_embedding_model,
            generation_model=settings.gemini_generation_model,
            embedding_dimension=settings.embedding_dimension,
            notes="Default AI provider configuration",
        )
        session.add(provider)
        await session.flush()
    return provider


# ── Endpoints ────────────────────────────────────────────────────────────────


@router.get("", response_model=list[ExperimentConfigOut])
async def list_experiments(
    session: AsyncSession = Depends(get_session),
) -> list[ExperimentConfig]:
    result = await session.execute(
        select(ExperimentConfig).order_by(ExperimentConfig.created_at.desc())
    )
    return list(result.scalars().all())


@router.post("", response_model=ExperimentConfigOut, status_code=status.HTTP_201_CREATED)
async def create_experiment(
    payload: ExperimentConfigCreate,
    session: AsyncSession = Depends(get_session),
) -> ExperimentConfig:
    existing = await session.execute(
        select(ExperimentConfig).where(ExperimentConfig.name == payload.name)
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Experiment with name '{payload.name}' already exists",
        )

    provider = await _get_or_create_default_provider(session, payload.provider_config_id)

    config = ExperimentConfig(
        name=payload.name,
        description=payload.description,
        provider_config_id=provider.id,
        dataset_name=payload.dataset_name,
        chunking_config=payload.chunking_config,
        retrieval_config=payload.retrieval_config,
        workload_config=payload.workload_config,
        random_seed=payload.random_seed,
        repetitions=payload.repetitions,
    )
    session.add(config)
    await session.commit()
    await session.refresh(config)
    logger.info("experiment.config.created", id=str(config.id), name=config.name)
    return config


@router.get("/{experiment_id}", response_model=ExperimentConfigOut)
async def get_experiment(
    experiment_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
) -> ExperimentConfig:
    obj = await session.get(ExperimentConfig, experiment_id)
    if obj is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return obj


@router.get("/{experiment_id}/runs", response_model=list[ExperimentRunOut])
async def list_runs(
    experiment_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
) -> list[ExperimentRun]:
    result = await session.execute(
        select(ExperimentRun)
        .where(ExperimentRun.config_id == experiment_id)
        .order_by(ExperimentRun.created_at.desc())
    )
    return list(result.scalars().all())


@router.post(
    "/{experiment_id}/runs",
    response_model=ExperimentRunOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_run(
    experiment_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
) -> ExperimentRun:
    exp = await session.get(ExperimentConfig, experiment_id)
    if exp is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Experiment not found")

    result = await session.execute(
        select(func.count(ExperimentRun.id)).where(ExperimentRun.config_id == experiment_id)
    )
    count = result.scalar() or 0

    run = ExperimentRun(
        config_id=experiment_id,
        repetition_index=count,
        status=RunStatus.PENDING,
    )
    session.add(run)
    await session.commit()
    await session.refresh(run)
    logger.info("experiment.run.created", id=str(run.id), config_id=str(experiment_id))
    return run


@router.get("/{experiment_id}/runs/{run_id}", response_model=ExperimentRunOut)
async def get_run(
    experiment_id: uuid.UUID,
    run_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
) -> ExperimentRun:
    """Retrieve details for a single experiment run."""
    run = await session.get(ExperimentRun, run_id)
    if run is None or run.config_id != experiment_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")
    return run


@router.post("/{experiment_id}/runs/{run_id}/execute")
async def execute_run_endpoint(
    experiment_id: uuid.UUID,
    run_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    """Trigger background execution of an existing run."""
    run = await session.get(ExperimentRun, run_id)
    if run is None or run.config_id != experiment_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")

    if run.status == RunStatus.RUNNING:
        return {"status": "already_running", "run_id": str(run_id)}

    session_factory = get_session_factory()
    task = asyncio.create_task(execute_experiment_run(session_factory, run_id))
    ACTIVE_RUN_TASKS[str(run_id)] = task

    logger.info("experiment.run.started", id=str(run.id), config_id=str(experiment_id))
    return {"status": "started", "run_id": str(run_id)}


@router.post("/{experiment_id}/runs/{run_id}/cancel")
async def cancel_run_endpoint(
    experiment_id: uuid.UUID,
    run_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    """Cancel an active run."""
    run = await session.get(ExperimentRun, run_id)
    if run is None or run.config_id != experiment_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")

    cancelled = cancel_active_run(str(run_id))
    return {"status": "cancelled" if cancelled else "not_running", "run_id": str(run_id)}


@router.post("/{experiment_id}/start", response_model=ExperimentRunOut)
async def start_new_run(
    experiment_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
) -> ExperimentRun:
    """Convenience endpoint: create a new repetition run and immediately launch execution."""
    exp = await session.get(ExperimentConfig, experiment_id)
    if exp is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Experiment not found")

    result = await session.execute(
        select(func.count(ExperimentRun.id)).where(ExperimentRun.config_id == experiment_id)
    )
    count = result.scalar() or 0

    run = ExperimentRun(
        config_id=experiment_id,
        repetition_index=count,
        status=RunStatus.PENDING,
    )
    session.add(run)
    await session.commit()
    await session.refresh(run)

    session_factory = get_session_factory()
    task = asyncio.create_task(execute_experiment_run(session_factory, run.id))
    ACTIVE_RUN_TASKS[str(run.id)] = task

    logger.info("experiment.run.launched", id=str(run.id), config_id=str(experiment_id))
    return run

