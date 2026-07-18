# Codex Prompt — Implement PPR Data Pipeline Checkpoint 3

Implement **Checkpoint 3 only** for the PPR data pipeline.

Checkpoint 2 is approved. Use the revised Checkpoint 2 output as the input to this work:

```text
data/interim/ppr/20260621/ppr_source_standardised.parquet
```

Do not rework Checkpoint 2 unless a genuine blocking defect is discovered.

Checkpoint 3 must implement:

1. deterministic address normalisation;
2. canonical-area mapping to the locked project geography;
3. geography mapping audits;
4. tests;
5. a Checkpoint 3 report;
6. a versioned geography-enriched interim output.

Stop after Checkpoint 3.

Do not implement multi-property detection, duplicate resolution, property-scope classification, final exclusions, training-candidate datasets, baseline-compatible outputs, modelling, or enrichment.

---

## 1. Checkpoint 2 status and deferred cleanup

Treat the current Checkpoint 2 output as approved.

The following minor cleanup items are explicitly deferred and must not block Checkpoint 3:

- generalising the VAT adjustment method label beyond the official 13.5% project rate;
- making all artifact publication atomic;
- changing the wording or mechanics of source row numbering;
- strengthening the synthetic VAT tie-rounding test.

Do not spend Checkpoint 3 effort on these items.

Preserve all existing Checkpoint 2 fields and values unchanged.

---

## 2. Checkpoint 3 objective

Transform the Checkpoint 2 `source-standardised` dataset into a geography-enriched interim dataset that:

- preserves every Checkpoint 2 row;
- preserves every Checkpoint 2 field;
- preserves the original raw address;
- creates a deterministic normalised address;
- maps records to the locked canonical areas using controlled, auditable rules;
- distinguishes inference, training-only, out-of-scope, unmatched, and ambiguous geography outcomes;
- does not silently broaden the supported geography;
- does not use uncontrolled fuzzy matching;
- does not make house-versus-apartment or single-dwelling decisions.

The resulting output is still not a final training dataset.

Use an output status such as:

```text
geography-enriched
```

Do not label it:

```text
training-candidate
```

or:

```text
house-only
```

---

## 3. Locked geography

### 3.1 Inference geography

Use exactly the following inference areas:

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
- Monkstown

### 3.2 Training-only geography

Use exactly the following training-only areas:

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
- Sandycove
- Dún Laoghaire

Do not add broader Dublin areas, postal districts, electoral districts, counties, local authorities, nearby neighbourhoods, or unofficial umbrella areas without explicit review.

---

## 4. Required design principles

### 4.1 Deterministic processing

The same input row and the same configuration must always produce the same:

- normalised address;
- candidate area matches;
- final canonical area;
- match method;
- match status;
- geo scope.

### 4.2 Raw-value preservation

Preserve:

```text
raw_address
```

unchanged.

Do not overwrite it.

### 4.3 Controlled matching

Use only:

1. exact normalised alias matching where applicable;
2. controlled phrase or token matching;
3. explicit reviewed override mappings;
4. unmatched or ambiguous status.

Do not implement:

- Levenshtein matching;
- semantic embeddings;
- probabilistic matching;
- unrestricted substring matching;
- general-purpose fuzzy matching;
- external geocoding;
- automatic Eircode lookup;
- postal district inference as a substitute for locality matching.

### 4.4 Conservative ambiguity handling

Where more than one canonical area plausibly matches, do not choose arbitrarily.

Return an ambiguous result and include all candidate areas in an audit field.

### 4.5 Matching must not depend on row order

Alias priority and override resolution must be explicit and deterministic.

### 4.6 Geography mapping is not property eligibility

A successful area match does not establish that the record is:

- a house;
- one dwelling;
- a full-market transaction;
- suitable for training;
- free of duplication;
- free of bulk-sale characteristics.

Do not set final training eligibility in this checkpoint.

---

## 5. Address normalisation

Implement a focused address-normalisation module.

Prefer extending an existing module if one already exists. Do not create a competing implementation.

