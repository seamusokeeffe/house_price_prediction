"""Conservative PPR house-versus-apartment scope assessment."""

from __future__ import annotations

import re

import pandas as pd
import pyarrow as pa


PROPERTY_SCOPE_FIELDS = [
    pa.field("property_scope_status", pa.string(), nullable=False),
    pa.field("property_scope_rule_ids", pa.string(), nullable=False),
    pa.field("property_scope_reason", pa.string(), nullable=False),
]
APARTMENT_PATTERN = re.compile(r"\bAPARTMENTS?\b", re.IGNORECASE)
FLAT_PATTERN = re.compile(r"\bFLATS?\b", re.IGNORECASE)
APT_IDENTIFIER_PATTERN = re.compile(r"\bAPT\b\.?\s*(?:NO\.?\s*)?[A-Z0-9]+\b", re.IGNORECASE)
UNIT_PATTERN = re.compile(r"\bUNITS?\b", re.IGNORECASE)


def assess_property_scope(
    frame: pd.DataFrame,
    *,
    address_column: str = "address_normalized",
) -> pd.DataFrame:
    """Append conservative property-scope fields without changing source types.

    Args:
        frame: Records containing a normalised address.
        address_column: Address field to inspect.

    Returns:
        Row-preserving copy with property-scope evidence.

    Raises:
        KeyError: If the address field is absent.
    """

    if address_column not in frame:
        raise KeyError(f"Missing property-scope address column: {address_column}")
    output = frame.copy()
    text = output[address_column].fillna("").astype(str)
    apartment = text.str.contains(APARTMENT_PATTERN, na=False)
    flat = text.str.contains(FLAT_PATTERN, na=False)
    apt = text.str.contains(APT_IDENTIFIER_PATTERN, na=False)
    unit = text.str.contains(UNIT_PATTERN, na=False)
    clear = apartment | flat | apt
    review = unit & ~clear
    output["property_scope_status"] = "unresolved_house_or_apartment"
    output.loc[review, "property_scope_status"] = "review_required"
    output.loc[clear, "property_scope_status"] = "clearly_non_house"
    rule_ids = pd.Series("", index=output.index, dtype="string")
    reasons = pd.Series("", index=output.index, dtype="string")
    for mask, rule_id, reason in [
        (apartment, "PROP001", "explicit apartment wording"),
        (flat, "PROP002", "explicit flat wording"),
        (apt, "PROP003", "APT abbreviation with an identifier"),
        (review, "PROP101", "ambiguous UNIT wording"),
    ]:
        rule_ids.loc[mask] = rule_ids.loc[mask].where(rule_ids.loc[mask].eq(""), rule_ids.loc[mask] + "|") + rule_id
        reasons.loc[mask] = reasons.loc[mask].where(reasons.loc[mask].eq(""), reasons.loc[mask] + "|") + reason
    output["property_scope_rule_ids"] = rule_ids
    output["property_scope_reason"] = reasons
    return output
