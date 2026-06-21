"""Filtering and target-preparation helpers."""

from __future__ import annotations

import math
from typing import Any

from house_valuation.config import SUPPORTED_HOUSE_TYPES, UNKNOWN_PROPERTY_TYPE


def parse_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def clean_property_type(value: Any) -> str:
    text = str(value or "").strip()
    return text if text else UNKNOWN_PROPERTY_TYPE


def filter_training_rows(
    rows: list[dict[str, Any]],
    *,
    include_unknown_property_type: bool = True,
) -> list[dict[str, Any]]:
    """Filter rows to V1 training scope while preserving unknown house type policy."""

    filtered: list[dict[str, Any]] = []
    for row in rows:
        if parse_bool(row.get("exclude_from_training")):
            continue

        property_type = clean_property_type(row.get("property_type"))
        supported = property_type in SUPPORTED_HOUSE_TYPES
        unknown_allowed = include_unknown_property_type and property_type == UNKNOWN_PROPERTY_TYPE
        if not (supported or unknown_allowed):
            continue

        price = coerce_float(row.get("sale_price_eur"))
        if price is None or price <= 0:
            continue

        output = dict(row)
        output["property_type"] = property_type
        output["sale_price_eur"] = price
        output["log_sale_price"] = math.log(price)
        filtered.append(output)

    if not filtered:
        raise ValueError("No usable training rows remain after filtering.")

    return filtered


def coerce_float(value: Any) -> float | None:
    if value is None:
        return None
    text = str(value).strip().replace(",", "")
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None

