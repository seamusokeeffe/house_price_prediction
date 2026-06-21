# PPR Data Pipeline Planning and Implementation Handoff

Act as a senior data engineer and ML data strategist working inside an existing local Python repository.

Your job is to continue planning and implementing the data pipeline for the **South Dublin House Valuation Tool**.

The immediate objective is to turn the downloaded Irish Residential Property Price Register dataset, `PPR-ALL.csv`, into a clean, auditable and versioned modelling dataset that can be consumed by the existing baseline training and validation code.

## Operating mode

This is an implementation-led task with supporting planning work.

You should:

- inspect the repository before making changes;
- read the existing planning and implementation documents;
- treat `AGENTS.md`, the decision log and project planning documents as the source of truth;
- extend existing modules rather than creating parallel implementations;
- work incrementally;
- run tests and pipeline commands where possible;
- preserve all raw source fields;
- avoid silently dropping or overwriting records;
- make cleaning decisions auditable;
- stop and report evidence where a rule requires human judgement;
- avoid model optimisation, UI work and deployment work during this task.

Before making major changes, create or recommend a Git checkpoint.

## Existing repository context

The repository already contains:

- `AGENTS.md`;
- project planning under `/planning/`;
- durable specifications under `/docs/`;
- implementation code under `/src/`;
- scripts under `/scripts/`;
- a grouped-median baseline;
- temporal validation code;
- a downloaded `PPR-ALL.csv` file, or a manually specified location for that file.

Read the relevant documents, including their equivalents if filenames differ:

- `planning/decision_log.md`
- `planning/roadmap.md`
- `planning/data/`
- `planning/modelling/`
- `docs/data/dataset_schema.md`
- `docs/data/data_cleaning_rules.md`
- `docs/data/raw_to_processed_workflow.md`
- `docs/implementation/how_to_run_baseline.md`
- `docs/implementation/mvp_code_structure.md`

Do not rewrite existing documents merely for stylistic consistency.

## Current baseline contract

The existing baseline requires at least:

- `transaction_date`
- `sale_price_eur`
- `canonical_area`
- `property_type`

Optional fields currently anticipated include:

- `geo_scope`
- `beds`
- `baths`
- `floor_area_sqm`
- `ber_rating`
- `exclude_from_training`

The current grouped-median baseline predicts using:

1. canonical area and property type;
2. canonical area fallback;
3. property type fallback;
4. global median fallback.

Do not fabricate detailed property types merely to satisfy this interface. If the PPR cannot support reliable detached, semi-detached, terraced and end-of-terrace labels, implement and document a safe temporary representation or support an area-only smoke-test baseline.

## Primary source

Use the downloaded **Residential Property Price Register** file, `PPR-ALL.csv`, as the transaction spine.

Treat it as the source for:

- sale date;
- recorded transaction price;
- raw address;
- county;
- `Not Full Market Price`;
- VAT-exclusive indicator;
- broad property description;
- source property-size description where present.

Do not assume that PPR alone provides reliable:

- detailed house type;
- exact floor area;
- bedrooms;
- bathrooms;
- BER rating;
- property condition.

Those require later enrichment and must not be inferred using weak heuristics.

## Important PPR interpretation decisions

### 1. `Not Full Market Price`

The source field is negatively phrased.

Interpret it as:

- raw `No` means the record is **not flagged as non-full-market-price**, so it is treated as a full-market-price transaction;
- raw `Yes` means the transaction is explicitly flagged as not full market price;
- missing or unrecognised values remain unknown and must be flagged.

Create a positively named processed field:

```text
is_full_market_price
```

Recommended mapping:

```text
No  -> True
Yes -> False
other or missing -> null / unknown
```

Normalise whitespace and case before mapping.

For the primary V1 training view:

- retain `is_full_market_price = True`;
- exclude `is_full_market_price = False`;
- flag unknown values for review;
- preserve all excluded records in audit outputs.

Do not interpret the large proportion of raw `No` values as meaning that most transactions are non-market transactions.

### 2. Multi-property and bulk transactions

