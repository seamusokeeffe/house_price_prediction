# Codex Follow-up Prompt — PPR Checkpoint 2

Revise the Checkpoint 2 design and then implement Checkpoint 2 only.

Use these reviewed artifacts:

- `ppr_source_profile_20260621.md`
- `ppr_checkpoint_1_implementation_plan.md`
- `decision_log.md`
- raw snapshot `data/raw/ppr/20260621/PPR-ALL.csv`

The Checkpoint 1 source profile is accepted, subject to the decisions and changes below.

## Confirmed project decisions

### 1. Source encoding

Use `cp1252` as the configured encoding for the `20260621` PPR source snapshot.

Do not assume that every future PPR snapshot will necessarily use CP1252. The encoding must be source configuration rather than an undocumented universal assumption.

The ingestion process must:

- fail explicitly on decoding errors;
- fail explicitly when required columns are missing;
- fail explicitly on duplicate source column names;
- allow required columns to appear in any order;
- report unexpected additional columns rather than failing solely because they exist.

Do not use probabilistic automatic encoding detection.

### 2. House-only modelling scope

Decision D-006 in `decision_log.md` is locked: V1 supports houses only and excludes apartments and other non-house property types.

However, the PPR source does not reliably distinguish houses from apartments. Therefore:

- `property_type = unknown` represents unavailable source information;
- it must not be interpreted as evidence that a transaction is a house;
- ambiguous house/apartment classification is a property-scope issue;
- final house-training eligibility will be determined in a later checkpoint;
- no weak property-type inference should be added during Checkpoint 2.

Checkpoint 2 may produce an all-dwelling, source-standardised dataset for pipeline testing. This must not be described as the final house-only training dataset.

A later house-eligible dataset must contain only records that pass the approved property-scope and transaction-scope rules.

### 3. Interim baseline treatment

The first processed PPR output may use `property_type = unknown` for source records where the PPR cannot safely identify a detailed property type.

This is acceptable only for an:

`all-dwelling area-only pipeline smoke test`

It must not be described as:

- a house-only baseline;
- a statistically credible house valuation model;
- evidence that the final model is decision-useful.

Inspect the existing baseline loader, filters and grouping logic and report:

- whether `property_type = unknown` is accepted;
- whether unknown-type rows are filtered out;
- whether the baseline requires an allow-listed property type;
- whether grouping or backoff logic supports an area-only test;
- the minimal compatibility change that would be required later.

Do not change baseline filtering behaviour during Checkpoint 2 unless a change is essential to validate the ingestion output. Prefer reporting the incompatibility and proposed later change.

### 4. House VAT adjustment

Remove the requirement for apartment-specific VAT rates.

For the V1 house-only modelling scope, configure:

`house_vat_rate = 0.135`

Use 13.5% as the configured VAT adjustment for an individual house transaction marked `VAT Exclusive = Yes`.

The VAT-inclusive calculation must be:

`sale_price_eur_raw * (1 + house_vat_rate)`

Therefore:

`sale_price_eur_raw * 1.135`

Use decimal-safe arithmetic or an explicitly documented rounding convention and add tests for the arithmetic and rounding.

Preserve both raw and adjusted prices for auditability.

The required fields should include at least:

- `sale_price_eur_raw_text`
- `sale_price_eur_raw`
- `vat_exclusive_raw`
- `vat_exclusive_flag`
- `vat_rate_applied`
- `sale_price_eur_adjusted`
- `sale_price_adjustment_method`

Use an adjustment method such as:

- `none`
- `provisional_house_vat_13_5_percent`

Do not implement an apartment VAT-rate decision engine.

Do not treat VAT configuration as the mechanism for deciding whether a record is a house or apartment.

Ambiguous house/apartment classification must be handled later as a property-scope issue.

### 5. Conditional use of adjusted price

Checkpoint 2 may calculate and preserve a provisional 13.5% adjusted value for records marked `VAT Exclusive = Yes`.

However, final use of that adjusted price in model training must be conditional on the transaction later qualifying for the house-only training dataset.

The pipeline must distinguish between:

- calculating a traceable provisional adjusted value;
- deciding that the record is eligible for house-only model training.

A calculated VAT-inclusive price does not prove that:

- the property is a house;
- the transaction represents one dwelling;
- the transaction belongs in the locked geography;
- the transaction is suitable for training.

For the later final house-training dataset:

- retained individual houses with `VAT Exclusive = Yes` may use the 13.5%-adjusted price;
- retained houses with `VAT Exclusive = No` use the recorded raw price;
- explicit apartments must be excluded;
- records whose house/apartment scope remains unresolved must not enter the final house-only training dataset unless a later reviewed rule resolves them.

Checkpoint 2 must not make these final exclusions.

### 6. Schema documentation timing

Update `docs/data/dataset_schema.md` at the start of Checkpoint 2, before or alongside the code that emits the new fields.

The documented contract must define:

- field name;
- data type;
- nullability;
- units;
- allowed values or enums;
- source or derivation;
- whether the field is raw, derived, audit-only or modelling-facing;
- the distinction between recorded raw price and adjusted price;
- the provisional nature of the house VAT adjustment before property-scope eligibility is resolved.

The documentation and implementation may be delivered in the same checkpoint, but the code must conform to an explicit documented schema.

## Required design changes

### Source identity and duplicate support

Use a unique source-row identity, for example a deterministic hash of:

- source name;
- source file SHA256;
- source row number.

Create a separate raw-record fingerprint based on canonical raw row values.

Exact duplicate raw rows must:

- have distinct `record_id` values;
- be allowed to share the same `raw_record_fingerprint`.

Do not remove duplicates during Checkpoint 2.

### Full-market-price interpretation

Map `Not Full Market Price` exactly as follows:

- raw `No` -> `is_full_market_price = true`
- raw `Yes` -> `is_full_market_price = false`
- missing or unrecognised -> null or unknown plus an explicit quality status

Preserve the raw source value.

Do not exclude non-full-market records during Checkpoint 2.

### Date handling

Parse dates using the documented day-first source format.

Use `source_snapshot_date` as the reproducible upper-bound reference for future-date validation.

Preserve the raw date text.

Do not remove invalid records during Checkpoint 2. Create flags and report counts.

### Property descriptions

Preserve:

- raw property description;
- raw property-size description.

Create explicit normalized mappings for all observed:

- English-language values;
- Irish-language values;
- known mojibake values.

Use the following user-confirmed exact mappings for observed Irish-language and mojibake values in `Description of Property`:

| Raw source value | English equivalent | Normalized category |
| --- | --- | --- |
| `Teach/?ras?n C?naithe Nua` | `New Dwelling house /Apartment` | `new_dwelling` |
| `Teach/Árasán Cónaithe Atháimhe` | `Second-Hand Dwelling house /Apartment` | `second_hand_dwelling` |
| `Teach/Árasán Cónaithe Nua` | `New Dwelling house /Apartment` | `new_dwelling` |

Preserve the exact original value in `property_description_raw`.

Apply these mappings through an explicit exact-value lookup table or configuration. Record the mapping method, for example:

`property_description_mapping_method = exact_source_value_mapping`

Do not implement:

- general-purpose mojibake correction;
- broad character replacement;
- automatic translation inference;
- fuzzy matching.

Unrecognised property-description values must remain unknown and be reported.

Before finalising the mapping configuration, reproduce the exact distinct raw strings and their counts from the CSV so the configured values can be checked against the actual source bytes and decoded text.

The normalized description may identify:

- new dwelling;
- second-hand dwelling;
- unknown or unrecognised description.

Do not derive:

- house versus apartment eligibility;
- detached, semi-detached, terraced or end-of-terrace type;
- bedrooms;
- exact floor area.

The PPR property-size description must remain a source bucket and must not populate `floor_area_sqm`.

### Price fields

Keep the recorded and adjusted values unambiguous.

Recommended semantics:

- `sale_price_eur_raw_text`: exact source text;
- `sale_price_eur_raw`: parsed amount recorded by the PPR;
- `sale_price_eur_adjusted`: raw amount with the provisional house VAT adjustment applied where `VAT Exclusive = Yes`;
- `vat_rate_applied`: `0`, `0.135`, or null for invalid/unrecognised VAT flags;
- `sale_price_adjustment_method`: method used to derive the adjusted field.

Do not overwrite the raw parsed price.

Do not present `sale_price_eur_adjusted` as a final modelling target until house-training eligibility is resolved.

If the existing schema requires `sale_price_eur`, document clearly whether it is:

- temporarily populated from the adjusted field for compatibility; or
- deferred until final training eligibility is determined.

Prefer retaining explicit raw and adjusted fields in the canonical typed dataset and handling baseline compatibility in a separate output layer.

