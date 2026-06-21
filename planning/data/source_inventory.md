# Source Inventory

## Source priority summary

| Priority | Source | Role | V1 decision |
| --- | --- | --- | --- |
| 1 | Residential Property Price Register | Sale-price target base | Required |
| 1 | Project canonical area lookup | Locked geography mapping | Required |
| 1 | Manual listing input | Inference feature source | Required |
| 2 | CSO Census 2022 SAPS / data tables | Stable area context | Should-have |
| 2 | Tailte Eireann open boundaries / GeoHive | Geography QA and joins | Should-have |
| 3 | GeoDirectory / Eircode commercial data | Address matching | Defer |
| 3 | Historical listing data | Property attributes and asking history | Defer |
| 3 | Amenities, schools, transport, planning | Enrichment features | Defer |

## Required sources

### Residential Property Price Register

- Owner: Property Services Regulatory Authority / Irish official residential sale price register.
- Use: transaction date, price, address, property status fields where available.
- Strengths: official sale-price target source; direct alignment with locked target decision.
- Weaknesses: address strings may be messy; property type, size, beds, baths, and condition may be absent.
- V1 handling: ingest as raw target base, clean conservatively, and add quality flags.

### Project canonical area lookup

- Owner: this repository.
- Use: map raw addresses and inference inputs to the locked training/inference geography.
- Strengths: makes project scope explicit and reproducible.
- Weaknesses: requires manual review for ambiguous records.
- V1 handling: create a small maintained table with aliases and scope flags.

### Manual listing input

- Owner: local product workflow.
- Use: structured inference fields after user review or direct manual entry.
- Strengths: robust when parsing fails; supports first-class manual path.
- Weaknesses: user-entered data can be inconsistent.
- V1 handling: validate required fields and keep raw/manual override values for reporting.

## Should-have sources

### CSO Census 2022 small-area statistics

- Owner: Central Statistics Office.
- Use: stable local context features such as housing stock and area demographics.
- Strengths: official, open, stable, useful for area-level context.
- Weaknesses: joins require boundaries or geography crosswalks; risk of adding complexity early.
- V1 handling: use only if canonical geography mapping is stable.

### Tailte Eireann open data / GeoHive boundaries

- Owner: Tailte Eireann.
- Use: open boundaries and geography QA where licensing allows.
- Strengths: official geospatial reference.
- Weaknesses: address-level products may be commercial or operationally heavier than needed.
- V1 handling: use open boundary data for QA; defer paid address matching.

## Deferred sources

### GeoDirectory / Eircode address products

- Reason to defer: likely useful for address precision, but may add cost, licensing, and integration work.
- Revisit when: raw address matching blocks useful support counts or confidence logic.

### Historical listing archives

- Reason to defer: risks drifting into scraping and asking-price modelling.
- Revisit when: official target data proves too sparse on structured attributes.

### Amenities, schools, transport, planning, BER databases

- Reason to defer: plausible incremental value but high integration surface.
- Revisit when: baseline error analysis shows specific missing signal that these sources could address.

## Source QA checklist

- Does the source directly support the locked V1 target or core feature set?
- Is licensing compatible with local personal use?
- Can it be snapshotted locally?
- Can it be joined deterministically?
- Does it create leakage risk?
- Does it materially improve the MVP before model/report quality is known?

