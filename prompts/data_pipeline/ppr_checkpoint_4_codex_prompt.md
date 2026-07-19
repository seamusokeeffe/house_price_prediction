# Codex Prompt — Implement PPR Data Pipeline Checkpoint 4

Act as a senior data engineer and ML data-quality specialist working inside the existing South Dublin House Valuation Tool repository.

Implement **Checkpoint 4 only** from:

```text
prompts/data_pipeline/ppr_data_pipeline_handoff_prompt.md
```

Checkpoint 4 covers:

1. evidence-led, transparent multi-property transaction detection;
2. conservative property-scope assessment needed for cleaning;
3. duplicate-like transaction assessment;
4. deterministic cleaning and training-exclusion decisions;
5. quality and audit outputs;
6. tests and a reproducible Checkpoint 4 report.

Use the approved Checkpoint 3 output as the input:

```text
data/interim/ppr/20260621/ppr_geography_enriched.parquet
```

Stop after Checkpoint 4. Do not produce the final processed dataset, DuckDB output, baseline-compatible CSV, baseline smoke test, temporal validation, model changes, enrichment, or Checkpoint 5 deliverables.

---

## 1. Working relationship and collaboration protocol

This is a collaborative implementation task. Do not assume that the entire checkpoint must be completed zero-shot.

Before making material cleaning or auto-exclusion decisions:

1. inspect the repository, current data, and prior checkpoint evidence;
2. show the user the relevant counts and representative examples;
3. explain the available options and your recommended default in plain language;
4. ask focused questions when the answer would materially change which records are excluded or how they are classified;
5. wait for the user's response when the decision cannot be made safely from existing locked decisions and evidence.

Do not interrupt progress for routine, reversible engineering choices. Make those choices, explain them, and continue.

At minimum, explicitly surface these policy choices before activating consequential rules unless an existing durable decision already resolves them:

- which high-precision multi-property rules automatically exclude and which only flag for review;
- whether exact source duplicates should keep one deterministic representative and exclude the other occurrences, or remain review-only in Checkpoint 4;
- whether unresolved PPR house-versus-apartment records may remain eligible with `property_type = unknown`, or must be excluded until enrichment/manual review;
- how to treat suspected multi-property rows that have only medium-strength evidence;
- the deterministic priority used when a row has several exclusion reasons.

If the user delegates a choice to you, select the conservative, auditable option and record the rationale.

When communicating during implementation:

- explain major decisions and major code-style or architecture choices;
- explain why a rule is high precision, review-only, or unsafe;
- after writing code, give a concise, intuitive summary of what the code does and how data moves through it;
- distinguish observed evidence from assumptions and recommendations;
- do not present generated counts as facts until the pipeline has actually run.

Before major changes, recommend a Git checkpoint. Do not create commits unless the user asks you to.

---

## 2. Sources of truth and files to inspect

Read `AGENTS.md` first and follow all locked project decisions.

Inspect at least:

```text
prompts/data_pipeline/ppr_data_pipeline_handoff_prompt.md
prompts/data_pipeline/ppr_checkpoint_3_codex_prompt.md
planning/data/ppr_checkpoint_1_implementation_plan.md
planning/decision_log.md
planning/roadmap.md
planning/specialist_handoffs.md              # if present
docs/data/dataset_schema.md
docs/data/data_cleaning_rules.md
docs/data/raw_to_processed_workflow.md
artifacts/data_quality/20260621/ppr_checkpoint_2_report.md
artifacts/data_quality/20260621/ppr_checkpoint_3_report.md
config/canonical_areas.csv
config/address_overrides.csv
src/house_valuation/data/ppr_ingestion.py
src/house_valuation/data/address_normalization.py
src/house_valuation/data/geography_mapping.py
scripts/build_ppr_checkpoint_2.py
scripts/build_ppr_checkpoint_3.py
tests/data/test_ppr_ingestion.py
tests/data/test_address_normalization.py
tests/data/test_geography_mapping.py
```

Also inspect the current baseline loaders and filters to understand future compatibility, but do not change baseline behaviour in this checkpoint.

