# Data Strategy

## Objective

Build the minimum reliable dataset needed to train and evaluate a local-first sale-price valuation model for the locked South Dublin house geography.

The V1 data strategy is deliberately conservative:

- official transaction sale prices are the target base
- structured features come first
- address/geography normalisation is a core data task
- commercial enrichment is deferred unless the baseline is clearly too weak
- Daft is used only for inference-time parsing, not training data scraping

## Minimum viable dataset

### Required records

The MVP training dataset should include residential sale transactions that can be mapped into the locked training geography and plausibly correspond to house property types.

Minimum viable record fields:

- transaction date
- sale price in euro
- raw address
- county/local authority if available
- new vs second-hand indicator if available
- VAT exclusive indicator if available
- canonical area
- geography scope flag: inference area, training-only area, out of scope
- inferred or joined property type
- beds, baths, and floor area where available
- derived time features
- derived location/support features
- record quality flags

### Required inference fields

The local inference path should accept these fields after parser/manual review:

- listing URL, optional
- asking price
- address or area
- canonical area
- property type
- beds
- baths
- floor area square metres
- BER, optional
- condition/renovation proxy, optional if structured
- notes, ignored by V1 model unless later promoted to structured fields

## Source stack priority

### Tier 1 - Required for MVP

1. Official Residential Property Price Register data.
2. Canonical geography lookup for the locked area list.
3. Manual listing input schema for inference.

### Tier 2 - Strong should-have

1. CSO Census 2022 small-area or electoral-division context for stable neighbourhood features.
2. Tailte Eireann / open boundary data for geography joins and QA.
3. Public open geospatial lookups where licensing is clear and maintenance burden is low.

### Tier 3 - Only if baseline needs it

1. Commercial address/geocoding datasets.
2. Paid GeoDirectory/Eircode style address matching.
3. Historical listing archives or scraped listing data.
4. Planning, schools, transport, crime, or amenities data.

## Canonical geography approach

V1 should use a project-owned canonical area lookup rather than relying on raw address strings directly.

Recommended approach:

1. Maintain a fixed `canonical_area` list matching the locked training and inference geography.
2. Map raw transaction addresses to canonical areas using deterministic string rules first.
3. Flag ambiguous, unmatched, or multi-area records for manual review.
4. Do not broaden geography to fix sparse data unless the decision log is explicitly updated.
5. Use geospatial joins only when open, reliable coordinates or boundaries are available.

This resolves handoff H-003 at strategy level: canonical mapping is required, deterministic first, and manual review is acceptable for ambiguous MVP records.

## Data versioning

Use simple local snapshot versioning:

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

Each processed dataset version should include:

- input source snapshot date
- transformation code version or script name
- row counts by stage
- excluded-record counts by reason
- area/property-type/size-band support summary
- schema version

## First tasks

1. Confirm the exact official transaction data access path and export format.
2. Create the canonical geography lookup for all locked training and inference areas.
3. Define the raw transaction schema and processed transaction schema.
4. Build a manual QA list for unmatched or ambiguous addresses.
5. Produce a support-count report by area, recency, price band, and likely property type.

## Defer

- Paid address products.
- Bulk Daft scraping.
- Image-derived property quality features.
- Text-heavy listing descriptions.
- Amenity and travel-time enrichment.
- Complex geospatial interpolation.

These may help later, but they are not first-order blockers for proving whether the core valuation loop can work.

