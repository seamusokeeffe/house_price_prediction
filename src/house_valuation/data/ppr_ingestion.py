"""PPR Checkpoint 2 source-standardised ingestion."""

from __future__ import annotations

import csv
import hashlib
import json
import re
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from typing import Any

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq


SOURCE_NAME = "ppr"
PPR_SNAPSHOT_DATE = date(2026, 6, 21)
PPR_ENCODING = "cp1252"
DEFAULT_HOUSE_VAT_RATE = Decimal("0.135")
CENT = Decimal("0.01")
PRICE_SOURCE_COLUMN = "Price (\u20ac)"

REQUIRED_SOURCE_COLUMNS = [
    "Date of Sale (dd/mm/yyyy)",
    "Address",
    "County",
    "Eircode",
    PRICE_SOURCE_COLUMN,
    "Not Full Market Price",
    "VAT Exclusive",
    "Description of Property",
    "Property Size Description",
]

CONFIRMED_IRISH_AND_MOJIBAKE_PROPERTY_DESCRIPTIONS = [
    "Teach/\u00c1ras\u00e1n C\u00f3naithe Ath\u00e1imhe",
    "Teach/\u00c1ras\u00e1n C\u00f3naithe Nua",
    "Teach/?ras?n C?naithe Nua",
]

PROPERTY_DESCRIPTION_MAPPING = {
    "Second-Hand Dwelling house /Apartment": ("second_hand_dwelling", False),
    "New Dwelling house /Apartment": ("new_dwelling", True),
    "Teach/\u00c1ras\u00e1n C\u00f3naithe Ath\u00e1imhe": ("second_hand_dwelling", False),
    "Teach/\u00c1ras\u00e1n C\u00f3naithe Nua": ("new_dwelling", True),
    "Teach/?ras?n C?naithe Nua": ("new_dwelling", True),
}

CORE_ARROW_FIELDS = [
    pa.field("source_name", pa.string(), nullable=False),
    pa.field("source_snapshot_date", pa.date32(), nullable=False),
    pa.field("source_file_sha256", pa.string(), nullable=False),
    pa.field("source_row_number", pa.int64(), nullable=False),
    pa.field("record_id", pa.string(), nullable=False),
    pa.field("raw_record_fingerprint", pa.string(), nullable=False),
    pa.field("transaction_date_raw", pa.string(), nullable=False),
    pa.field("transaction_date", pa.date32(), nullable=True),
    pa.field("transaction_year", pa.int64(), nullable=True),
    pa.field("date_parse_status", pa.string(), nullable=False),
    pa.field("is_future_transaction", pa.bool_(), nullable=True),
    pa.field("raw_address", pa.string(), nullable=False),
    pa.field("county_raw", pa.string(), nullable=False),
    pa.field("eircode_raw", pa.string(), nullable=True),
    pa.field("sale_price_eur_raw_text", pa.string(), nullable=False),
    pa.field("sale_price_eur_raw", pa.decimal128(18, 2), nullable=True),
    pa.field("price_parse_status", pa.string(), nullable=False),
    pa.field("not_full_market_price_raw", pa.string(), nullable=True),
    pa.field("is_full_market_price", pa.bool_(), nullable=True),
    pa.field("full_market_price_mapping_status", pa.string(), nullable=False),
    pa.field("vat_exclusive_raw", pa.string(), nullable=True),
    pa.field("vat_exclusive_flag", pa.bool_(), nullable=True),
    pa.field("vat_mapping_status", pa.string(), nullable=False),
    pa.field("vat_rate_applied", pa.decimal128(5, 3), nullable=True),
    pa.field("sale_price_eur_adjusted", pa.decimal128(18, 2), nullable=True),
    pa.field("sale_price_adjustment_method", pa.string(), nullable=False),
    pa.field("property_description_raw", pa.string(), nullable=True),
    pa.field("property_description_normalized", pa.string(), nullable=False),
    pa.field("property_description_mapping_method", pa.string(), nullable=False),
    pa.field("is_new_build", pa.bool_(), nullable=True),
    pa.field("property_type", pa.string(), nullable=False),
    pa.field("property_type_source", pa.string(), nullable=False),
    pa.field("property_type_quality_flag", pa.string(), nullable=False),
    pa.field("property_size_description_raw", pa.string(), nullable=True),
    pa.field("property_size_bucket_source", pa.string(), nullable=True),
    pa.field("floor_area_sqm", pa.float64(), nullable=True),
]


class PPRSourceSchemaError(ValueError):
    """Raised when the raw PPR source schema is not acceptable."""


class PPRPhysicalSchemaError(ValueError):
    """Raised when the written Checkpoint 2 Parquet schema is not acceptable."""