Prefer extending existing modules and patterns. Do not create parallel implementations of ingestion, address normalisation, geography mapping, schema conversion, test capture, checksum generation, or report helpers.

Preserve unrelated user changes in the worktree.

---

## 3. Approved input state and inherited evidence

Treat Checkpoints 1–3 as approved unless a genuine blocking defect is found.

The Checkpoint 3 report currently records:

- 790,415 input and output rows;
- zero row difference;
- zero duplicate `record_id` values;
- all Checkpoint 2 fields preserved;
- 58,063 matched geography rows;
- 727,086 unmatched geography rows;
- 5,265 ambiguous geography rows;
- one invalid address;
- 538,240 confidently out-of-scope rows;
- 194,112 rows with unknown geography scope;
- 30,190 inference-scope matches;
- 27,873 training-only matches;
- no manual geography overrides;
- no property-scope, duplicate, multi-property, or training-exclusion logic.

Regenerate or verify any count used to make a Checkpoint 4 decision. Do not rely solely on this summary.

Preserve every Checkpoint 3 row, column, and value unchanged. Checkpoint 4 must append assessment fields; it must not rewrite approved upstream values.

Do not overwrite:

```text
data/interim/ppr/20260621/ppr_source_standardised.parquet
data/interim/ppr/20260621/ppr_geography_enriched.parquet
```

---

## 4. Inherited issues to verify and surface

Monkstown is a locked **inference** geography. The root `AGENTS.md`, approved Checkpoint 3 prompt, and Checkpoint 3 output now agree on this decision. Preserve `Monkstown -> geo_scope = inference` and do not reopen it during Checkpoint 4.

Verify the following before using geography scope in exclusion logic:

1. The Checkpoint 3 report displays `DÃºn Laoghaire`. Determine whether this is only a console/report rendering problem or an actual stored/configured canonical value. Do not silently rewrite approved upstream data. If it is real and affects locked-area validation or exclusions, report the evidence and ask how the user wants the upstream correction handled.
2. The Checkpoint 3 report recommends review of high-volume aliases, ambiguous matches, county conflicts, and zero/low-coverage areas. Do not broaden or retune geography during Checkpoint 4. Carry unresolved geography states into explicit cleaning decisions and audits.

If an inherited issue is not blocking Checkpoint 4, document it as a follow-up rather than expanding this checkpoint.

---

## 5. Checkpoint boundary and output status

Checkpoint 4 creates a row-preserving, cleaning-assessed interim dataset. Use a status such as:

```text
cleaning-assessed
```

Do not label this output:

```text
final-processed
baseline-compatible
model-ready
house-only
```

The output may contain an `exclude_from_training` assessment, but Checkpoint 5 remains responsible for publishing final processed/training views and running the baseline smoke test.

A suitable versioned output path is:

```text
data/interim/ppr/20260621/ppr_cleaning_assessed.parquet
```

Use the existing snapshot/date configuration rather than scattering `20260621` through transformation logic.

---

## 6. Evidence pass before rule activation

Before implementing consequential rules, profile the full Checkpoint 3 data and create a concise evidence-led proposal.

At minimum, inspect counts and representative examples for:

- address ranges, including numeric ranges and unit ranges;
- semicolon-separated or obviously listed addresses;
- repeated apartment, flat, unit, house, block, lot, or property identifiers;
- multiple block/building references;
- explicit development phase, portfolio, block, scheme, lot, and bulk terminology;
- individual apartment/flat indicators;
- development terminology with and without an identifiable individual dwelling;
- extreme prices combined with non-individual address patterns;
- VAT-exclusive and new-build intersections with suspected multi-property patterns;
- raw-fingerprint duplicate groups;
- duplicate-like groups based on normalised address, transaction date, adjusted/raw price, and source status fields;
- same-day/same-price clusters with distinct addresses;
- missing or invalid target/date/status values;
- geography match state and scope;
- explicit apartment/flat signals versus unresolved house/apartment scope;
- overlap among proposed exclusion reasons.

For each proposed rule, show:

```text
rule_id
plain-language description
signal or matching logic
candidate row count
sample records
known false-positive risks
severity
recommended action: auto_exclude or review_only
```

