# PPR Checkpoint 1 Implementation Plan

## Scope

This document completes Checkpoint 1 from `prompts/ppr_data_pipeline_handoff_prompt.md`:

- inspect repository and `PPR-ALL.csv`;
- produce a source profile;
- reconcile planned schema against actual source columns;
- propose an exact implementation plan and initial rule set for review.

No code has been changed, and no cleaning behaviour has been modified.

## Repository Findings

Current implementation:

- `src/house_valuation/data/loaders.py` loads processed modelling CSV files only.
- `src/house_valuation/data/filters.py` filters already-processed rows using `exclude_from_training`, `property_type`, and `sale_price_eur`.
- `scripts/train_baseline.py` and `scripts/run_validation.py` expect a baseline-compatible processed CSV.
- There is no source-specific PPR ingestion, no Parquet/DuckDB writer, no canonical area lookup, no VAT-adjustment module, and no multi-property audit module yet.

Current baseline contract:

- required: `transaction_date`, `sale_price_eur`, `canonical_area`, `property_type`;
- optional: `geo_scope`, `beds`, `baths`, `floor_area_sqm`, `ber_rating`, `exclude_from_training`.

The baseline can support a first area-only or unknown-type smoke test if the PPR cannot reliably produce detailed house types.

## Schema Reconciliation

Observed PPR source columns:

1. `Date of Sale (dd/mm/yyyy)`
2. `Address`
3. `County`
4. `Eircode`
5. `Price (EUR symbol)`
6. `Not Full Market Price`
7. `VAT Exclusive`
8. `Description of Property`
9. `Property Size Description`

Recommended raw-to-processed mapping:

| Source column | Interim field | Processed / modelling field | Notes |
| --- | --- | --- | --- |
| `Date of Sale (dd/mm/yyyy)` | `transaction_date_raw` | `transaction_date` | Parse as day-first date. |
| `Address` | `raw_address` | `address_normalized`, `canonical_area`, `geo_scope` | Preserve raw value. |
| `County` | `county_raw` | `county` | Use in geography QA; do not treat as sufficient geography. |
| `Eircode` | `eircode_raw` | optional metadata | 69.9390% blank; not required for V1. |
| `Price (EUR symbol)` | `sale_price_eur_raw_text`, `sale_price_eur_raw` | `sale_price_eur` | Final value may be VAT-adjusted. |
| `Not Full Market Price` | `not_full_market_price_raw` | `is_full_market_price` | Raw `No` maps to true; raw `Yes` maps to false. |
| `VAT Exclusive` | `vat_exclusive_raw` | `vat_exclusive_flag`, `vat_rate_applied`, `sale_price_adjustment_method` | Apply configured VAT rate only when resolvable. |
| `Description of Property` | `property_description_raw` | `is_new_build`, `property_type_coarse`, `property_type` | Does not reliably separate house vs apartment. |
| `Property Size Description` | `property_size_description_raw` | `property_size_bucket_source` | Do not map to exact `floor_area_sqm`. |

Required additions to `docs/data/dataset_schema.md` before implementation:

- `sale_price_eur_raw_text`
- `sale_price_eur_raw`
- `sale_price_adjustment_method`
- `vat_rate_applied`
- `not_full_market_price_raw`
- `is_full_market_price`
- `vat_exclusive_raw`
- `property_description_raw`
- `property_type_coarse`
- `property_type_quality_flag`
- `property_size_description_raw`
- `property_size_bucket_source`
- `geography_match_method`
- `geography_match_status`
- `is_possible_multi_property_sale`
- `multi_property_reason`
- `single_dwelling_confidence`

## Schema Mismatches And Risks

1. Encoding mismatch:
   The existing processed CSV loader assumes `utf-8-sig`; `PPR-ALL.csv` is not valid UTF-8 and must be read as CP1252 or through explicit source encoding configuration.

2. Price semantics mismatch:
   Current schema has one `sale_price_eur`; PPR requires preserving raw recorded price separately from final buyer-facing modelling price after VAT adjustment.

3. Full-market-price mismatch:
   Existing docs mention non-standard transactions generally but do not encode the PPR-specific negative field interpretation. Raw `No` must not be treated as non-market.

4. Property-type mismatch:
   PPR source descriptions combine dwelling house/apartment and do not support the locked detailed house labels. V1 should use `unknown` or coarse property type unless enrichment supplies reliable house subtype.

