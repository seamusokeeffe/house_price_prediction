"""Deterministic duplicate-like grouping for PPR Checkpoint 4."""

from __future__ import annotations

import hashlib
import json
from typing import Any

import pandas as pd
import pyarrow as pa


DUPLICATE_FIELDS = [
    pa.field("duplicate_group_id", pa.string(), nullable=True),
    pa.field("duplicate_group_size", pa.int64(), nullable=False),
    pa.field("duplicate_status", pa.string(), nullable=False),
    pa.field("duplicate_rule_ids", pa.string(), nullable=False),
    pa.field("duplicate_action", pa.string(), nullable=False),
    pa.field("duplicate_representative_record_id", pa.string(), nullable=True),
]
PUBLICATION_KEY = [
    "address_normalized", "transaction_date", "sale_price_eur_raw",
    "sale_price_eur_adjusted", "is_full_market_price", "vat_exclusive_flag",
    "property_description_raw",
]
WEAK_KEY = ["address_normalized", "transaction_date", "sale_price_eur_adjusted"]
SAME_DAY_KEY = [
    "transaction_date", "sale_price_eur_adjusted", "is_full_market_price",
    "vat_exclusive_flag",
]


class DuplicateAssessmentError(ValueError):
    """Raised when required duplicate evidence is missing."""


def assess_duplicate_like_transactions(frame: pd.DataFrame) -> pd.DataFrame:
    """Append deterministic duplicate categories without removing records.

    Exact logical source duplicates keep the lowest source row number (then
    record ID) as representative. Strong normalised publication matches and
    weaker conflicting-status matches remain review-only. Same-day/equal-price
    records at distinct addresses are explicitly protected from exclusion.

    Args:
        frame: Checkpoint 3 records plus earlier Checkpoint 4 assessments.

    Returns:
        Row-preserving copy with duplicate assessment fields.

    Raises:
        DuplicateAssessmentError: If required evidence columns are missing.
    """

    required = {
        "record_id", "source_row_number", "raw_record_fingerprint",
        *PUBLICATION_KEY, *WEAK_KEY, *SAME_DAY_KEY,
    }
    missing = sorted(required - set(frame.columns))
    if missing:
        raise DuplicateAssessmentError(f"Missing duplicate evidence columns: {missing}")
    output = frame.copy()
    output["duplicate_group_id"] = pd.Series(pd.NA, index=output.index, dtype="string")
    output["duplicate_group_size"] = pd.Series(1, index=output.index, dtype="int64")
    output["duplicate_status"] = "not_duplicate_like"
    output["duplicate_rule_ids"] = ""
    output["duplicate_action"] = "none"
    output["duplicate_representative_record_id"] = pd.Series(pd.NA, index=output.index, dtype="string")

    exact_size = output.groupby("raw_record_fingerprint", dropna=False)["record_id"].transform("size")
    exact = exact_size.gt(1)
    _assign_groups(output, exact, ["raw_record_fingerprint"], "exact")
    representatives = (
        output.loc[exact, ["raw_record_fingerprint", "source_row_number", "record_id"]]
        .sort_values(["raw_record_fingerprint", "source_row_number", "record_id"])
        .drop_duplicates("raw_record_fingerprint")
        .set_index("raw_record_fingerprint")["record_id"]
    )
    output.loc[exact, "duplicate_representative_record_id"] = output.loc[exact, "raw_record_fingerprint"].map(representatives)
    output.loc[exact, "duplicate_group_size"] = exact_size.loc[exact].astype("int64")
    output.loc[exact, "duplicate_status"] = "exact_source_duplicate"
    output.loc[exact, "duplicate_rule_ids"] = "DUP001"
    is_representative = output["record_id"].eq(output["duplicate_representative_record_id"])
    output.loc[exact & is_representative, "duplicate_action"] = "retain_representative"
    output.loc[exact & ~is_representative, "duplicate_action"] = "auto_exclude"

    publication_size = output.groupby(PUBLICATION_KEY, dropna=False)["record_id"].transform("size")
    fingerprint_count = output.groupby(PUBLICATION_KEY, dropna=False)["raw_record_fingerprint"].transform("nunique")
    plausible = ~exact & publication_size.gt(1) & fingerprint_count.gt(1)
    _assign_groups(output, plausible, PUBLICATION_KEY, "publication")
    output.loc[plausible, "duplicate_group_size"] = publication_size.loc[plausible].astype("int64")
    output.loc[plausible, "duplicate_status"] = "plausible_duplicate_publication"
    output.loc[plausible, "duplicate_rule_ids"] = "DUP002"
    output.loc[plausible, "duplicate_action"] = "review_only"

    weak_size = output.groupby(WEAK_KEY, dropna=False)["record_id"].transform("size")
    publication_variant_count = output.groupby(WEAK_KEY, dropna=False)[PUBLICATION_KEY[-4:]].transform("nunique").max(axis=1)
    unresolved = ~exact & ~plausible & weak_size.gt(1) & publication_variant_count.gt(1)
    _assign_groups(output, unresolved, WEAK_KEY, "unresolved")
    output.loc[unresolved, "duplicate_group_size"] = weak_size.loc[unresolved].astype("int64")
    output.loc[unresolved, "duplicate_status"] = "unresolved_duplicate_like"
    output.loc[unresolved, "duplicate_rule_ids"] = "DUP003"
    output.loc[unresolved, "duplicate_action"] = "review_only"

    same_day_size = output.groupby(SAME_DAY_KEY, dropna=False)["record_id"].transform("size")
    address_count = output.groupby(SAME_DAY_KEY, dropna=False)["address_normalized"].transform("nunique")
    distinct = ~exact & ~plausible & ~unresolved & same_day_size.gt(1) & address_count.gt(1)
    _assign_groups(output, distinct, SAME_DAY_KEY, "same_day_distinct")
    output.loc[distinct, "duplicate_group_size"] = same_day_size.loc[distinct].astype("int64")
    output.loc[distinct, "duplicate_status"] = "same_day_distinct_transaction"
    output.loc[distinct, "duplicate_rule_ids"] = "DUP004"
    output.loc[distinct, "duplicate_action"] = "none"
    return output


def _assign_groups(frame: pd.DataFrame, mask: pd.Series, columns: list[str], namespace: str) -> None:
    """Assign stable content-derived group IDs to selected rows."""

    if not mask.any():
        return
    keys = frame.loc[mask, columns].apply(
        lambda row: _stable_group_id(namespace, [_canonical(value) for value in row]), axis=1
    )
    frame.loc[mask, "duplicate_group_id"] = keys.astype("string")


def _stable_group_id(namespace: str, values: list[str]) -> str:
    """Create an order-invariant group ID from canonical key values."""

    payload = json.dumps([namespace, *values], ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _canonical(value: Any) -> str:
    """Convert duplicate evidence to a stable text representation."""

    if pd.isna(value):
        return "<NULL>"
    return str(value)
