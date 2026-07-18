"""Build the PPR Checkpoint 2 source-standardised dataset and report."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import pandas as pd
import pyarrow as pa

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from house_valuation.data.ppr_ingestion import (  # noqa: E402
    CONFIRMED_IRISH_AND_MOJIBAKE_PROPERTY_DESCRIPTIONS,
    PPRSourceConfig,
    build_ppr_source_standardised_result,
    source_raw_column_name,
    validate_checkpoint2_parquet,
    write_checkpoint2_parquet,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", default="data/raw/ppr/20260621/PPR-ALL.csv")
    parser.add_argument("--output-dir", default="data/interim/ppr/20260621")
    parser.add_argument("--report-dir", default="artifacts/data_quality/20260621")
    parser.add_argument("--test-output", default="artifacts/data_quality/20260621/test_output.txt")
    parser.add_argument("--skip-tests", action="store_true")
    args = parser.parse_args()

    config = PPRSourceConfig(source_path=Path(args.source))
    output_dir = Path(args.output_dir)
    report_dir = Path(args.report_dir)
    test_output_path = Path(args.test_output)
    output_dir.mkdir(parents=True, exist_ok=True)
    report_dir.mkdir(parents=True, exist_ok=True)
    test_output_path.parent.mkdir(parents=True, exist_ok=True)

    result = build_ppr_source_standardised_result(config)
    transformed_rows = len(result.frame)
    row_difference = transformed_rows - result.raw_row_count
    if row_difference != 0:
        raise AssertionError(
            f"Checkpoint 2 row reconciliation failed: raw rows={result.raw_row_count}, "
            f"transformed rows={transformed_rows}, difference={row_difference}"
        )

    parquet_path = output_dir / "ppr_source_standardised.parquet"
    write_schema = write_checkpoint2_parquet(result.frame, result.validation.columns, parquet_path)
    readback_schema = validate_checkpoint2_parquet(parquet_path, result.validation.columns, transformed_rows)

    schema_map_path = output_dir / "ppr_source_raw_column_map.json"
    raw_column_map = {column: source_raw_column_name(column) for column in result.validation.columns}
    schema_map_path.write_text(json.dumps(raw_column_map, indent=2, ensure_ascii=False), encoding="utf-8")

    test_result = run_tests(test_output_path, skip=args.skip_tests)
    report = build_report(
        frame=result.frame,
        validation=result.validation,
        checksum=result.source_file_sha256,
        raw_row_count=result.raw_row_count,
        parquet_path=parquet_path,
        schema_map_path=schema_map_path,
        config=config,
        write_schema=write_schema,
        readback_schema=readback_schema,
        test_result=test_result,
    )
    report_path = report_dir / "ppr_checkpoint_2_report.md"
    report_path.write_text(report, encoding="utf-8")

    print(f"Wrote source-standardised Parquet: {parquet_path}")
    print(f"Wrote raw-column map: {schema_map_path}")
    print(f"Wrote test output: {test_output_path}")
    print(f"Wrote Checkpoint 2 report: {report_path}")


def run_tests(test_output_path: Path, *, skip: bool) -> dict[str, Any]:
    command = [sys.executable, "-m", "unittest", "discover", "-s", "tests"]
    env = os.environ.copy()
    existing_pythonpath = env.get("PYTHONPATH")
    env["PYTHONPATH"] = "src" if not existing_pythonpath else f"src{os.pathsep}{existing_pythonpath}"
    display_command = f"PYTHONPATH=src {' '.join(command)}"
    if skip:
        test_output_path.write_text("Tests skipped by --skip-tests.\n", encoding="utf-8")
        return {
            "command": display_command,
            "exit_status": None,
            "test_count": None,
            "output_path": test_output_path,
            "output": "Tests skipped by --skip-tests.\n",
        }

    completed = subprocess.run(
        command,
        cwd=Path(__file__).resolve().parents[1],
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    output = completed.stdout + completed.stderr
    test_output_path.write_text(output, encoding="utf-8")
    if completed.returncode != 0:
        raise RuntimeError(f"Checkpoint 2 tests failed. See {test_output_path}")
    return {
        "command": display_command,
        "exit_status": completed.returncode,
        "test_count": parse_unittest_count(output),
        "output_path": test_output_path,
        "output": output,
    }


def parse_unittest_count(output: str) -> int | None:
    import re

    match = re.search(r"Ran (\d+) tests?", output)
    return int(match.group(1)) if match else None


def build_report(
    *,
    frame: pd.DataFrame,
    validation: Any,
    checksum: str,
    raw_row_count: int,
    parquet_path: Path,
    schema_map_path: Path,
    config: PPRSourceConfig,
    write_schema: pa.Schema,
    readback_schema: pa.Schema,
    test_result: dict[str, Any],
) -> str:
    transformed_rows = len(frame)
    row_difference = transformed_rows - raw_row_count
    duplicate_metrics = duplicate_fingerprint_metrics(frame)
    duplicate_record_ids = int(frame["record_id"].duplicated().sum())
    raw_columns = [source_raw_column_name(column) for column in validation.columns]
    raw_preservation = all(column in frame.columns for column in raw_columns)

    lines: list[str] = [
        f"# PPR Checkpoint 2 Report - {config.snapshot_date:%Y%m%d}",
        "",
        "## Metadata",
        "",
        f"- Snapshot date: `{config.snapshot_date.isoformat()}`",
        f"- Source encoding used: `{config.encoding}`",
        f"- Configured provisional house VAT rate: `{config.house_vat_rate}`",
        f"- Source file SHA256: `{checksum}`",
        "",
        "## Output Status",
        "",
        "- `source-standardised`: produced by this checkpoint.",
        "- `training-candidate`: not produced; reserved for later geography, property-scope, transaction-scope and exclusion rules.",
        "- `baseline-compatible`: not produced; existing baseline compatibility is assessed only.",
        "",
        "## Files",
        "",
        f"- Source-standardised Parquet: `{parquet_path.as_posix()}`",
        f"- Raw source column map: `{schema_map_path.as_posix()}`",
        f"- Captured test output: `{Path(test_result['output_path']).as_posix()}`",
        "",
        "## Reconciliation",
        "",
        f"- Raw rows read: {raw_row_count:,}",
        f"- Transformed rows emitted: {transformed_rows:,}",
        f"- Difference: {row_difference:,}",
        f"- Reconciliation status: {'pass' if row_difference == 0 else 'fail'}",
        "- Row preservation assertion: passed; no rows were lost or added during Checkpoint 2.",
        f"- Duplicate `record_id` count: {duplicate_record_ids:,}",
        f"- Raw-fingerprint groups with more than one row: {duplicate_metrics['groups']:,}",
        f"- Total rows participating in duplicate raw-fingerprint groups: {duplicate_metrics['rows']:,}",
        f"- Repeated raw-fingerprint occurrences beyond the first: {duplicate_metrics['beyond_first']:,}",
        f"- Required source columns: {', '.join(f'`{column}`' for column in validation.required_columns)}",
        f"- Unexpected additional source columns: {format_list(validation.unexpected_columns)}",
        f"- Preserved raw-column name collisions: {format_list(list(validation.raw_output_column_collisions))}",
        f"- All raw source columns preserved: {raw_preservation}",
        "",
        "## Physical Schema Validation",
        "",
        f"- Parquet write schema validated: {write_schema == readback_schema}",
        f"- Parquet read-back row count: {transformed_rows:,}",
        "- Parquet schema validation against documented Checkpoint 2 fields: passed.",
        "",
        arrow_schema_markdown(readback_schema),
        "",
        "## Quality Counts",
        "",
        f"- Date parse-failure count: {count_not(frame, 'date_parse_status', 'parsed'):,}",
        f"- Future-date flag count: {count_true(frame, 'is_future_transaction'):,}",
        f"- Price parse-failure count: {count_in(frame, 'price_parse_status', ['missing', 'invalid']):,}",
        f"- Zero or negative price count: {count_value(frame, 'price_parse_status', 'non_positive'):,}",
        "",
        "### Full-Market Mapping",
        "",
        value_counts_markdown(frame, "full_market_price_mapping_status"),
        "",
        "### VAT Mapping",
        "",
        value_counts_markdown(frame, "vat_mapping_status"),
        "",
        f"- VAT-adjusted record count: {count_value(frame, 'sale_price_adjustment_method', 'provisional_house_vat_13_5_percent'):,}",
        "",
        "### Applied VAT Rate",
        "",
        value_counts_markdown(frame, "vat_rate_applied"),
        "",
        "### Adjustment Method",
        "",
        value_counts_markdown(frame, "sale_price_adjustment_method"),
        "",
        "### VAT-Adjusted Counts By Transaction Year",
        "",
        grouped_count_markdown(
            frame[frame["sale_price_adjustment_method"] == "provisional_house_vat_13_5_percent"],
            "transaction_year",
        ),
        "",
        "## Property Description",
        "",
        "### Exact Distinct Raw Values",
        "",
        value_counts_markdown(frame, "property_description_raw"),
        "",
        "### Normalized Values",
        "",
        value_counts_markdown(frame, "property_description_normalized"),
        "",
        "### Confirmed Irish-Language And Mojibake Mapping Counts",
        "",
        irish_mapping_counts(frame),
        "",
        "Speculative unobserved mojibake variants are not active mappings in Checkpoint 2.",
        "",
        "### Unrecognised Property-Description Samples",
        "",
        samples_markdown(frame[frame["property_description_mapping_method"] == "unrecognised"], ["property_description_raw"], limit=5),
        "",
        "## Raw Versus Adjusted Price Samples",
        "",
        samples_markdown(
            frame[["sale_price_eur_raw_text", "sale_price_eur_raw", "vat_exclusive_raw", "vat_rate_applied", "sale_price_eur_adjusted", "sale_price_adjustment_method"]].head(5),
            ["sale_price_eur_raw_text", "sale_price_eur_raw", "vat_exclusive_raw", "vat_rate_applied", "sale_price_eur_adjusted", "sale_price_adjustment_method"],
        ),
        "",
        "## Representative Examples",
        "",
        example_section(frame),
        "",
        "## Created Field Null Counts And Pandas Dtypes",
        "",
        nulls_and_dtypes_markdown(frame),
        "",
        "## Baseline Compatibility Findings",
        "",
        "- `src/house_valuation/data/filters.py::filter_training_rows` accepts `property_type = unknown` by default via `include_unknown_property_type=True`.",
        "- `src/house_valuation/features/build_features.py::baseline_group_key` forms `(canonical_area, property_type)` keys and keeps `unknown` as a valid grouping value.",
        "- `src/house_valuation/models/baseline.py::GroupedMedianBaseline.predict_one` supports area fallback when the area/property-type group has insufficient support.",
        "- `tests/data/test_ppr_ingestion.py::test_baseline_unknown_type_and_area_fallback_evidence` proves unknown type can train and predict via area fallback without an allow-listed detailed type.",
        "- Minimal later compatibility change: create a separate `baseline-compatible` output with `transaction_date`, `sale_price_eur`, `canonical_area`, and `property_type`; keep that separate from the richer source-standardised dataset. Checkpoint 2 does not create this output because geography mapping is out of scope.",
        "",
        "## Requirements-To-Test Summary",
        "",
        requirements_to_test_markdown(),
        "",
        "## Confirmed Non-Actions",
        "",
        "- No address normalisation was applied.",
        "- No geography mapping was applied.",
        "- No property-scope or house/apartment classification was applied.",
        "- No duplicate removal or duplicate resolution was applied.",
        "- No multi-property detection or exclusion was applied.",
        "- No low-price or high-price exclusion was applied.",
        "- No final training exclusions were applied.",
        "- No baseline-compatible output was created.",
        "",
        "## Test Output",
        "",
        f"- Exact command: `{test_result['command']}`",
        f"- Exit status: `{test_result['exit_status']}`",
        f"- Test count: `{test_result['test_count']}`",
        f"- Complete captured output path: `{Path(test_result['output_path']).as_posix()}`",
        "",
        "```text",
        test_result["output"].rstrip(),
        "```",
    ]
    return "\n".join(lines) + "\n"


def duplicate_fingerprint_metrics(frame: pd.DataFrame) -> dict[str, int]:
    counts = frame["raw_record_fingerprint"].value_counts()
    duplicate_counts = counts[counts > 1]
    return {
        "groups": int(len(duplicate_counts)),
        "rows": int(duplicate_counts.sum()),
        "beyond_first": int((duplicate_counts - 1).sum()),
    }


def arrow_schema_markdown(schema: pa.Schema) -> str:
    lines = ["| Field | PyArrow type | Nullable |", "| --- | --- | --- |"]
    for field in schema:
        lines.append(f"| `{field.name}` | `{field.type}` | `{field.nullable}` |")
    return "\n".join(lines)


def value_counts_markdown(frame: pd.DataFrame, column: str) -> str:
    counts = frame[column].astype("string").fillna("<null>").value_counts(dropna=False)
    if counts.empty:
        return "_No rows._"
    lines = ["| Value | Count |", "| --- | ---: |"]
    lines.extend(f"| `{value}` | {count:,} |" for value, count in counts.items())
    return "\n".join(lines)


def grouped_count_markdown(frame: pd.DataFrame, column: str) -> str:
    if frame.empty:
        return "_No rows._"
    counts = frame[column].astype("string").fillna("<null>").value_counts(dropna=False).sort_index()
    lines = ["| Value | Count |", "| --- | ---: |"]
    lines.extend(f"| `{value}` | {count:,} |" for value, count in counts.items())
    return "\n".join(lines)


def samples_markdown(frame: pd.DataFrame, columns: list[str], *, limit: int = 5) -> str:
    sample = frame.loc[:, columns].head(limit)
    if sample.empty:
        return "_No samples._"
    lines = ["| " + " | ".join(columns) + " |", "| " + " | ".join(["---"] * len(columns)) + " |"]
    for _, row in sample.iterrows():
        lines.append("| " + " | ".join(f"`{row[column]}`" for column in columns) + " |")
    return "\n".join(lines)


def example_section(frame: pd.DataFrame) -> str:
    duplicate_group = frame[frame["raw_record_fingerprint"].duplicated(keep=False)]
    if not duplicate_group.empty:
        selected_fingerprint = duplicate_group.iloc[0]["raw_record_fingerprint"]
        duplicate_pair = frame[frame["raw_record_fingerprint"] == selected_fingerprint].head(2)
    else:
        duplicate_pair = duplicate_group

    sections = [
        ("Normal VAT-inclusive transaction", frame[frame["sale_price_adjustment_method"] == "none"].head(1)),
        ("VAT-exclusive transaction", frame[frame["sale_price_adjustment_method"] == "provisional_house_vat_13_5_percent"].head(1)),
        ("Non-full-market transaction", frame[frame["is_full_market_price"] == False].head(1)),  # noqa: E712
        ("Irish second-hand description", frame[frame["property_description_raw"] == "Teach/\u00c1ras\u00e1n C\u00f3naithe Ath\u00e1imhe"].head(1)),
        ("Irish new description", frame[frame["property_description_raw"] == "Teach/\u00c1ras\u00e1n C\u00f3naithe Nua"].head(1)),
        ("Known mojibake description", frame[frame["property_description_raw"] == "Teach/?ras?n C?naithe Nua"].head(1)),
        ("Exact duplicate pair from one fingerprint group", duplicate_pair),
    ]
    columns = [
        "record_id",
        "raw_record_fingerprint",
        "transaction_date_raw",
        "raw_address",
        "sale_price_eur_raw_text",
        "vat_exclusive_raw",
        "sale_price_eur_adjusted",
        "not_full_market_price_raw",
        "property_description_raw",
    ]
    lines: list[str] = []
    for title, sample in sections:
        lines.extend([f"### {title}", "", samples_markdown(sample, columns, limit=2), ""])
    lines.extend(
        [
            "### Invalid Or Unrecognised Categorical Fixture",
            "",
            "No unrecognised categorical source values were observed in the snapshot. Unit tests include synthetic fixtures for unrecognised `Not Full Market Price`, `VAT Exclusive`, and property-description values.",
        ]
    )
    return "\n".join(lines)


def irish_mapping_counts(frame: pd.DataFrame) -> str:
    subset = frame[frame["property_description_raw"].isin(CONFIRMED_IRISH_AND_MOJIBAKE_PROPERTY_DESCRIPTIONS)]
    return value_counts_markdown(subset, "property_description_raw")


def nulls_and_dtypes_markdown(frame: pd.DataFrame) -> str:
    lines = ["| Field | Null count | Pandas dtype |", "| --- | ---: | --- |"]
    for column in frame.columns:
        lines.append(f"| `{column}` | {int(frame[column].isna().sum()):,} | `{frame[column].dtype}` |")
    return "\n".join(lines)


def requirements_to_test_markdown() -> str:
    rows = [
        ("CP1252 decoding and decoding failure", "test_cp1252_decoding_and_explicit_decoding_failure"),
        ("Required columns reordered", "test_full_ingestion_required_columns_reordered"),
        ("Missing/extra/duplicate/colliding source columns", "test_missing_required_source_column_fails; test_unexpected_additional_source_column_is_reported; test_duplicate_source_column_names_fail; test_preserved_raw_column_name_collision_fails"),
        ("Date parsing, missing and invalid dates", "test_date_price_status_vat_and_fingerprints; test_missing_date_and_missing_price"),
        ("Price parsing, missing, invalid, zero and negative prices", "test_date_price_status_vat_and_fingerprints; test_missing_date_and_missing_price"),
        ("Full-market and VAT mappings", "test_date_price_status_vat_and_fingerprints"),
        ("VAT raw/adjusted preservation, ROUND_HALF_UP, configurable rate", "test_raw_versus_adjusted_price_preservation; test_documented_vat_rounding_half_up_exact_half_cent; test_configurable_vat_rate_is_used"),
        ("Duplicate IDs/fingerprints and order-invariant fingerprints", "test_date_price_status_vat_and_fingerprints; test_source_column_order_invariant_fingerprints"),
        ("English, Irish and mojibake property descriptions", "test_exact_property_description_mappings; test_raw_field_preservation_for_confirmed_irish_and_mojibake_descriptions"),
        ("Unrecognised property description and floor-area null policy", "test_unrecognised_property_description_remains_unknown; test_property_size_bucket_does_not_populate_floor_area"),
        ("Physical schema and Parquet readback", "test_checkpoint2_parquet_schema_and_row_count_validation"),
        ("Baseline unknown-type area fallback evidence", "test_baseline_unknown_type_and_area_fallback_evidence"),
    ]
    lines = ["| Requirement area | Test coverage |", "| --- | --- |"]
    lines.extend(f"| {area} | `{tests}` |" for area, tests in rows)
    return "\n".join(lines)


def count_value(frame: pd.DataFrame, column: str, value: Any) -> int:
    return int((frame[column] == value).sum())


def count_not(frame: pd.DataFrame, column: str, value: Any) -> int:
    return int((frame[column] != value).sum())


def count_in(frame: pd.DataFrame, column: str, values: list[Any]) -> int:
    return int(frame[column].isin(values).sum())


def count_true(frame: pd.DataFrame, column: str) -> int:
    return int((frame[column] == True).sum())  # noqa: E712


def format_list(values: list[str]) -> str:
    return ", ".join(f"`{value}`" for value in values) if values else "none"


if __name__ == "__main__":
    main()
