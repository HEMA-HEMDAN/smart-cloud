"""Reuse rate analysis for Strategy B."""

from __future__ import annotations

from typing import Any

import pandas as pd


def compute_reuse_summary(prep_df: pd.DataFrame) -> dict[str, Any]:
    """
    Compute preparation reuse statistics from preparation events.

    Parameters
    ----------
    prep_df : DataFrame from PreparationEvent records.
              Must have columns: strategy, is_reuse, run_id.
    """
    if "is_reuse" not in prep_df.columns:
        return {"error": "is_reuse column not present in data"}

    shared = prep_df[prep_df["strategy"] == "shared"]
    if len(shared) == 0:
        return {"note": "No shared strategy preparation events found"}

    total = len(shared)
    reused = shared["is_reuse"].sum()
    first_preps = total - reused

    return {
        "total_preparation_events": int(total),
        "first_preparations": int(first_preps),
        "reuses": int(reused),
        "reuse_rate": float(reused / total) if total > 0 else None,
        "avoided_preparations": int(reused),
    }
