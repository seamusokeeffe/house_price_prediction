# MVP Code Structure

This implementation pass creates the smallest credible code skeleton for the planned local-first valuation tool.

## Package layout

```text
src/house_valuation/
  config.py
  data/
    loaders.py
    filters.py
  features/
    build_features.py
  models/
    baseline.py
  evaluation/
    metrics.py
    validation.py
  inference/
    schemas.py
    predict.py
  reporting/
    build_report.py
scripts/
  train_baseline.py
  run_validation.py
```

## Current vertical slice

The current code can:

- load a processed modelling CSV
- validate required training columns
- filter to supported V1 house scope, with unknown plausible house type retained
- prepare `log_sale_price`
- train a grouped median baseline
- run a temporal validation split
- calculate basic validation metrics
- predict one manually supplied inference record
- build a structured report payload

## Baseline model

The implemented baseline follows the modelling plan:

1. median log price by canonical area and property type
2. back off to canonical area
3. back off to property type
4. back off to global median

## Current limitations

- CSV is the only implemented loader.
- DuckDB and Parquet are planned but not implemented in this skeleton.
- Intervals are represented in the schema but not calibrated yet.
- Confidence is a support-count placeholder and must be validated later.
- No Daft parser or UI is implemented.

