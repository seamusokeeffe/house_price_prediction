"""Structured feature helpers for the grouped-median baseline."""

from __future__ import annotations

from typing import Any

from house_valuation.config import UNKNOWN_PROPERTY_TYPE
from house_valuation.data.filters import clean_property_type, coerce_float


def broad_size_band(floor_area_sqm: Any) -> str:
    """Return a coarse size band for support diagnostics."""

    area = coerce_float(floor_area_sqm)
    if area is None:
        return "unknown"
    if area < 90:
        return "small"
    if area < 140:
        return "medium"
    if area < 200:
        return "large"
    return "very_large"


def baseline_group_key(row: dict[str, Any]) -> tuple[str, str]:
    """Primary grouped-median key: canonical area and property type."""

    area = str(row.get("canonical_area") or "").strip()
    property_type = clean_property_type(row.get("property_type")) or UNKNOWN_PROPERTY_TYPE
    return area, property_type


def feature_snapshot(row: dict[str, Any]) -> dict[str, Any]:
    """Small shared feature view for later model implementations."""

    return {
        "canonical_area": str(row.get("canonical_area") or "").strip(),
        "geo_scope": str(row.get("geo_scope") or "").strip(),
        "property_type": clean_property_type(row.get("property_type")),
        "beds": coerce_float(row.get("beds")),
        "baths": coerce_float(row.get("baths")),
        "floor_area_sqm": coerce_float(row.get("floor_area_sqm")),
        "size_band": broad_size_band(row.get("floor_area_sqm")),
        "ber_rating": str(row.get("ber_rating") or "").strip() or None,
    }

