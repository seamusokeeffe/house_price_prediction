# Evaluation Protocol

## Objective

Evaluate whether the model gives useful, honest sale-price estimates for the locked inference geography.

Primary evaluation must estimate future transaction performance, not random-split interpolation.

## Target

- Train on `log_sale_price`.
- Convert predictions back to euro for reporting.
- Evaluate both log-scale and euro-scale behaviour where useful.

## Splitting strategy

Use temporal validation.

Recommended initial setup:

- train on earlier transactions
- validate on a later holdout period
- repeat across rolling recent windows
- compare 3-year, 5-year, and 10-year training windows

Do not use random train/test split as the main validation score. Random split can be used only for debugging.

## Metrics

Required overall metrics:

- median absolute percentage-style error
- MAE in euro
- RMSE or MAE on log price, optional but useful for training diagnostics
- interval coverage
- median interval width in euro

Required segment metrics:

- canonical area
- inference vs training-only geography
- property type
- size band
- price band
- large houses
- confidence state

## Benchmarking order

1. Recent grouped median baseline.
2. Regularised regression or comparable simple structured baseline.
3. Main tree-based model.
4. Interval/calibration layer.

The main model should not be accepted just because overall error improves. It must avoid materially worse performance in key inference segments unless the confidence logic catches those cases.

## Leakage checks

Before accepting an experiment, confirm:

- no future transactions influence training features for validation rows
- derived support features use only transactions available before the valuation date
- target-derived bands are used only for reporting/analysis, not as training inputs
- asking price is not used as a model feature for sale-price prediction
- source fields unavailable at inference are excluded from model inputs

## Reporting format

Each evaluation summary should include:

- dataset version
- feature set
- model configuration
- validation date range
- training date range
- overall metrics
- segment metrics
- worst segments
- interval coverage
- confidence-state breakdown
- decision: keep, reject, or investigate

