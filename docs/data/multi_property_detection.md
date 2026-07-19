# PPR Multi-Property Detection

## Purpose

Checkpoint 4 identifies transactions that may contain more than one dwelling.
It uses transparent address rules, never an opaque classifier or price cutoff.
The reviewed configuration is `config/multi_property_rules.csv`; structural
matching code is in `src/house_valuation/data/multi_property.py`.

## Evidence tiers

- `high` plus `auto_exclude`: explicit plural unit ranges, explicit lists or
  quantities, multiple distinct blocks, multiple numbered postal addresses,
  inclusive ranges, and explicit bulk/portfolio language.
- `medium` plus `review_only`: generic numeric ranges, singular unit ranges,
  and development/scheme/phase wording.
- No hit: `multi_property_action = none` and
  `single_dwelling_confidence = high` for this rule system only.

`single_dwelling_confidence` is a deterministic evidence label, not a
statistical probability and not proof that the row is a house.

## Deliberate non-rules

The following never establish multi-property status alone:

- transaction price;
- commas or semicolons;
- any hyphen;
- an estate or development name;
- one `UNIT` token;
- VAT-exclusive status;
- new-build status.

Observed semicolons were commonly typos. Numeric ranges included individual
apartments inside buildings such as `13-17 Pembroke Road`. Development phases
commonly contained an identifiable individual dwelling. These findings are why
the corresponding evidence is review-only or omitted.

## Multiple hits

All matching IDs and descriptions are retained in stable rule-ID order. Highest
severity and action win deterministically:

```text
none < review_only < auto_exclude
```

Excluded and flagged rows remain in the cleaning-assessed Parquet and audit CSVs.
