# Assumptions Log

Use this file for assumptions that affect planning or implementation but are not locked decisions yet.

## Status legend

- Open
- Testing
- Accepted
- Rejected
- Superseded

## Template

```markdown
### A-001 - Short assumption title
- Status: Open
- Owner: Workstream or person
- Assumption: What is being assumed.
- Why it matters: What could break if this is false.
- Validation path: How to check it.
- Related decisions: D-###
- Notes:
```

## Current assumptions

### A-001 - Official transaction data can support MVP valuation ranges
- Status: Open
- Owner: Data / Modelling
- Assumption: Available transaction records can be cleaned and enriched enough to support useful local valuation ranges for the locked geography.
- Why it matters: If the usable sample is too sparse or noisy, the MVP needs stronger unsupported-case logic or narrower confidence claims.
- Validation path: Build the minimum viable dataset, inspect counts by area/type/size band, and run the first temporal baseline.
- Related decisions: D-012, D-015, D-017
- Notes:

### A-002 - Structured listing fields are enough for V1 decision support
- Status: Open
- Owner: Product / Modelling
- Assumption: Area, property type, beds, baths, floor area, asking price, and derived location/time features can produce a useful first report without image or text-heavy modelling.
- Why it matters: This supports the V1 scope restriction and keeps implementation lightweight.
- Validation path: Compare baseline performance and user usefulness after the first modelling pass.
- Related decisions: D-008, D-019
- Notes:

### A-003 - Locked training geography provides enough comparable support
- Status: Open
- Owner: Data / Modelling
- Assumption: The locked training geography gives enough nearby and similar house transactions to support the locked inference geography.
- Why it matters: Sparse areas or unusual property bands may need stronger unsupported-case handling.
- Validation path: Count usable records by area, property type, size band, price band, and recency.
- Related decisions: D-009, D-010, D-017, D-018
- Notes:

### A-004 - Address and area normalisation can be made reliable enough for MVP
- Status: Open
- Owner: Data
- Assumption: Area names, address strings, and any geospatial joins can be normalised well enough for modelling and confidence support.
- Why it matters: Poor geography mapping can corrupt features and comparable-support logic.
- Validation path: Define canonical area mapping and manually inspect ambiguous or unmatched records.
- Related decisions: D-009, D-010, D-014
- Notes:

### A-005 - Paid address matching is not required for the first useful dataset
- Status: Open
- Owner: Data
- Assumption: Deterministic area aliases plus manual review of ambiguous records will be enough to build the MVP dataset without paid address products.
- Why it matters: Paid address data could consume budget and add licensing complexity early.
- Validation path: Measure unmatched and ambiguous transaction rates after the first raw-to-interim pass.
- Related decisions: D-024, D-026
- Notes:

### A-006 - Area-level enrichment can wait until the first baseline
- Status: Open
- Owner: Data / Modelling
- Assumption: The first baseline should be trained on core structured fields before adding CSO, boundary, amenity, or transport enrichment.
- Why it matters: Enrichment can create integration drag before the project knows its baseline failure modes.
- Validation path: Run baseline and segment error analysis, then add only enrichment that addresses observed error.
- Related decisions: D-008, D-015, D-024
- Notes:
