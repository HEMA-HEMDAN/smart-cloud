"""Core Experiment Execution Engine for Paired A/B Strategy Evaluation."""

from __future__ import annotations

import asyncio
import time
import uuid
from datetime import datetime
from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from analysis.evaluation import compute_answer_correctness, compute_recall_at_k
from app.core.config import settings
from app.db.models import (
    DocumentVersion,
    ExperimentConfig,
    ExperimentRun,
    PrepStatus,
    RunStatus,
)
from app.db.qdrant import get_qdrant
from app.documents.service import get_document_text
from app.embeddings.base import EmbeddingProvider
from app.embeddings.mock import MockEmbeddingProvider
from app.experiments.workload import BenchmarkQuestion, generate_workload_plan
from app.generation.base import GenerationProvider
from app.generation.mock import MockGenerationProvider
from app.rag.base import RAGRequest
from app.rag.independent.strategy import IndependentRAG
from app.rag.persistence import (
    record_preparation_event,
    record_request_measurement,
    update_run_status,
)
from app.rag.shared.strategy import SharedIntelligenceRAG

logger = structlog.get_logger(__name__)

# Global in-memory tracking of active run progress for UI polling
ACTIVE_RUN_PROGRESS: dict[str, dict[str, Any]] = {}
ACTIVE_RUN_TASKS: dict[str, asyncio.Task[None]] = {}


def get_run_progress(run_id: str) -> dict[str, Any] | None:
    """Return live execution progress for an active or recently finished run."""
    return ACTIVE_RUN_PROGRESS.get(run_id)


def cancel_active_run(run_id: str) -> bool:
    """Request cancellation of a currently executing run task."""
    task = ACTIVE_RUN_TASKS.get(run_id)
    if task and not task.done():
        task.cancel()
        return True
    return False


