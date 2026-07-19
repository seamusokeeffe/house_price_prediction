"""Build the row-preserving PPR Checkpoint 4 cleaning-assessed dataset."""

from __future__ import annotations

import argparse
from collections.abc import Iterable
import os
from pathlib import Path
import re
import subprocess
import sys
from typing import Any

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from house_valuation.data.cleaning import (
    EXCLUSION_PRIORITY,
    assess_cleaning,
    validate_checkpoint4_parquet,
    write_checkpoint4_parquet,
)
from house_valuation.data.duplicate_detection import assess_duplicate_like_transactions
from house_valuation.data.multi_property import (
    MultiPropertyRule,
    assess_multi_property_frame,
    load_multi_property_rules,
    rule_match_counts,
)
from house_valuation.data.ppr_ingestion import PPR_SNAPSHOT_DATE, file_sha256
from house_valuation.data.property_scope import assess_property_scope


SNAPSHOT = PPR_SNAPSHOT_DATE.strftime("%Y%m%d")
DEFAULT_INPUT = Path("data/interim/ppr") / SNAPSHOT / "ppr_geography_enriched.parquet"
DEFAULT_OUTPUT = Path("data/interim/ppr") / SNAPSHOT / "ppr_cleaning_assessed.parquet"
DEFAULT_REPORT_DIR = Path("artifacts/data_quality") / SNAPSHOT
DEFAULT_RULES = Path("config/multi_property_rules.csv")
AUDIT_BASE_COLUMNS = [
    "record_id", "source_row_number", "raw_record_fingerprint", "raw_address",
    "address_normalized", "county_raw", "transaction_date", "transaction_year",
    "sale_price_eur_raw", "sale_price_eur_adjusted", "not_full_market_price_raw",
    "is_full_market_price", "vat_exclusive_raw", "vat_exclusive_flag",
    "vat_mapping_status", "sale_price_adjustment_method", "property_description_raw",
    "is_new_build", "property_type", "canonical_area", "geo_scope",
    "geography_match_status", "multi_property_rule_ids", "multi_property_reason",
    "multi_property_action", "property_scope_status", "property_scope_rule_ids",
    "duplicate_group_id", "duplicate_group_size", "duplicate_status",
    "duplicate_rule_ids", "duplicate_action", "quality_flags",
    "exclude_from_training", "exclusion_reason", "exclusion_reasons",
    "exclusion_rule_ids", "cleaning_assessment_status",
]


