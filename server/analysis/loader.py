"""Load completed experiment run data from the database or exported CSV/JSONL.

Analysis is always read-only. Never writes to the experiment database.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


def load_run_from_csv(measurements_path: str | Path) -> pd.DataFrame:
    """Load request measurements from an exported CSV file.

    The CSV must include columns produced by RequestMeasurement ORM model.
    Clearly labelled SYNTHETIC if loaded from fixture data.
    """
    df = pd.read_csv(measurements_path)
    _validate_columns(df)
    return df


def load_run_from_jsonl(measurements_path: str | Path) -> pd.DataFrame:
    """Load request measurements from an exported JSONL file."""
    records = []
    with open(measurements_path) as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    df = pd.DataFrame(records)
    _validate_columns(df)
    return df


def load_run(path: str | Path) -> pd.DataFrame:
    """Auto-detect CSV or JSONL and load measurements."""
    p = Path(path)
    if p.suffix == ".csv":
        return load_run_from_csv(p)
    elif p.suffix in (".jsonl", ".ndjson"):
        return load_run_from_jsonl(p)
    raise ValueError(f"Unsupported file format: {p.suffix}. Use .csv or .jsonl")


def _validate_columns(df: pd.DataFrame) -> None:
    required = {"run_id", "strategy", "question_id", "total_duration_ms"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Measurement data is missing required columns: {missing}")
