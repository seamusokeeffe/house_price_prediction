# Codex Prompt - Implement PPR Data Pipeline Checkpoint 5

Act as a senior data engineer and ML validation specialist working inside the existing South Dublin House Valuation Tool repository.

Implement **Checkpoint 5 only** from:

```text
prompts/data_pipeline/ppr_data_pipeline_handoff_prompt.md
```

Checkpoint 5 is the publication and smoke-test checkpoint. It must:

1. publish versioned final processed outputs from the approved Checkpoint 4 assessment;
2. produce a baseline-compatible CSV without weakening the approved exclusions;
3. validate the final data contract and row reconciliation;
4. run the existing grouped-median baseline as a smoke test;
5. run the existing temporal validation as a smoke test;
6. capture reproducible data-quality, test, and model-run evidence;
7. document limitations, operational instructions, and the next enrichment steps.

Use this as the only transformation input:

```text
data/interim/ppr/20260621/ppr_cleaning_assessed.parquet
```

Treat Checkpoints 1-4 as approved unless a genuine blocking defect is demonstrated with evidence. Do not reopen their business rules merely to make the baseline metrics look better.

Stop after Checkpoint 5. Do not tune or replace the model, implement enrichment, broaden geography, scrape listings, build a UI, or begin deployment work.

---

## 1. Working relationship and collaboration protocol

This is a collaborative implementation task. You are not required to complete it zero-shot.

Before making a decision that materially changes the published dataset contract, installed dependencies, model artifacts, or interpretation of an upstream field:

1. inspect the current repository and generated evidence;
2. show the user the relevant facts, counts, paths, and trade-offs;
3. recommend a default in plain language;
4. ask a focused question when the user's answer would materially improve or change the output;
5. wait for the user's answer when proceeding would create an unsafe or hard-to-reverse contract.

Do not stop for routine, reversible engineering choices. Make those choices, state the assumption, explain the rationale, and continue.

At minimum, explicitly surface the following choices before publication unless durable project documentation already resolves them:

- whether the final processed Parquet is the row-preserving, audit-complete dataset and the baseline CSV is an included-record-only view;
- the exact published filenames and dataset version, with `20260621` as the recommended version because it is the source snapshot used by all prior checkpoints;
- where the smoke-test model artifact should be written, with a versioned Checkpoint 5 artifact directory recommended to avoid silently overwriting an existing model;
- whether any existing baseline or validation code truly needs modification for compatibility. Prefer adapting the published CSV to the existing contract over changing model behaviour.

Recommended output contract, subject to the user's review:

- publish a row-preserving final processed Parquet containing all 790,415 assessed rows, all inherited fields, the final modelling target alias, dataset-version metadata, and inclusion/exclusion evidence;
- publish an included-record-only baseline CSV containing exactly the records for which `exclude_from_training == False` and the columns required to reproduce and audit baseline input;
- retain excluded rows in the processed Parquet and existing/final audit outputs, never in the training view;
- set `sale_price_eur` from `sale_price_eur_adjusted` without overwriting or renaming the raw and adjusted price fields;
- validate log-price finiteness during publication, but do not persist a redundant `log_sale_price` column unless a documented consumer requires it, because the current filter creates it at runtime;
- retain `property_type = unknown` under the approved Checkpoint 4 policy and report that this makes the current smoke test primarily an area-level baseline.

If the user delegates one of these choices, select the smallest, most auditable, low-maintenance option and record why.

When communicating during implementation:

- explain every material data-contract, architecture, and code-style decision;
- distinguish observed evidence, inherited decisions, assumptions, and recommendations;
- before or immediately after a major code addition, give a concise explanation of its structure and why that style was chosen;
- after writing code, summarize what it does in plain language so the user can build an intuition for how records move through it;
- report actual counts and test results only after commands have run;
- never invent a successful command, metric, checksum, or artifact.

Before major changes, recommend a Git checkpoint. Do not create commits unless the user asks.

---

## 2. Sources of truth and required inspection

