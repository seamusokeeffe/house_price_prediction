"""Dataset loading helpers for the MVP skeleton."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from house_valuation.config import REQUIRED_TRAINING_COLUMNS


def load_csv_dataset(path: str | Path) -> list[dict[str, Any]]:
    """Load a CSV modelling dataset as row dictionaries.

    The loader is intentionally small and dependency-free. Later passes can add
    Parquet/DuckDB readers once the storage implementation lands.
    """

    dataset_path = Path(path)
    if not dataset_path.exists():
        raise FileNotFoundError(f"Dataset not found: {dataset_path}")
    if dataset_path.suffix.lower() != ".csv":
        raise ValueError("MVP loader currently supports CSV files only.")

    with dataset_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = [dict(row) for row in reader]

    validate_required_columns(rows, REQUIRED_TRAINING_COLUMNS)
    return rows


def validate_required_columns(rows: list[dict[str, Any]], required: set[str]) -> None:
    """Fail clearly when required columns are missing."""

    if not rows:
        raise ValueError("Dataset is empty.")

    present = set(rows[0])
    missing = sorted(required - present)
    if missing:
        raise ValueError(f"Dataset is missing required columns: {', '.join(missing)}")