Price must never be the sole multi-property or exclusion signal. Do not introduce a global maximum-price cutoff, hard outlier cutoff, or winsorisation in this checkpoint.

Where evidence is weak, keep the rule review-only or omit it.

---

## 7. Transparent multi-property rules engine

Implement a deterministic, inspectable rules engine for suspected multi-property transactions.

Prefer:

```text
src/house_valuation/data/multi_property.py
config/multi_property_rules.csv
tests/data/test_multi_property.py
```

Use equivalent existing files if they already exist.

Each active rule must have:

- a stable rule ID;
- a concise description;
- an explicit pattern or matching function;
- severity;
- action (`auto_exclude` or `review_only`);
- a rationale;
- tests covering matches and non-matches;
- an audit count;
- representative examples in the report.

The configuration should contain rule metadata and safely configurable patterns. Keep genuinely structural logic in named, tested Python functions rather than forcing complicated logic into opaque regular expressions or CSV expressions.

Begin with conservative, high-precision evidence. Candidate rule families include:

- explicit address or unit ranges combined with block/development/unit evidence;
- multiple clearly separate postal addresses in one source field;
- repeated unit/apartment identifiers;
- multiple named blocks/buildings;
- explicit portfolio, bulk, multiple-property, development-phase, or entire-block language;
- source evidence that other properties are included, if such a source field actually exists;
- extreme transaction value combined with a strong non-individual-address signal.

Do not assume that:

- every high-value sale is bulk;
- every comma means multiple properties;
- every hyphen denotes an address range;
- every development or estate name is multi-property;
- every new build or VAT-exclusive sale is multi-property;
- every occurrence of `UNIT` or a plural word proves multiple dwellings.

Create fields at least equivalent to:

```text
is_possible_multi_property_sale
multi_property_rule_ids
multi_property_reason
multi_property_max_severity
multi_property_action
single_dwelling_confidence
```

Use deterministic, documented enums. If `single_dwelling_confidence` is used, define what each level means; do not present it as a statistical probability.

When multiple rules hit one record, retain all rule IDs in a stable order and calculate the overall action deterministically.

---

## 8. Property-scope assessment

The PPR source description combines houses and apartments and cannot reliably provide the locked detailed house types.

Do not infer detached, semi-detached, terraced, end-of-terrace, bedroom count, or floor area from weak address text.

Implement only the conservative property-scope assessment required to support cleaning. Prefer fields such as:

```text
property_scope_status
property_scope_rule_ids
property_scope_reason
```

Suggested statuses are:

```text
clearly_non_house
unresolved_house_or_apartment
review_required
```

Do not label a row `house` merely because it lacks apartment keywords.

Explicit, token-bounded apartment/flat indicators may support `clearly_non_house` only after examples and false-positive risks are reviewed. Treat ambiguous abbreviations such as `APT`, `UNIT`, or building names carefully and test token boundaries.

Preserve the existing upstream fields:

```text
property_type = unknown
property_type_source = unknown
property_type_quality_flag = ppr_house_apartment_ambiguous
```

unless the user explicitly approves a documented Checkpoint 4 change. Do not fabricate detailed categories merely to satisfy a downstream interface.

Ask the user whether unresolved house/apartment records should remain eligible with quality flags or be excluded pending enrichment/manual review. Explain the coverage trade-off with actual counts before applying the decision.

---

## 9. Duplicate-like assessment

Implement deterministic duplicate-like grouping and auditing without silently dropping rows.

Prefer a focused module such as:

```text
src/house_valuation/data/duplicate_detection.py
```

or place narrowly scoped logic in `cleaning.py` if a separate module would be unnecessary. Explain the choice.

Use available evidence including:

- `raw_record_fingerprint` for exact logical source duplicates;
- normalised address;
- transaction date;
- raw and adjusted price;
- full-market-price status;
- VAT status;
- source property description;
- geography fields where relevant.

Separate at least:

```text
exact_source_duplicate
plausible_duplicate_publication
same_day_distinct_transaction
unresolved_duplicate_like
not_duplicate_like
```

Create fields at least equivalent to:

```text
duplicate_group_id
duplicate_group_size
duplicate_status
duplicate_rule_ids
duplicate_action
```

Group IDs must be deterministic and invariant to row order.

Do not automatically discard every repeated address, same-day sale, equal price, raw fingerprint, or clustered development transaction. Show evidence and obtain user input before making duplicate rules auto-excluding. If one representative is retained from an exact-duplicate group, make selection deterministic, retain all rows in the cleaning-assessed output, and explicitly mark the excluded occurrences.

---

## 10. Cleaning and exclusion engine

Prefer:

```text
src/house_valuation/data/cleaning.py
tests/data/test_cleaning.py
```

The engine must be deterministic, configuration-aware, auditable, and row preserving.

Every record must retain:

- all Checkpoint 3 fields and values;
- all relevant raw fields;
- combined quality flags;
- `exclude_from_training`;
- a stable primary `exclusion_reason` when excluded;
- all applicable exclusion reasons and rule IDs so information is not lost when several rules apply.

Recommended fields include:

```text
quality_flags
exclude_from_training
exclusion_reason
exclusion_reasons
exclusion_rule_ids
cleaning_assessment_status
```

Use a documented deterministic priority table to select the primary `exclusion_reason`. Preserve all reasons separately in stable order.

Assess at least:

- missing, invalid, zero, or negative target;
- missing, invalid, implausibly future, or unsupported transaction date where policy exists;
- `is_full_market_price = False`;
- missing or unrecognised full-market-price status;
- out-of-scope geography;
- unmatched/unknown geography;
- unresolved ambiguous geography;
- invalid address where it prevents required matching;
- clearly excluded property scope;
- suspected/confirmed multi-property transaction according to approved rule actions;
- duplicate-like transaction according to approved duplicate actions;
- invalid or unresolved VAT treatment;
- insufficient required fields.

Use stable exclusion reason values such as:

```text
invalid_target
invalid_date
non_full_market_transaction
unresolved_market_price_status
out_of_scope_geography
unmatched_geography_unresolved
ambiguous_geography_unresolved
excluded_property_type
multi_property_transaction
duplicate_unresolved
unresolved_vat_treatment
insufficient_required_fields
```

Reconcile these values with existing documentation rather than creating near-duplicates. If existing docs conflict with the safer PPR-specific wording, explain the proposed change before editing durable policy.

Important distinctions:

- VAT-exclusive status alone is not an exclusion reason when the price was validly adjusted.
- New-build status alone is not an exclusion reason.
- High or low price alone is not an exclusion reason unless an already-approved, evidence-based policy exists.
- Unknown detailed property type is not evidence of a house and is not automatically an error; its eligibility requires the explicit policy choice above.
- An unmatched nationwide record can be confidently out of scope or unresolved; retain the Checkpoint 3 distinction.
- An auto-excluded multi-property rule and a review-only suspicion must not be conflated.

Do not drop excluded rows from the Checkpoint 4 Parquet.

---

## 11. Schema and versioned output

Extend the documented schema before or alongside implementation. Do not rely on Pandas `object` inference for the physical output.

Implement an explicit PyArrow schema for all Checkpoint 4 fields. Validate:

- exact input/output row reconciliation;
- unchanged `record_id` values and order;
- unchanged values for every Checkpoint 3 column;
- unique field names;
- expected nullability and types;
- deterministic enum values;
- successful Parquet read-back;
- read-back row count;
- schema conformance;
- deterministic output across repeated transformations with identical input and configuration.

Write the versioned row-preserving interim output, for example:

```text
data/interim/ppr/20260621/ppr_cleaning_assessed.parquet
```

Do not create the final processed/training-only view in this checkpoint.

---

## 12. Required quality and audit outputs

Write versioned artifacts under:

```text
artifacts/data_quality/20260621/
```

At minimum, produce:

```text
ppr_checkpoint_4_report.md
checkpoint_4_rule_evidence.csv
suspected_multi_property_transactions.csv
multi_property_rule_summary.csv
duplicate_like_transactions.csv
duplicate_rule_summary.csv
property_scope_review.csv
excluded_records_checkpoint_4.csv
exclusion_reason_summary.csv
cleaning_quality_summary.csv
vat_treatment_review.csv
test_output_checkpoint_4.txt
```