Read `AGENTS.md` first and follow all locked decisions and repository conventions.

Inspect at least:

```text
prompts/data_pipeline/ppr_data_pipeline_handoff_prompt.md
prompts/data_pipeline/ppr_checkpoint_3_codex_prompt.md
prompts/data_pipeline/ppr_checkpoint_4_codex_prompt.md
planning/data/ppr_checkpoint_1_implementation_plan.md
planning/decision_log.md
planning/roadmap.md
planning/specialist_handoffs.md
docs/data/dataset_schema.md
docs/data/data_cleaning_rules.md
docs/data/raw_to_processed_workflow.md
docs/implementation/how_to_run_baseline.md
docs/implementation/mvp_code_structure.md
artifacts/data_quality/20260621/ppr_checkpoint_2_report.md
artifacts/data_quality/20260621/ppr_checkpoint_3_report.md
artifacts/data_quality/20260621/ppr_checkpoint_4_report.md
artifacts/data_quality/20260621/test_output_checkpoint_4.txt
config/canonical_areas.csv
config/address_overrides.csv
config/multi_property_rules.csv
src/house_valuation/config.py
src/house_valuation/data/loaders.py
src/house_valuation/data/filters.py
src/house_valuation/data/ppr_ingestion.py
src/house_valuation/data/address_normalization.py
src/house_valuation/data/geography_mapping.py
src/house_valuation/data/multi_property.py
src/house_valuation/data/property_scope.py
src/house_valuation/data/duplicate_detection.py
src/house_valuation/data/cleaning.py
src/house_valuation/features/build_features.py
src/house_valuation/models/baseline.py
src/house_valuation/evaluation/validation.py
scripts/build_ppr_checkpoint_2.py
scripts/build_ppr_checkpoint_3.py
scripts/build_ppr_checkpoint_4.py
scripts/train_baseline.py
scripts/run_validation.py
tests/
```

Prefer extending existing modules and conventions. Do not duplicate checksum, report, schema, Parquet, or audit helpers when a focused extension is clearer. Preserve unrelated user changes in the dirty worktree.

---

## 3. Approved Checkpoint 4 state

Verify these values from the actual input and report before relying on them:

- input/output rows at Checkpoint 4: 790,415;
- duplicate `record_id` values: 0;
- Checkpoint 4 output SHA256: `d10dc60f1aa25ba5c8ebddb8466eff48b7cd3e0a6ced8e933e780aae58d31526`;
- included records: 51,045;
- excluded records: 739,370;
- included review-flagged records: 147;
- matched locked-geography records: 58,063;
- excluded within matched locked geography: 7,018;
- suspected multi-property records: 2,422;
- multi-property auto-exclusions: 713 total and 47 within locked geography;
- exact duplicate occurrences auto-excluded: 1,062, with one deterministic representative retained per group;
- unresolved house-or-apartment status is retained under the approved policy;
- explicit apartment/flat evidence is outside house scope;
- `property_type` remains conservative and may be `unknown`;
- VAT-exclusive and new-build status alone never exclude;
- out-of-scope, unmatched, and ambiguous geography exclude from training;
- price alone is neither capped nor used as an exclusion rule;
- `Dun Laoghaire` accent garbling noted previously was a terminal-rendering issue, not a stored/configuration defect.

Checkpoint 4 produced 81 fields and preserved all upstream values. Its output is `cleaning-assessed`, not yet final processed or model-ready.

Do not overwrite or mutate:

```text
data/interim/ppr/20260621/ppr_source_standardised.parquet
data/interim/ppr/20260621/ppr_geography_enriched.parquet
data/interim/ppr/20260621/ppr_cleaning_assessed.parquet
```

Do not recompute Checkpoint 4 classifications in a separate implementation. Publish the approved assessment fields as they exist.

---

## 4. Inherited evidence discrepancy to resolve first

There is a test-evidence inconsistency that must be verified before final publication:

- `ppr_checkpoint_4_report.md` records exit status `0` and 58 tests;
- the currently referenced `test_output_checkpoint_4.txt` contains only `No module named unittest` and has a later modification time than the report;
- direct import of Python's standard-library `unittest` succeeded when this Checkpoint 5 prompt was prepared.

Treat this as likely overwritten/stale evidence, not automatically as a Checkpoint 4 logic failure. Run the complete current test suite with the project interpreter before implementing publication logic. Capture fresh Checkpoint 5 test evidence in a new file. Do not silently edit or overwrite the Checkpoint 4 report or its historical artifact.

If the suite fails:

1. identify whether the failure is an environment/invocation issue, an inherited defect, or caused by Checkpoint 5 work;
2. explain the evidence and impact to the user;
3. fix only an in-scope defect needed to complete Checkpoint 5;
4. ask before changing an approved upstream business rule.

---

## 5. Checkpoint boundary and publication layout

Use a versioned layout consistent with the handoff, preferably:

```text
data/processed/dataset_version=20260621/
    ppr_processed_transactions.parquet
    processed_transactions.csv
    dataset_manifest.json

artifacts/data_quality/20260621/
    ppr_checkpoint_5_report.md
    checkpoint_5_row_reconciliation.csv
    checkpoint_5_quality_summary.csv
    checkpoint_5_schema.json
    test_output_checkpoint_5.txt
    baseline_train_output_checkpoint_5.txt
    baseline_validation_checkpoint_5.json

artifacts/models/ppr/20260621/baseline_smoke_test/
    grouped_median_baseline.pkl
```

Equivalent names are acceptable if existing conventions clearly require them. Do not replace prior checkpoint reports or model artifacts.

The recommended status distinction is:

- final processed Parquet: `final-processed`, row-preserving and audit-complete;
- baseline CSV: `baseline-compatible`, included-record-only training view;
- model and validation results: `smoke-test`, not a production or accepted performance benchmark.

DuckDB is deliberately out of scope for Checkpoint 5. The current dataset size does not justify an additional database dependency or publication layer. Use Parquet as the canonical analytical output and CSV as the baseline interchange format. Do not revisit this decision unless the user explicitly changes it.

Publish files safely: write to a temporary sibling path where practical, validate them, and then replace only the exact intended final target. Do not use broad destructive operations.

---

## 6. Final processed Parquet contract

Create the final processed Parquet directly from the Checkpoint 4 table.

It must:

- contain exactly one row for every Checkpoint 4 row;
- preserve every Checkpoint 4 field, value, type, null, and row order unless an explicitly approved final field is appended;
- preserve `record_id` uniqueness;
- retain all raw, interim, assessment, quality, and exclusion fields;
- append `sale_price_eur` as the final modelling-price alias of `sale_price_eur_adjusted`;
- never overwrite `sale_price_eur_raw`, `sale_price_eur_adjusted`, or `sale_price_adjustment_method`;
- append an explicit dataset version and publication/status field if this is consistent with the chosen schema design;
- use an explicit PyArrow schema rather than Pandas `object` inference;
- retain decimal monetary semantics in Parquet;
- store useful schema metadata, including dataset version, source snapshot date, schema version, publication timestamp policy, and source/input checksum, without introducing non-deterministic content into the data file unless deliberately documented;
- pass write/read-back validation;
- be deterministic for identical input, code, configuration, and metadata policy.

If publication timestamps would make repeat checksums vary, keep them in the manifest rather than embedding them in the Parquet, or explain another deterministic design.

The all-record Parquet may contain excluded rows because it is the auditable processed dataset. It must not be described as a training-only view.

---

## 7. Baseline-compatible CSV contract

Create the CSV as an explicit projection of the approved included rows, not by re-running or duplicating cleaning rules.

Recommended selection:

```text
exclude_from_training == False
```

The CSV must include at least:

```text
record_id
transaction_date
sale_price_eur
canonical_area
geo_scope
property_type
exclude_from_training
```

Also retain enough traceability to understand the current coarse target and flags without making the file needlessly huge. Consider including:

