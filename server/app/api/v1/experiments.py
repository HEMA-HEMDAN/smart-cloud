"""Experiments API – CRUD for experiment configs and runs."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ExperimentConfig, ExperimentRun
from app.db.session import get_session

logger = structlog.get_logger(__name__)
router = APIRouter()


# ── Schemas ──────────────────────────────────────────────────────────────────


class ExperimentConfigCreate(BaseModel):
    name: str
    description: str | None = None
    provider_config_id: uuid.UUID
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


# ── Endpoints ────────────────────────────────────────────────────────────────


@router.get("", response_model=list[ExperimentConfigOut])
async def list_experiments(
    session: AsyncSession = Depends(get_session),
) -> list[ExperimentConfig]:
    result = await session.execute(
        select(ExperimentConfig).order_by(ExperimentConfig.created_at.desc())
    )
    return list(result.scalars().all())


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
