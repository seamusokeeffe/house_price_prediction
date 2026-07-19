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

Checkpoint 4 policy:

- exact raw-fingerprint groups retain the lowest `source_row_number` (then
  `record_id`) and mark later occurrences for exclusion;
- normalised publication-key matches remain review-only;
- weaker conflicting-status matches remain review-only;
- same-date/equal-price clusters with distinct addresses are explicitly not
  treated as duplicates solely for that evidence;
- all rows remain in the cleaning-assessed Parquet.

### Non-standard transactions

Exclude or flag where detectable:

- multi-property lots
- partial interests
- non-market transfers
- obvious data entry errors
- VAT-exclusive/new-build records if modelling decides they are incompatible with resale houses

Checkpoint 4 uses configured high-precision multi-property rules for automatic
exclusion. Generic numeric ranges, singular unit ranges, and development/phase
terminology are review-only. Price, semicolons, commas, VAT-exclusive status,
and new-build status never establish a multi-property transaction by themselves.

### PPR property scope

- Explicit token-bounded `APARTMENT`, `APARTMENTS`, `FLAT`, `FLATS`, or `APT`
  with an identifier is `clearly_non_house` and excluded from house training.
- Otherwise isolated `UNIT` wording is `review_required` and remains eligible.
- Absence of those tokens is `unresolved_house_or_apartment`, never confirmed
  house evidence.
- Per resolved handoff H-005, unresolved records retain `property_type = unknown`
  and remain eligible with quality flags for the first broad baseline.
- Detailed house type is not inferred from address text.

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

Checkpoint 4 uses this deterministic primary-reason priority while retaining
all applicable reasons separately:

1. `invalid_target`
2. `invalid_date`
3. `non_full_market_transaction`
4. `unresolved_market_price_status`
5. `out_of_scope_geography`
6. `unmatched_geography_unresolved`
7. `ambiguous_geography_unresolved`
8. `excluded_property_type`
9. `multi_property_transaction`
10. `duplicate_unresolved`
11. `unresolved_vat_treatment`
12. `insufficient_required_fields`

VAT-exclusive status alone is not an exclusion. A valid adjusted target remains
eligible unless another rule applies. New-build status and high/low price alone
are also not exclusions. No hard floor-area-above-200-square-metre rule exists.
