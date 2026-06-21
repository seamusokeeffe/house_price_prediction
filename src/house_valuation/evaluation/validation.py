"""Temporal validation flow for the baseline model."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from house_valuation.data.filters import filter_training_rows
from house_valuation.evaluation.metrics import (
    log_mae,
    mae_eur,
    median_absolute_percentage_error,
)
from house_valuation.models.baseline import GroupedMedianBaseline


def parse_date(value: Any) -> date:
    text = str(value).strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Unsupported date format: {value!r}")


def temporal_train_validation_split(
    rows: list[dict[str, Any]],
    *,
    holdout_months: int = 12,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Split rows so the latest transactions form the validation set."""

    if holdout_months <= 0:
        raise ValueError("holdout_months must be positive.")

    dated_rows = sorted((parse_date(row["transaction_date"]), row) for row in rows)
    if len(dated_rows) < 2:
        raise ValueError("Need at least two rows for temporal validation.")

    latest = dated_rows[-1][0]
    cutoff_month = latest.month - holdout_months
    cutoff_year = latest.year
    while cutoff_month <= 0:
        cutoff_month += 12
        cutoff_year -= 1
    cutoff = date(cutoff_year, cutoff_month, min(latest.day, 28))

    train = [row for row_date, row in dated_rows if row_date < cutoff]
    validation = [row for row_date, row in dated_rows if row_date >= cutoff]

    if not train or not validation:
        raise ValueError("Temporal split produced an empty train or validation set.")

    return train, validation


def run_baseline_validation(
    raw_rows: list[dict[str, Any]],
    *,
    holdout_months: int = 12,
    min_group_support: int = 3,
) -> dict[str, Any]:
    """Run the grouped-median baseline through temporal validation."""

    rows = filter_training_rows(raw_rows)
    train_rows, validation_rows = temporal_train_validation_split(rows, holdout_months=holdout_months)

    model = GroupedMedianBaseline(min_group_support=min_group_support).fit(train_rows)
    predictions = model.predict(validation_rows)

    actual_prices = [float(row["sale_price_eur"]) for row in validation_rows]
    predicted_prices = [prediction.predicted_price_eur for prediction in predictions]
    actual_logs = [float(row["log_sale_price"]) for row in validation_rows]
    predicted_logs = [prediction.predicted_log_price for prediction in predictions]

    return {
        "model": "grouped_median_baseline",
        "train_rows": len(train_rows),
        "validation_rows": len(validation_rows),
        "holdout_months": holdout_months,
        "min_group_support": min_group_support,
        "metrics": {
            "mae_eur": mae_eur(actual_prices, predicted_prices),
            "median_absolute_percentage_error": median_absolute_percentage_error(actual_prices, predicted_prices),
            "log_mae": log_mae(actual_logs, predicted_logs),
        },
        "backoff_counts": _backoff_counts(predictions),
    }


def _backoff_counts(predictions: list[Any]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for prediction in predictions:
        counts[prediction.backoff_level] = counts.get(prediction.backoff_level, 0) + 1
    return counts

