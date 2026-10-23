"""Ground-truth evaluation metrics for retrieval and answer correctness."""

from __future__ import annotations

import re


def _tokenize(text: str) -> set[str]:
    """Simple lowercase token set for lexical alignment."""
    tokens = re.findall(r"\w+", text.lower())
    return set(tokens)


def compute_recall_at_k(
    retrieved_chunk_ids: list[str] | None,
    expected_chunk_ids: list[str] | None,
) -> float | None:
    """
    Compute Retrieval Recall@k against human-reviewed ground truth chunk references.

    Returns None if expected_chunk_ids is missing or empty (metrics.md rule:
    do not assign artificial quality scores when ground truth is absent).
    """
    if not expected_chunk_ids:
        return None

    if not retrieved_chunk_ids:
        return 0.0

    retrieved_set = set(retrieved_chunk_ids)
    expected_set = set(expected_chunk_ids)

    matches = retrieved_set.intersection(expected_set)
    return round(len(matches) / len(expected_set), 4)


def compute_answer_correctness(
    generated_answer: str | None,
    expected_answer: str | None,
) -> float | None:
    """
    Compute lexical token-overlap F1 score against reference answer.

    Returns None if reference answer is not provided.
    """
    if not expected_answer or not expected_answer.strip():
        return None

    if not generated_answer or not generated_answer.strip():
        return 0.0

    gen_tokens = _tokenize(generated_answer)
    ref_tokens = _tokenize(expected_answer)

    if not ref_tokens:
        return None

    overlap = gen_tokens.intersection(ref_tokens)
    if not overlap:
        return 0.0

    precision = len(overlap) / len(gen_tokens)
    recall = len(overlap) / len(ref_tokens)
    f1 = 2 * (precision * recall) / (precision + recall)
    return round(f1, 4)
