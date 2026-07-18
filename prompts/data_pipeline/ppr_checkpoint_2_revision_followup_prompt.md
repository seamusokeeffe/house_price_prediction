# Codex Follow-up — Revise PPR Checkpoint 2 Before Checkpoint 3

Revise the existing Checkpoint 2 implementation only. Do not begin address normalisation, geography mapping, property-scope classification, multi-property detection, duplicate resolution, training exclusions, or baseline output creation.

Use the current files, including:

- `src/house_valuation/data/ppr_ingestion.py`
- `scripts/build_ppr_checkpoint_2.py`
- `tests/data/test_ppr_ingestion.py`
- `docs/data/dataset_schema.md`
- `artifacts/data_quality/20260621/ppr_checkpoint_2_report.md`
- `data/interim/ppr/20260621/ppr_source_standardised.parquet`

Preserve the accepted Checkpoint 2 decisions and existing output semantics.

## Required revisions

### 1. Make row reconciliation independent

The current report derives both input and output row counts from the transformed dataframe.

Capture the raw source row count before transformation and report separately:

- raw rows read;
- transformed rows emitted;
- difference;
- reconciliation status.

Add an explicit assertion that no rows were lost or added during Checkpoint 2.

### 2. Make raw-record fingerprints canonical

The current raw fingerprint depends on source-column order.

Calculate `raw_record_fingerprint` from deterministic column-name/value pairs so that the same raw logical row receives the same fingerprint even when source columns are reordered.

Preserve distinctions between genuinely different raw values. Do not include source row number in the fingerprint.

Add a test proving that reordered source columns produce the same raw fingerprint.

### 3. Detect preserved raw-column name collisions

Before creating `source_raw__...` columns, detect whether two source column names normalise to the same output name.

Fail explicitly with a clear schema error if a collision occurs.

Add a unit test using two distinct source headings that normalise to the same preserved name.

### 4. Move VAT rate into explicit configuration

Add the configured provisional house VAT rate to an explicit configuration object used by the transformation, defaulting to:

`Decimal("0.135")`

Do not introduce apartment VAT rates or effective-date logic.

The report must display the configured rate actually used.

### 5. Enforce and validate the physical output schema

Do not rely only on inferred Pandas `object` dtypes.

Before writing, explicitly enforce the documented Checkpoint 2 schema, including:

- dates;
- integers;
- nullable booleans;
- strings;
- `decimal(18,2)` price fields;
- `decimal(5,3)` VAT rate;
- nullable floating-point `floor_area_sqm`, even though it is entirely null.

After writing the Parquet:

1. read it back;
2. verify the row count;
3. inspect its PyArrow schema;
4. validate the fields against `docs/data/dataset_schema.md`;
5. fail the build if the physical schema does not conform.

Include the actual PyArrow schema or a concise field/type table in the report.

Do not change the meaning of any existing fields.

### 6. Make report generation reproducible

The supplied `ppr_checkpoint_2_report.md` contains actual test output, but the supplied build script only emits an instruction to run tests.

Make the checked-in/generated report reproducible from documented commands.

Choose one clear approach:

- have the checkpoint build command execute the relevant tests and capture their output; or
- have a documented orchestration command run tests first and pass the captured output into the report generator.

Do not manually edit generated evidence after the build.

Report:

- exact command;
- exit status;
- test count;
- complete captured test output path.

Use the configured snapshot date and encoding in report titles and metadata rather than hardcoding `20260621` and `cp1252` inside report-generation logic.

### 7. Clarify duplicate metrics

Report separately:

- duplicate `record_id` count;
- number of raw-fingerprint groups with more than one row;
- total rows participating in duplicate groups;
- repeated fingerprint occurrences beyond the first.

Select a representative duplicate pair by choosing one fingerprint group and showing at least two records from that same group.

Do not remove duplicates.

### 8. Review speculative property-description mappings

The implementation currently includes exact mappings for:

- `Teach/Ã\x81rasÃ¡n CÃ³naithe AthÃ¡imhe`
- `Teach/Ã\x81rasÃ¡n CÃ³naithe Nua`

These were not reported among the observed source values and were not part of the confirmed three Irish/mojibake mappings.

Either:

- remove them from active mapping; or
- document their provenance and place them in an explicit reviewed mapping configuration as unobserved compatibility variants.

Do not silently retain speculative text corrections.

Keep the confirmed observed mappings unchanged.

### 9. Expand test coverage

Add or strengthen tests for:

- missing date;
- missing price;
- full ingestion with required columns reordered;
- full ingestion with an unexpected additional column;
- raw field preservation for each confirmed Irish/mojibake description;
- raw versus adjusted price preservation;
- a genuine half-cent VAT result proving `ROUND_HALF_UP`, for example a value whose unrounded adjusted amount ends exactly in half a cent;
- configurable VAT rate use;
- source-column-order-invariant fingerprints;
- preserved raw-column-name collisions;
- explicit nullable dtype/schema enforcement;
- Parquet write/read-back row count;
- Parquet physical schema validation.

Retain the existing tests.

Provide a requirements-to-test summary showing coverage of the scenarios requested in the original Checkpoint 2 prompt. Multiple scenarios may be covered by one test, but this must be explicit.

### 10. Support baseline findings with evidence

Do not change baseline behaviour.

Add file/function references and, preferably, a focused synthetic test proving:

- `property_type = unknown` is accepted under the relevant default;
- area fallback can support the planned area-only smoke test;
- no allow-listed detailed type is required for that path.

If this cannot be tested without changing unrelated code, document the exact inspected files and functions instead.

## Acceptance criteria

Checkpoint 2 may be approved when:

- raw and output row counts are independently reconciled;
- raw fingerprints are invariant to source-column ordering;
- raw-column collisions are detected;
- the VAT rate is explicit configuration;
- the written Parquet conforms to the documented physical schema;
- the Parquet is read back and validated;
- the report is reproducibly generated by the supplied code and commands;
- duplicate metrics are unambiguous;
- speculative mappings are removed or documented;
- expanded tests pass;
- all Checkpoint 2 counts are regenerated;
- no later-checkpoint transformations or exclusions have been introduced.

Regenerate:

- `ppr_source_standardised.parquet`
- `ppr_source_raw_column_map.json`
- `ppr_checkpoint_2_report.md`
- `test_output.txt`

Report all changed files, commands, test results, revised counts, schema-validation results, and any deviations.

Stop after the revised Checkpoint 2.
