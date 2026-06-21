"""Build structured report payloads for local output."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from house_valuation.inference.schemas import InferenceInput, PredictionOutput


def build_report_payload(
    inference_input: InferenceInput,
    prediction: PredictionOutput,
) -> dict[str, Any]:
    """Build a simple structured payload for downstream CLI/UI/reporting work."""

    asking_price = inference_input.asking_price_eur
    predicted_price = prediction.predicted_price_eur
    asking_delta = asking_price - predicted_price

    return {
        "input": asdict(inference_input),
        "prediction": asdict(prediction),
        "asking_price_comparison": {
            "asking_price_eur": asking_price,
            "predicted_price_eur": predicted_price,
            "asking_minus_predicted_eur": asking_delta,
            "asking_vs_predicted_pct": asking_delta / predicted_price if predicted_price > 0 else None,
        },
        "notes": [
            "Baseline MVP skeleton output; interval calibration is not implemented yet.",
            "Confidence state is based on grouped-median support and should be calibrated later.",
        ],
    }