```text
source_snapshot_date
sale_price_eur_raw
sale_price_eur_adjusted
sale_price_adjustment_method
is_full_market_price
vat_exclusive_flag
vat_rate_applied
is_new_build
property_type_source
property_type_quality_flag
property_scope_status
is_possible_multi_property_sale
multi_property_action
duplicate_status
duplicate_action
quality_flags
cleaning_assessment_status
```

Discuss the exact compact projection with the user if it would materially affect usability. The baseline itself requires only the current contract, but traceability is valuable for a personal decision-support tool.

CSV publication must be deterministic and clearly specify:

- UTF-8 encoding, preferably `utf-8-sig` if retaining compatibility with the current loader;
- ISO `YYYY-MM-DD` transaction dates;
- stable source order unless a documented deterministic sort is approved;
- two-decimal price serialization without scientific notation;
- a consistent boolean representation accepted by the loader;
- a header even if a test fixture produces zero rows;
- no index column;
- no excluded rows;
- no null canonical areas;
- only `inference` and `training_only` geography scopes;
- positive modelling prices;
- `property_type` values allowed by the existing filter, including approved `unknown`.

Do not fabricate detailed house type to improve the grouped baseline. Report the `unknown` coverage and expected backoff behaviour.

---

## 8. Dataset manifest and reproducibility

Create a machine-readable manifest for the published dataset. Include at least:

- dataset version;
- schema version;
- source name and snapshot date;
- Checkpoint 4 input path and SHA256;
- output paths, sizes, SHA256 values, row counts, and column counts;
- included and excluded counts;
- final target derivation (`sale_price_eur = sale_price_eur_adjusted`);
- CSV projection and serialization policy;
- code/script entry point;
- relevant configuration checksums;
- Python and key library versions;
- test command and result;
- baseline and validation command parameters;
- canonical storage and interchange formats;
- known limitations.

Use deterministic JSON ordering and formatting. If the manifest contains a wall-clock generation time, exclude that value from any claim that repeated manifests are byte-identical, or use a documented deterministic acquisition/publication date.

Do not put secrets, machine-specific user paths, or unnecessary environment details in the manifest.

---

## 9. Final data-quality validation

Implement focused reusable validation, likely by creating or extending:

```text
src/house_valuation/data/quality_checks.py
src/house_valuation/data/writers.py
```

Use existing modules instead if equivalent functionality already exists after inspection.

Validate at least:

### All-record processed dataset

- input/output row count reconciliation;
- identical inherited field names, values, types, nulls, `record_id` sequence, and row order;
- unique field names and unique `record_id` values;
- explicit schema and nullability;
- `sale_price_eur` equality with `sale_price_eur_adjusted`, including null behaviour;
- valid dataset/schema version recording;
- successful Parquet read-back;
- output checksum and size;
- deterministic repeat output under the selected metadata policy.

### Baseline training view

- row count equals the number of Checkpoint 4 rows with `exclude_from_training == False`;
- record IDs are exactly the included-record IDs, once each and in the approved order;
- no excluded record appears;
- all required baseline columns exist;
- no missing or invalid transaction dates;
- no non-positive, missing, or non-finite modelling prices;
- `log(sale_price_eur)` is finite for every row;
- no missing canonical area;
- canonical areas are restricted to the exact locked list from `AGENTS.md` and configuration;
- geography scope is only `inference` or `training_only`;
- full-market-price status is valid and true for every included row;
- VAT-adjusted targets are traceable to raw price, rate, and adjustment method;
- no unresolved VAT treatment appears;
- no auto-excluding multi-property row appears;
- no auto-excluded duplicate occurrence appears;
- no clearly excluded property type appears;
- only supported house types or the approved `unknown` type appear;
- every included row has sufficient required fields;
- no price winsorisation, cap, hard high-price exclusion, or hard `>200m2` floor-area filter is introduced.

### Reconciliation and reporting

