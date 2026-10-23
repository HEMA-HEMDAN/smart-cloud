"""Latency analysis functions."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


def compute_latency_summary(df: pd.DataFrame) -> dict[str, Any]:
    """
    Compute median and p95 latency per strategy.

    Parameters
    ----------
    df : DataFrame with ``total_duration_ms`` and ``strategy`` columns.
    """
    results: dict[str, Any] = {"per_strategy": {}}
    for strategy, group in df.groupby("strategy"):
        ms = group["total_duration_ms"].dropna()
        if len(ms) == 0:
            results["per_strategy"][strategy] = {"note": "no data"}
            continue
        results["per_strategy"][strategy] = {
            "median_ms": float(np.median(ms)),
            "p95_ms": float(np.percentile(ms, 95)),
            "mean_ms": float(ms.mean()),
            "min_ms": float(ms.min()),
            "max_ms": float(ms.max()),
            "n": int(len(ms)),
        }
    return results