Use clearer equivalent names if the repository already has a convention. Do not overwrite prior checkpoint reports or test output.

Audit files must retain enough source evidence for manual review, including where relevant:

```text
record_id
raw_address
address_normalized
county_raw
transaction_date
sale_price_eur_raw
sale_price_eur_adjusted
not_full_market_price_raw
is_full_market_price
vat_exclusive_raw
vat_exclusive_flag
property_description_raw
is_new_build
canonical_area
geo_scope
geography_match_status
rule IDs
rule reasons
actions
quality flags
exclusion fields
```

For empty categories, still write a header-only CSV and explain the zero count.

Audit CSVs may contain only relevant subsets, but the Parquet must preserve every row.

---

## 13. Required report content

The reproducibly generated Checkpoint 4 report must include:

### Input, output, and reconciliation

- input and output paths;
- input and output SHA256 checksums;
- input and output row counts;
- row difference;
- duplicate `record_id` count;
- confirmation that all Checkpoint 3 fields and values were preserved;
- schema-validation result;
- Parquet read-back result;
- configuration file checksums or versions.

### Rule proposal and decisions

- each active multi-property, property-scope, duplicate, and exclusion rule;
- severity and action;
- evidence count;
- false-positive considerations;
- user decisions or delegated choices;
- deterministic exclusion-reason priority;
- major implementation and code-style choices with rationale.

### Counts and intersections

Report counts and percentages by:

- `exclude_from_training`;
- primary exclusion reason;
- every applicable exclusion reason;
- exclusion rule ID;
- quality flag;
- multi-property rule and action;
- duplicate status and action;
- property-scope status;
- geography scope and match status;
- canonical area;
- transaction year;
- raw and processed full-market status;
- VAT status and adjustment method;
- new-build status;
- source property description;
- property type.

Also report:

- total included and excluded rows;
- counts before and after each logical exclusion stage without physically dropping rows;
- overlap among exclusion reasons;
- in-scope rows excluded by each reason;
- flagged-review rows that remain included;
- suspected multi-property rows by rule and severity;
- exact source duplicate groups and participating rows;
- duplicate-like groups and participating rows;
- unresolved VAT rows;
- invalid target/date rows;
- unknown/ambiguous/out-of-scope geography rows;
- clearly non-house versus unresolved property-scope coverage;
- examples where multiple rules hit the same row.

Clearly separate full-dataset counts from counts within matched locked geography. The nationwide dataset will otherwise make rule coverage hard to interpret.

### Representative evidence

Include small, readable samples for:

- every auto-excluding multi-property rule;
- every review-only multi-property rule;
- likely false positives rejected by tests/rule design;
- exact duplicates;
- plausible duplicate publications;
- same-day distinct transactions not treated as duplicates;
- explicit apartment/flat property-scope cases;
- unresolved property-scope cases;
- each exclusion reason;
- rows with multiple exclusion reasons;
- valid VAT-adjusted individual-looking new builds retained by transaction rules;
- high-value individual-looking properties not excluded on price alone.

### Test evidence

- exact test command;
- exit status;
- test count;
- captured output path;
- requirements-to-test matrix.

Do not manually edit evidence into the generated report after the build. The report must be reproducible from documented commands.

---

## 14. Required tests

Add focused unit and integration tests. Tests may cover several related requirements, but the report must map requirements to test names.

### Multi-property rules

Test at least:

1. an explicit multi-unit address range that should match;
2. an ordinary hyphenated house number that should not match;
3. multiple clearly separate addresses that should match;
4. an ordinary comma-separated single address that should not match;
5. repeated apartment/unit identifiers;
6. multiple named blocks;
7. explicit bulk/portfolio/entire-block wording;
8. development or estate wording with an individual dwelling that should not be auto-excluded merely for that wording;
9. high price alone does not match;
10. high price plus a strong non-individual pattern follows the approved action;
11. VAT-exclusive status alone does not match;
12. new-build status alone does not match;
13. multiple rule hits retain all stable rule IDs;
14. deterministic overall severity/action;
15. token and regex boundaries prevent obvious false positives;
16. invalid rule configuration fails clearly.