- all processed rows partition exactly into included and excluded sets;
- included plus excluded equals 790,415 unless the verified Checkpoint 4 input differs;
- baseline CSV count is expected to be 51,045 unless verification finds a legitimate input change;
- counts are reported by year, canonical area, geography scope, property type, property-type quality, full-market status, VAT status/method, new-build status, multi-property action, duplicate action, inclusion status, primary exclusion reason, and quality flag;
- final artifacts and prior checkpoint audit paths exist and are checksummed or linked from the report/manifest.

Fail clearly on contract violations. Do not silently drop bad rows during publication to make validation pass.

---

## 10. Baseline smoke test

After the final CSV passes validation, run the existing training command against it. Prefer the current interface:

```powershell
.venv\Scripts\python.exe scripts/train_baseline.py `
  --dataset data/processed/dataset_version=20260621/processed_transactions.csv `
  --artifacts-dir artifacts/models/ppr/20260621/baseline_smoke_test `
  --min-group-support 3
```

Adjust command syntax for the actual shell, and record the exact command executed.

The smoke test must:

- use the published CSV, not an in-memory frame or a separate ad hoc export;
- leave the grouped-median algorithm and backoff order unchanged unless a blocking compatibility defect is demonstrated;
- write to the approved versioned artifact directory;
- capture stdout, stderr, exit status, training row count, and output path;
- verify that the model artifact exists and can be loaded;
- record group coverage and relevant model state where straightforward;
- be described only as a pipeline compatibility check.

Do not tune `min_group_support`, add features, or compare models during this checkpoint.

If the current script cannot expose needed evidence without a small change, explain the proposed change and keep it generic, backwards-compatible, and limited to observability or output-path safety.

---

## 11. Temporal validation smoke test

Run the current temporal validation command against the same published CSV, initially using the documented 12-month holdout and minimum group support of 3:

```powershell
.venv\Scripts\python.exe scripts/run_validation.py `
  --dataset data/processed/dataset_version=20260621/processed_transactions.csv `
  --holdout-months 12 `
  --min-group-support 3
```

Capture structured results in:

```text
artifacts/data_quality/20260621/baseline_validation_checkpoint_5.json
```

Record:

- exact command and exit status;
- dataset version and checksum;
- total usable rows;
- temporal cutoff date;
- train and validation date ranges;
- train and validation row counts;
- proof that the validation window is later than the training window;
- MAE in euro;
- median absolute percentage-style error;
- log MAE;
- backoff counts and percentages;
- area and property-type coverage in train and validation;
- unknown property-type coverage;
- any unseen-area or fallback behaviour;
- relevant warnings or limitations.

The existing command may not currently emit every requested diagnostic. Prefer adding reusable, backwards-compatible diagnostics to the validation result rather than scraping console text. Explain any such code change before or immediately after making it.

Do not claim the metrics demonstrate decision usefulness. The PPR still lacks reliable detailed house type, exact floor area, bedrooms, bathrooms, BER, condition, and precise property identity. Treat poor or deceptively good metrics as findings, not reasons to alter cleaning rules or tune the model.

---

## 12. Required implementation shape

Inspect before creating files. Likely deliverables are:

```text
src/house_valuation/data/writers.py
src/house_valuation/data/quality_checks.py
scripts/build_ppr_dataset.py
tests/data/test_writers.py
tests/data/test_quality_checks.py
tests/data/test_ppr_dataset_build.py
```

Use different or fewer files if the repository already contains suitable homes for the logic.

Keep the design layered:

1. pure functions define final-field derivation and validation;
2. writer functions serialize explicit schemas and stable projections;
3. the build script orchestrates input, validation, writes, checksums, tests, smoke commands, and report generation;
4. baseline/model code remains independent of PPR-specific publication details;
5. side effects stay at script/writer boundaries.

The Checkpoint 5 build should support explicit paths and safe defaults, for example:

```text
--input
--output-dir
--report-dir
--model-artifacts-dir
--dataset-version
--run-smoke-tests / --skip-smoke-tests
```

