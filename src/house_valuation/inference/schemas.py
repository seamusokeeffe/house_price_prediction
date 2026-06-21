"""Inference and prediction payload schemas."""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class InferenceInput:
    canonical_area: str
    property_type: str
    beds: int
    floor_area_sqm: float
    asking_price_eur: float
    baths: int | None = None
    ber_rating: str | None = None
    listing_url: str | None = None
    raw_address: str | None = None

    def to_model_row(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class PredictionOutput:
    predicted_price_eur: float
    lower_price_eur: float | None
    upper_price_eur: float | None
    confidence_state: str
    support_count: int
    backoff_level: str
    model_name: str = "grouped_median_baseline"

