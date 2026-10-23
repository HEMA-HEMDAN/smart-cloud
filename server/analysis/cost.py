"""Cost analysis functions.

Uses the simplified economic model:
  C_independent = N(C_p + C_q)
  C_shared      = C_p + N*C_q + C_m

where C_p = preparation cost per document per consumer,
      C_q = per-question processing cost,
      C_m = shared-layer maintenance overhead,
      N   = number of consumers.
"""

from __future__ import annotations

from typing import Any

import pandas as pd


def compute_cost_summary(df: pd.DataFrame) -> dict[str, Any]:
    """
    Summarise total and per-question cost by strategy.

    Parameters
    ----------
    df : DataFrame with columns from RequestMeasurement.
         ``estimated_cost_usd`` may be None/NaN when provider did not report usage.

    Returns
    -------
    dict with keys:
        - per_strategy: {strategy -> {total_usd, per_question_usd, questions_with_cost}}
        - note: explanation of any unavailable cost data
    """
    results: dict[str, Any] = {"per_strategy": {}, "note": ""}
    missing = df["estimated_cost_usd"].isna().sum()
    if missing > 0:
        results["note"] = (
            f"{missing} of {len(df)} measurements have no cost data "
            "(provider did not report usage). Reported costs are partial estimates."
        )

    for strategy, group in df.groupby("strategy"):
        valid = group["estimated_cost_usd"].dropna()
        results["per_strategy"][strategy] = {
            "total_estimated_usd": float(valid.sum()) if len(valid) > 0 else None,
            "per_question_mean_usd": float(valid.mean()) if len(valid) > 0 else None,
            "questions_with_cost_data": int(len(valid)),
            "total_questions": int(len(group)),
        }

    return results


def breakeven_consumers(
    c_p: float,
    c_m: float = 0.0,
) -> float:
    """
    Compute the break-even number of consumers using the simplified model.

    Under the simplified model where C_q is equal for both strategies,
    shared preparation breaks even when (N-1)*C_p > C_m, so:
        N* = C_m/C_p + 1   (minimum N where shared is cheaper)

    This model is explicitly documented in docs/research/metrics.md.
    It assumes C_q is identical between strategies.
    """
    if c_p <= 0:
        raise ValueError("c_p must be positive")
    return (c_m / c_p) + 1