Do not make a misleading successful final report possible when required tests or smoke tests were skipped. A skip mode may support deterministic development reruns, but the final acceptance run must execute the required suite and smoke tests.

---

## 13. Required tests

Add focused unit and integration tests. Test names may cover several related requirements, but the generated report must map requirements to test evidence.

### Target derivation and final schema

1. `sale_price_eur` exactly mirrors adjusted price and preserves nulls;
2. raw and adjusted price fields are unchanged;
3. final fields have explicit PyArrow types and nullability;
4. dataset and schema versions are recorded;
5. inherited field names, values, types, nulls, order, and row order are preserved;
6. duplicate field names fail clearly;
7. duplicate or reordered `record_id` values fail clearly;
8. Parquet write/read-back preserves schema and rows;
9. deterministic repeated writes follow the documented metadata policy.

### Baseline CSV

10. only `exclude_from_training == False` rows are selected;
11. included record IDs exactly reconcile to Checkpoint 4;
12. required baseline columns exist;
13. transaction dates serialize as ISO dates;
14. decimal prices serialize to two decimal places;
15. UTF-8/loader compatibility works for accented Irish text;
16. booleans round-trip through the current loader/filter behaviour;
17. no CSV index column is written;
18. row order is deterministic;
19. unknown property type is retained under the approved policy;
20. excluded property types and auto-excluding transaction evidence cannot enter the CSV.

### Quality checks

21. missing/non-positive/non-finite target fails;
22. non-finite computed log target fails;
23. invalid or future transaction date fails according to the approved final contract;
24. missing/out-of-list canonical area fails;
25. out-of-scope/unknown geography cannot enter the training view;
26. false or unresolved full-market status cannot enter the training view;
27. VAT-adjusted rows are traceable and valid VAT/new-build rows remain eligible;
28. unresolved VAT treatment cannot enter the training view;
29. auto-excluding multi-property rows cannot enter the training view;
30. excluded duplicate occurrences cannot enter the training view;
31. all-record output partitions exactly into included and excluded records;
32. high price alone remains valid;
33. no hard floor-area-above-200m2 rule appears.

### Manifest and build integration

34. manifest paths, checksums, counts, and versions match written files;
35. manifest JSON is stable and machine-readable;
36. missing required artifacts fail clearly;
37. audit/report files are created, including header-only summaries when a category is empty;
38. a full-data build reconciles the 790,415 input rows and expected included rows;
39. the published CSV can be loaded by the existing loader and filtered without changing its record set;
40. the grouped baseline can fit and predict on a small representative final-contract fixture;
41. temporal validation uses a strictly later validation window with no row overlap;
42. the final report records real test and smoke-test results;
43. prior checkpoint outputs and reports are not overwritten.

Use small synthetic fixtures for rule and serialization behaviour. Use the full dataset for final integration, checksums, row reconciliation, and smoke-test evidence. Avoid tests coupled to incidental nationwide row order except where stable source order is itself the publication contract.

Run the complete repository suite, not only the new tests. Capture fresh output in `test_output_checkpoint_5.txt`.

---

## 14. Documentation and next steps

Update existing documents rather than creating near-duplicates.

At minimum, update as needed:

```text
docs/data/dataset_schema.md
docs/data/data_cleaning_rules.md
docs/data/raw_to_processed_workflow.md
docs/implementation/how_to_run_baseline.md
docs/implementation/mvp_code_structure.md
```

Document:

- the distinction between the row-preserving final processed dataset and included-only baseline view;
- target derivation and VAT traceability;
- physical schemas and paths;
- dataset/manifest versioning;
- exact reproducible build, test, train, and validation commands;
- Parquet as the canonical analytical format and CSV as the baseline interchange format;
- how to inspect excluded records and prior audit files;
- how unknown property type affects the grouped baseline and backoff interpretation;
- why smoke-test metrics are not evidence of a production-quality valuation model.

After the pipeline succeeds, create or update a short planning document such as:

```text
planning/data/enrichment_feasibility.md
```

