# Data Cleaning Rules

## Principles

- Prefer conservative exclusion over silently keeping dubious target records.
- Preserve raw values and add cleaned values rather than overwriting source data.
- Every exclusion should have a reason.
- Cleaning must be deterministic and reproducible.
- Keep audit tables for records excluded from training.

## Required cleaning rules

### Transaction date

- Parse to a date.
- Exclude records with missing or invalid transaction dates.
- Exclude records outside the supported source period.

### Sale price

- Parse euro values into numeric `sale_price_eur`.
- Exclude missing, zero, or negative prices.
- Flag suspiciously low or high prices for review.
- Apply hard outlier rules only after inspecting the raw distribution.
- Do not winsorise target prices silently for V1.

### Address

- Preserve `raw_address`.
- Create `address_normalized` using deterministic rules:
  - uppercase
  - trim whitespace
  - standardise punctuation spacing
  - normalise common abbreviations where safe
  - keep original tokens available for audit
- Flag missing or very short addresses.

### Geography

- Map to `canonical_area` using the project area lookup.
- Set `geo_scope` as `inference`, `training_only`, or `out_of_scope`.
- Exclude `out_of_scope` records from training.
- Flag ambiguous area matches for manual review.

### Property type

- Allowed V1 house types:
  - House
  - Detached House
  - Semi-Detached House
  - Terraced House
  - End of Terrace House
- Exclude apartments and clearly non-house property types.
- Keep unknown type only with a specific modelling decision; otherwise exclude from training.

### Duplicate-like records

Flag potential duplicates using:

- same normalised address
- same transaction date
- same sale price
- same source status fields

Do not drop duplicates automatically until the pattern is inspected.

### Non-standard transactions

Exclude or flag where detectable:

- multi-property lots
- partial interests
- non-market transfers
- obvious data entry errors
- VAT-exclusive/new-build records if modelling decides they are incompatible with resale houses

### Floor area, beds, and baths

- Parse to numeric values where available.
- Flag impossible or implausible values.
- Do not apply a hard `>200 sqm` exclusion.
- Create missingness flags for modelling.

## Quality flags

Use compact, stable flag names:

- `missing_transaction_date`
- `invalid_price`
- `suspicious_low_price`
- `suspicious_high_price`
- `missing_address`
- `unmatched_area`
- `ambiguous_area`
- `out_of_scope_area`
- `unknown_property_type`
- `excluded_property_type`
- `duplicate_like`
- `possible_non_market_sale`
- `missing_floor_area`
- `implausible_floor_area`

## Exclusion policy

Records excluded from training should remain in audit outputs.

Required exclusion reasons:

- `invalid_target`
- `invalid_date`
- `out_of_scope_geography`
- `excluded_property_type`
- `ambiguous_geography_unresolved`
- `non_standard_transaction`
- `duplicate_unresolved`
- `insufficient_required_fields`

