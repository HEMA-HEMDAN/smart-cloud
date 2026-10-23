"""Workload generation utilities for deterministic A/B experiment execution."""

from __future__ import annotations

import random
from dataclasses import dataclass


@dataclass
class BenchmarkQuestion:
    question_id: str
    question_text: str
    expected_answer: str | None = None
    expected_chunk_ids: list[str] | None = None


@dataclass
class ConsumerTask:
    consumer_id: str
    repetition_index: int
    questions: list[BenchmarkQuestion]


@dataclass
class WorkloadPlan:
    consumer_count: int
    repetitions: int
    random_seed: int
    workload_type: str
    tasks_per_repetition: list[list[ConsumerTask]]


def generate_workload_plan(
    consumer_count: int = 10,
    repetitions: int = 10,
    questions: list[BenchmarkQuestion] | None = None,
    workload_type: str = "high_reuse",
    random_seed: int = 42,
) -> WorkloadPlan:
    """
    Generate a deterministic schedule of consumer tasks across repetitions.

    Each repetition tests all consumer_count consumers accessing the document
    and answering the benchmark questions.
    """
    if consumer_count <= 0:
        raise ValueError("consumer_count must be positive")
    if repetitions <= 0:
        raise ValueError("repetitions must be positive")

    benchmark_qs = questions or [
        BenchmarkQuestion(
            question_id="q1",
            question_text="What is the primary subject of the document?",
        )
    ]

    rng = random.Random(random_seed)  # noqa: S311 - deterministic experiment workload schedule
    repetition_tasks: list[list[ConsumerTask]] = []

    for rep in range(repetitions):
        consumer_ids = [f"c_{i:02d}" for i in range(consumer_count)]
        if workload_type == "high_reuse":
            # Fixed sequential order: c_00 is always the first demand
            pass
        elif workload_type == "moderate_reuse":
            # Slight random permutation of consumer arrival order per repetition
            rng.shuffle(consumer_ids)
        elif workload_type == "cold_start":
            # Every request tests fresh consumer ordering
            rng.shuffle(consumer_ids)

        tasks = [
            ConsumerTask(
                consumer_id=cid,
                repetition_index=rep,
                questions=benchmark_qs,
            )
            for cid in consumer_ids
        ]
        repetition_tasks.append(tasks)

    return WorkloadPlan(
        consumer_count=consumer_count,
        repetitions=repetitions,
        random_seed=random_seed,
        workload_type=workload_type,
        tasks_per_repetition=repetition_tasks,
    )