5. Floor-area mismatch:
   PPR has a sparse bucket field, mostly blank, and no exact floor area. It must not populate `floor_area_sqm`.

6. Geography mismatch:
   PPR is nationwide. Address strings alone are noisy and ambiguous. Canonical-area mapping needs a controlled lookup, county guardrails, and audit outputs.

7. Multi-property mismatch:
   Extreme prices and address patterns show bulk/development records. Existing cleaning docs mention non-standard transactions but need a transparent PPR-specific rules engine and audit file.

8. Current pipeline stage mismatch:
   Existing scripts start from a processed CSV. Checkpoints 2-5 need new source-specific ingestion and writer modules before the baseline can consume PPR.

## Exact Implementation Plan For Review

### Checkpoint 2 - Ingestion, Price Parsing, Status Interpretation

Create:

- `src/house_valuation/data/ppr_ingestion.py`
- `src/house_valuation/data/price_adjustment.py`
- `scripts/profile_ppr_dataset.py`
- tests under `tests/data/`

Implement:

- required-source-column validation using the nine observed PPR columns;
- CP1252 source read with explicit failure message for missing columns;
- preservation of every raw source field;
- stable `record_id`, initially hash of source snapshot date plus canonical raw row values;
- `source_name = ppr`;
- `source_snapshot_date = 2026-06-21`;
- date parsing to `transaction_date`;
- price parsing to `sale_price_eur_raw`;
- `Not Full Market Price` mapping to `is_full_market_price`;
- `VAT Exclusive` mapping to `vat_exclusive_flag`;
- interim Parquet if dependencies already support it, otherwise interim CSV plus a clear follow-up to add Parquet.

Do not apply training exclusions in Checkpoint 2 except for validation counts and flags.

### Checkpoint 3 - Address Normalisation And Geography Mapping

Create:

- `src/house_valuation/data/address_normalization.py`
- `src/house_valuation/data/geography_mapping.py`
- `config/canonical_areas.csv`
- `config/address_overrides.csv`

Implement:

- deterministic uppercase/spacing/punctuation address normalisation;
- accent/apostrophe handling policy;
- exact alias matching;
- controlled phrase/token matching;
- manual override lookup;
- unmatched and ambiguous audit outputs.

Do not use uncontrolled fuzzy matching.

### Checkpoint 4 - Multi-Property Rules, Cleaning, Exclusions

Create:

- `src/house_valuation/data/multi_property.py`
- `src/house_valuation/data/cleaning.py`
- `config/multi_property_rules.csv`
- quality/audit report writers.

Implement:

- high-precision multi-property flags first;
- `exclude_from_training`;
- stable `exclusion_reason`;
- audit files for excluded, unmatched, ambiguous, duplicate-like, VAT unresolved, and suspected multi-property records.

### Checkpoint 5 - Processed Outputs And Baseline Smoke Test

Create or extend:

- `src/house_valuation/data/writers.py`
- `src/house_valuation/data/quality_checks.py`
- `scripts/build_ppr_dataset.py`

Implement:

- processed Parquet and baseline-compatible CSV;
- DuckDB output if dependency setup is already straightforward;
- row-count reconciliation;
- baseline training and temporal validation smoke test;
- data-quality summary under `artifacts/data_quality/20260621/`.

## Initial Rule Set For Review

These are proposed rules only. They should be reviewed before implementation.

### Source Schema Rules

| Rule ID | Severity | Action | Rule |
| --- | --- | --- | --- |
| `PPR_SCHEMA_001` | error | stop ingestion | All nine observed source columns must be present exactly. |
| `PPR_SCHEMA_002` | warning | report | Extra source columns are preserved and reported. |
| `PPR_SCHEMA_003` | error | stop ingestion | Source must decode using configured encoding, initially CP1252. |

### Date Rules

| Rule ID | Severity | Action | Rule |
| --- | --- | --- | --- |
| `PPR_DATE_001` | error/flag | flag and exclude later | Missing or unparsable transaction date. |
| `PPR_DATE_002` | warning | flag | Transaction date after source snapshot date or implausibly old date. |

### Price Rules

