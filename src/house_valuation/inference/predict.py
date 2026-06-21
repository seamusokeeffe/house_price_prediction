"""Single-property prediction helpers."""

from __future__ import annotations

from house_valuation.inference.schemas import InferenceInput, PredictionOutput
from house_valuation.models.baseline import GroupedMedianBaseline


def predict_single_property(
    model: GroupedMedianBaseline,
    inference_input: InferenceInput,
) -> PredictionOutput:
    """Predict a single property using the current baseline model."""

    prediction = model.predict_one(inference_input.to_model_row())
    confidence_state = confidence_from_support(prediction.support_count, prediction.backoff_level)

    return PredictionOutput(
        predicted_price_eur=prediction.predicted_price_eur,
        lower_price_eur=None,
        upper_price_eur=None,
        confidence_state=confidence_state,
        support_count=prediction.support_count,
        backoff_level=prediction.backoff_level,
    )


def confidence_from_support(support_count: int, backoff_level: str) -> str:
    """Initial confidence placeholder based on planning thresholds."""

    if backoff_level == "global" or support_count < 5:
        return "not_enough_comparable_support"
    if support_count < 15 or backoff_level != "area_property_type":
        return "low_confidence"
    return "normal_confidence"