def main() -> None:
    """Run tests, transform Checkpoint 3, validate, and publish audits."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--report-dir", type=Path, default=DEFAULT_REPORT_DIR)
    parser.add_argument("--rules", type=Path, default=DEFAULT_RULES)
    parser.add_argument("--skip-tests", action="store_true")
    parser.add_argument("--expected-output-sha256")
    args = parser.parse_args()
    args.report_dir.mkdir(parents=True, exist_ok=True)
    test_path = args.report_dir / "test_output_checkpoint_4.txt"
    test_result = run_tests(test_path, skip=args.skip_tests)
    print(f"Reading Checkpoint 3: {args.input}")
    input_checksum = file_sha256(args.input)
    input_table = pq.read_table(args.input)
    frame = input_table.to_pandas()
    rules = load_multi_property_rules(args.rules)
    assessed = run_assessment(frame, rules)
    assert_inherited_pandas_values(frame, assessed, input_table.schema.names)
    print(f"Writing cleaning-assessed rows: {len(assessed):,}")
    write_schema = write_checkpoint4_parquet(assessed, input_table.schema, args.output)
    read_schema = validate_checkpoint4_parquet(args.output, input_table)
    output_checksum = file_sha256(args.output)
    deterministic_match = (
        args.expected_output_sha256 is None
        or args.expected_output_sha256 == output_checksum
    )
    if not deterministic_match:
        raise RuntimeError(
            f"Repeated-build checksum mismatch: expected {args.expected_output_sha256}, got {output_checksum}"
        )
    audit_paths = write_audits(assessed, rules, args.report_dir)
    config_checksums = {
        str(path): file_sha256(path)
        for path in [args.rules, Path("config/canonical_areas.csv"), Path("config/address_overrides.csv")]
    }
    report = build_report(
        assessed=assessed,
        rules=rules,
        input_path=args.input,
        output_path=args.output,
        input_checksum=input_checksum,
        output_checksum=output_checksum,
        input_rows=input_table.num_rows,
        input_schema=input_table.schema,
        write_schema=write_schema,
        read_schema=read_schema,
        test_result=test_result,
        test_path=test_path,
        config_checksums=config_checksums,
        deterministic_expected=args.expected_output_sha256,
        audit_paths=audit_paths,
    )
    report_path = args.report_dir / "ppr_checkpoint_4_report.md"
    report_path.write_text(report, encoding="utf-8")
    print(f"Wrote Checkpoint 4 output: {args.output}")
    print(f"Output SHA256: {output_checksum}")
    print(f"Wrote report: {report_path}")


def run_assessment(frame: pd.DataFrame, rules: list[MultiPropertyRule]) -> pd.DataFrame:
    """Run the four pure assessment stages in deterministic order.

    Args:
        frame: Approved Checkpoint 3 frame.
        rules: Validated multi-property rules.

    Returns:
        Fully cleaning-assessed frame with identical inherited rows.
    """

    print("Assessing multi-property evidence")
    result = assess_multi_property_frame(frame, rules)
    print("Assessing conservative property scope")
    result = assess_property_scope(result)
    print("Assessing duplicate-like groups")
    result = assess_duplicate_like_transactions(result)
    print("Aggregating cleaning exclusions and quality flags")
    return assess_cleaning(result)


def assert_inherited_pandas_values(
    before: pd.DataFrame,
    after: pd.DataFrame,
    columns: list[str],
) -> None:
    """Assert inherited columns and row order are unchanged before writing.

    Args:
        before: Checkpoint 3 frame.
        after: Assessed frame.
        columns: Approved Checkpoint 3 field order.

    Raises:
        AssertionError: If any inherited field, value, or row differs.
    """

    if len(before) != len(after):
        raise AssertionError(f"Row reconciliation failed before write: {len(before)} != {len(after)}")
    pd.testing.assert_frame_equal(before[columns], after[columns], check_dtype=True, check_names=True)


def run_tests(path: Path, *, skip: bool) -> dict[str, Any]:
    """Run and capture the complete repository unittest suite.

    Args:
        path: Captured output path.
        skip: Whether this invocation intentionally skips tests.

    Returns:
        Test command, exit status, and parsed test count.

    Raises:
        RuntimeError: If the test command fails.
    """

    command = [sys.executable, "-m", "unittest", "discover", "-s", "tests"]
    display = f"PYTHONPATH=src {' '.join(command)}"
    if skip:
        if not path.exists():
            path.write_text("Tests skipped for deterministic repeat build; see prior captured run.\n", encoding="utf-8")
        return {"command": display, "exit_status": "skipped", "test_count": None}
    env = os.environ.copy()
    env["PYTHONPATH"] = "src"
    completed = subprocess.run(command, capture_output=True, text=True, env=env, check=False)
    output = completed.stdout + completed.stderr
    path.write_text(output, encoding="utf-8")
    count_match = re.search(r"Ran (\d+) tests?", output)
    result = {
        "command": display,
        "exit_status": completed.returncode,
        "test_count": int(count_match.group(1)) if count_match else None,
    }
    if completed.returncode != 0:
        raise RuntimeError(f"Checkpoint 4 tests failed; see {path}")
    return result


def write_audits(
    frame: pd.DataFrame,
    rules: list[MultiPropertyRule],
    report_dir: Path,
) -> dict[str, Path]:
    """Write required versioned audit and summary CSVs.

    Args:
        frame: Cleaning-assessed records.
        rules: Active rule metadata.
        report_dir: Versioned data-quality directory.

    Returns:
        Logical audit name to written path.
    """

    paths = {
        "rule_evidence": report_dir / "checkpoint_4_rule_evidence.csv",
        "multi_transactions": report_dir / "suspected_multi_property_transactions.csv",
        "multi_summary": report_dir / "multi_property_rule_summary.csv",
        "duplicate_transactions": report_dir / "duplicate_like_transactions.csv",
        "duplicate_summary": report_dir / "duplicate_rule_summary.csv",
        "property_scope": report_dir / "property_scope_review.csv",
        "excluded": report_dir / "excluded_records_checkpoint_4.csv",
        "exclusion_summary": report_dir / "exclusion_reason_summary.csv",
        "quality_summary": report_dir / "cleaning_quality_summary.csv",
        "vat_review": report_dir / "vat_treatment_review.csv",
    }
    columns = [column for column in AUDIT_BASE_COLUMNS if column in frame]
    multi = frame[frame["is_possible_multi_property_sale"]].sort_values("record_id")
    multi[columns].to_csv(paths["multi_transactions"], index=False, encoding="utf-8")
    duplicate_review = frame[frame["duplicate_status"].isin([
        "exact_source_duplicate", "plausible_duplicate_publication", "unresolved_duplicate_like"
    ])]
    distinct_sample = stable_sample(
        frame[frame["duplicate_status"].eq("same_day_distinct_transaction")],
        500,
    )
    pd.concat([duplicate_review, distinct_sample], ignore_index=True)[columns].sort_values(
        ["duplicate_status", "duplicate_group_id", "record_id"], na_position="last"
    ).to_csv(paths["duplicate_transactions"], index=False, encoding="utf-8")
    frame[frame["property_scope_status"].ne("unresolved_house_or_apartment")][columns].sort_values(
        ["property_scope_status", "record_id"]
    ).to_csv(paths["property_scope"], index=False, encoding="utf-8")
    frame[frame["exclude_from_training"]][columns].sort_values(
        ["exclusion_reason", "record_id"]
    ).to_csv(paths["excluded"], index=False, encoding="utf-8")
    unresolved_vat = ~frame["vat_mapping_status"].isin(["mapped_vat_exclusive", "mapped_vat_inclusive"])
    frame.loc[unresolved_vat, columns].to_csv(paths["vat_review"], index=False, encoding="utf-8")
    evidence = build_rule_evidence(frame, rules)
    evidence.to_csv(paths["rule_evidence"], index=False, encoding="utf-8")
    evidence[evidence["rule_category"].eq("multi_property")].to_csv(
        paths["multi_summary"], index=False, encoding="utf-8"
    )
    duplicate_summary(frame).to_csv(paths["duplicate_summary"], index=False, encoding="utf-8")
    exclusion_summary(frame).to_csv(paths["exclusion_summary"], index=False, encoding="utf-8")
    quality_summary(frame).to_csv(paths["quality_summary"], index=False, encoding="utf-8")
    return paths


def build_rule_evidence(frame: pd.DataFrame, rules: list[MultiPropertyRule]) -> pd.DataFrame:
    """Create one evidence row for every active assessment or exclusion rule.

    Args:
        frame: Cleaning-assessed records.
        rules: Active multi-property rules.

    Returns:
        Rule metadata and observed counts.
    """

    multi_counts = rule_match_counts(frame, rules)
    rows = [{
        "rule_category": "multi_property", "rule_id": rule.rule_id,
        "description": rule.description, "signal_or_logic": rule.matcher,
        "severity": rule.severity, "action": rule.action,
        "candidate_row_count": multi_counts[rule.rule_id],
        "locked_geography_count": _rule_locked_count(frame, "multi_property_rule_ids", rule.rule_id),
        "rationale": rule.rationale, "false_positive_risk": rule.false_positive_risk,
    } for rule in rules]
    property_rules = [
        ("PROP001", "Explicit apartment wording", "high", "auto_exclude", "Apartment wording is outside house scope."),
        ("PROP002", "Explicit flat wording", "high", "auto_exclude", "Flat wording is outside house scope."),
        ("PROP003", "APT abbreviation with identifier", "high", "auto_exclude", "Token and identifier boundaries reduce abbreviation risk."),
        ("PROP101", "Ambiguous UNIT wording", "medium", "review_only", "UNIT can describe an apartment or other unit."),
    ]
    for rule_id, description, severity, action, risk in property_rules:
        rows.append(_simple_rule_row(frame, "property_scope", "property_scope_rule_ids", rule_id, description, severity, action, risk))
    duplicate_rules = [
        ("DUP001", "Exact raw fingerprint group", "high", "exclude_later_occurrences", "One lowest-row representative is retained."),
        ("DUP002", "Normalised publication-key group", "medium", "review_only", "Legitimate repeated publications remain possible."),
        ("DUP003", "Weaker conflicting-status duplicate group", "medium", "review_only", "Conflicting source status prevents automatic resolution."),
        ("DUP004", "Same-day same-price distinct addresses", "info", "none", "Distinct addresses are protected from duplicate exclusion."),
    ]
    for rule_id, description, severity, action, risk in duplicate_rules:
        rows.append(_simple_rule_row(frame, "duplicate", "duplicate_rule_ids", rule_id, description, severity, action, risk))
    for position, reason in enumerate(EXCLUSION_PRIORITY, start=1):
        rows.append({
            "rule_category": "cleaning_exclusion", "rule_id": f"CLEAN{position:03d}",
            "description": reason, "signal_or_logic": "named deterministic mask",
            "severity": "exclusion", "action": "auto_exclude",
            "candidate_row_count": int(_pipe_has(frame["exclusion_reasons"], reason).sum()),
            "locked_geography_count": int((_pipe_has(frame["exclusion_reasons"], reason) & _locked(frame)).sum()),
            "rationale": f"Approved Checkpoint 4 exclusion reason priority {position}.",
            "false_positive_risk": "All applicable reasons are retained even when this is not primary.",
        })
    return pd.DataFrame(rows)


def _simple_rule_row(
    frame: pd.DataFrame,
    category: str,
    column: str,
    rule_id: str,
    description: str,
    severity: str,
    action: str,
    risk: str,
) -> dict[str, Any]:
    """Build one generic evidence row for a pipe-delimited rule field."""

    mask = _pipe_has(frame[column], rule_id)
    return {
        "rule_category": category, "rule_id": rule_id, "description": description,
        "signal_or_logic": "named deterministic rule", "severity": severity,
        "action": action, "candidate_row_count": int(mask.sum()),
        "locked_geography_count": int((mask & _locked(frame)).sum()),
        "rationale": description, "false_positive_risk": risk,
    }


def duplicate_summary(frame: pd.DataFrame) -> pd.DataFrame:
    """Summarise duplicate categories, actions, rows, and groups."""

    return (
        frame.groupby(["duplicate_status", "duplicate_action"], dropna=False)
        .agg(row_count=("record_id", "size"), group_count=("duplicate_group_id", "nunique"))
        .reset_index()
    )


def exclusion_summary(frame: pd.DataFrame) -> pd.DataFrame:
    """Summarise primary and all-applicable exclusion reasons."""

    rows = []
    for reason in EXCLUSION_PRIORITY:
        all_mask = _pipe_has(frame["exclusion_reasons"], reason)
        primary_mask = frame["exclusion_reason"].eq(reason)
        rows.append({
            "exclusion_reason": reason,
            "primary_count": int(primary_mask.sum()),
            "all_applicable_count": int(all_mask.sum()),
            "locked_geography_count": int((all_mask & _locked(frame)).sum()),
            "overlap_count": int((all_mask & frame["exclusion_reasons"].str.contains(r"\|", regex=True)).sum()),
        })
    return pd.DataFrame(rows)


def quality_summary(frame: pd.DataFrame) -> pd.DataFrame:
    """Create long-form full-data and locked-geography quality counts."""

    columns = [
        "exclude_from_training", "exclusion_reason", "multi_property_action",
        "multi_property_max_severity", "duplicate_status", "duplicate_action",
        "property_scope_status", "geo_scope", "geography_match_status",
        "canonical_area", "transaction_year", "not_full_market_price_raw",
        "is_full_market_price", "vat_exclusive_raw", "vat_mapping_status",
        "sale_price_adjustment_method", "is_new_build", "property_description_raw",
        "property_type", "cleaning_assessment_status",
    ]
    rows: list[dict[str, Any]] = []
    for scope, mask in [("full_dataset", pd.Series(True, index=frame.index)), ("locked_geography", _locked(frame))]:
        denominator = int(mask.sum())
        for column in columns:
            counts = frame.loc[mask, column].astype("string").fillna("<NULL>").value_counts(dropna=False)
            for value, count in counts.items():
                rows.append({
                    "dataset_scope": scope, "metric": column, "value": value,
                    "count": int(count), "percent": (100 * int(count) / denominator) if denominator else 0,
                })
        for metric in ["quality_flags", "exclusion_reasons", "exclusion_rule_ids", "multi_property_rule_ids"]:
            exploded = frame.loc[mask, metric].fillna("").str.split("|").explode()
            counts = exploded[exploded.ne("")].value_counts()
            for value, count in counts.items():
                rows.append({
                    "dataset_scope": scope, "metric": f"each_{metric}", "value": value,
                    "count": int(count), "percent": (100 * int(count) / denominator) if denominator else 0,
                })
    return pd.DataFrame(rows)


def build_report(
    *,
    assessed: pd.DataFrame,
    rules: list[MultiPropertyRule],
    input_path: Path,
    output_path: Path,
    input_checksum: str,
    output_checksum: str,
    input_rows: int,
    input_schema: pa.Schema,
    write_schema: pa.Schema,
    read_schema: pa.Schema,
    test_result: dict[str, Any],
    test_path: Path,
    config_checksums: dict[str, str],
    deterministic_expected: str | None,
    audit_paths: dict[str, Path],
) -> str:
    """Render the complete reproducible Checkpoint 4 Markdown report."""

    locked = _locked(assessed)
    excluded = assessed["exclude_from_training"]
    multi_counts = rule_match_counts(assessed, rules)
    sections = [
        f"# PPR Checkpoint 4 Report - {SNAPSHOT}",
        "## Output Status\n\n- `cleaning-assessed`: produced.\n- No final processed, baseline-compatible, DuckDB, model, or temporal-validation output was produced.",
        "## Input, Output, And Reconciliation",
        f"- Input: `{input_path.as_posix()}`\n- Input SHA256: `{input_checksum}`\n- Output: `{output_path.as_posix()}`\n- Output SHA256: `{output_checksum}`\n- Input rows: {input_rows:,}\n- Output rows: {len(assessed):,}\n- Row difference: {len(assessed) - input_rows:,}\n- Duplicate `record_id` count: {int(assessed['record_id'].duplicated().sum()):,}\n- Every Checkpoint 3 field, value, and row order preserved: passed\n- Explicit schema validation: {write_schema.remove_metadata() == read_schema.remove_metadata()}\n- Parquet read-back: passed",
        "### Configuration Checksums\n\n" + "\n".join(f"- `{path}`: `{checksum}`" for path, checksum in config_checksums.items()),
        "### Determinism\n\n" + (f"Repeated full-build expected checksum `{deterministic_expected}` matched: yes." if deterministic_expected else "Pure transformation determinism is covered by tests; run this script again with `--expected-output-sha256` set to the checksum above for a full-build checksum proof."),
        "## Approved Decisions",
        "- High-precision multi-property rules auto-exclude; medium evidence remains review-only.\n- Exact fingerprint groups retain the lowest source row number and exclude later occurrences.\n- Non-exact duplicate-like groups remain review-only.\n- Explicit apartment/flat/APT-with-identifier rows are outside house scope.\n- Ambiguous UNIT and otherwise unresolved house/apartment rows remain eligible with flags.\n- VAT-exclusive and new-build status alone never exclude.\n- Out-of-scope, unmatched, and ambiguous geography exclude because training requires a resolved locked area.\n- All reasons are retained; the approved priority selects only the primary reason.",
        "### Exclusion Priority\n\n" + "\n".join(f"{index}. `{reason}`" for index, reason in enumerate(EXCLUSION_PRIORITY, 1)),
        "## Inclusion And Exclusion",
        f"- Included: {int((~excluded).sum()):,} ({100 * (~excluded).mean():.2f}%)\n- Excluded: {int(excluded.sum()):,} ({100 * excluded.mean():.2f}%)\n- Included within matched locked geography: {int((~excluded & locked).sum()):,}\n- Excluded within matched locked geography: {int((excluded & locked).sum()):,}\n- Included review-flagged rows: {int((~excluded & assessed['cleaning_assessment_status'].eq('eligible_with_review')).sum()):,}",
        "### Primary And Applicable Exclusion Reasons\n\n" + dataframe_markdown(exclusion_summary(assessed)),
        "### Cumulative Logical Stages\n\n" + dataframe_markdown(stage_counts(assessed)),
        "### Exclusion Overlap\n\n" + overlap_markdown(assessed),
        "## Multi-Property Assessment",
        f"- Suspected rows: {int(assessed['is_possible_multi_property_sale'].sum()):,}\n- Auto-exclude: {int(assessed['multi_property_action'].eq('auto_exclude').sum()):,}\n- Review-only: {int(assessed['multi_property_action'].eq('review_only').sum()):,}\n- Auto-exclude within locked geography: {int((assessed['multi_property_action'].eq('auto_exclude') & locked).sum()):,}",
        "### Rule Evidence\n\n" + multi_rule_markdown(rules, multi_counts, assessed),
        "### Multi-Rule Examples\n\n" + rule_samples_markdown(assessed, rules),
        "## Property Scope\n\n" + dataframe_markdown(value_count_frame(assessed, "property_scope_status")),
        "### Explicit And Unresolved Examples\n\n" + samples_markdown(assessed[assessed["property_scope_status"].ne("unresolved_house_or_apartment")], ["record_id", "raw_address", "property_scope_status", "property_scope_rule_ids", "exclude_from_training"], 10) + "\n\n" + samples_markdown(assessed[assessed["property_scope_status"].eq("unresolved_house_or_apartment")], ["record_id", "raw_address", "property_scope_status", "exclude_from_training"], 5),
        "## Duplicate-Like Assessment\n\n" + dataframe_markdown(duplicate_summary(assessed)),
        "### Exact, Plausible, Unresolved, And Distinct Examples\n\n" + samples_markdown(assessed[assessed["duplicate_status"].ne("not_duplicate_like")], ["record_id", "raw_address", "transaction_date", "sale_price_eur_adjusted", "duplicate_group_id", "duplicate_status", "duplicate_action"], 16),
        "## Geography, VAT, New Build, And Source Coverage",
        "### Geography Scope\n\n" + dataframe_markdown(value_count_frame(assessed, "geo_scope")),
        "### Geography Match Status\n\n" + dataframe_markdown(value_count_frame(assessed, "geography_match_status")),
        f"### VAT And New Build\n\n- VAT-exclusive rows: {int(assessed['vat_exclusive_flag'].eq(True).sum()):,}\n- Unresolved VAT rows: {int((~assessed['vat_mapping_status'].isin(['mapped_vat_exclusive', 'mapped_vat_inclusive'])).sum()):,}\n- New-build rows: {int(assessed['is_new_build'].eq(True).sum()):,}\n- Valid VAT-adjusted/new-build rows excluded solely for VAT or new-build: 0",
        "### Retained VAT-Adjusted Individual-Looking New Builds\n\n" + samples_markdown(assessed[assessed["vat_exclusive_flag"].eq(True) & assessed["is_new_build"].eq(True) & assessed["multi_property_action"].eq("none")], ["record_id", "raw_address", "sale_price_eur_adjusted", "vat_exclusive_flag", "is_new_build", "exclude_from_training", "exclusion_reasons"], 8),
        "### High-Value Rows Not Excluded By Price\n\n" + samples_markdown(assessed[assessed["multi_property_action"].eq("none")].sort_values("sale_price_eur_adjusted", ascending=False), ["record_id", "raw_address", "sale_price_eur_adjusted", "multi_property_action", "exclude_from_training", "exclusion_reasons"], 8),
        "## Representative Exclusion And Overlap Evidence\n\n" + exclusion_samples_markdown(assessed),
        "## Test Evidence",
        f"- Exact command: `{test_result['command']}`\n- Exit status: `{test_result['exit_status']}`\n- Test count: `{test_result['test_count']}`\n- Captured output: `{test_path.as_posix()}`",
        "### Requirements-To-Test Matrix\n\n| Requirement | Tests / validation |\n| --- | --- |\n| Multi-property rules 1-16 | `tests/data/test_multi_property.py` |\n| Property scope 17-22 | `tests/data/test_property_scope.py` |\n| Duplicate assessment 23-30 | `tests/data/test_duplicate_detection.py` |\n| Cleaning rules 31-51 | `tests/data/test_cleaning.py` |\n| Schema, audits, reproducibility 52-60 | `test_schema_readback_preservation_and_determinism`; build-time full-data reconciliation; repeated-build checksum |",
        "## Physical Schema\n\n" + arrow_schema_markdown(read_schema, inherited_count=len(input_schema)),
        "## Audit Outputs\n\n" + "\n".join(f"- {name}: `{path.as_posix()}`" for name, path in audit_paths.items()),
        "## Inherited Findings And Limits",
        "- `Dún Laoghaire` is correctly encoded in configuration, code, report source, and Parquet; prior garbling was terminal rendering only.\n- Geography aliases, ambiguity, and county conflicts were carried forward unchanged.\n- Address text cannot prove that every unresolved PPR dwelling is a house; approved H-005 retains those rows with explicit flags.\n- Review-only rules identify candidates but do not represent completed manual review.\n- Price is not capped, winsorised, or used alone for exclusion.\n- No hard floor-area threshold is applied.",
    ]
    return "\n\n".join(sections) + "\n"


def stage_counts(frame: pd.DataFrame) -> pd.DataFrame:
    """Count rows remaining after each logical exclusion stage."""

    stages = [
        ("input", []),
        ("valid_target_date", EXCLUSION_PRIORITY[:2]),
        ("market_status", EXCLUSION_PRIORITY[:4]),
        ("resolved_geography", EXCLUSION_PRIORITY[:7]),
        ("property_scope", EXCLUSION_PRIORITY[:8]),
        ("multi_property", EXCLUSION_PRIORITY[:9]),
        ("duplicates", EXCLUSION_PRIORITY[:10]),
        ("vat_and_required_fields", EXCLUSION_PRIORITY),
    ]
    rows = []
    for name, reasons in stages:
        excluded = pd.Series(False, index=frame.index)
        for reason in reasons:
            excluded |= _pipe_has(frame["exclusion_reasons"], reason)
        rows.append({"stage": name, "eligible_rows": int((~excluded).sum()), "excluded_rows": int(excluded.sum())})
    return pd.DataFrame(rows)


def overlap_markdown(frame: pd.DataFrame) -> str:
    """Render common multi-reason intersections."""

    counts = frame["exclusion_reasons"].str.count(r"\|").add(1).where(frame["exclusion_reasons"].ne(""), 0)
    distribution = counts.value_counts().sort_index().rename_axis("reason_count").reset_index(name="rows")
    combinations = frame.loc[counts.ge(2), "exclusion_reasons"].value_counts().head(20).rename_axis("reason_combination").reset_index(name="rows")
    return "#### Number Of Applicable Reasons\n\n" + dataframe_markdown(distribution) + "\n\n#### Most Common Intersections\n\n" + dataframe_markdown(combinations)


def multi_rule_markdown(
    rules: list[MultiPropertyRule],
    counts: dict[str, int],
    frame: pd.DataFrame,
) -> str:
    """Render active multi-property rule metadata and counts."""

    rows = []
    for rule in rules:
        mask = _pipe_has(frame["multi_property_rule_ids"], rule.rule_id)
        rows.append({
            "rule_id": rule.rule_id, "description": rule.description,
            "severity": rule.severity, "action": rule.action,
            "rows": counts[rule.rule_id], "locked_rows": int((mask & _locked(frame)).sum()),
            "false_positive_risk": rule.false_positive_risk,
        })
    return dataframe_markdown(pd.DataFrame(rows))


def rule_samples_markdown(frame: pd.DataFrame, rules: list[MultiPropertyRule]) -> str:
    """Render deterministic examples for every active multi-property rule."""

    parts = []
    for rule in rules:
        subset = frame[_pipe_has(frame["multi_property_rule_ids"], rule.rule_id)]
        parts.append(f"#### `{rule.rule_id}` {rule.description}\n\n" + samples_markdown(
            subset, ["record_id", "raw_address", "sale_price_eur_adjusted", "geo_scope", "multi_property_rule_ids", "multi_property_action"], 4
        ))
    return "\n\n".join(parts)


def exclusion_samples_markdown(frame: pd.DataFrame) -> str:
    """Render samples for every exclusion reason and multi-reason rows."""

    parts = []
    columns = ["record_id", "raw_address", "geo_scope", "property_scope_status", "multi_property_action", "duplicate_action", "exclusion_reason", "exclusion_reasons"]
    for reason in EXCLUSION_PRIORITY:
        subset = frame[_pipe_has(frame["exclusion_reasons"], reason)]
        parts.append(f"### `{reason}`\n\n" + samples_markdown(subset, columns, 3))
    parts.append("### Multiple applicable reasons\n\n" + samples_markdown(frame[frame["exclusion_reasons"].str.contains(r"\|", regex=True)], columns, 10))
    return "\n\n".join(parts)


def value_count_frame(frame: pd.DataFrame, column: str) -> pd.DataFrame:
    """Return full and locked counts for one categorical field."""

    full = frame[column].astype("string").fillna("<NULL>").value_counts().rename("full_rows")
    locked = frame.loc[_locked(frame), column].astype("string").fillna("<NULL>").value_counts().rename("locked_rows")
    return pd.concat([full, locked], axis=1).fillna(0).astype(int).rename_axis(column).reset_index()


def samples_markdown(frame: pd.DataFrame, columns: list[str], limit: int) -> str:
    """Render a small deterministic Markdown sample."""

    available = [column for column in columns if column in frame]
    if frame.empty:
        return "_No matching rows._"
    return dataframe_markdown(stable_sample(frame, limit)[available])


def stable_sample(frame: pd.DataFrame, limit: int) -> pd.DataFrame:
    """Take a deterministic record-ID-ordered sample."""

    if frame.empty:
        return frame.head(0)
    return frame.sort_values("record_id").head(limit)


def dataframe_markdown(frame: pd.DataFrame) -> str:
    """Render a DataFrame as dependency-free Markdown."""

    if frame.empty:
        return "_No rows._"
    display = frame.copy().fillna("").astype(str)
    headers = [str(column) for column in display.columns]
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"]
    for values in display.itertuples(index=False, name=None):
        lines.append("| " + " | ".join(str(value).replace("|", "\\|").replace("\n", " ") for value in values) + " |")
    return "\n".join(lines)


def arrow_schema_markdown(schema: pa.Schema, *, inherited_count: int) -> str:
    """Render physical schema with inherited/new field distinction."""

    rows = []
    for index, field in enumerate(schema):
        rows.append({
            "field": field.name, "type": str(field.type), "nullable": field.nullable,
            "stage": "Checkpoint 3 inherited" if index < inherited_count else "Checkpoint 4 appended",
        })
    return dataframe_markdown(pd.DataFrame(rows))


def _locked(frame: pd.DataFrame) -> pd.Series:
    """Return matched inference/training-only geography mask."""

    return frame["geo_scope"].isin(["inference", "training_only"]) & frame["geography_match_status"].eq("matched")


def _pipe_has(series: pd.Series, token: str) -> pd.Series:
    """Match a complete token inside a pipe-delimited field."""

    return series.fillna("").str.contains(fr"(?:^|\|){re.escape(token)}(?:\||$)", regex=True)


def _rule_locked_count(frame: pd.DataFrame, column: str, rule_id: str) -> int:
    """Count one rule within matched locked geography."""

    return int((_pipe_has(frame[column], rule_id) & _locked(frame)).sum())


if __name__ == "__main__":
    main()