The PPR includes transactions that may represent:

- apartment blocks;
- housing estates;
- development phases;
- multiple properties;
- portfolios;
- bulk institutional purchases;
- other transactions that are not sales of one individual dwelling.

These are outside the target problem and should be excluded from the single-house training view.

Do not use a single global maximum-price cutoff as the sole rule. Expensive single houses can be valid in the target geography.

Implement evidence-based detection using signals such as:

- multiple addresses in one source field;
- address ranges;
- several unit numbers;
- apartment-block or development terminology;
- estate or development names without an identifiable individual dwelling;
- source fields showing other properties included in the sale, where available;
- extreme transaction value combined with a non-individual address pattern;
- repeated property separators or lists;
- keywords suggesting blocks, phases, portfolios or multiple units.

Add fields such as:

```text
is_possible_multi_property_sale
multi_property_reason
single_dwelling_confidence
```

Use a stable exclusion reason such as:

```text
multi_property_transaction
```

The pipeline should produce an audit file of suspected bulk transactions for manual review.

Do not automatically classify every high-value transaction as bulk.

### 3. VAT-exclusive transactions

Preserve both the raw recorded price and the buyer-facing adjusted price.

Use fields such as:

```text
sale_price_eur_raw
vat_exclusive_flag
vat_rate_applied
sale_price_eur
sale_price_adjustment_method
```

For a valid individual house transaction marked VAT-exclusive:

```text
sale_price_eur =
sale_price_eur_raw * (1 + applicable_vat_rate)
```

Do not scatter a hardcoded VAT rate throughout the code. Implement a configurable effective-date lookup, for example:

```csv
effective_from,effective_to,property_category,vat_rate
2010-01-01,9999-12-31,new_house,0.135
```

The lookup must:

- use transaction date;
- support future rate changes;
- record the applied rate;
- fail or flag the row if a rate cannot be resolved;
- retain the original recorded value.

Initially use the documented applicable rate for houses, subject to verification in project documentation.

VAT conversion does not by itself establish that the record is suitable. Bulk-development VAT-exclusive sales must still be excluded.

### 4. New builds

Where the source supports it:

- derive or preserve an `is_new_build` flag;
- retain valid individual new-build house transactions after VAT adjustment;
- exclude bulk-development transactions;
- evaluate new-build and second-hand performance separately later.

Do not automatically exclude all VAT-exclusive or all new-build records.

## Supported property scope

V1 supports houses only:

- House
- Detached House
- Semi-Detached House
- Terraced House
- End of Terrace House

Apartments and clearly non-house property types are out of scope.

Because the PPR may not reliably identify detailed house type:

- retain source descriptions separately;
- use conservative coarse classification;
- attach `property_type_source`;
- attach a quality or confidence flag;
- do not infer detailed type from weak address text;
- report the proportion of records with unknown or coarse type.

## Inference geography

- Sandymount
- Ballsbridge
- Ranelagh
- Rathmines
- Rathgar
- Terenure
- Donnybrook
- Milltown
- Dartry
- Clonskeagh
- Windy Arbour
- Churchtown
- Dundrum
- Goatstown
- Foxrock
- Seapoint
- Blackrock
- Booterstown
- Merrion
- Mount Merrion
- Kilmacud
- Stillorgan
- Ardilea

## Additional training-only geography

- Harolds Cross
- Kimmage
- Templeogue
- Rathfarnham
- Knocklyon
- Butterfield
- Edmondstown
- Ballyboden
- Scholarstown
- Ballinteer
- Balally
- Sandyford
- Kilgobbin
- Carrickmines
- Kilternan
- Deansgrange
- Cabinteely
- Loughlinstown
- Shankill
- Ballybrack
- Killiney
- Kilbogget
- Glenageary
- Thomastown
- Dalkey
- Woodpark
- Monkstown
- Sandycove
- Dún Laoghaire

Do not broaden beyond these areas.

## Required pipeline

Implement the following flow:

```text
PPR-ALL.csv raw snapshot
    ↓
source ingestion
    ↓
raw schema standardisation
    ↓
price and date parsing
    ↓
full-market-price interpretation
    ↓
VAT adjustment
    ↓
address normalisation
    ↓
canonical-area mapping
    ↓
single-dwelling / bulk-transaction assessment
    ↓
property-scope classification
    ↓
cleaning and exclusion rules
    ↓
processed Parquet and DuckDB outputs
    ↓
baseline-compatible CSV
    ↓
quality and audit reports
```

## Phase 1: repository and data inspection

Before implementing:

1. Inspect all relevant planning documents.
2. Inspect existing loaders, filters, schemas, baseline code and validation scripts.
3. Inspect `PPR-ALL.csv`:
   - encoding;
   - delimiter;
   - raw columns;
   - row count;
   - date range;
   - null rates;
   - unique values for status fields;
   - basic price distribution;
   - sample records at the top and bottom of the price range.
4. Reconcile the planned schema with actual source columns.
5. Record any required schema changes.
6. Do not make irreversible cleaning decisions based only on assumptions.

Produce a short source-profile report before applying aggressive exclusions.

## Phase 2: raw snapshot and source specification

Store the unchanged source under a versioned path such as:

```text
data/raw/ppr/YYYYMMDD/PPR-ALL.csv
```

Record:

- acquisition date;
- original filename;
- source URL or acquisition note;
- checksum;
- row count;
- encoding;
- observed schema;
- source date range.

Never modify the raw source file.

Create or update:

```text
docs/data/ppr_source_specification.md
docs/data/ppr_field_mapping.md
```

## Phase 3: PPR ingestion

Implement source-specific ingestion that:

- handles encoding safely;
- standardises raw column names;
- preserves all raw fields;
- parses dates;
- parses euro values;
- creates a stable `record_id`;
- attaches `source_name`;
- attaches `source_snapshot_date`;
- raises a clear error when required fields are absent;
- writes standardised interim Parquet.

Keep source ingestion separate from generic cleaning.

## Phase 4: price treatment

Implement separate fields for:

- raw source price;
- parsed source price;
- VAT-adjusted price;
- final modelling price;
- adjustment method;
- VAT rate applied.

Validate:

- missing prices;
- non-numeric prices;
- zero and negative prices;
- conversion failures;
- implausible values requiring review.

Do not silently winsorise prices.

Produce price summaries before and after VAT adjustment.

## Phase 5: address normalisation

Implement deterministic address normalisation that:

- preserves `raw_address`;
- creates `address_normalized`;
- uppercases consistently;
- trims and collapses whitespace;
- standardises punctuation spacing;
- handles apostrophes and accents consistently;
- uses only safe abbreviation normalisation;
- retains original tokens for audit;
- flags missing or unusually short addresses.

Add unit tests using representative Irish addresses.

## Phase 6: canonical-area mapping

Use a data-driven lookup file, such as:

```text
config/canonical_areas.csv
```

The table should support:

- `canonical_area`;
- `alias`;
- `scope`;
- `match_priority`;
- optional notes.

Match in this order:

1. exact normalised alias;
2. controlled phrase or token match;
3. manually reviewed override table;
4. unmatched.

Output:

- `canonical_area`;
- `geo_scope`;
- `geography_match_method`;
- `geography_match_status`;
- relevant quality flags.

Create audit outputs for:

- unmatched records;
- ambiguous matches;
- manual overrides;
- out-of-scope records.

Do not use uncontrolled fuzzy matching in the first pass.

## Phase 7: multi-property transaction detection

Implement a transparent rules engine for suspected multi-property transactions.

Each rule should have:

- a stable rule ID;
- description;
- matching logic;
- severity;
- whether it automatically excludes or only flags;
- tests;
- an audit count.

Begin with conservative high-precision rules. Examples may include:

- address ranges;
- multiple semicolon-separated or comma-separated postal addresses;
- repeated unit identifiers;
- explicit apartment block or development phase phrases;
- bulk/development terminology;
- extreme value plus non-individual address;
- source evidence of multiple properties.

Do not implement an opaque classifier at this stage.

