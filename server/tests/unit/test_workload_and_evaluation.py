"""Unit tests for workload schedule generation and ground-truth evaluation."""

from __future__ import annotations

import pandas as pd
import pytest
from analysis.reuse import compute_reuse_summary
from app.experiments.workload import BenchmarkQuestion, generate_workload_plan

from analysis.evaluation import compute_answer_correctness, compute_recall_at_k


@pytest.mark.unit
def test_workload_plan_counts() -> None:
    questions = [
        BenchmarkQuestion(question_id="q1", question_text="What is X?"),
        BenchmarkQuestion(question_id="q2", question_text="What is Y?"),
    ]
    plan = generate_workload_plan(
        consumer_count=10,
        repetitions=10,
        questions=questions,
        workload_type="high_reuse",
        random_seed=42,
    )

    assert plan.consumer_count == 10
    assert plan.repetitions == 10
    assert len(plan.tasks_per_repetition) == 10

    for rep_tasks in plan.tasks_per_repetition:
        assert len(rep_tasks) == 10
        for task in rep_tasks:
            assert len(task.questions) == 2


@pytest.mark.unit
def test_workload_determinism() -> None:
    plan1 = generate_workload_plan(consumer_count=5, repetitions=3, random_seed=99)
    plan2 = generate_workload_plan(consumer_count=5, repetitions=3, random_seed=99)

    c_ids1 = [[t.consumer_id for t in rep] for rep in plan1.tasks_per_repetition]
    c_ids2 = [[t.consumer_id for t in rep] for rep in plan2.tasks_per_repetition]
    assert c_ids1 == c_ids2


@pytest.mark.unit
def test_recall_at_k() -> None:
    # Exact match
    assert compute_recall_at_k(["c_0", "c_1"], ["c_0", "c_1"]) == 1.0
    # Partial match
    assert compute_recall_at_k(["c_0", "c_2"], ["c_0", "c_1"]) == 0.5
    # Zero match
    assert compute_recall_at_k(["c_2", "c_3"], ["c_0", "c_1"]) == 0.0
    # Missing ground truth -> returns None
    assert compute_recall_at_k(["c_0"], None) is None
    assert compute_recall_at_k(["c_0"], []) is None


@pytest.mark.unit
def test_answer_correctness() -> None:
    # Exact match
    assert compute_answer_correctness("hello world", "hello world") == 1.0
    # Partial match
    score = compute_answer_correctness("the quick brown fox", "quick fox")
    assert score is not None
    assert 0.0 < score < 1.0
    # No match
    assert compute_answer_correctness("apple banana", "orange grape") == 0.0
    # Missing reference -> returns None
    assert compute_answer_correctness("some answer", None) is None
    assert compute_answer_correctness("some answer", "") is None


@pytest.mark.unit
def test_reuse_summary_zero_denominator() -> None:
    # When total is 0, reuse_rate must be None (not 0.0)
    df = pd.DataFrame(columns=["run_id", "strategy", "is_reuse"])
    summary = compute_reuse_summary(df)
    assert "note" in summary or summary.get("reuse_rate") is None
