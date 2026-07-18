# Dataset Schema

## Schema version

Initial schema: `v0.1`

The schema is intentionally small. Add fields only when they are available for both training and inference, or when they are clearly training-only metadata that will not leak future information.

## Core processed transaction table

Suggested table name: `processed_transactions`

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `record_id` | string | yes | Stable project-generated ID for the processed record. |
| `source_name` | string | yes | Source system, for example `ppr`. |
| `source_snapshot_date` | date | yes | Date the raw source snapshot was acquired. |
| `transaction_date` | date | yes | Sale transaction date. |
| `sale_price_eur` | decimal | yes | Cleaned sale price in euro. |
| `log_sale_price` | float | yes | Natural log of `sale_price_eur`, used as modelling target. |
| `raw_address` | string | yes | Original source address. |
| `address_normalized` | string | yes | Uppercase/punctuation-normalised address string. |
| `canonical_area` | string | yes | Project canonical area. |
| `geo_scope` | string | yes | `inference`, `training_only`, or `out_of_scope`. |
| `county` | string | no | County or local authority where available. |
| `property_type` | string | no | House type when known or inferred. |
| `property_type_source` | string | no | `source`, `inferred`, `manual`, or `unknown`. |
| `is_new_build` | boolean | no | New-build indicator where available. |
| `vat_exclusive_flag` | boolean | no | Whether price is marked VAT exclusive where available. |
| `beds` | integer | no | Bedroom count if available. |
| `baths` | integer | no | Bathroom count if available. |
| `floor_area_sqm` | float | no | Floor area in square metres if available. |
| `ber_rating` | string | no | BER rating if available as a structured feature. |
| `year` | integer | yes | Transaction year. |
| `month` | integer | yes | Transaction month. |
| `quarter` | integer | yes | Transaction quarter. |
| `price_band` | string | yes | Derived band for QA and segment metrics. |
| `size_band` | string | no | Derived floor-area band where floor area exists. |
| `quality_flags` | string | yes | Pipe-delimited flags or JSON array. |
| `exclude_from_training` | boolean | yes | Whether the record is excluded from training. |
| `exclusion_reason` | string | no | Primary exclusion reason. |

## PPR Checkpoint 2 Source-Standardised Transaction Table

Checkpoint 2 produces a `source-standardised` PPR dataset. It is parsed and typed
for audit and pipeline testing, but it is not a `training-candidate` dataset and
must not be described as house-only. Geography, final house eligibility,
multi-property detection, duplicate resolution, and training exclusions are
reserved for later checkpoints.

Suggested table name: `ppr_source_standardised_transactions`.

| Field | Type | Nullable | Units | Allowed values / enum | Source or derivation | Role |
| --- | --- | --- | --- | --- | --- | --- |
| `record_id` | string | no | n/a | SHA256 hex | Hash of `source_name`, `source_file_sha256`, and `source_row_number`. Exact duplicate raw rows must still have distinct IDs. | audit |
| `raw_record_fingerprint` | string | no | n/a | SHA256 hex | Hash of deterministic source-column-name/source-value pairs sorted by source column name. Exact duplicate raw logical rows share this value even if source columns arrive in a different order. | audit |
| `source_name` | string | no | n/a | `ppr` | Constant source identifier. | audit |
| `source_snapshot_date` | date | no | n/a | ISO date | Configured snapshot date; also the reproducible future-date validation reference. | audit |
| `source_file_sha256` | string | no | n/a | SHA256 hex | Checksum of the raw source file. | audit |
| `source_row_number` | integer | no | row number | positive integer | Physical data row number excluding the header. | audit |
| `transaction_date_raw` | string | no | n/a | raw source text | `Date of Sale (dd/mm/yyyy)`. | raw |
| `transaction_date` | date | yes | n/a | ISO date or null | Day-first parse of `transaction_date_raw`. Invalid values are flagged, not removed. | derived |
| `transaction_year` | integer | yes | calendar year | year | Derived from valid `transaction_date`. | derived |
| `date_parse_status` | string | no | n/a | `parsed`, `missing`, `invalid` | Date parse quality status. | audit |
| `is_future_transaction` | boolean | yes | n/a | `true`, `false`, null | `transaction_date > source_snapshot_date` when date parses. | audit |
| `raw_address` | string | no | n/a | raw source text | `Address`. | raw |
| `county_raw` | string | no | n/a | raw source text | `County`. | raw |
| `eircode_raw` | string | yes | n/a | raw source text or null | `Eircode`. | raw |
| `sale_price_eur_raw_text` | string | no | EUR text | raw source text | `Price (€)`, preserved exactly after source decoding. | raw |
| `sale_price_eur_raw` | decimal(18,2) | yes | EUR | non-null when parse succeeds | Parsed amount recorded by the PPR before any VAT adjustment. Invalid values are flagged, not removed. | derived |
| `price_parse_status` | string | no | n/a | `parsed`, `missing`, `invalid`, `non_positive` | Price parse and basic target-quality status. | audit |
| `not_full_market_price_raw` | string | yes | n/a | raw source text or null | `Not Full Market Price`. | raw |
| `is_full_market_price` | boolean | yes | n/a | `true`, `false`, null | Raw `No` maps to `true`; raw `Yes` maps to `false`; missing/unrecognised maps to null. | derived |
| `full_market_price_mapping_status` | string | no | n/a | `mapped_full_market`, `mapped_not_full_market`, `missing`, `unrecognised` | Mapping status for the negatively phrased source field. | audit |
| `vat_exclusive_raw` | string | yes | n/a | raw source text or null | `VAT Exclusive`. | raw |
| `vat_exclusive_flag` | boolean | yes | n/a | `true`, `false`, null | Raw `Yes` maps to `true`; raw `No` maps to `false`; missing/unrecognised maps to null. | derived |
| `vat_mapping_status` | string | no | n/a | `mapped_vat_exclusive`, `mapped_vat_inclusive`, `missing`, `unrecognised` | VAT source-value mapping status. | audit |
| `vat_rate_applied` | decimal(5,3) | yes | rate | `0`, configured house VAT rate, null | The configured Checkpoint 2 default is `0.135`; it applies only for records marked `VAT Exclusive = Yes`; `0` for `No`; null for invalid/unrecognised VAT flags. | derived |
| `sale_price_eur_adjusted` | decimal(18,2) | yes | EUR | null when raw price or VAT flag is invalid | `sale_price_eur_raw` plus provisional V1 house VAT adjustment when `VAT Exclusive = Yes`; otherwise the raw parsed price. | derived |
| `sale_price_adjustment_method` | string | no | n/a | `none`, `provisional_house_vat_13_5_percent`, `unresolved_vat_flag`, `invalid_raw_price` | How `sale_price_eur_adjusted` was derived. | audit |
| `property_description_raw` | string | yes | n/a | raw source text or null | `Description of Property`, preserved exactly after source decoding. | raw |
| `property_description_normalized` | string | no | n/a | `new_dwelling`, `second_hand_dwelling`, `unknown` | Exact-value lookup for observed English, Irish-language, and known mojibake values. | derived |
| `property_description_mapping_method` | string | no | n/a | `exact_source_value_mapping`, `unrecognised`, `missing` | Mapping method/status. No fuzzy matching or translation inference is applied. | audit |
| `is_new_build` | boolean | yes | n/a | `true`, `false`, null | Derived only from exact property-description mapping. | derived |
| `property_type` | string | no | n/a | `unknown` | PPR does not safely distinguish house versus apartment in Checkpoint 2. | modelling-facing placeholder |
| `property_type_source` | string | no | n/a | `unknown` | Indicates no reliable source property type is available yet. | audit |
| `property_type_quality_flag` | string | no | n/a | `ppr_house_apartment_ambiguous` | Explicit reminder that `unknown` is not evidence of a house. | audit |
| `property_size_description_raw` | string | yes | n/a | raw source text or null | `Property Size Description`. | raw |
| `property_size_bucket_source` | string | yes | n/a | raw source text or null | Same as source size bucket, retained for audit. | raw |
| `floor_area_sqm` | float | yes | square metres | always null in Checkpoint 2 | PPR size buckets must not populate exact floor area. | modelling-facing placeholder |