Cover future feasibility and ordering for BER matching, exact floor area, dwelling type, BER rating, and geospatial enrichment. Keep this concise and separate. Do not implement record linkage or enrichment in Checkpoint 5.

Update `planning/decision_log.md` only for new material decisions approved during this checkpoint. Update `planning/specialist_handoffs.md` only for genuine cross-specialist dependencies or unresolved handoffs.

---

## 15. Engineering and code-quality standards

- Python only.
- Use type hints for every public function and meaningful internal boundary.
- Add **Google-style docstrings** to every new or materially modified module, class, function, and method.
- Include `Args`, `Returns`, and `Raises` sections whenever applicable; do not use a one-line docstring where those sections are needed.
- If existing code must be materially modified, bring that modified boundary up to the same docstring standard without performing unrelated cleanup.
- Keep transformations deterministic and side effects at script/writer boundaries.
- Use explicit schemas, typed structures, named constants, and focused pure functions where they improve clarity.
- Explain the choice of dataclasses or other abstractions if introduced.
- Preserve decimal price semantics through Parquet and deliberate decimal formatting through CSV.
- Prefer vectorized checks where readable; explain any necessary row-wise processing and its impact on roughly 790,000 rows.
- Use explicit exceptions with actionable messages for contract, schema, path, checksum, and smoke-test failures.
- Use stage-level logging with row counts and artifact paths.
- Keep artifact/report generation reproducible.
- Do not silently drop, overwrite, relabel, coerce, or repair records.
- Do not add excessive comments that restate syntax. Use docstrings and concise comments for business rules, invariants, serialization decisions, and non-obvious safety boundaries.
- Do not introduce a notebook-only implementation, fuzzy matching, opaque classifier, external API, or proprietary service.

For every code file created or materially changed, provide the user with a short intuition summary covering:

1. its responsibility;
2. its main inputs and outputs;
3. how it fits into the pipeline;
4. its major style/architecture choices and why they were made.

---

## 16. Prohibited behaviour in Checkpoint 5

Do not:

- transform from raw PPR or an earlier checkpoint instead of the approved Checkpoint 4 Parquet;
- overwrite any Checkpoint 2, 3, or 4 dataset or report;
- recalculate or weaken approved exclusions;
- drop excluded records from the audit-complete processed Parquet;
- allow excluded records into the baseline CSV;
- fabricate detailed house types;
- infer house type from weak address heuristics;
- broaden or fuzzily remap geography;
- silently resolve ambiguous geography or review-only rules;
- mutate, cap, winsorise, or threshold prices merely to improve metrics;
- exclude expensive houses based on price alone;
- add a hard `>200m2` training filter;
- change the correct negative interpretation of `Not Full Market Price`;
- exclude valid VAT-exclusive or new-build rows solely for that status;
- introduce a database publication layer or unnecessary storage dependency;
- overwrite an existing unversioned model artifact silently;
- tune the model, try alternative models, engineer new predictive features, or optimize metrics;
- implement BER/geospatial/listing enrichment;
- implement Daft scraping, text/image modelling, UI, deployment, or automated retraining;
- claim a smoke test establishes model usefulness;
- claim success if required publication validation, tests, baseline training, or temporal validation did not run successfully;
- invent or manually edit generated evidence after the build.

---

## 17. Acceptance criteria

Checkpoint 5 is complete when:

1. The approved Checkpoint 4 Parquet is the only transformation input.
2. The inherited test-evidence discrepancy is investigated and a fresh full test run is captured.
3. A versioned, row-preserving final processed Parquet is published.
4. Every Checkpoint 4 row and field is preserved exactly, with only approved final fields appended.
5. `sale_price_eur` is traceably derived from `sale_price_eur_adjusted` without overwriting raw/adjusted values.
6. The final Parquet has an explicit schema and passes read-back, reconciliation, checksum, and determinism checks.
7. A deterministic baseline-compatible CSV is published from exactly the approved included rows.
8. The CSV contains no excluded, invalid-target, invalid-date, non-full-market, unresolved-geography, excluded-property-type, auto-excluding multi-property, excluded-duplicate, or unresolved-VAT records.
9. Canonical area and geography scope are restricted to locked training geography.
10. Unknown property type is handled according to the approved conservative policy and its coverage is reported.
11. A machine-readable dataset manifest records versions, paths, checksums, schemas, counts, commands, dependency decisions, and limitations.
12. Processed, included, and excluded row counts reconcile exactly.
13. Required quality summaries and a reproducible Checkpoint 5 report are produced.
14. The complete repository test suite passes and fresh output is captured.
15. The existing grouped-median baseline trains successfully from the published CSV.
16. Its model artifact is written and validated without silently overwriting an unrelated artifact.
17. Existing temporal validation runs successfully on the same CSV with a 12-month holdout.
18. Validation metrics, date ranges, row counts, property-type coverage, and backoff counts are captured.
19. Baseline results are explicitly labelled as a smoke test rather than model acceptance.
20. Durable data and run documentation is updated without duplicate specs.
21. Limitations and a concise enrichment feasibility/next-step plan are documented without implementing enrichment.
22. All new or materially modified code has type hints and Google-style docstrings.
23. Major decisions and code-style choices are explained to the user.
24. The user receives an intuitive file-by-file code summary.
25. No model tuning, geography broadening, upstream-rule revision, UI, deployment, or unrelated enrichment is introduced.

---

## 18. Required Checkpoint 5 report

Generate `ppr_checkpoint_5_report.md` reproducibly from the build, rather than hand-editing observed results into it.

Include:

### Publication and reconciliation

- input and output paths, sizes, checksums, row counts, and column counts;
- dataset and schema versions;
- input/output row difference;
- inherited-field preservation result;
- duplicate `record_id` count;
- processed, included, and excluded counts;
- target derivation and equality result;
- Parquet and CSV read-back results;
- physical schema and CSV projection;
- determinism result;
- manifest path and checksum.

### Final data quality

- counts and percentages by year, area, geo scope, property type, property-type quality, full-market status, VAT status/method, new-build status, multi-property action, duplicate action, inclusion status, exclusion reason, and quality flag;
- final required-field completeness;
- VAT traceability checks;
- finite log-target result;
- locked-geography validation;
- unknown property-type coverage;
- review-flagged included count;
- paths to prior and final audit outputs;
- any difference from the verified Checkpoint 4 expected counts.

### Test and smoke-test evidence

- fresh full-suite command, exit status, test count, and captured output path;
- requirements-to-test matrix;
- baseline training command, parameters, exit status, row count, and artifact path;
- temporal validation command, parameters, exit status, cutoff/date ranges, train/validation counts, metrics, and backoff counts;
- explicit statement that results are a compatibility smoke test only.

### Decisions, limitations, and follow-up

- user decisions and delegated choices;
- major implementation and code-style choices with rationale;
- deviations from this prompt;
- inherited defects or evidence discrepancies;
- known PPR and baseline limitations;
- recommended next enrichment step and handoff.

---

## 19. End-of-checkpoint response

Lead with whether Checkpoint 5 passed its acceptance criteria. Then report:

1. files created or updated;
2. a plain-language, file-by-file intuition summary of every code file created or materially changed;
3. major data-contract, architecture, and code-style decisions and why they were made;
4. user decisions, delegated choices, and assumptions;
5. exact commands run;
6. full test result and captured evidence path;
7. final processed, included, and excluded row reconciliation;
8. schema, read-back, target equality, and determinism results;
9. published dataset, manifest, and audit paths with checksums;
10. baseline training result and model artifact path;
11. temporal split dates and row counts;
12. validation metrics and baseline backoff counts;
13. area and property-type coverage, especially `unknown` type;
14. VAT, new-build, multi-property, duplicate, and review-flagged counts;
15. evidence discrepancy resolution;
16. documentation updates;
17. deviations and known limitations;
18. open questions or follow-ups;
19. the recommended next enrichment task.

Stop after Checkpoint 5.
