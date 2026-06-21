"""Model evaluation metrics."""

from __future__ import annotations

import math
import statistics


def mae_eur(actual: list[float], predicted: list[float]) -> float:
    _validate_equal_length(actual, predicted)
    return sum(abs(a - p) for a, p in zip(actual, predicted)) / len(actual)


def median_absolute_percentage_error(actual: list[float], predicted: list[float]) -> float:
    _validate_equal_length(actual, predicted)
    errors = [abs(a - p) / a for a, p in zip(actual, predicted) if a > 0]
    if not errors:
        raise ValueError("No positive actual values available for percentage error.")
    return statistics.median(errors)


def log_mae(actual_log: list[float], predicted_log: list[float]) -> float:
    _validate_equal_length(actual_log, predicted_log)
    return sum(abs(a - p) for a, p in zip(actual_log, predicted_log)) / len(actual_log)


def residual_interval(log_prediction: float, residual_abs_quantile: float) -> tuple[float, float]:
    """Minimal symmetric residual interval on the euro scale."""

    return math.exp(log_prediction - residual_abs_quantile), math.exp(log_prediction + residual_abs_quantile)


def _validate_equal_length(left: list[float], right: list[float]) -> None:
    if not left or not right:
        raise ValueError("Metric inputs must not be empty.")
    if len(left) != len(right):
        raise ValueError("Metric inputs must have the same length.")