Likely location:

```text
src/house_valuation/data/address_normalization.py
```

### 5.1 Required output fields

Create at least:

```text
address_normalized
address_normalization_status
address_quality_flags
```

Recommended status values:

```text
normalized
missing
too_short
```

`address_quality_flags` may be a pipe-delimited string or another project-consistent deterministic representation.

### 5.2 Required normalisation behaviour

Apply conservative deterministic normalisation such as:

- Unicode-aware uppercase conversion;
- leading and trailing whitespace removal;
- collapse repeated whitespace;
- standardise whitespace around commas;
- standardise repeated punctuation;
- remove or standardise full stops where safe;
- standardise apostrophe variants;
- standardise common dash variants;
- preserve meaningful digits;
- preserve unit numbers;
- preserve estate names;
- preserve locality names;
- preserve Eircode separately rather than appending it automatically;
- preserve accents consistently or create a separate accent-folded matching form.

Do not delete tokens merely because they appear unimportant.

Do not remove:

- apartment or unit identifiers;
- house numbers;
- estate names;
- road names;
- locality names;
- county references;
- Dublin postal districts.

These may be required for later audits, multi-property detection, or ambiguity review.

### 5.3 Accent handling

The canonical output may preserve Unicode accents.

For matching, it is acceptable to create a separate deterministic comparison form such as:

```text
address_match_text
```

which uses controlled accent folding.

If this is implemented:

- preserve `address_normalized` separately;
- document the distinction;
- add tests for `Dún Laoghaire`, `Dun Laoghaire`, and other relevant accented forms.

### 5.4 Safe abbreviation handling

Only add abbreviation normalisation where the transformation is unambiguous and reviewed.

Examples that may be considered:

```text
RD -> ROAD
ST -> STREET
AVE -> AVENUE
CO -> COUNTY
```

Do not use aggressive abbreviation expansion where tokens may have multiple meanings.

All abbreviation rules must be explicit and tested.

### 5.5 Missing and short addresses

Flag:

- missing or blank address;
- very short normalised address;
- address containing only punctuation;
- address containing only a broad locality with no property-level detail.

Do not exclude these records yet.

---

## 6. Canonical-area configuration

Use a data-driven configuration file rather than embedding all aliases directly in procedural logic.

Preferred location:

```text
config/canonical_areas.csv
```

The file should support at least:

```text
canonical_area
alias
scope
match_type
match_priority
notes
```

Recommended `scope` values:

```text
inference
training_only
```

Recommended `match_type` values:

```text
exact_address
controlled_phrase
token_phrase
```

If a simpler design is used, it must still support explicit priority and auditability.

### 6.1 Alias requirements

Include:

- exact canonical-area names;
- known accented and unaccented variants;
- spacing variants;
- common safe variants;
- reviewed locality forms observed in the source.

Do not invent large numbers of aliases based only on intuition.

Inspect the actual source addresses before finalising alias coverage.

### 6.2 Postal districts and broad regions

Do not map broad values such as:

```text
DUBLIN 4
DUBLIN 6
DUBLIN 14
SOUTH DUBLIN
DUN LAOGHAIRE RATHDOWN
```

directly to a single canonical neighbourhood.

Postal districts may contain multiple canonical areas and must not override locality evidence.

They may be retained as supporting context or audit features only.

### 6.3 Nested and overlapping names

Pay particular attention to areas whose names may overlap or appear within broader addresses, including:

- Merrion versus Mount Merrion;
- Blackrock versus areas containing Blackrock as a postal locality;
- Dundrum versus nearby training-only localities;
- Sandyford versus Sandyford Industrial Estate or broader Sandyford postal references;
- Dún Laoghaire versus Dún Laoghaire-Rathdown;
- Milltown as a potentially non-unique Irish locality name;
- Churchtown as a potentially non-unique locality name;
- Monkstown as a potentially non-unique locality name;
- Shankill as a potentially non-unique locality name;
- Blackrock as a potentially non-unique locality name.