@dataclass(frozen=True)
class SourceSchemaValidation:
    columns: list[str]
    required_columns: list[str]
    missing_columns: list[str]
    unexpected_columns: list[str]
    duplicate_columns: list[str]
    raw_output_column_collisions: dict[str, list[str]]


@dataclass(frozen=True)
class PPRSourceConfig:
    source_path: Path
    snapshot_date: date = PPR_SNAPSHOT_DATE
    encoding: str = PPR_ENCODING
    source_name: str = SOURCE_NAME
    house_vat_rate: Decimal = DEFAULT_HOUSE_VAT_RATE


@dataclass(frozen=True)
class PPRBuildResult:
    frame: pd.DataFrame
    validation: SourceSchemaValidation
    source_file_sha256: str
    raw_row_count: int


def file_sha256(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_source_header(path: str | Path, *, encoding: str = PPR_ENCODING) -> list[str]:
    try:
        with Path(path).open("r", encoding=encoding, errors="strict", newline="") as handle:
            return next(csv.reader(handle))
    except UnicodeDecodeError as exc:
        raise UnicodeDecodeError(exc.encoding, exc.object, exc.start, exc.end, f"PPR source failed to decode as {encoding}") from exc
    except StopIteration as exc:
        raise PPRSourceSchemaError("PPR source file is empty.") from exc


def validate_source_columns(columns: list[str]) -> SourceSchemaValidation:
    duplicate_columns = sorted({column for column in columns if columns.count(column) > 1})
    missing_columns = [column for column in REQUIRED_SOURCE_COLUMNS if column not in columns]
    unexpected_columns = [column for column in columns if column not in REQUIRED_SOURCE_COLUMNS]
    raw_output_column_collisions = preserved_raw_column_collisions(columns)
    validation = SourceSchemaValidation(
        columns=list(columns),
        required_columns=list(REQUIRED_SOURCE_COLUMNS),
        missing_columns=missing_columns,
        unexpected_columns=unexpected_columns,
        duplicate_columns=duplicate_columns,
        raw_output_column_collisions=raw_output_column_collisions,
    )
    if duplicate_columns:
        raise PPRSourceSchemaError(f"Duplicate PPR source columns: {', '.join(duplicate_columns)}")
    if missing_columns:
        raise PPRSourceSchemaError(f"Missing required PPR source columns: {', '.join(missing_columns)}")
    if raw_output_column_collisions:
        details = "; ".join(
            f"{output_name}: {', '.join(source_names)}"
            for output_name, source_names in raw_output_column_collisions.items()
        )
        raise PPRSourceSchemaError(f"Preserved raw source column-name collisions: {details}")
    return validation


def read_ppr_source(config: PPRSourceConfig) -> tuple[pd.DataFrame, SourceSchemaValidation, str]:
    columns = read_source_header(config.source_path, encoding=config.encoding)
    validation = validate_source_columns(columns)
    checksum = file_sha256(config.source_path)
    try:
        frame = pd.read_csv(
            config.source_path,
            encoding=config.encoding,
            encoding_errors="strict",
            dtype="string",
            keep_default_na=False,
        )
    except UnicodeDecodeError as exc:
        raise UnicodeDecodeError(exc.encoding, exc.object, exc.start, exc.end, f"PPR source failed to decode as {config.encoding}") from exc
    return frame, validation, checksum


def source_raw_column_name(column: str) -> str:
    normalized = re.sub(r"[^0-9a-zA-Z]+", "_", column.strip()).strip("_").lower()
    return f"source_raw__{normalized}"


def preserved_raw_column_collisions(columns: list[str]) -> dict[str, list[str]]:
    grouped: dict[str, list[str]] = {}
    for column in columns:
        grouped.setdefault(source_raw_column_name(column), []).append(column)
    return {output_name: source_names for output_name, source_names in grouped.items() if len(source_names) > 1}


def transform_ppr_source(frame: pd.DataFrame, config: PPRSourceConfig, source_file_sha256: str) -> pd.DataFrame:
    output = pd.DataFrame(index=frame.index)
    source_row_numbers = pd.Series(range(1, len(frame) + 1), index=frame.index)

    output["source_name"] = config.source_name
    output["source_snapshot_date"] = config.snapshot_date
    output["source_file_sha256"] = source_file_sha256
    output["source_row_number"] = source_row_numbers
    output["record_id"] = [
        stable_hash([config.source_name, source_file_sha256, str(row_number)])
        for row_number in source_row_numbers
    ]
    output["raw_record_fingerprint"] = [
        raw_record_fingerprint(dict(zip(frame.columns, row, strict=True)))
        for row in frame.itertuples(index=False, name=None)
    ]

    output["transaction_date_raw"] = frame["Date of Sale (dd/mm/yyyy)"]
    parsed_dates = pd.to_datetime(output["transaction_date_raw"], format="%d/%m/%Y", errors="coerce")
    output["transaction_date"] = parsed_dates.dt.date
    output.loc[parsed_dates.isna(), "transaction_date"] = pd.NA
    output["transaction_year"] = parsed_dates.dt.year.astype("Int64")
    output["date_parse_status"] = output["transaction_date_raw"].apply(date_parse_status)
    output.loc[parsed_dates.notna(), "date_parse_status"] = "parsed"
    output["is_future_transaction"] = pd.Series(
        [pd.NA if pd.isna(value) else bool(value > config.snapshot_date) for value in parsed_dates.dt.date],
        dtype="boolean",
    )

    output["raw_address"] = frame["Address"]
    output["county_raw"] = frame["County"]
    output["eircode_raw"] = blank_to_na_series(frame["Eircode"])

    output["sale_price_eur_raw_text"] = frame[PRICE_SOURCE_COLUMN]
    raw_price_results = output["sale_price_eur_raw_text"].apply(parse_price_with_status)
    output["sale_price_eur_raw"] = raw_price_results.apply(lambda result: result[0])
    output["price_parse_status"] = raw_price_results.apply(lambda result: result[1])

    output["not_full_market_price_raw"] = blank_to_na_series(frame["Not Full Market Price"])
    full_market_results = output["not_full_market_price_raw"].apply(map_full_market_price)
    output["is_full_market_price"] = pd.Series(
        [result[0] for result in full_market_results],
        dtype="boolean",
    )
    output["full_market_price_mapping_status"] = full_market_results.apply(lambda result: result[1])

    output["vat_exclusive_raw"] = blank_to_na_series(frame["VAT Exclusive"])
    vat_results = output["vat_exclusive_raw"].apply(map_vat_exclusive)
    output["vat_exclusive_flag"] = pd.Series([result[0] for result in vat_results], dtype="boolean")
    output["vat_mapping_status"] = vat_results.apply(lambda result: result[1])

    adjustment_results = [
        apply_vat_adjustment(raw_price, price_status, vat_flag, config.house_vat_rate)
        for raw_price, price_status, vat_flag in zip(
            output["sale_price_eur_raw"],
            output["price_parse_status"],
            output["vat_exclusive_flag"],
            strict=True,
        )
    ]
    output["vat_rate_applied"] = [result[0] for result in adjustment_results]
    output["sale_price_eur_adjusted"] = [result[1] for result in adjustment_results]
    output["sale_price_adjustment_method"] = [result[2] for result in adjustment_results]

    output["property_description_raw"] = blank_to_na_series(frame["Description of Property"])
    property_results = output["property_description_raw"].apply(map_property_description)
    output["property_description_normalized"] = property_results.apply(lambda result: result[0])
    output["property_description_mapping_method"] = property_results.apply(lambda result: result[1])
    output["is_new_build"] = pd.Series([result[2] for result in property_results], dtype="boolean")
    output["property_type"] = "unknown"
    output["property_type_source"] = "unknown"
    output["property_type_quality_flag"] = "ppr_house_apartment_ambiguous"

    output["property_size_description_raw"] = blank_to_na_series(frame["Property Size Description"])
    output["property_size_bucket_source"] = output["property_size_description_raw"]
    output["floor_area_sqm"] = pd.Series([pd.NA] * len(output), dtype="Float64")

    for column in frame.columns:
        output[source_raw_column_name(column)] = frame[column]

    return output


def build_ppr_source_standardised(config: PPRSourceConfig) -> tuple[pd.DataFrame, SourceSchemaValidation, str]:
    result = build_ppr_source_standardised_result(config)
    return result.frame, result.validation, result.source_file_sha256


def build_ppr_source_standardised_result(config: PPRSourceConfig) -> PPRBuildResult:
    frame, validation, checksum = read_ppr_source(config)
    transformed = transform_ppr_source(frame, config, checksum)
    raw_row_count = len(frame)
    if raw_row_count != len(transformed):
        raise AssertionError(
            f"Checkpoint 2 row reconciliation failed: raw rows={raw_row_count}, "
            f"transformed rows={len(transformed)}"
        )
    return PPRBuildResult(transformed, validation, checksum, raw_row_count)


def stable_hash(parts: Any) -> str:
    payload = json.dumps(parts, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def raw_record_fingerprint(row: dict[str, Any]) -> str:
    canonical_pairs = [
        [str(column), canonical_raw_value(row[column])]
        for column in sorted(row)
    ]
    return stable_hash(canonical_pairs)


def canonical_raw_value(value: Any) -> str:
    if pd.isna(value):
        return ""
    return str(value)


def blank_to_na_series(series: pd.Series) -> pd.Series:
    return series.apply(lambda value: pd.NA if str(value).strip() == "" else value)


def date_parse_status(value: Any) -> str:
    if str(value or "").strip() == "":
        return "missing"
    return "invalid"


def parse_price_with_status(value: Any) -> tuple[Decimal | pd.NA, str]:
    text = str(value or "").strip()
    if not text:
        return pd.NA, "missing"
    cleaned = text.replace("\u20ac", "").replace(",", "").strip()
    try:
        amount = Decimal(cleaned).quantize(CENT, rounding=ROUND_HALF_UP)
    except (InvalidOperation, ValueError):
        return pd.NA, "invalid"
    if amount <= 0:
        return amount, "non_positive"
    return amount, "parsed"


def map_full_market_price(value: Any) -> tuple[bool | pd.NA, str]:
    text = "" if pd.isna(value) else str(value).strip().lower()
    if not text:
        return pd.NA, "missing"
    if text == "no":
        return True, "mapped_full_market"
    if text == "yes":
        return False, "mapped_not_full_market"
    return pd.NA, "unrecognised"


def map_vat_exclusive(value: Any) -> tuple[bool | pd.NA, str]:
    text = "" if pd.isna(value) else str(value).strip().lower()
    if not text:
        return pd.NA, "missing"
    if text == "no":
        return False, "mapped_vat_inclusive"
    if text == "yes":
        return True, "mapped_vat_exclusive"
    return pd.NA, "unrecognised"


def apply_vat_adjustment(
    raw_price: Any,
    price_status: str,
    vat_flag: Any,
    house_vat_rate: Decimal = DEFAULT_HOUSE_VAT_RATE,
) -> tuple[Decimal | pd.NA, Decimal | pd.NA, str]:
    if pd.isna(raw_price) or price_status != "parsed":
        return pd.NA, pd.NA, "invalid_raw_price"
    if pd.isna(vat_flag):
        return pd.NA, pd.NA, "unresolved_vat_flag"
    if bool(vat_flag):
        adjusted = (raw_price * (Decimal("1") + house_vat_rate)).quantize(CENT, rounding=ROUND_HALF_UP)
        return house_vat_rate, adjusted, "provisional_house_vat_13_5_percent"
    return Decimal("0"), raw_price, "none"


def map_property_description(value: Any) -> tuple[str, str, bool | pd.NA]:
    if pd.isna(value) or str(value).strip() == "":
        return "unknown", "missing", pd.NA
    text = str(value)
    mapped = PROPERTY_DESCRIPTION_MAPPING.get(text)
    if mapped is None:
        return "unknown", "unrecognised", pd.NA
    normalized, is_new_build = mapped
    return normalized, "exact_source_value_mapping", is_new_build


def checkpoint2_arrow_schema(raw_source_columns: list[str]) -> pa.Schema:
    raw_fields = [pa.field(source_raw_column_name(column), pa.string(), nullable=False) for column in raw_source_columns]
    return pa.schema(CORE_ARROW_FIELDS + raw_fields)


def dataframe_to_checkpoint2_table(frame: pd.DataFrame, raw_source_columns: list[str]) -> pa.Table:
    schema = checkpoint2_arrow_schema(raw_source_columns)
    frame_for_arrow = frame.copy()
    for field in schema:
        if field.name not in frame_for_arrow.columns:
            raise PPRPhysicalSchemaError(f"Missing output field before Parquet write: {field.name}")
    frame_for_arrow = frame_for_arrow[[field.name for field in schema]].copy()
    return pa.Table.from_pandas(frame_for_arrow, schema=schema, preserve_index=False)


def write_checkpoint2_parquet(frame: pd.DataFrame, raw_source_columns: list[str], path: str | Path) -> pa.Schema:
    table = dataframe_to_checkpoint2_table(frame, raw_source_columns)
    pq.write_table(table, path)
    return table.schema


def validate_checkpoint2_parquet(path: str | Path, raw_source_columns: list[str], expected_row_count: int) -> pa.Schema:
    table = pq.read_table(path)
    expected_schema = checkpoint2_arrow_schema(raw_source_columns)
    if table.num_rows != expected_row_count:
        raise PPRPhysicalSchemaError(
            f"Parquet row-count validation failed: expected {expected_row_count}, got {table.num_rows}"
        )
    if table.schema != expected_schema:
        raise PPRPhysicalSchemaError(
            "Parquet physical schema validation failed.\n"
            f"Expected:\n{expected_schema}\n\nActual:\n{table.schema}"
        )
    return table.schema