All original PPR source columns are also preserved in the output under
`source_raw__...` columns with deterministic column-name normalisation. The
Checkpoint 2 report records the mapping from original source column names to
preserved output names. If two source columns would normalise to the same
preserved output name, Checkpoint 2 fails explicitly before writing output.

### Provisional VAT Adjustment

For V1 house scope, the configured provisional house VAT rate is `0.135`. When
`VAT Exclusive = Yes`, Checkpoint 2 calculates:

```text
sale_price_eur_adjusted = sale_price_eur_raw * 1.135
```

The calculation uses decimal arithmetic and rounds to cents using
`ROUND_HALF_UP`. This adjusted value is provisional before property-scope
eligibility is resolved. It does not prove that the record is a house, one
dwelling, in geography, or suitable for model training. A later
`training-candidate` dataset may use the adjusted price only for records that
pass the approved house-only and transaction-scope rules.

## Canonical area lookup

Suggested table name: `canonical_areas`

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `canonical_area` | string | yes | Project-approved area name. |
| `scope` | string | yes | `inference` or `training_only`. |
| `aliases` | string | yes | Pipe-delimited aliases or JSON array. |
| `parent_area` | string | no | Optional broader grouping for reporting. |
| `notes` | string | no | Ambiguity or mapping notes. |

## Inference input table

Suggested table name: `inference_inputs`

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `input_id` | string | yes | Stable ID for a valuation request. |
| `created_at` | timestamp | yes | Local timestamp. |
| `listing_url` | string | no | Daft URL or other source URL. |
| `asking_price_eur` | decimal | yes | Asking price used for comparison. |
| `raw_address` | string | no | Listing or manual address. |
| `canonical_area` | string | yes | Project canonical area after review. |
| `property_type` | string | yes | One of the locked house types. |
| `beds` | integer | yes | Bedroom count. |
| `baths` | integer | no | Bathroom count. |
| `floor_area_sqm` | float | yes | Floor area in square metres. |
| `ber_rating` | string | no | BER rating if available. |
| `input_source` | string | yes | `parser`, `manual`, or `parser_with_overrides`. |
| `review_status` | string | yes | `reviewed` before valuation. |

## Shared training/inference feature contract

The first shared feature contract should include only fields that can be created for both historical records and inference inputs:

- `canonical_area`
- `geo_scope`
- `property_type`
- `beds`
- `baths`
- `floor_area_sqm`
- `ber_rating`, if available enough
- derived time features for training; inference should use valuation date features only where the modelling protocol allows
- derived support counts from historical comparables

Resolved handoff H-004 at schema level: training and inference should share these core feature names, with source-only fields excluded from inference features.

## Prohibited V1 training fields

Do not use:

- listing description text
- listing images
- future sale information
- asking price as a target proxy
- post-sale information unavailable at inference time
- manually created labels that encode the target
