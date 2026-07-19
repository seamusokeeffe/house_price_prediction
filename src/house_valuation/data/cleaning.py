"""Row-preserving Checkpoint 4 cleaning and exclusion aggregation."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from house_valuation.data.duplicate_detection import DUPLICATE_FIELDS
from house_valuation.data.multi_property import MULTI_PROPERTY_FIELDS
from house_valuation.data.property_scope import PROPERTY_SCOPE_FIELDS


EXCLUSION_PRIORITY = [
    "invalid_target",
    "invalid_date",
    "non_full_market_transaction",
    "unresolved_market_price_status",
    "out_of_scope_geography",
    "unmatched_geography_unresolved",
    "ambiguous_geography_unresolved",
    "excluded_property_type",
    "multi_property_transaction",
    "duplicate_unresolved",
    "unresolved_vat_treatment",
    "insufficient_required_fields",
]
EXCLUSION_RULE_BY_REASON = {
    "invalid_target": "CLEAN001",
    "invalid_date": "CLEAN002",
    "non_full_market_transaction": "CLEAN003",
    "unresolved_market_price_status": "CLEAN004",
    "out_of_scope_geography": "CLEAN005",
    "unmatched_geography_unresolved": "CLEAN006",
    "ambiguous_geography_unresolved": "CLEAN007",
    "excluded_property_type": "CLEAN008",
    "multi_property_transaction": "CLEAN009",
    "duplicate_unresolved": "CLEAN010",
    "unresolved_vat_treatment": "CLEAN011",
    "insufficient_required_fields": "CLEAN012",
}
CLEANING_FIELDS = [
    pa.field("quality_flags", pa.string(), nullable=False),
    pa.field("exclude_from_training", pa.bool_(), nullable=False),
    pa.field("exclusion_reason", pa.string(), nullable=True),
    pa.field("exclusion_reasons", pa.string(), nullable=False),
    pa.field("exclusion_rule_ids", pa.string(), nullable=False),
    pa.field("cleaning_assessment_status", pa.string(), nullable=False),
]
CHECKPOINT4_FIELDS = MULTI_PROPERTY_FIELDS + PROPERTY_SCOPE_FIELDS + DUPLICATE_FIELDS + CLEANING_FIELDS


class Checkpoint4PhysicalSchemaError(ValueError):
    """Raised when Checkpoint 4 schema or reconciliation validation fails."""


def assess_cleaning(frame: pd.DataFrame) -> pd.DataFrame:
    """Aggregate approved exclusions and quality flags without dropping rows.

    Args:
        frame: Records with multi-property, property-scope, and duplicate fields.

    Returns:
        Row-preserving cleaning-assessed copy.

    Raises:
        KeyError: If a required evidence field is absent.
    """

    required = {
        "record_id", "raw_address", "transaction_date", "date_parse_status",
        "is_future_transaction", "sale_price_eur_adjusted", "price_parse_status",
        "is_full_market_price", "full_market_price_mapping_status", "geo_scope",
        "geography_match_status", "property_scope_status", "multi_property_action",
        "duplicate_action", "vat_mapping_status", "sale_price_adjustment_method",
    }
    missing = sorted(required - set(frame.columns))
    if missing:
        raise KeyError(f"Missing cleaning evidence fields: {missing}")
    output = frame.copy()
    reasons = pd.Series("", index=output.index, dtype="string")
    rule_ids = pd.Series("", index=output.index, dtype="string")
    masks = {
        "invalid_target": output["sale_price_eur_adjusted"].isna()
        | output["price_parse_status"].ne("parsed")
        | output["sale_price_eur_adjusted"].le(0),
        "invalid_date": output["transaction_date"].isna()
        | output["date_parse_status"].ne("parsed")
        | output["is_future_transaction"].eq(True),
        "non_full_market_transaction": output["is_full_market_price"].eq(False),
        "unresolved_market_price_status": output["is_full_market_price"].isna()
        | ~output["full_market_price_mapping_status"].isin(["mapped_full_market", "mapped_not_full_market"]),
        "out_of_scope_geography": output["geo_scope"].eq("out_of_scope"),
        "unmatched_geography_unresolved": output["geo_scope"].eq("unknown")
        & output["geography_match_status"].isin(["unmatched", "invalid_address"]),
        "ambiguous_geography_unresolved": output["geography_match_status"].eq("ambiguous"),
        "excluded_property_type": output["property_scope_status"].eq("clearly_non_house"),
        "multi_property_transaction": output["multi_property_action"].eq("auto_exclude"),
        "duplicate_unresolved": output["duplicate_action"].eq("auto_exclude"),
        "unresolved_vat_treatment": ~output["vat_mapping_status"].isin(
            ["mapped_vat_exclusive", "mapped_vat_inclusive"]
        ) | output["sale_price_adjustment_method"].eq("unresolved_vat_flag"),
        "insufficient_required_fields": output["record_id"].isna()
        | output["raw_address"].fillna("").astype(str).str.strip().eq(""),
    }
    primary = pd.Series(pd.NA, index=output.index, dtype="string")
    for reason in EXCLUSION_PRIORITY:
        mask = masks[reason]
        reasons.loc[mask] = _append_pipe(reasons.loc[mask], reason)
        rule_ids.loc[mask] = _append_pipe(rule_ids.loc[mask], EXCLUSION_RULE_BY_REASON[reason])
        primary.loc[mask & primary.isna()] = reason
    output["exclude_from_training"] = reasons.ne("")
    output["exclusion_reason"] = primary
    output["exclusion_reasons"] = reasons
    output["exclusion_rule_ids"] = rule_ids
    flags = pd.Series("", index=output.index, dtype="string")
    flag_masks = [
        (masks["invalid_target"], "invalid_target"),
        (masks["invalid_date"], "invalid_date"),
        (masks["non_full_market_transaction"], "possible_non_market_sale"),
        (output["geo_scope"].eq("out_of_scope"), "out_of_scope_area"),
        (output["geography_match_status"].isin(["unmatched", "invalid_address"]), "unmatched_area"),
        (output["geography_match_status"].eq("ambiguous"), "ambiguous_area"),
        (output["property_scope_status"].eq("clearly_non_house"), "excluded_property_type"),
        (output["property_scope_status"].ne("clearly_non_house"), "unknown_property_type"),
        (output["multi_property_action"].eq("auto_exclude"), "multi_property_auto_exclude"),
        (output["multi_property_action"].eq("review_only"), "possible_multi_property_sale"),
        (output["duplicate_status"].ne("not_duplicate_like"), "duplicate_like"),
        (output["duplicate_action"].eq("review_only"), "duplicate_review_required"),
        (masks["unresolved_vat_treatment"], "unresolved_vat_treatment"),
    ]
    for mask, flag in flag_masks:
        flags.loc[mask] = _append_pipe(flags.loc[mask], flag)
    for source_column in ["address_quality_flags", "geography_quality_flags", "property_type_quality_flag"]:
        if source_column in output:
            source = output[source_column].fillna("").astype("string").str.strip("|")
            has_source = source.ne("")
            flags.loc[has_source] = flags.loc[has_source].where(
                flags.loc[has_source].eq(""), flags.loc[has_source] + "|"
            ) + source.loc[has_source]
    output["quality_flags"] = flags.map(_deduplicate_pipe).astype("string")
    review = output["multi_property_action"].eq("review_only") | output["duplicate_action"].eq("review_only") | output["property_scope_status"].eq("review_required")
    output["cleaning_assessment_status"] = "eligible"
    output.loc[review & ~output["exclude_from_training"], "cleaning_assessment_status"] = "eligible_with_review"
    output.loc[output["exclude_from_training"], "cleaning_assessment_status"] = "excluded"
    return output


def checkpoint4_arrow_schema(input_schema: pa.Schema) -> pa.Schema:
    """Build the explicit Checkpoint 4 physical schema.

    Args:
        input_schema: Approved Checkpoint 3 schema.

    Returns:
        Input fields followed by Checkpoint 4 assessment fields.

    Raises:
        Checkpoint4PhysicalSchemaError: If any new name already exists.
    """

    existing = set(input_schema.names)
    duplicate = existing & {field.name for field in CHECKPOINT4_FIELDS}
    if duplicate:
        raise Checkpoint4PhysicalSchemaError(f"Checkpoint 4 fields already exist: {sorted(duplicate)}")
    return pa.schema(list(input_schema) + CHECKPOINT4_FIELDS)


def dataframe_to_checkpoint4_table(frame: pd.DataFrame, input_schema: pa.Schema) -> pa.Table:
    """Convert an assessed frame using the explicit physical schema.

    Args:
        frame: Fully assessed data.
        input_schema: Approved Checkpoint 3 schema.

    Returns:
        Explicitly typed Arrow table.

    Raises:
        Checkpoint4PhysicalSchemaError: If a required field is missing.
    """

    schema = checkpoint4_arrow_schema(input_schema)
    missing = [name for name in schema.names if name not in frame]
    if missing:
        raise Checkpoint4PhysicalSchemaError(f"Missing Checkpoint 4 output fields: {missing}")
    return pa.Table.from_pandas(frame[schema.names], schema=schema, preserve_index=False)


def write_checkpoint4_parquet(frame: pd.DataFrame, input_schema: pa.Schema, path: str | Path) -> pa.Schema:
    """Write the row-preserving cleaning-assessed Parquet.

    Args:
        frame: Fully assessed data.
        input_schema: Approved Checkpoint 3 schema.
        path: Output Parquet path.

    Returns:
        Written Arrow schema.
    """

    table = dataframe_to_checkpoint4_table(frame, input_schema)
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(table, path)
    return table.schema


def validate_checkpoint4_parquet(
    path: str | Path,
    input_table: pa.Table,
) -> pa.Schema:
    """Validate read-back schema, rows, order, and every inherited value.

    Args:
        path: Written Checkpoint 4 Parquet.
        input_table: Approved Checkpoint 3 input table.

    Returns:
        Validated read-back schema.

    Raises:
        Checkpoint4PhysicalSchemaError: If reconciliation or schema differs.
    """

    table = pq.read_table(path)
    expected = checkpoint4_arrow_schema(input_table.schema)
    if table.num_rows != input_table.num_rows:
        raise Checkpoint4PhysicalSchemaError(
            f"Row reconciliation failed: {input_table.num_rows} != {table.num_rows}"
        )
    if table.schema.remove_metadata() != expected.remove_metadata():
        raise Checkpoint4PhysicalSchemaError("Checkpoint 4 physical schema validation failed.")
    inherited = table.select(input_table.schema.names).cast(input_table.schema)
    if not inherited.equals(input_table):
        raise Checkpoint4PhysicalSchemaError("Checkpoint 3 values or row order changed.")
    return table.schema


def _append_pipe(values: pd.Series, token: str) -> pd.Series:
    """Append a token to stable pipe-delimited strings."""

    return values.where(values.eq(""), values + "|") + token


def _deduplicate_pipe(value: str) -> str:
    """Deduplicate tokens while retaining their first stable occurrence."""

    return "|".join(dict.fromkeys(token for token in str(value).split("|") if token))