Produce:

```text
artifacts/data_quality/YYYYMMDD/suspected_multi_property_transactions.csv
```

Include rule hits and source fields for manual review.

## Phase 8: cleaning and exclusions

Each record must retain:

- quality flags;
- `exclude_from_training`;
- `exclusion_reason`;
- all relevant raw values.

Apply rules for:

- invalid target;
- invalid date;
- non-full-market transaction;
- out-of-scope geography;
- unresolved ambiguous geography;
- clearly excluded property type;
- suspected or confirmed multi-property transaction;
- unresolved duplicate;
- incompatible or unresolved VAT treatment;
- insufficient required fields.

Keep excluded records in audit outputs.

## Phase 9: duplicate handling

Flag duplicate-like records using:

- normalised address;
- transaction date;
- raw or adjusted price;
- source-status fields.

Do not automatically discard all duplicates.

Separate:

- exact source duplicates;
- plausible duplicate publications;
- same-day legitimate multiple transactions;
- unresolved duplicate-like cases.

Produce a duplicate audit file.

## Phase 10: property-type treatment

Inspect actual source descriptions and design the safest V1 mapping.

Keep fields such as:

```text
property_description_raw
property_type_coarse
property_type
property_type_source
property_type_quality_flag
```

If reliable detailed type is unavailable:

- use a documented coarse value;
- allow unknown type;
- run the baseline primarily through area fallback;
- report coverage and fallback counts;
- do not fabricate detailed categories.

## Phase 11: processed outputs

Produce versioned outputs under:

```text
data/
  raw/
    ppr/YYYYMMDD/
  interim/
    YYYYMMDD/
  processed/
    dataset_version=YYYYMMDD/

artifacts/
  data_quality/
    YYYYMMDD/
```

At minimum, produce:

- standardised interim Parquet;
- processed transaction Parquet;
- baseline-compatible CSV;
- DuckDB table or view if straightforward;
- excluded-record audit;
- unmatched-area audit;
- ambiguous-area audit;
- suspected bulk-transaction audit;
- duplicate-like audit;
- VAT-adjustment audit;
- row-count reconciliation report;
- data-quality summary.

## Phase 12: data validation

Implement automated checks for:

- input and output row-count reconciliation;
- required columns;
- valid transaction dates;
- finite log sale price;
- no non-positive modelling prices;
- no excluded records in the training view;
- no out-of-scope records in the training view;
- canonical areas restricted to the locked list;
- valid full-market-price mapping;
- VAT conversion traceability;
- audit-output creation;
- dataset and schema version recording.

Report counts by:

- year;
- canonical area;
- geo scope;
- raw full-market-price value;
- processed full-market-price status;
- VAT status;
- new-build status;
- source property description;
- processed property type;
- inclusion status;
- exclusion reason;
- multi-property rule;
- quality flag.

## Phase 13: baseline smoke test

After producing the processed CSV:

1. Run the current baseline training command.
2. Run temporal validation.
3. Record:
   - dataset version;
   - included and excluded row counts;
   - date range;
   - area coverage;
   - property-type coverage;
   - full-market-price exclusions;
   - VAT adjustments;
   - suspected bulk-sale exclusions;
   - validation metrics;
   - baseline backoff counts.
4. Treat results as a pipeline smoke test, not proof of model usefulness.
5. Do not tune or replace the model during this task.

## Planning updates

Update the data planning documentation to reflect:

- correct interpretation of `Not Full Market Price`;
- VAT-inclusive modelling-price policy;
- treatment of new builds;
- multi-property detection policy;
- raw versus adjusted price fields;
- manual-review workflow;
- limitations of PPR property-type data.

Add or update decision-log entries only for material decisions.

## Enrichment planning

Once the PPR pipeline works, create a short, separate feasibility document for:

- BER matching;
- floor area;
- dwelling type;
- BER rating;
- geospatial enrichment.

Do not implement advanced record linkage in this task.

## Preferred deliverables

Use existing files where equivalent modules already exist. Otherwise, likely deliverables include:

```text
planning/data/ppr_acquisition_plan.md
planning/data/ppr_cleaning_decisions.md
planning/data/enrichment_feasibility.md

docs/data/ppr_source_specification.md
docs/data/ppr_field_mapping.md
docs/data/canonical_area_mapping.md
docs/data/multi_property_detection.md
docs/data/vat_adjustment_policy.md
docs/data/data_quality_checks.md

config/canonical_areas.csv
config/address_overrides.csv
config/vat_rates.csv
config/multi_property_rules.csv

src/house_valuation/data/ppr_ingestion.py
src/house_valuation/data/address_normalization.py
src/house_valuation/data/geography_mapping.py
src/house_valuation/data/price_adjustment.py
src/house_valuation/data/multi_property.py
src/house_valuation/data/cleaning.py
src/house_valuation/data/quality_checks.py
src/house_valuation/data/writers.py

scripts/profile_ppr_dataset.py
scripts/build_ppr_dataset.py

tests/data/test_ppr_ingestion.py
tests/data/test_address_normalization.py
tests/data/test_geography_mapping.py
tests/data/test_price_adjustment.py
tests/data/test_multi_property.py
tests/data/test_cleaning.py
```

Do not create duplicate modules if equivalent files already exist.

## Engineering standards

- Python only;
- type hints for public functions;
- focused modules;
- deterministic transformations;
- configuration over hidden constants;
- explicit exceptions for invalid source schemas;
- stage-level logging and row counts;
- unit tests for pure functions;
- no notebook-only implementation;
- no silent dropping of records;
- no reliance on proprietary services for the core pipeline;
- conservative rules before fuzzy or probabilistic matching;
- clear separation between raw, cleaned and modelling fields.

## Execution approach

Do not attempt the entire pipeline as one opaque change.

Work in checkpoints:

### Checkpoint 1
- inspect source and repository;
- produce source profile;
- reconcile schema;
- propose exact implementation plan.

### Checkpoint 2
- implement ingestion, price parsing and status interpretation;
- add tests;
- run on a sample or full dataset;
- report row counts.

### Checkpoint 3
- implement address normalisation and area mapping;
- add audit outputs and tests.

### Checkpoint 4
- implement multi-property rules, cleaning and exclusions;
- create quality reports.

### Checkpoint 5
- produce final processed outputs;
- run baseline smoke test;
- document limitations and next steps.

After each checkpoint:

- run relevant tests;
- summarise files changed;
- report key counts;
- flag decisions requiring human review.

Do not proceed through a major ambiguous rule without surfacing the evidence.

## Acceptance criteria

The task is complete when:

1. `PPR-ALL.csv` can be ingested reproducibly.
2. Raw source values are preserved.
3. `Not Full Market Price` is interpreted correctly.
4. VAT-exclusive individual-house prices are adjusted transparently.
5. Suspected bulk and multi-property transactions are identified and audited.
6. Addresses are normalised deterministically.
7. Transactions are mapped to locked geography or clearly flagged.
8. Exclusions are explicit and auditable.
9. A versioned processed dataset is produced.
10. A baseline-compatible CSV is produced.
11. Quality and audit reports are produced.
12. Existing baseline and validation scripts run successfully.
13. Tests cover the most important transformations.
14. Known limitations around property type and enrichment are documented.

## Out of scope

Do not implement:

- Daft scraping;
- historical listing acquisition;
- image processing;
- text modelling;
- advanced probabilistic record linkage;
- model tuning;
- public UI;
- production deployment;
- automated retraining.

## End-of-task report

At the end, report:

1. Files created or updated
2. Pipeline stages implemented
3. Commands used
4. Row counts at each stage
5. Exclusion counts by reason
6. VAT-adjustment counts
7. Suspected multi-property counts
8. Geography match coverage
9. Property-type coverage
10. Test results
11. Assumptions and deviations
12. Manual-review tasks
13. Known limitations
14. Recommended next task

If the raw dataset is unavailable at the expected location, implement what is possible, provide exact placement instructions, and do not invent results.
