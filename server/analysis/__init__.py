"""Analysis package for the Shared AI Intelligence experiment.

Runnable independently of FastAPI using read-only DB access or exported data.
"""

from __future__ import annotations

from analysis.compare import compare_strategies
from analysis.cost import compute_cost_summary
from analysis.latency import compute_latency_summary
from analysis.loader import load_run
from analysis.reuse import compute_reuse_summary

__all__ = [
    "load_run",
    "compute_cost_summary",
    "compute_latency_summary",
    "compute_reuse_summary",
    "compare_strategies",
]