Use county and address context where necessary to avoid mapping same-named localities elsewhere in Ireland into the Dublin scope.

Because the project is focused on selected Dublin areas, a locality-name match outside the relevant Dublin county context should not automatically map.

---

## 7. Manual overrides

Support an explicit reviewed override file, for example:

```text
config/address_overrides.csv
```

Suggested fields:

```text
record_id
canonical_area
geo_scope
override_reason
reviewed_by
review_date
notes
```

At this checkpoint:

- implement the override mechanism;
- do not invent large numbers of manual overrides;
- only include overrides justified by reviewed examples;
- ensure overrides are separate from procedural matching code;
- record when an override is applied.

Recommended match method:

```text
manual_override
```

An override must take precedence over automatic alias matching.

Add tests for:

- a valid override;
- an override referencing an unknown canonical area;
- duplicate conflicting overrides for the same record;
- an override with a scope inconsistent with the canonical-area configuration.

Invalid override configuration must fail explicitly.

---

## 8. Required geography output fields

Create at least:

```text
canonical_area
geo_scope
geography_match_status
geography_match_method
geography_match_alias
geography_match_priority
geography_candidate_areas
geography_quality_flags
```

Recommended `geo_scope` values:

```text
inference
training_only
out_of_scope
unknown
```

Recommended `geography_match_status` values:

```text
matched
unmatched
ambiguous
manual_override
invalid_address
```

It is acceptable for `manual_override` to be a match method rather than a status, provided the schema remains clear and consistent.

Recommended `geography_match_method` values:

```text
manual_override
exact_normalized_alias
controlled_phrase
token_phrase
none
```

For unmatched records:

```text
canonical_area = null
geo_scope = out_of_scope or unknown
```

Choose one consistent policy and document it.

Recommended distinction:

- `out_of_scope`: confidently identified as outside the locked geography;
- `unknown`: insufficient evidence to decide whether it is in or out of scope.

Do not treat every unmatched Irish address as an ambiguous in-scope address.

---

## 9. Matching strategy

Implement a deterministic staged mapping process.

### Stage 1: manual override

Apply a valid reviewed override where present.

### Stage 2: exact controlled match

Match exact normalised aliases where the address or an address component provides an exact reviewed locality match.

### Stage 3: controlled phrase match

Search for canonical aliases as controlled phrases with explicit token boundaries.

Do not use unrestricted substring matching.

For example, an alias should not match merely because its letters appear inside a larger unrelated token.

### Stage 4: candidate resolution

If exactly one canonical area is supported, assign it.

If more than one canonical area is supported:

- use explicit match priority only where the priority rule is reviewed and defensible;
- otherwise mark the record ambiguous;
- retain all candidates in `geography_candidate_areas`.

### Stage 5: unmatched or out-of-scope

If no canonical area is supported:

- do not broaden the geography;
- leave `canonical_area` null;
- assign an appropriate status;
- include the record in an audit output.

---

## 10. County and Dublin-context safeguards

The source contains nationwide PPR records.

Add safeguards so that areas with non-unique names are not matched outside the intended Dublin context.

At minimum, inspect and use:

```text
county_raw
raw_address
address_normalized
eircode_raw
```

Do not rely on county alone, because Dublin-related addresses may use varying county text.

Do not treat an Eircode routing key as a definitive neighbourhood unless a reviewed lookup is explicitly added, which is not required in this checkpoint.

Create quality flags for cases such as:

```text
canonical_alias_outside_expected_dublin_context
conflicting_county_context
broad_dublin_reference_only
```

Do not automatically exclude these rows.

---

## 11. Checkpoint 3 output

Write a versioned interim Parquet, for example:

```text
data/interim/ppr/20260621/ppr_geography_enriched.parquet
```

The output must:

- contain exactly the same number of rows as the Checkpoint 2 input;
- preserve `record_id`;
- preserve all Checkpoint 2 columns;
- add only the documented Checkpoint 3 fields;
- retain one row per Checkpoint 2 record;
- use an explicit PyArrow schema;
- be read back and validated after writing.

Do not overwrite:

```text
ppr_source_standardised.parquet
```

---

## 12. Required audit outputs

Produce versioned audit outputs under a path such as:

```text
artifacts/data_quality/20260621/
```

At minimum, produce:

```text
ppr_checkpoint_3_report.md
unmatched_geography.csv
ambiguous_geography.csv
manual_geography_overrides_applied.csv
out_of_scope_geography_sample.csv
geography_alias_match_summary.csv
address_normalization_quality_summary.csv
test_output_checkpoint_3.txt
```

If no manual overrides are applied, still create an empty audit file with headers or explicitly document that no override file was used.

### 12.1 Unmatched audit

Include at least:

```text
record_id
raw_address
address_normalized
county_raw
eircode_raw
geography_match_status
geography_quality_flags
```

### 12.2 Ambiguous audit

Include at least:

```text
record_id
raw_address
address_normalized
county_raw
geography_candidate_areas
matched_aliases
match_methods
match_priorities
```

### 12.3 Alias summary

Report counts by:

```text
canonical_area
alias
scope
match_method
match_priority
```

This is needed to detect aliases that match unexpectedly large numbers of rows.

---

## 13. Required tests

Add focused unit and integration tests covering at least the following.

### Address normalisation

1. Leading and trailing whitespace.
2. Repeated internal whitespace.
3. Comma and punctuation spacing.
4. Repeated punctuation.
5. Uppercase normalisation.
6. Apostrophe variants.
7. Hyphen or dash variants.
8. Accented locality preservation.
9. Accent-folded matching form where implemented.
10. House and unit numbers preserved.
11. Missing address.
12. Punctuation-only address.
13. Very short address.
14. Raw address preserved unchanged.
15. Normalisation idempotence:

```text
normalize(normalize(x)) == normalize(x)
```

### Canonical-area matching

16. Exact canonical name match.
17. Safe alias match.
18. Accented `Dún Laoghaire`.
19. Unaccented `Dun Laoghaire`.
20. Inference scope assignment.
21. Training-only scope assignment.
22. Unmatched address.
23. Clearly out-of-scope address.
24. Multiple candidate areas producing ambiguity.
25. Match priority where an explicit reviewed priority resolves overlap.
26. Token boundaries preventing false substring matches.
27. Postal district alone not mapping to a neighbourhood.
28. `Mount Merrion` not incorrectly mapped to `Merrion`.
29. `Dún Laoghaire-Rathdown` not automatically mapped to `Dún Laoghaire`.
30. A non-Dublin locality with a duplicate name not mapped into project scope.
31. County/context conflict being flagged.
32. Manual override takes precedence.
33. Invalid override area fails.
34. Conflicting overrides fail.
35. Override scope mismatch fails.
36. `Monkstown` maps to `geo_scope = inference`, not `training_only`.

### Pipeline and schema

37. Checkpoint 2 input row count equals Checkpoint 3 output row count.
38. `record_id` values are unchanged.
39. All Checkpoint 2 columns are preserved.
40. New geography fields match the documented physical schema.
41. Parquet write/read-back row count.
42. Audit files are created.
43. No training exclusion fields are changed.
44. No property-type or multi-property classification is introduced.
45. Deterministic output across repeated runs with the same input and configuration.

Tests may combine related scenarios, but provide a requirements-to-test matrix in the report.

---

## 14. Required evidence and report contents

The Checkpoint 3 report must include:

### Input and reconciliation

- input file path;
- input file checksum;
- input row count;
- output row count;
- row difference;
- duplicate `record_id` count;
- confirmation that all Checkpoint 2 fields were preserved;
- output file checksum;
- physical schema validation result.

### Address normalisation

- missing raw-address count;
- missing normalised-address count;
- too-short address count;
- count by normalisation status;
- count by address quality flag;
- representative raw-to-normalised examples;
- examples containing accents;
- examples containing apostrophes;
- examples containing unit or apartment identifiers;
- proof of normalisation idempotence from tests.

### Geography mapping

Report counts and percentages for:

```text
matched
unmatched
ambiguous
manual_override
invalid_address
```

Report counts by:

```text
canonical_area
geo_scope
geography_match_method
geography_match_status
match alias
match priority
county_raw
transaction year
```

Report:

- inference-area matched count;
- training-only matched count;
- confidently out-of-scope count;
- unresolved/unmatched count;
- ambiguous count;
- manual override count;
- rows matching more than one candidate before resolution.

### Coverage by canonical area

For every locked inference and training-only area, report:

- matched row count;
- earliest transaction date;
- latest transaction date;
- number of distinct matched aliases;
- proportion matched by each method.

Include areas with zero matches.

### Manual samples

Include representative samples for:

- each inference area;
- each training-only area;
- unmatched addresses;
- ambiguous addresses;
- broad postal-district-only addresses;
- county/context conflicts;
- overlapping-area cases;
- Dún Laoghaire accented and unaccented cases;
- Merrion versus Mount Merrion;
- Monkstown cases confirming inference scope;
- Dublin-area names that also exist elsewhere in Ireland.

A small sample per category is sufficient, but do not omit difficult cases.

### Test evidence

Include:

- exact test command;
- exit status;
- number of tests;
- captured test output path;
- requirements-to-test matrix.

---

## 15. Manual review before accepting mapping rules

Before finalising Checkpoint 3, inspect representative samples for every alias or rule with:

- unexpectedly high match volume;
- more than one candidate;
- county conflict;
- broad-area terminology;
- postal district-only evidence;
- non-unique locality names;
- zero or very low coverage;
- possible overlap with another canonical area.

Do not automatically resolve ambiguous rules solely to improve match coverage.

Prefer lower recall over systematically incorrect geography labels.

Where evidence is insufficient:

- leave records unmatched or ambiguous;
- document the unresolved rule;
- include the records in audit outputs.

---

## 16. Prohibited behaviour during Checkpoint 3

Do not:

- classify house versus apartment;
- infer detailed property type;
- detect or exclude multi-property transactions;
- remove duplicates;
- exclude non-full-market transactions;
- apply price thresholds;
- create `sale_price_eur` as a final modelling target;
- create a training-candidate dataset;
- create the final baseline-compatible CSV;
- run model validation;
- broaden the geography;
- use external geocoding services;
- use uncontrolled fuzzy matching;
- overwrite Checkpoint 2 outputs;
- silently resolve ambiguous area matches.

---

## 17. Acceptance criteria

Checkpoint 3 is complete when:

1. Address normalisation is deterministic and tested.
2. Raw addresses remain unchanged.
3. The canonical-area configuration contains only the locked areas.
4. Monkstown is configured as an inference area and not as training-only.
5. Alias matching is controlled and auditable.
6. Manual overrides are separate from code.
7. Overlapping matches are resolved deterministically or marked ambiguous.
8. Broad postal districts are not treated as canonical neighbourhoods.
9. Duplicate locality names outside Dublin are guarded against.
10. Every input row appears exactly once in the output.
11. Every Checkpoint 2 field is preserved.
12. New fields conform to an explicit physical schema.
13. The output Parquet is read back and validated.
14. Unmatched and ambiguous audit outputs are produced.
15. Counts are reported by area, scope, status, method, alias, year, and county.
16. Representative difficult cases are manually sampled.
17. Tests pass.
18. No Checkpoint 4 logic has been introduced.
19. The output remains clearly labelled geography-enriched rather than training-ready.

---

## 18. End-of-checkpoint response

At completion, report:

1. files created or updated;
2. commands run;
3. test results;
4. input and output row counts;
5. physical schema validation result;
6. address-normalisation quality counts;
7. geography match counts and percentages;
8. counts by canonical area;
9. unmatched count;
10. ambiguous count;
11. manual override count;
12. out-of-scope count;
13. alias rules added;
14. high-volume or risky aliases;
15. manual-review findings;
16. assumptions and deviations;
17. known limitations;
18. decisions requiring review before Checkpoint 4.

Stop after Checkpoint 3.
