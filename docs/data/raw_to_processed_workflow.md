# Raw-to-Processed Workflow

## Goal

Create a deterministic, inspectable path from raw transaction records to a processed modelling dataset.

## Directory convention

```text
data/
  raw/
    ppr/YYYYMMDD/
  interim/
    YYYYMMDD/
  processed/
    dataset_version=YYYYMMDD/
artifacts/
  data_quality/YYYYMMDD/
```

## Workflow stages

### 1. Snapshot raw sources

Save raw source files without editing them.

Record:

- acquisition date
- source URL or manual acquisition notes
- row count
- file checksum if practical
- schema observed at ingestion

### 2. Standardise raw transaction fields

Convert raw fields into a consistent interim structure:

- parse dates
- parse euro prices
- preserve raw address
- normalise address text into `address_normalized`
- preserve source status fields
- generate source-level IDs where possible

### 3. Apply geography mapping

Map `address_normalized` to `canonical_area`.

Order of operations:

1. exact alias match
2. contains/phrase match for canonical area aliases
3. manually reviewed override table
4. unmatched flag

Do not infer out-of-scope areas into the locked geography just to keep records.

### 4. Apply property scope filters

Keep only plausible house records for training.

Where property type is unknown, keep the record only if the downstream modelling plan explicitly allows unknown type with a quality flag. Otherwise exclude from training but retain for audit.

### 5. Apply cleaning and exclusion rules

Use the rules in `docs/data/data_cleaning_rules.md`.

Each exclusion must set:

- `exclude_from_training = true`
- `exclusion_reason`
- a quality flag

### 6. Derive features and support fields

Create deterministic derived fields:

- year, month, quarter
- price band
- size band
- area scope
- comparable-support counts, once modelling defines thresholds

### 7. Write processed outputs

Write:

- processed Parquet files
- DuckDB tables or views
- data quality summary
- excluded-record summary
- support-count summary

### 8. Validate processed dataset

Minimum checks:

- row counts by stage reconcile
- no missing target in included training rows
- no non-positive sale prices
- no out-of-scope records in training dataset
- locked area list matches decision log
- no excluded records appear in training views

## Dataset versioning

Use `YYYYMMDD` snapshot versions until a more formal semantic scheme is needed.

Each modelling experiment should record:

- dataset version
- schema version
- cleaning rules version
- feature pipeline version

