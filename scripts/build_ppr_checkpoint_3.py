"""Build the PPR Checkpoint 3 geography-enriched dataset and audits.

The script reads the approved Checkpoint 2 Parquet, appends deterministic
address and geography fields, writes a versioned Parquet output, validates it,
publishes audit CSVs, runs tests, and writes the checkpoint report.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from house_valuation.data.geography_mapping import (  # noqa: E402
    INFERENCE_AREAS,
    TRAINING_ONLY_AREAS,
    enrich_with_geography,
    load_canonical_aliases,
    validate_checkpoint3_parquet,
    write_checkpoint3_parquet,
)
from house_valuation.data.ppr_ingestion import file_sha256  # noqa: E402


def main() -> None:
    """Run the Checkpoint 3 build from command-line arguments."""

    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="data/interim/ppr/20260621/ppr_source_standardised.parquet")
    parser.add_argument("--output", default="data/interim/ppr/20260621/ppr_geography_enriched.parquet")
    parser.add_argument("--canonical-areas", default="config/canonical_areas.csv")
    parser.add_argument("--overrides", default="config/address_overrides.csv")
    parser.add_argument("--report-dir", default="artifacts/data_quality/20260621")
    parser.add_argument("--test-output", default="artifacts/data_quality/20260621/test_output_checkpoint_3.txt")
    parser.add_argument("--skip-tests", action="store_true")
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)
    report_dir = Path(args.report_dir)
    test_output_path = Path(args.test_output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    report_dir.mkdir(parents=True, exist_ok=True)

    input_table = pq.read_table(input_path)
    input_schema = input_table.schema
    input_frame = input_table.to_pandas()
    input_columns = list(input_frame.columns)
    input_rows = len(input_frame)

    aliases = load_canonical_aliases(args.canonical_areas)
    output_frame = enrich_with_geography(
        input_frame,
        canonical_areas_path=args.canonical_areas,
        overrides_path=args.overrides,
    )
    validate_frame_reconciliation(input_frame, output_frame, input_columns)

    write_schema = write_checkpoint3_parquet(output_frame, input_schema, output_path)
    readback_schema = validate_checkpoint3_parquet(output_path, input_schema, len(output_frame))

    audit_paths = write_audits(output_frame, aliases, report_dir)
    test_result = run_tests(test_output_path, skip=args.skip_tests)

    report = build_report(
        frame=output_frame,
        input_path=input_path,
        output_path=output_path,
        canonical_path=Path(args.canonical_areas),
        overrides_path=Path(args.overrides),
        aliases=aliases,
        input_checksum=file_sha256(input_path),
        output_checksum=file_sha256(output_path),
        input_rows=input_rows,
        input_columns=input_columns,
        write_schema=write_schema,
        readback_schema=readback_schema,
        audit_paths=audit_paths,
        test_result=test_result,
    )
    report_path = report_dir / "ppr_checkpoint_3_report.md"
    report_path.write_text(report, encoding="utf-8")

    print(f"Wrote geography-enriched Parquet: {output_path}")
    print(f"Wrote Checkpoint 3 report: {report_path}")
    print(f"Wrote test output: {test_output_path}")


def validate_frame_reconciliation(input_frame: pd.DataFrame, output_frame: pd.DataFrame, input_columns: list[str]) -> None:
    """Assert that Checkpoint 3 preserved all Checkpoint 2 rows and values.

    Args:
        input_frame: Source-standardised Checkpoint 2 frame.
        output_frame: Geography-enriched Checkpoint 3 frame.
        input_columns: Columns expected to be preserved unchanged.

    Raises:
        AssertionError: If row count, row order, preserved columns, or preserved
            values differ.
    """

    if len(input_frame) != len(output_frame):
        raise AssertionError(f"Row-count mismatch: input={len(input_frame)}, output={len(output_frame)}")
    if input_frame["record_id"].tolist() != output_frame["record_id"].tolist():
        raise AssertionError("record_id values changed or row order changed.")
    missing = [column for column in input_columns if column not in output_frame.columns]
    if missing:
        raise AssertionError(f"Checkpoint 2 columns were not preserved: {missing}")
    for column in input_columns:
        if not input_frame[column].equals(output_frame[column]):
            raise AssertionError(f"Checkpoint 2 column values changed: {column}")


def write_audits(frame: pd.DataFrame, aliases: list[Any], report_dir: Path) -> dict[str, Path]:
    """Write required Checkpoint 3 audit CSVs.

    Args:
        frame: Geography-enriched frame.
        aliases: Loaded alias configuration. Kept for call-site clarity.
        report_dir: Directory where audit CSVs are written.

    Returns:
        Mapping from audit name to written path.
    """

    paths = {
        "unmatched": report_dir / "unmatched_geography.csv",
        "ambiguous": report_dir / "ambiguous_geography.csv",
        "manual": report_dir / "manual_geography_overrides_applied.csv",
        "out_of_scope": report_dir / "out_of_scope_geography_sample.csv",
        "alias_summary": report_dir / "geography_alias_match_summary.csv",
        "address_summary": report_dir / "address_normalization_quality_summary.csv",
    }
    frame.loc[
        frame["geography_match_status"].isin(["unmatched", "invalid_address"]),
        ["record_id", "raw_address", "address_normalized", "county_raw", "eircode_raw", "geography_match_status", "geography_quality_flags"],
    ].to_csv(paths["unmatched"], index=False)
    frame.loc[
        frame["geography_match_status"] == "ambiguous",
        ["record_id", "raw_address", "address_normalized", "county_raw", "geography_candidate_areas", "matched_aliases", "match_methods", "match_priorities"],
    ].to_csv(paths["ambiguous"], index=False)
    frame.loc[
        frame["geography_match_method"] == "manual_override",
        ["record_id", "raw_address", "address_normalized", "canonical_area", "geo_scope", "geography_match_status", "geography_match_method"],
    ].to_csv(paths["manual"], index=False)
    frame.loc[
        frame["geo_scope"] == "out_of_scope",
        ["record_id", "raw_address", "address_normalized", "county_raw", "geography_match_status", "geography_quality_flags"],
    ].head(500).to_csv(paths["out_of_scope"], index=False)

    alias_summary = frame[frame["geography_match_alias"].notna()].copy()
    if alias_summary.empty:
        alias_summary_out = pd.DataFrame(columns=["canonical_area", "alias", "scope", "match_method", "match_priority", "count"])
    else:
        alias_summary_out = (
            alias_summary.groupby(
                ["canonical_area", "geography_match_alias", "geo_scope", "geography_match_method", "geography_match_priority"],
                dropna=False,
            )
            .size()
            .reset_index(name="count")
            .rename(
                columns={
                    "geography_match_alias": "alias",
                    "geo_scope": "scope",
                    "geography_match_method": "match_method",
                    "geography_match_priority": "match_priority",
                }
            )
            .sort_values(["count", "canonical_area"], ascending=[False, True])
        )
    alias_summary_out.to_csv(paths["alias_summary"], index=False)

    flag_counts = explode_pipe_counts(frame, "address_quality_flags", empty_label="no_flags")
    status_counts = frame["address_normalization_status"].value_counts(dropna=False).rename_axis("address_normalization_status").reset_index(name="count")
    pd.concat(
        [
            status_counts.assign(summary_type="status").rename(columns={"address_normalization_status": "value"}),
            flag_counts.assign(summary_type="quality_flag").rename(columns={"address_quality_flags": "value"}),
        ],
        ignore_index=True,
    )[["summary_type", "value", "count"]].to_csv(paths["address_summary"], index=False)
    return paths


def run_tests(test_output_path: Path, *, skip: bool) -> dict[str, Any]:
    """Run the repository test suite and capture output.

    Args:
        test_output_path: File path for captured stdout and stderr.
        skip: Whether to skip test execution.

    Returns:
        Command metadata, exit status, parsed test count, output path, and
        captured output text.

    Raises:
        RuntimeError: If tests are run and fail.
    """

    command = [sys.executable, "-m", "unittest", "discover", "-s", "tests"]
    env = os.environ.copy()
    existing_pythonpath = env.get("PYTHONPATH")
    env["PYTHONPATH"] = "src" if not existing_pythonpath else f"src{os.pathsep}{existing_pythonpath}"
    display_command = f"PYTHONPATH=src {' '.join(command)}"
    if skip:
        test_output_path.write_text("Tests skipped by --skip-tests.\n", encoding="utf-8")
        return {"command": display_command, "exit_status": None, "test_count": None, "output_path": test_output_path, "output": "Tests skipped by --skip-tests.\n"}
    completed = subprocess.run(command, cwd=Path(__file__).resolve().parents[1], env=env, text=True, capture_output=True, check=False)
    output = completed.stdout + completed.stderr
    test_output_path.write_text(output, encoding="utf-8")
    if completed.returncode != 0:
        raise RuntimeError(f"Checkpoint 3 tests failed. See {test_output_path}")
    return {"command": display_command, "exit_status": completed.returncode, "test_count": parse_unittest_count(output), "output_path": test_output_path, "output": output}


def parse_unittest_count(output: str) -> int | None:
    """Parse the number of tests from unittest output.

    Args:
        output: Captured unittest output.

    Returns:
        Parsed test count, or `None` if no count is present.
    """

    import re

    match = re.search(r"Ran (\d+) tests?", output)
    return int(match.group(1)) if match else None


def build_report(**kwargs: Any) -> str:
    """Build the Markdown Checkpoint 3 report.

    Args:
        **kwargs: Report inputs assembled by `main`, including frames, paths,
            checksums, schemas, audit paths, aliases, and test metadata.

    Returns:
        Markdown report text.
    """

    frame: pd.DataFrame = kwargs["frame"]
    input_rows = kwargs["input_rows"]
    row_difference = len(frame) - input_rows
    duplicate_record_ids = int(frame["record_id"].duplicated().sum())
    preserved = all(column in frame.columns for column in kwargs["input_columns"])
    status_counts = frame["geography_match_status"].value_counts(dropna=False)
    total = len(frame)
    manual_count = int((frame["geography_match_method"] == "manual_override").sum())
    out_scope_count = int((frame["geo_scope"] == "out_of_scope").sum())
    rows_multi = int(frame["geography_candidate_areas"].astype(str).str.contains(r"\|", regex=True).sum())

    lines = [
        "# PPR Checkpoint 3 Report - 20260621",
        "",
        "## Output Status",
        "",
        "- `geography-enriched`: produced by this checkpoint.",
        "- `training-candidate`, `house-only`, model validation, duplicate resolution and multi-property detection were not produced.",
        "",
        "## Input And Reconciliation",
        "",
        f"- Input file: `{kwargs['input_path'].as_posix()}`",
        f"- Input file SHA256: `{kwargs['input_checksum']}`",
        f"- Input row count: {input_rows:,}",
        f"- Output file: `{kwargs['output_path'].as_posix()}`",
        f"- Output file SHA256: `{kwargs['output_checksum']}`",
        f"- Output row count: {len(frame):,}",
        f"- Row difference: {row_difference:,}",
        f"- Duplicate `record_id` count: {duplicate_record_ids:,}",
        f"- All Checkpoint 2 fields preserved: {preserved}",
        f"- Physical schema validation result: {kwargs['write_schema'].remove_metadata() == kwargs['readback_schema'].remove_metadata()}",
        "",
        "## Address Normalisation",
        "",
        f"- Missing raw-address count: {int(frame['raw_address'].astype('string').str.strip().eq('').sum()):,}",
        f"- Missing normalised-address count: {int(frame['address_normalized'].isna().sum()):,}",
        f"- Too-short address count: {int((frame['address_normalization_status'] == 'too_short').sum()):,}",
        "",
        "### Normalisation Status",
        value_counts_markdown(frame, "address_normalization_status"),
        "",
        "### Address Quality Flags",
        pipe_counts_markdown(frame, "address_quality_flags", empty_label="no_flags"),
        "",
        "### Representative Raw-To-Normalised Examples",
        samples_markdown(frame, ["raw_address", "address_normalized", "address_match_text", "address_quality_flags"], limit=8),
        "",
        "### Accent, Apostrophe, Unit Examples",
        samples_markdown(
            sample_contains(frame, ["Dún", "Dun Laoghaire", "'", "Apartment", "Apt"]),
            ["raw_address", "address_normalized", "address_match_text"],
            limit=10,
        ),
        "",
        "- Normalisation idempotence proof: covered by `test_raw_address_is_preserved_and_normalization_is_idempotent`.",
        "",
        "## Geography Mapping",
        "",
        status_percent_markdown(status_counts, total),
        "",
        f"- Inference-area matched count: {int(((frame['geo_scope'] == 'inference') & frame['canonical_area'].notna()).sum()):,}",
        f"- Training-only matched count: {int(((frame['geo_scope'] == 'training_only') & frame['canonical_area'].notna()).sum()):,}",
        f"- Confidently out-of-scope count: {out_scope_count:,}",
        f"- Unresolved/unmatched count: {int((frame['geography_match_status'] == 'unmatched').sum()):,}",
        f"- Ambiguous count: {int((frame['geography_match_status'] == 'ambiguous').sum()):,}",
        f"- Manual override count: {manual_count:,}",
        f"- Rows matching more than one candidate before resolution: {rows_multi:,}",
        "",
        "### By Canonical Area",
        value_counts_markdown(frame[frame["canonical_area"].notna()], "canonical_area"),
        "",
        "### By Geo Scope",
        value_counts_markdown(frame, "geo_scope"),
        "",
        "### By Match Method",
        value_counts_markdown(frame, "geography_match_method"),
        "",
        "### By Match Alias",
        value_counts_markdown(frame[frame["geography_match_alias"].notna()], "geography_match_alias", limit=50),
        "",
        "### By Match Priority",
        value_counts_markdown(frame, "geography_match_priority"),
        "",
        "### By County",
        value_counts_markdown(frame, "county_raw", limit=40),
        "",
        "### By Transaction Year",
        value_counts_markdown(frame, "transaction_year", limit=30),
        "",
        "## Coverage By Locked Canonical Area",
        "",
        coverage_by_area_markdown(frame),
        "",
        "## Manual Samples",
        "",
        sample_sections(frame),
        "",
        "## Audit Outputs",
        "",
        *[f"- {name}: `{path.as_posix()}`" for name, path in kwargs["audit_paths"].items()],
        "",
        "## Alias Rules",
        "",
        f"- Alias rules added: {len(kwargs['aliases']):,}",
        "- High-volume aliases requiring review are listed in `geography_alias_match_summary.csv` sorted by count.",
        "- Risky aliases: Blackrock, Milltown, Churchtown, Monkstown, Shankill, Merrion, Mount Merrion, Dún Laoghaire.",
        "- Manual-review finding: duplicate locality names outside Dublin were not mapped; broad postal districts were not mapped; ambiguous multi-area records were retained for audit.",
        "",
        "## Requirements-To-Test Matrix",
        "",
        requirements_to_test_markdown(),
        "",
        "## Test Evidence",
        "",
        f"- Exact command: `{kwargs['test_result']['command']}`",
        f"- Exit status: `{kwargs['test_result']['exit_status']}`",
        f"- Test count: `{kwargs['test_result']['test_count']}`",
        f"- Captured test output path: `{Path(kwargs['test_result']['output_path']).as_posix()}`",
        "",
        "```text",
        kwargs["test_result"]["output"].rstrip(),
        "```",
        "",
        "## Assumptions, Deviations, And Limits",
        "",
        "- Unmatched rows are `unknown` when Dublin context exists but no locked locality is found, and `out_of_scope` when non-Dublin context is clear.",
        "- Manual override mechanism is implemented, but the configured override file contains headers only.",
        "- No external geocoding, Eircode lookup, fuzzy matching, property-type classification, training exclusions, duplicate handling, or multi-property detection was added.",
        "- Before Checkpoint 4, review high-volume alias counts, ambiguous records, and county-conflict samples.",
    ]
    return "\n".join(lines) + "\n"


def value_counts_markdown(frame: pd.DataFrame, column: str, *, limit: int | None = None) -> str:
    """Render value counts for one column as a Markdown table."""

    counts = frame[column].astype("string").fillna("<null>").value_counts(dropna=False)
    if limit:
        counts = counts.head(limit)
    if counts.empty:
        return "_No rows._"
    lines = ["| Value | Count |", "| --- | ---: |"]
    lines.extend(f"| `{value}` | {count:,} |" for value, count in counts.items())
    return "\n".join(lines)


def status_percent_markdown(counts: pd.Series, total: int) -> str:
    """Render status counts and percentages as a Markdown table."""

    lines = ["| Status | Count | Percent |", "| --- | ---: | ---: |"]
    for status, count in counts.items():
        lines.append(f"| `{status}` | {count:,} | {count / total:.2%} |")
    return "\n".join(lines)


def explode_pipe_counts(frame: pd.DataFrame, column: str, *, empty_label: str) -> pd.DataFrame:
    """Count pipe-delimited values in a column.

    Args:
        frame: Frame containing the pipe-delimited column.
        column: Column to explode and count.
        empty_label: Label used for empty values.

    Returns:
        DataFrame with value and count columns.
    """

    values: list[str] = []
    for value in frame[column].fillna("").astype(str):
        values.extend(value.split("|") if value else [empty_label])
    return pd.Series(values, name=column).value_counts().rename_axis(column).reset_index(name="count")


def pipe_counts_markdown(frame: pd.DataFrame, column: str, *, empty_label: str) -> str:
    """Render pipe-delimited value counts as a Markdown table."""

    counts = explode_pipe_counts(frame, column, empty_label=empty_label)
    lines = ["| Flag | Count |", "| --- | ---: |"]
    lines.extend(f"| `{row[column]}` | {row['count']:,} |" for _, row in counts.iterrows())
    return "\n".join(lines)


def samples_markdown(frame: pd.DataFrame, columns: list[str], *, limit: int = 5) -> str:
    """Render a small row sample as a Markdown table."""

    sample = frame.loc[:, columns].head(limit)
    if sample.empty:
        return "_No samples._"
    lines = ["| " + " | ".join(columns) + " |", "| " + " | ".join(["---"] * len(columns)) + " |"]
    for _, row in sample.iterrows():
        lines.append("| " + " | ".join(f"`{row[column]}`" for column in columns) + " |")
    return "\n".join(lines)


def sample_contains(frame: pd.DataFrame, terms: list[str]) -> pd.DataFrame:
    """Return rows whose raw address contains any supplied term."""

    mask = pd.Series(False, index=frame.index)
    raw = frame["raw_address"].astype("string")
    for term in terms:
        mask = mask | raw.str.contains(term, case=False, na=False, regex=False)
    return frame[mask]


def coverage_by_area_markdown(frame: pd.DataFrame) -> str:
    """Render canonical-area coverage, including zero-match areas."""

    rows = []
    for area in INFERENCE_AREAS + TRAINING_ONLY_AREAS:
        subset = frame[frame["canonical_area"] == area]
        rows.append(
            {
                "canonical_area": area,
                "scope": "inference" if area in INFERENCE_AREAS else "training_only",
                "matched_rows": len(subset),
                "earliest_transaction_date": subset["transaction_date"].min() if not subset.empty else "",
                "latest_transaction_date": subset["transaction_date"].max() if not subset.empty else "",
                "distinct_aliases": subset["geography_match_alias"].nunique(dropna=True),
                "method_mix": "; ".join(f"{k}:{v}" for k, v in subset["geography_match_method"].value_counts().items()) if not subset.empty else "",
            }
        )
    lines = ["| Canonical area | Scope | Rows | Earliest | Latest | Distinct aliases | Method mix |", "| --- | --- | ---: | --- | --- | ---: | --- |"]
    for row in rows:
        lines.append(
            f"| `{row['canonical_area']}` | `{row['scope']}` | {row['matched_rows']:,} | `{row['earliest_transaction_date']}` | "
            f"`{row['latest_transaction_date']}` | {row['distinct_aliases']:,} | `{row['method_mix']}` |"
        )
    return "\n".join(lines)


def sample_sections(frame: pd.DataFrame) -> str:
    """Render representative manual-review sample sections."""

    sections = [
        ("Inference area samples", frame[frame["geo_scope"] == "inference"]),
        ("Training-only area samples", frame[frame["geo_scope"] == "training_only"]),
        ("Unmatched addresses", frame[frame["geography_match_status"] == "unmatched"]),
        ("Ambiguous addresses", frame[frame["geography_match_status"] == "ambiguous"]),
        ("Broad postal-district-only addresses", frame[frame["geography_quality_flags"].str.contains("broad_dublin_reference_only", na=False)]),
        ("County/context conflicts", frame[frame["geography_quality_flags"].str.contains("conflicting_county_context", na=False)]),
        ("Overlapping-area cases", frame[frame["geography_candidate_areas"].astype(str).str.contains(r"\|", regex=True, na=False)]),
        ("Dun Laoghaire cases", sample_contains(frame, ["Dún Laoghaire", "Dun Laoghaire"])),
        ("Merrion versus Mount Merrion", sample_contains(frame, ["Merrion", "Mount Merrion"])),
        ("Monkstown inference cases", frame[frame["canonical_area"] == "Monkstown"]),
        ("Dublin names also observed elsewhere", frame[frame["geography_quality_flags"].str.contains("conflicting_county_context|non_unique_locality_name", regex=True, na=False)]),
    ]
    columns = ["record_id", "raw_address", "county_raw", "canonical_area", "geo_scope", "geography_match_status", "geography_quality_flags"]
    lines: list[str] = []
    for title, sample in sections:
        lines.extend([f"### {title}", "", samples_markdown(sample, columns, limit=8), ""])
    return "\n".join(lines)


def requirements_to_test_markdown() -> str:
    """Render the Checkpoint 3 requirements-to-test matrix."""

    rows = [
        ("1-15 Address normalisation", "tests/data/test_address_normalization.py"),
        ("16-31 Canonical-area matching and safeguards", "tests/data/test_geography_mapping.py"),
        ("32-35 Manual overrides", "test_manual_override_takes_precedence; test_invalid_override_area_conflict_and_scope_mismatch_fail"),
        ("36 Monkstown inference scope", "test_exact_canonical_safe_alias_and_scopes"),
        ("37-45 Pipeline/schema/audit/no Checkpoint 4 fields/determinism", "test_pipeline_schema_row_count_preservation_and_determinism; test_no_training_or_property_scope_fields_are_introduced; build script audit publication"),
    ]
    lines = ["| Requirement range | Evidence |", "| --- | --- |"]
    lines.extend(f"| {area} | `{tests}` |" for area, tests in rows)
    return "\n".join(lines)


if __name__ == "__main__":
    main()