async def execute_experiment_run(
    session_factory: async_sessionmaker[AsyncSession],
    run_id: uuid.UUID,
) -> None:
    """
    Execute a full paired A/B experiment run sequentially across all repetitions.

    Persists observations incrementally to PostgreSQL.
    """
    run_key = str(run_id)
    t0_start = time.monotonic()

    # Progress state
    ACTIVE_RUN_PROGRESS[run_key] = {
        "run_id": run_key,
        "status": RunStatus.RUNNING,
        "current_repetition": 0,
        "total_repetitions": 1,
        "current_strategy": "initializing",
        "completed_requests": 0,
        "failed_requests": 0,
        "security_violations": 0,
        "started_at": datetime.now().isoformat(),
        "elapsed_seconds": 0.0,
    }

    async with session_factory() as session:
        run = await session.get(ExperimentRun, run_id)
        if run is None:
            logger.error("experiment.run.not_found", run_id=run_key)
            ACTIVE_RUN_PROGRESS[run_key]["status"] = RunStatus.FAILED
            return

        config = await session.get(ExperimentConfig, run.config_id)
        if config is None:
            logger.error("experiment.config.not_found", config_id=str(run.config_id))
            await update_run_status(
                session, run_id, RunStatus.FAILED, "Experiment configuration not found."
            )
            ACTIVE_RUN_PROGRESS[run_key]["status"] = RunStatus.FAILED
            return

        # Mark run as RUNNING in DB
        run.status = RunStatus.RUNNING
        run.started_at = datetime.now()
        await session.commit()

        # Resolve document
        doc_version_id_str = config.workload_config.get("document_version_id")
        doc_version: DocumentVersion | None = None
        if doc_version_id_str:
            try:
                doc_version = await session.get(DocumentVersion, uuid.UUID(doc_version_id_str))
            except Exception:
                doc_version = None

        if doc_version is None:
            # Fallback to most recent document version in DB
            result = await session.execute(
                select(DocumentVersion).order_by(DocumentVersion.created_at.desc()).limit(1)
            )
            doc_version = result.scalar_one_or_none()

        if doc_version is None:
            err = "No document version found to execute experiment on."
            await update_run_status(session, run_id, RunStatus.FAILED, err, finished=True)
            ACTIVE_RUN_PROGRESS[run_key]["status"] = RunStatus.FAILED
            ACTIVE_RUN_PROGRESS[run_key]["error"] = err
            return

        try:
            document_text = await get_document_text(doc_version)
        except Exception as exc:
            err = f"Failed to read document text: {exc}"
            await update_run_status(session, run_id, RunStatus.FAILED, err, finished=True)
            ACTIVE_RUN_PROGRESS[run_key]["status"] = RunStatus.FAILED
            ACTIVE_RUN_PROGRESS[run_key]["error"] = err
            return

    # Workload parameters
    repetitions = max(1, config.repetitions)
    consumer_count = config.workload_config.get("consumer_count", 10)
    random_seed = config.random_seed or 42
    workload_type = config.workload_config.get("type", "high_reuse")
    chunk_size = config.chunking_config.get("chunk_size", 512)
    chunk_overlap = config.chunking_config.get("chunk_overlap", 64)
    top_k = config.retrieval_config.get("top_k", 5)

    raw_questions = config.workload_config.get("benchmark_questions", [])
    benchmark_questions = [
        BenchmarkQuestion(
            question_id=q.get("question_id", f"q{i}"),
            question_text=q.get("question_text", q.get("question", "")),
            expected_answer=q.get("expected_answer"),
            expected_chunk_ids=q.get("expected_chunk_ids"),
        )
        for i, q in enumerate(raw_questions)
    ]
    if not benchmark_questions:
        benchmark_questions = [
            BenchmarkQuestion(
                question_id="q0",
                question_text="What are the key concepts described in this document?",
            )
        ]

    workload_plan = generate_workload_plan(
        consumer_count=consumer_count,
        repetitions=repetitions,
        questions=benchmark_questions,
        workload_type=workload_type,
        random_seed=random_seed,
    )

    ACTIVE_RUN_PROGRESS[run_key]["total_repetitions"] = repetitions

    # Select AI providers (mock vs live gemini)
    provider_type = config.workload_config.get("provider", "mock").lower()
    embedder: EmbeddingProvider
    generator: GenerationProvider

    if provider_type == "gemini":
        from app.embeddings.gemini import GeminiEmbeddingProvider
        from app.generation.gemini import GeminiGenerationProvider

        try:
            embedder = GeminiEmbeddingProvider()
            generator = GeminiGenerationProvider()
        except Exception as exc:
            logger.warning(
                "gemini.provider.failed_fallback_to_mock",
                error=str(exc),
            )
            embedder = MockEmbeddingProvider(dim=settings.embedding_dimension)
            generator = MockGenerationProvider()
    else:
        embedder = MockEmbeddingProvider(dim=settings.embedding_dimension)
        generator = MockGenerationProvider()

    qdrant = get_qdrant()

    try:
        # Loop over repetitions
        for rep_idx in range(repetitions):
            ACTIVE_RUN_PROGRESS[run_key]["current_repetition"] = rep_idx + 1
            tasks = workload_plan.tasks_per_repetition[rep_idx]

            # Fresh RAG strategy instances per repetition
            strategy_a = IndependentRAG(
                embedding_provider=embedder,
                generation_provider=generator,
                qdrant_client=qdrant,
            )
            strategy_b = SharedIntelligenceRAG(
                embedding_provider=embedder,
                generation_provider=generator,
                qdrant_client=qdrant,
            )

            # ── 1. STRATEGY A (Independent Baseline) ──────────────────────────
            ACTIVE_RUN_PROGRESS[run_key]["current_strategy"] = "Strategy A (Independent)"
            for task in tasks:
                cid = task.consumer_id

                # Prepare document independently for this consumer
                try:
                    prep_res = await strategy_a.prepare_document(
                        document_id=doc_version.document_id,
                        version_hash=doc_version.version_hash,
                        text=document_text,
                        run_id=run_key,
                        consumer_id=cid,
                        chunk_size=chunk_size,
                        chunk_overlap=chunk_overlap,
                        repetition_index=rep_idx,
                    )
                    async with session_factory() as s:
                        await record_preparation_event(
                            s,
                            run_id=run_id,
                            document_version_id=doc_version.id,
                            strategy="independent",
                            consumer_id=cid,
                            status=PrepStatus.COMPLETED,
                            is_reuse=False,
                            chunk_count=prep_res.get("chunk_count"),
                            embedding_tokens_used=prep_res.get("embedding_tokens_used"),
                            embedding_tokens_available=prep_res.get(
                                "embedding_tokens_available", True
                            ),
                            duration_ms=prep_res.get("duration_ms"),
                            estimated_cost_usd=0.0,
                            qdrant_collection=prep_res.get("collection"),
                        )
                except Exception as exc:
                    logger.error("prep.failed.strat_a", consumer=cid, error=str(exc))
                    ACTIVE_RUN_PROGRESS[run_key]["failed_requests"] += 1
                    async with session_factory() as s:
                        await record_preparation_event(
                            s,
                            run_id=run_id,
                            document_version_id=doc_version.id,
                            strategy="independent",
                            consumer_id=cid,
                            status=PrepStatus.FAILED,
                            is_reuse=False,
                            chunk_count=None,
                            embedding_tokens_used=None,
                            embedding_tokens_available=False,
                            duration_ms=None,
                            estimated_cost_usd=None,
                            qdrant_collection=None,
                            error_message=str(exc),
                        )

                # Execute benchmark queries for this consumer
                for q in task.questions:
                    req = RAGRequest(
                        run_id=run_key,
                        question_id=q.question_id,
                        question=q.question_text,
                        consumer_id=cid,
                        top_k=top_k,
                        repetition_index=rep_idx,
                    )
                    try:
                        ans_res = await strategy_a.answer(req)
                        retrieved_ids = [c.chunk_id for c in ans_res.retrieved_chunks]
                        recall = compute_recall_at_k(retrieved_ids, q.expected_chunk_ids)
                        correctness = compute_answer_correctness(
                            ans_res.answer, q.expected_answer
                        )

                        async with session_factory() as s:
                            await record_request_measurement(
                                s,
                                run_id=run_id,
                                strategy="independent",
                                consumer_id=cid,
                                question_id=q.question_id,
                                question_text=q.question_text,
                                retrieved_chunk_ids=retrieved_ids,
                                retrieval_top_k=top_k,
                                retrieval_duration_ms=ans_res.retrieval_duration_ms,
                                answer_text=ans_res.answer,
                                prompt_tokens=ans_res.prompt_tokens,
                                completion_tokens=ans_res.completion_tokens,
                                generation_tokens_available=ans_res.tokens_available,
                                generation_duration_ms=ans_res.generation_duration_ms,
                                total_duration_ms=ans_res.total_duration_ms,
                                estimated_generation_cost_usd=ans_res.estimated_cost_usd,
                                estimated_retrieval_cost_usd=0.0,
                                ground_truth_answer=q.expected_answer,
                                recall_at_k=recall,
                                answer_correctness=correctness,
                            )
                        ACTIVE_RUN_PROGRESS[run_key]["completed_requests"] += 1
                    except Exception as exc:
                        logger.error("query.failed.strat_a", consumer=cid, error=str(exc))
                        ACTIVE_RUN_PROGRESS[run_key]["failed_requests"] += 1
                        async with session_factory() as s:
                            await record_request_measurement(
                                s,
                                run_id=run_id,
                                strategy="independent",
                                consumer_id=cid,
                                question_id=q.question_id,
                                question_text=q.question_text,
                                retrieved_chunk_ids=None,
                                retrieval_top_k=top_k,
                                retrieval_duration_ms=None,
                                answer_text=None,
                                prompt_tokens=None,
                                completion_tokens=None,
                                generation_tokens_available=False,
                                generation_duration_ms=None,
                                total_duration_ms=None,
                                estimated_generation_cost_usd=None,
                                estimated_retrieval_cost_usd=None,
                                error_message=str(exc),
                            )

            # ── 2. STRATEGY B (Shared Intelligence RAG) ───────────────────────
            ACTIVE_RUN_PROGRESS[run_key]["current_strategy"] = "Strategy B (Shared)"
            for task in tasks:
                cid = task.consumer_id

                # Prepare / reuse document
                try:
                    prep_res = await strategy_b.prepare_document(
                        document_id=doc_version.document_id,
                        version_hash=doc_version.version_hash,
                        text=document_text,
                        run_id=run_key,
                        consumer_id=cid,
                        chunk_size=chunk_size,
                        chunk_overlap=chunk_overlap,
                        repetition_index=rep_idx,
                    )
                    is_reuse = prep_res.get("is_reuse", False)
                    async with session_factory() as s:
                        await record_preparation_event(
                            s,
                            run_id=run_id,
                            document_version_id=doc_version.id,
                            strategy="shared",
                            consumer_id=cid,
                            status=PrepStatus.COMPLETED,
                            is_reuse=is_reuse,
                            chunk_count=prep_res.get("chunk_count"),
                            embedding_tokens_used=prep_res.get("embedding_tokens_used"),
                            embedding_tokens_available=prep_res.get(
                                "embedding_tokens_available", True
                            ),
                            duration_ms=prep_res.get("duration_ms"),
                            estimated_cost_usd=0.0,
                            qdrant_collection=prep_res.get("collection"),
                        )
                except Exception as exc:
                    logger.error("prep.failed.strat_b", consumer=cid, error=str(exc))
                    ACTIVE_RUN_PROGRESS[run_key]["failed_requests"] += 1
                    async with session_factory() as s:
                        await record_preparation_event(
                            s,
                            run_id=run_id,
                            document_version_id=doc_version.id,
                            strategy="shared",
                            consumer_id=cid,
                            status=PrepStatus.FAILED,
                            is_reuse=False,
                            chunk_count=None,
                            embedding_tokens_used=None,
                            embedding_tokens_available=False,
                            duration_ms=None,
                            estimated_cost_usd=None,
                            qdrant_collection=None,
                            error_message=str(exc),
                        )

                # Execute benchmark queries for this consumer
                for q in task.questions:
                    req = RAGRequest(
                        run_id=run_key,
                        question_id=q.question_id,
                        question=q.question_text,
                        consumer_id=cid,
                        top_k=top_k,
                        repetition_index=rep_idx,
                    )
                    try:
                        ans_res = await strategy_b.answer(req)
                        retrieved_ids = [c.chunk_id for c in ans_res.retrieved_chunks]
                        recall = compute_recall_at_k(retrieved_ids, q.expected_chunk_ids)
                        correctness = compute_answer_correctness(
                            ans_res.answer, q.expected_answer
                        )

                        async with session_factory() as s:
                            await record_request_measurement(
                                s,
                                run_id=run_id,
                                strategy="shared",
                                consumer_id=cid,
                                question_id=q.question_id,
                                question_text=q.question_text,
                                retrieved_chunk_ids=retrieved_ids,
                                retrieval_top_k=top_k,
                                retrieval_duration_ms=ans_res.retrieval_duration_ms,
                                answer_text=ans_res.answer,
                                prompt_tokens=ans_res.prompt_tokens,
                                completion_tokens=ans_res.completion_tokens,
                                generation_tokens_available=ans_res.tokens_available,
                                generation_duration_ms=ans_res.generation_duration_ms,
                                total_duration_ms=ans_res.total_duration_ms,
                                estimated_generation_cost_usd=ans_res.estimated_cost_usd,
                                estimated_retrieval_cost_usd=0.0,
                                ground_truth_answer=q.expected_answer,
                                recall_at_k=recall,
                                answer_correctness=correctness,
                            )
                        ACTIVE_RUN_PROGRESS[run_key]["completed_requests"] += 1
                    except Exception as exc:
                        logger.error("query.failed.strat_b", consumer=cid, error=str(exc))
                        ACTIVE_RUN_PROGRESS[run_key]["failed_requests"] += 1
                        async with session_factory() as s:
                            await record_request_measurement(
                                s,
                                run_id=run_id,
                                strategy="shared",
                                consumer_id=cid,
                                question_id=q.question_id,
                                question_text=q.question_text,
                                retrieved_chunk_ids=None,
                                retrieval_top_k=top_k,
                                retrieval_duration_ms=None,
                                answer_text=None,
                                prompt_tokens=None,
                                completion_tokens=None,
                                generation_tokens_available=False,
                                generation_duration_ms=None,
                                total_duration_ms=None,
                                estimated_generation_cost_usd=None,
                                estimated_retrieval_cost_usd=None,
                                error_message=str(exc),
                            )

            # ── 3. ADVERSARIAL AUTHORIZATION PROBE ───────────────────────────
            # Verify that an unauthorized consumer receives exactly 0 chunks
            try:
                probe_req = RAGRequest(
                    run_id=run_key,
                    question_id="security_probe_q",
                    question="Adversarial probe query for unauthorized chunk extraction",
                    consumer_id="adversary_unauthorized_user",
                    top_k=top_k,
                    repetition_index=rep_idx,
                )
                probe_res = await strategy_b.answer(probe_req)
                if len(probe_res.retrieved_chunks) > 0:
                    logger.critical(
                        "security.violation.cross_consumer_leakage",
                        run_id=run_key,
                        repetition=rep_idx,
                        retrieved_count=len(probe_res.retrieved_chunks),
                    )
                    ACTIVE_RUN_PROGRESS[run_key]["security_violations"] += 1
            except Exception as exc:
                logger.warning("security.probe.failed", run_id=run_key, error=str(exc))

            ACTIVE_RUN_PROGRESS[run_key]["elapsed_seconds"] = round(
                time.monotonic() - t0_start, 2
            )

        # Finished all repetitions
        final_status = RunStatus.COMPLETED
        final_err: str | None = None
        if (
            ACTIVE_RUN_PROGRESS[run_key]["completed_requests"] == 0
            and ACTIVE_RUN_PROGRESS[run_key]["failed_requests"] > 0
        ):
            final_status = RunStatus.FAILED
            final_err = (
                "All benchmark requests failed during execution. "
                "Check provider configuration or credentials."
            )
            ACTIVE_RUN_PROGRESS[run_key]["error"] = final_err

        async with session_factory() as s:
            await update_run_status(s, run_id, final_status, error_message=final_err, finished=True)

        ACTIVE_RUN_PROGRESS[run_key]["status"] = final_status
        ACTIVE_RUN_PROGRESS[run_key]["elapsed_seconds"] = round(
            time.monotonic() - t0_start, 2
        )
        logger.info(
            "experiment.run.completed",
            run_id=run_key,
            elapsed_sec=ACTIVE_RUN_PROGRESS[run_key]["elapsed_seconds"],
            completed=ACTIVE_RUN_PROGRESS[run_key]["completed_requests"],
            failed=ACTIVE_RUN_PROGRESS[run_key]["failed_requests"],
            security_violations=ACTIVE_RUN_PROGRESS[run_key]["security_violations"],
        )

    except asyncio.CancelledError:
        logger.warning("experiment.run.cancelled", run_id=run_key)
        async with session_factory() as s:
            await update_run_status(
                s, run_id, RunStatus.CANCELLED, "Run cancelled by user.", finished=True
            )
        ACTIVE_RUN_PROGRESS[run_key]["status"] = RunStatus.CANCELLED
    except Exception as exc:
        logger.exception("experiment.run.fatal_error", run_id=run_key, error=str(exc))
        async with session_factory() as s:
            await update_run_status(s, run_id, RunStatus.FAILED, str(exc), finished=True)
        ACTIVE_RUN_PROGRESS[run_key]["status"] = RunStatus.FAILED
        ACTIVE_RUN_PROGRESS[run_key]["error"] = str(exc)
    finally:
        ACTIVE_RUN_TASKS.pop(run_key, None)
