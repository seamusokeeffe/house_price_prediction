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

