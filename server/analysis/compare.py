"""Side-by-side strategy comparison."""

from __future__ import annotations

from typing import Any

import pandas as pd

from analysis.cost import compute_cost_summary
from analysis.latency import compute_latency_summary


def compare_strategies(df: pd.DataFrame) -> dict[str, Any]:
    """
    Produce a side-by-side comparison of Strategy A vs Strategy B.

    Parameters
    ----------
    df : Merged measurement DataFrame with both strategies.

    Returns
    -------
    dict with cost, latency summaries and a conclusion note.
    The conclusion is descriptive only – never claims the hypothesis is proven.
    """
    cost = compute_cost_summary(df)
    latency = compute_latency_summary(df)

    strategies = set(df["strategy"].unique())
    if "independent" not in strategies or "shared" not in strategies:
        return {
            "cost": cost,
            "latency": latency,
            "conclusion": (
                "Comparison requires both 'independent' and 'shared' strategy data. "
                f"Available strategies: {sorted(strategies)}"
            ),
        }

    return {
        "cost": cost,
        "latency": latency,
        "conclusion": (
            "Raw comparison complete. Statistical significance and break-even "
            "analysis require repeated runs with fixed seeds. "
            "See docs/research/metrics.md for the full analysis plan."
        ),
    }
