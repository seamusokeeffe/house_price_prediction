# PPR Source Profile - Snapshot 20260621

## Scope

This profile covers the raw source file:

```text
data/raw/ppr/20260621/PPR-ALL.csv
```

Checkpoint 1 only. No cleaning, filtering, or processed dataset generation has been applied.

## File Profile

| Item | Observed value |
| --- | --- |
| Snapshot date | 20260621 |
| File size | 108,186,632 bytes |
| Last modified | 2026-06-17 17:49:26 local filesystem time |
| SHA256 | `79922A9924E1E9744BD46B3CA674E82CB736FD5139A0CA53B5AACE84FFB9F50E` |
| Delimiter | Comma |
| Quoting | Double-quoted CSV fields |
| Header row | Present |
| Byte order mark | Not present; first bytes are `44617465` |
| Encoding | Not valid UTF-8; reads cleanly as Windows-1252 / CP1252 |
| Row count excluding header | 790,415 |

Encoding evidence:

- `utf-8-sig` and `utf-8` fail on byte `0x80` in the price header.
- CP1252 reads the euro symbol in `Price (€)` correctly.

## Observed Source Schema

| Source column | Null count | Null rate | Notes |
| --- | ---: | ---: | --- |
| `Date of Sale (dd/mm/yyyy)` | 0 | 0.0000% | All rows parsed with `%d/%m/%Y`. |
| `Address` | 0 | 0.0000% | Free-text address. |
| `County` | 0 | 0.0000% | Nationwide county field, not restricted to Dublin. |
| `Eircode` | 552,808 | 69.9390% | Too sparse to rely on for V1 geography. |
| `Price (€)` | 0 | 0.0000% | Currency-formatted string in CP1252 source. |
| `Not Full Market Price` | 0 | 0.0000% | Negative phrasing; raw `No` means not flagged as non-market. |
| `VAT Exclusive` | 0 | 0.0000% | Requires explicit VAT-adjustment trace fields. |
| `Description of Property` | 0 | 0.0000% | Broad new/second-hand dwelling house/apartment descriptions only. |
| `Property Size Description` | 737,570 | 93.3143% | Sparse bucket field, not exact floor area. |

## Date Profile

| Metric | Value |
| --- | --- |
| Parsed rows | 790,415 |
| Parse failures | 0 |
| Minimum date | 2010-01-01 |
| Maximum date | 2026-06-12 |

## Price Profile

Prices below are parsed from the raw currency string without VAT adjustment.

| Metric | Value |
| --- | ---: |
| Parsed rows | 790,415 |
| Parse failures | 0 |
| Zero or negative prices | 0 |
| Minimum | 5,001.00 |
| 0.1 percentile | 8,000.00 |
| 1 percentile | 24,000.00 |
| 5 percentile | 50,000.00 |
| 25 percentile | 144,914.39 |
| Median | 242,000.00 |
| 75 percentile | 361,233.48 |
| 95 percentile | 698,250.00 |
| 99 percentile | 1,409,692.00 |
| 99.9 percentile | 6,206,094.38 |
| Maximum | 387,665,198.00 |
| Mean | 317,600.21 |

The highest prices are dominated by clear development, block, apartment, or bulk-looking records. These support creating a multi-property audit process, but they do not support using a single global maximum-price cutoff.

## Status Field Values

### Not Full Market Price

| Raw value | Count | Interpretation for proposed processed field |
| --- | ---: | --- |
| `No` | 750,175 | `is_full_market_price = true` |
| `Yes` | 40,240 | `is_full_market_price = false` |

No missing or unrecognised values were observed in this snapshot, but the ingestion logic should still handle them explicitly.

### VAT Exclusive

| Raw value | Count |
| --- | ---: |
| `No` | 652,354 |
| `Yes` | 138,061 |

Raw price summary by VAT flag:

| VAT Exclusive | Count | Minimum | Median | Maximum |
| --- | ---: | ---: | ---: | ---: |
| `No` | 652,354 | 5,001.00 | 225,000.00 | 189,392,525.60 |
| `Yes` | 138,061 | 5,179.00 | 304,375.00 | 387,665,198.00 |

## Property Description Values

| Raw value | Count |
| --- | ---: |
| `Second-Hand Dwelling house /Apartment` | 649,947 |
| `New Dwelling house /Apartment` | 140,419 |
| Irish-language second-hand dwelling house/apartment value | 45 |
| Irish-language new dwelling house/apartment value | 3 |
| Mojibake/corrupted Irish-language new dwelling value | 1 |

The source does not reliably distinguish houses from apartments, nor does it provide detached, semi-detached, terraced, or end-of-terrace labels.

## Property Size Description Values

| Raw value | Count |
| --- | ---: |
| Blank | 737,570 |
| `greater than or equal to 38 sq metres and less than 125 sq metres` | 38,106 |
| `greater than 125 sq metres` | 6,847 |
| `greater than or equal to 125 sq metres` | 4,622 |
| `less than 38 sq metres` | 3,267 |
| Irish-language or mojibake size bucket values | 3 |

This field is suitable only as a sparse source-size bucket, not as `floor_area_sqm`.

## County Coverage

Top observed counties:

| County | Count |
| --- | ---: |
| Dublin | 247,359 |
| Cork | 87,549 |
| Kildare | 42,962 |
| Galway | 38,166 |
| Meath | 32,886 |
| Limerick | 29,029 |
| Wexford | 27,633 |
| Wicklow | 26,730 |
| Louth | 22,118 |
| Waterford | 21,657 |

Dublin-specific status counts:

| Field | Raw value | Dublin count |
| --- | --- | ---: |
| `Not Full Market Price` | `No` | 236,469 |
| `Not Full Market Price` | `Yes` | 10,890 |
| `VAT Exclusive` | `No` | 203,964 |
| `VAT Exclusive` | `Yes` | 43,395 |

## Rough Locked-Geography Signal

A simple read-only alias scan against the locked area names found many possible matches, but it also showed why the real implementation must use county constraints, alias priority, ambiguity handling, and manual overrides:

- Dublin rows: 247,359.
- Dublin rows unmatched by simple alias scan: 184,032.
- Simple alias matches can overcount due to overlapping names, nested areas, and non-Dublin locations with the same names.
- Examples of cross-county false positives include `Donnybrook, Douglas`, `Blackrock Court, Ballina`, `Thomastown, Kilkenny`, and `Sandycove, Kinsale`.

The source supports deterministic geography mapping only through carefully controlled address rules; uncontrolled fuzzy matching should not be used for the first pass.

## Extreme Price Examples

Lowest raw-price examples include non-full-market records, very low second-hand records, and repeated low-price new-build rows at the same development. These should be flagged through target-validity, full-market, duplicate-like, and multi-property review rules before any modelling use.

Highest raw-price examples include:

| Date | Address signal | County | Raw price | VAT exclusive | Description |
| --- | --- | --- | ---: | --- | --- |
| 2024-10-17 | Tinakilly Park, Rathnew | Wicklow | 387,665,198.00 | Yes | New dwelling house/apartment |
| 2023-02-10 | O'Devaney Gardens, Arbour Hill | Dublin | 225,000,000.00 | Yes | New dwelling house/apartment |
| 2026-01-27 | Montpelier, Dublin 7 | Dublin | 225,000,000.00 | Yes | New dwelling house/apartment |
| 2026-03-31 | `BLOCK A B AND C, NEWMARKET YARDS` | Dublin | 189,392,525.60 | No | Second-hand dwelling house/apartment |
| 2020-07-17 | `Apartments 1 - 186 ... Apartments 1-182 ...` | Dublin | 182,378,854.63 | Yes | New dwelling house/apartment |

These examples support high-precision multi-property rules based on address structure and development language, not a price-only exclusion.