### Property scope

17. explicit apartment wording follows the approved scope policy;
18. explicit flat wording follows the approved scope policy;
19. ambiguous abbreviation does not create an unsafe classification;
20. absence of apartment wording does not label a row as a confirmed house;
21. detailed house type is not fabricated;
22. upstream property fields remain unchanged unless an approved decision says otherwise.

### Duplicate-like detection

23. exact raw-fingerprint duplicates share a deterministic group;
24. group ID is invariant to row order;
25. normalised-address/date/price/status matches are classified as configured;
26. same date and price with distinct addresses is not automatically a duplicate;
27. repeated address on different dates is not automatically a duplicate publication;
28. same-day legitimate distinct transactions remain distinguishable;
29. deterministic representative selection if that policy is approved;
30. no rows are physically removed.

### Cleaning and exclusions

31. missing, invalid, zero, and negative targets;
32. missing and invalid dates;
33. future-date handling follows the documented policy;
34. raw `No` for `Not Full Market Price` remains full market and is not excluded for that reason;
35. raw `Yes` is excluded as non-full-market;
36. missing/unrecognised full-market status follows the approved policy;
37. valid VAT-adjusted rows are not excluded merely because they were VAT exclusive;
38. unresolved VAT treatment is handled explicitly;
39. new builds are not excluded merely for being new;
40. out-of-scope geography is excluded;
41. unmatched/unknown geography follows the approved policy;
42. unresolved ambiguous geography is excluded or reviewed according to the approved policy;
43. review-only multi-property suspicion does not become an auto-exclusion accidentally;
44. auto-excluding multi-property evidence sets the expected reason;
45. duplicate action follows the approved policy;
46. property-scope action follows the approved policy;
47. multiple exclusion reasons are retained;
48. primary exclusion reason follows deterministic priority;
49. quality flags are stable, deduplicated, and ordered;
50. high/low price alone is not excluded;
51. no hard `>200m²` filter exists.

### Pipeline, schema, audits, and reproducibility

52. Checkpoint 3 input row count equals Checkpoint 4 output row count;
53. `record_id` values and order are unchanged;
54. every Checkpoint 3 column and value is preserved;
55. all new fields match the documented physical schema;
56. Parquet write/read-back row count and schema validation;
57. required audit files are created, including header-only files for zero-count categories;
58. deterministic output for repeated runs with identical inputs/configuration;
59. no final processed dataset or baseline-compatible CSV is created;
60. no baseline training or temporal validation is run.

Use small synthetic fixtures for rule behaviour. Use a full-data integration check for reconciliation, schemas, and generated counts. Avoid tests whose expected results depend on incidental full-snapshot row ordering.

---

## 15. Documentation updates

Update existing documents rather than creating near-duplicates.

At minimum, update as needed:

```text
docs/data/dataset_schema.md
docs/data/data_cleaning_rules.md
docs/data/raw_to_processed_workflow.md
```

Create a focused durable document such as:

```text
docs/data/multi_property_detection.md
```

only if no equivalent file exists and the rule semantics would otherwise be buried in generated reports.

Update `planning/decision_log.md` only for material approved decisions. Record cross-specialist implications in `planning/specialist_handoffs.md` if that file exists or if a genuine handoff is needed.

Documentation must distinguish:

- source-standardised;
- geography-enriched;
- cleaning-assessed;
- final processed/training views reserved for Checkpoint 5.

---

## 16. Engineering and code-quality standards

- Python only.
- Use type hints for public functions and meaningful internal boundaries.
- Add **Google-style docstrings** to every new or materially modified module, class, function, and method. Include `Args`, `Returns`, and `Raises` sections where applicable.
- Keep transformations deterministic and side effects at script/writer boundaries.
- Prefer focused pure functions for individual rules and exclusion aggregation.
- Prefer configuration and named constants over scattered literals.
- Compile and validate regular expressions once rather than repeatedly per row.
- Use vectorised operations where they remain readable and testable; explain any justified row-wise operation and its performance implications on 790,415 rows.
- Use dataclasses or similarly explicit typed structures where they clarify rule definitions/results; explain the choice.
- Use explicit exceptions for invalid configuration and physical schemas.
- Use stage-level logging and row counts.
- Preserve decimal price semantics; do not convert monetary targets through binary floating point unnecessarily.
- Keep stable pipe-delimited audit fields deduplicated and deterministically ordered, or use another documented representation that remains easy to inspect in CSV.
- Do not silently drop, overwrite, relabel, or resolve records.
- Do not add opaque classifiers, fuzzy matching, external APIs, or notebook-only logic.
- Keep build/report generation reproducible.