| Rule ID | Severity | Action | Rule |
| --- | --- | --- | --- |
| `PPR_PRICE_001` | error/flag | flag and exclude later | Missing, unparsable, zero, or negative raw price. |
| `PPR_PRICE_002` | review | flag only initially | Very low raw price; threshold to be set after geography-specific inspection. |
| `PPR_PRICE_003` | review | flag only initially | Very high raw price; never exclude on price alone. |

### Full-Market-Price Rules

| Rule ID | Severity | Action | Rule |
| --- | --- | --- | --- |
| `PPR_FMP_001` | info | map | Raw `No` maps to `is_full_market_price = true`. |
| `PPR_FMP_002` | exclusion candidate | exclude later | Raw `Yes` maps to `is_full_market_price = false`. |
| `PPR_FMP_003` | review | flag | Missing or unrecognised raw value maps to unknown. |

### VAT Rules

| Rule ID | Severity | Action | Rule |
| --- | --- | --- | --- |
| `PPR_VAT_001` | info | map | Raw `No` maps to `vat_exclusive_flag = false`. |
| `PPR_VAT_002` | info | adjust if resolvable | Raw `Yes` maps to `vat_exclusive_flag = true` and requires configured VAT-rate lookup by transaction date. |
| `PPR_VAT_003` | review | flag | VAT-exclusive row without resolvable rate. |
| `PPR_VAT_004` | info | retain | VAT-exclusive/new-build status alone is not an exclusion reason. |

### New-Build And Property-Type Rules

| Rule ID | Severity | Action | Rule |
| --- | --- | --- | --- |
| `PPR_PROP_001` | info | map | Source new dwelling descriptions map to `is_new_build = true`. |
| `PPR_PROP_002` | info | map | Source second-hand descriptions map to `is_new_build = false`. |
| `PPR_PROP_003` | warning | flag | Unrecognised description maps to unknown. |
| `PPR_PROP_004` | warning | coarse type only | PPR description cannot produce reliable detailed house type. Use `property_type = unknown` unless enriched or manually reviewed. |
| `PPR_PROP_005` | exclusion candidate | exclude later | Explicit apartment/unit/flat signals may exclude from house training after rule review, but must be audited. |

### Geography Rules

| Rule ID | Severity | Action | Rule |
| --- | --- | --- | --- |
| `PPR_GEO_001` | info | match | Exact normalised alias match from `config/canonical_areas.csv`. |
| `PPR_GEO_002` | info | match | Controlled token/phrase match using aliases and priority. |
| `PPR_GEO_003` | review | flag | Multiple canonical areas match one record. |
| `PPR_GEO_004` | exclusion candidate | exclude later | No locked geography match. |
| `PPR_GEO_005` | review | flag | County/address conflict or known cross-county area-name ambiguity. |

### Multi-Property Rules

| Rule ID | Severity | Action | Rule |
| --- | --- | --- | --- |
| `PPR_MULTI_001` | high | flag/exclude candidate | Address range with unit/property range, e.g. `1-186`, `1 - 186`, combined with apartment/block/development wording. |
| `PPR_MULTI_002` | high | flag/exclude candidate | Multiple blocks/buildings in one address, e.g. `BLOCK A B AND C`, `BLOCKS L J I K`. |
| `PPR_MULTI_003` | high | flag/exclude candidate | Repeated apartment/unit identifiers in one address. |
| `PPR_MULTI_004` | medium | flag | Development/phase/portfolio language without an individual dwelling identifier. |
| `PPR_MULTI_005` | medium | flag | Extreme price combined with non-individual address pattern. |
| `PPR_MULTI_006` | review | flag | Repeated same-date, same-price, same-development records suggesting batch publication or duplicates. |

### Duplicate-Like Rules

| Rule ID | Severity | Action | Rule |
| --- | --- | --- | --- |
| `PPR_DUP_001` | review | flag | Same normalised address, transaction date, raw price, full-market flag, and VAT flag. |
| `PPR_DUP_002` | review | flag | Same development, date, and price across many nearby numbered addresses. |

## Decisions Needed Before Checkpoint 2

1. Confirm CP1252 as the configured PPR source encoding for this snapshot.
2. Confirm whether the first processed PPR baseline may use `property_type = unknown` for plausible house records because PPR cannot safely provide detailed house type.
3. Confirm the initial VAT-rate configuration source and effective date table before applying VAT adjustments.
4. Confirm whether source docs should be updated before or during Checkpoint 2 to add raw/adjusted price and PPR status fields.