## Implementation scope

Implement during Checkpoint 2:

- source-column validation;
- configured CP1252 ingestion;
- preservation of all raw source columns;
- source metadata;
- unique source-row IDs;
- duplicate fingerprints;
- date parsing and date-quality flags;
- raw price parsing and price-quality flags;
- full-market mapping;
- VAT flag mapping;
- provisional 13.5% house VAT adjustment;
- raw and adjusted price preservation;
- exact normalized mappings for English, Irish-language and known mojibake property-description values;
- typed interim output, preferably Parquet;
- tests;
- stage-level reconciliation;
- a Checkpoint 2 report.

Do not implement during Checkpoint 2:

- apartment-specific VAT rates;
- geography mapping;
- fuzzy address matching;
- final house-versus-apartment classification;
- detailed property-type inference;
- multi-property exclusions;
- duplicate removal;
- low-price or high-price exclusions;
- final training exclusions;
- claims about model accuracy;
- claims about decision usefulness.

## Required tests

Add tests covering at least:

1. CP1252 decoding and explicit decoding failure.
2. Required columns present in a different order.
3. Missing required source column.
4. Unexpected additional source column.
5. Duplicate source column names.
6. Correct day-first date parsing.
7. Invalid date handling.
8. Correct raw price parsing.
9. Invalid, zero or negative price flags.
10. `Not Full Market Price = No` mapping to `true`.
11. `Not Full Market Price = Yes` mapping to `false`.
12. Missing or unrecognised full-market value.
13. `VAT Exclusive = No` preserving the raw amount without adjustment.
14. `VAT Exclusive = Yes` applying `raw_price * 1.135`.
15. Documented VAT rounding behaviour.
16. Missing or unrecognised VAT value.
17. Preservation of raw and adjusted price fields.
18. Unique `record_id` values for exact duplicate rows.
19. Shared `raw_record_fingerprint` for exact duplicate rows.
20. Exact normalization of each observed English property-description value.
21. Exact normalization of `Teach/?ras?n C?naithe Nua` to `new_dwelling`.
22. Exact normalization of `Teach/Árasán Cónaithe Atháimhe` to `second_hand_dwelling`.
23. Exact normalization of `Teach/Árasán Cónaithe Nua` to `new_dwelling`.
24. Preservation of the original Irish-language or mojibake value in `property_description_raw`.
25. Confirmation that unrecognised values remain unknown.
26. Confirmation that property-size buckets do not populate exact floor area.

## Required Checkpoint 2 evidence

Report:

- input row count;
- output row count;
- row-count reconciliation;
- duplicate `record_id` count;
- duplicate raw-fingerprint count;
- source encoding used;
- required and unexpected source columns;
- date parse-failure count;
- future-date flag count;
- price parse-failure count;
- zero or negative price count;
- counts for every full-market mapping result;
- counts for every VAT mapping result;
- VAT-adjusted record count;
- counts grouped by applied VAT rate;
- counts grouped by adjustment method;
- VAT-adjusted counts by transaction year;
- raw versus adjusted price samples;
- exact distinct raw property-description values and counts;
- counts for every normalized property-description value;
- counts for each Irish-language and mojibake mapping;
- unrecognised property-description samples;
- null counts and dtypes for every created field;
- proof that all raw source columns were preserved;
- complete test output;
- findings on baseline support for `property_type = unknown`;
- confirmation that no geography, property-scope, duplicate, multi-property or price-based exclusions were applied.

Include representative raw-to-processed examples for:

- a normal VAT-inclusive transaction;
- a VAT-exclusive transaction;
- a non-full-market transaction;
- each observed Irish-language property-description value;
- the known mojibake description;
- an exact duplicate pair showing distinct IDs and a common fingerprint;
- an invalid or unrecognised categorical value using a synthetic test fixture if none exists in the snapshot.

## Output status labels

Clearly distinguish outputs as:

1. `source-standardised`  
   Parsed and typed, but not cleaned or restricted to houses.

2. `training-candidate`  
   Reserved for a later checkpoint after geography, house eligibility, multi-property and exclusion rules have been applied.

3. `baseline-compatible`  
   A compatibility output for existing scripts. It must not replace the richer canonical typed dataset or imply house-only validity.

Stop after Checkpoint 2.

Do not proceed to geography mapping, property-scope classification, multi-property detection, exclusions or final modelling outputs until the Checkpoint 2 evidence has been reviewed.