Do not add excessive inline comments that merely restate syntax. Use docstrings and concise comments to explain business rules, invariants, non-obvious regex boundaries, and exclusion precedence.

Before or immediately after each major code addition, explain its style and architecture in plain language. At the end, provide a file-by-file intuition summary so the user understands what the code is doing.

---

## 17. Prohibited behaviour in Checkpoint 4

Do not:

- drop rows from the cleaning-assessed Parquet;
- overwrite raw or upstream processed values;
- alter Checkpoint 2 or 3 semantics merely for cleanup;
- broaden or fuzzily remap geography;
- silently resolve ambiguous geography;
- infer detailed house type from address text;
- treat lack of apartment keywords as proof of a house;
- exclude every high-value, VAT-exclusive, new-build, development-address, or duplicate-like row;
- use price alone as a bulk-sale rule;
- winsorise, cap, or mutate prices;
- apply a hard floor-area-above-200m² exclusion;
- implement BER, geospatial, listing, text, or image enrichment;
- create final processed Parquet, DuckDB, or baseline-compatible CSV outputs;
- run or modify baseline training and temporal validation;
- tune models;
- proceed through a materially ambiguous auto-exclusion policy without user input or an existing locked decision;
- invent counts, test results, or manual-review outcomes.

---

## 18. Acceptance criteria

Checkpoint 4 is complete when:

1. The Checkpoint 3 Parquet is used as the only transformation input.
2. Every input row appears exactly once in the output.
3. Every Checkpoint 3 field and value is preserved.
4. Multi-property detection is transparent, deterministic, tested, and evidence-led.
5. Each multi-property rule has stable metadata, an action, tests, counts, and audit examples.
6. Price alone never determines multi-property status or exclusion.
7. Property scope is treated conservatively without fabricating detailed house types.
8. Duplicate-like groups are deterministic, categorised, and audited without silent removal.
9. Cleaning decisions preserve all applicable reasons and choose a primary reason deterministically.
10. Auto-excluding and review-only rule actions remain distinct.
11. Full-market-price interpretation remains correct.
12. Valid VAT-adjusted and individual-looking new-build records are not excluded solely for VAT/new-build status.
13. Geography and status exclusions follow approved policies.
14. Excluded rows remain in the output and audit files.
15. The output has an explicit, validated PyArrow schema and passes read-back validation.
16. Required audit files and a reproducible quality report are generated.
17. Relevant unit and integration tests pass.
18. Material user decisions, assumptions, deviations, and inherited issues are documented.
19. Google-style docstrings are present in all new or materially modified code.
20. The user receives an intuitive summary of every code file created or materially changed.
21. No Checkpoint 5 output, model run, or unrelated enrichment is introduced.

---

## 19. End-of-checkpoint response

At completion, lead with whether Checkpoint 4 passed its acceptance criteria, then report:

1. files created or updated;
2. a plain-language, file-by-file summary of what the code does;
3. major design and code-style choices and why they were made;
4. user decisions and assumptions applied;
5. commands run;
6. test results and captured evidence path;
7. input/output row reconciliation;
8. physical schema validation result;
9. included and excluded counts;
10. exclusion counts and overlaps by reason;
11. suspected multi-property counts by rule, severity, and action;
12. duplicate group counts by category and action;
13. property-scope coverage and unresolved count;
14. geography-related exclusion counts;
15. VAT and new-build treatment counts;
16. manual-review findings and artifact paths;
17. inherited defects or policy discrepancies;
18. deviations and known limitations;
19. open questions or follow-ups;
20. the recommended Checkpoint 5 handoff.

Stop after Checkpoint 4.
