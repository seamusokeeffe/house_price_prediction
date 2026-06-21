# Interval and Confidence Method

## Goal

Produce a plausible sale-price interval and confidence state that are useful for personal decision support.

Intervals should be calibrated enough to avoid false certainty. Confidence should reflect both model uncertainty and comparable support.

## Recommended MVP interval approach

Start with residual-calibrated intervals on log price:

1. Train the chosen point model on log sale price.
2. Generate temporal validation residuals.
3. Estimate residual quantiles globally and by broad segment where support allows.
4. Add residual quantiles to the predicted log price.
5. Convert lower, median, and upper values back to euro.
6. Validate interval coverage overall and by segment.

Use this before a more complex quantile model because it is easier to audit and calibrate.

## Alternative to compare

Compare against quantile tree models only after the residual method has a benchmark.

Quantile models are attractive but can produce poorly calibrated intervals in sparse segments. They should be accepted only if temporal validation coverage and interval widths improve.

## Suggested interval levels

For V1, use one primary interval:

- central 80% interval for the report

Optional internal tracking:

- central 50% interval for model diagnostics
- central 90% interval for stress testing

## Confidence states

### Normal confidence

Use when:

- property is within locked inference geography
- required fields are present
- comparable support is adequate
- validation segment performance is not a known failure
- prediction is not extrapolating far outside training ranges

### Low confidence

Use when:

- support exists but is thin
- key fields are missing or imputed
- property is large, premium, unusual, or in a weak segment
- interval is unusually wide
- validation segment coverage is poor

### Not enough comparable support

Use when:

- canonical area cannot be matched reliably
- property is outside locked inference geography
- too few recent nearby/similar transactions exist
- floor area or property type is too far outside training support
- required inference fields are missing

## Initial comparable-support thresholds

Use these as starting thresholds, then tune using validation:

- normal confidence: at least 15 comparable transactions in the last 5 years across canonical area or close backoff group, with at least 5 in a similar size band and broad property type
- low confidence: 5 to 14 comparable transactions in the last 5 years, or enough support only after broad backoff
- not enough comparable support: fewer than 5 comparable transactions after allowed backoff, or no reliable canonical area match

Comparable definition for V1:

- same canonical area if possible
- same broad property type group where possible
- floor area within a broad size band
- transaction date within 5 years, with 10-year backoff for support diagnostics only

## Calibration checks

Report coverage:

- overall
- by confidence state
- by inference area
- by property type
- by size band
- by price band

If low-confidence intervals do not have worse error or wider uncertainty than normal-confidence intervals, confidence rules are not doing useful work and should be revised.

