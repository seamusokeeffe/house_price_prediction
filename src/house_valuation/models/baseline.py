"""Grouped recent median baseline model."""

from __future__ import annotations

import math
import statistics
from dataclasses import dataclass, field
from typing import Any

from house_valuation.features.build_features import baseline_group_key


@dataclass(frozen=True)
class BaselinePrediction:
    predicted_log_price: float
    predicted_price_eur: float
    backoff_level: str
    support_count: int


@dataclass
class GroupedMedianBaseline:
    """Median log-price model with transparent backoff.

    Backoff order:
    1. canonical area + property type
    2. canonical area
    3. property type
    4. global median
    """

    min_group_support: int = 3
    group_medians: dict[tuple[str, str], float] = field(default_factory=dict)
    group_counts: dict[tuple[str, str], int] = field(default_factory=dict)
    area_medians: dict[str, float] = field(default_factory=dict)
    area_counts: dict[str, int] = field(default_factory=dict)
    type_medians: dict[str, float] = field(default_factory=dict)
    type_counts: dict[str, int] = field(default_factory=dict)
    global_median: float | None = None
    global_count: int = 0

    def fit(self, rows: list[dict[str, Any]]) -> "GroupedMedianBaseline":
        if not rows:
            raise ValueError("Cannot fit baseline on an empty dataset.")

        group_values: dict[tuple[str, str], list[float]] = {}
        area_values: dict[str, list[float]] = {}
        type_values: dict[str, list[float]] = {}
        global_values: list[float] = []

        for row in rows:
            log_price = float(row["log_sale_price"])
            area, property_type = baseline_group_key(row)
            group_values.setdefault((area, property_type), []).append(log_price)
            area_values.setdefault(area, []).append(log_price)
            type_values.setdefault(property_type, []).append(log_price)
            global_values.append(log_price)

        self.group_medians = {key: statistics.median(values) for key, values in group_values.items()}
        self.group_counts = {key: len(values) for key, values in group_values.items()}
        self.area_medians = {key: statistics.median(values) for key, values in area_values.items()}
        self.area_counts = {key: len(values) for key, values in area_values.items()}
        self.type_medians = {key: statistics.median(values) for key, values in type_values.items()}
        self.type_counts = {key: len(values) for key, values in type_values.items()}
        self.global_median = statistics.median(global_values)
        self.global_count = len(global_values)
        return self

    def predict_one(self, row: dict[str, Any]) -> BaselinePrediction:
        if self.global_median is None:
            raise ValueError("Baseline model has not been fitted.")

        area, property_type = baseline_group_key(row)
        group_key = (area, property_type)

        if self.group_counts.get(group_key, 0) >= self.min_group_support:
            return self._prediction(self.group_medians[group_key], "area_property_type", self.group_counts[group_key])

        if self.area_counts.get(area, 0) >= self.min_group_support:
            return self._prediction(self.area_medians[area], "area", self.area_counts[area])

        if self.type_counts.get(property_type, 0) >= self.min_group_support:
            return self._prediction(self.type_medians[property_type], "property_type", self.type_counts[property_type])

        return self._prediction(self.global_median, "global", self.global_count)

    def predict(self, rows: list[dict[str, Any]]) -> list[BaselinePrediction]:
        return [self.predict_one(row) for row in rows]

    @staticmethod
    def _prediction(log_price: float, backoff_level: str, support_count: int) -> BaselinePrediction:
        return BaselinePrediction(
            predicted_log_price=log_price,
            predicted_price_eur=math.exp(log_price),
            backoff_level=backoff_level,
            support_count=support_count,
        )

