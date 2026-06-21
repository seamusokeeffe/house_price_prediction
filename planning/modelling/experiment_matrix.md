# Experiment Matrix

## Experiment ladder

| ID | Name | Goal | Model | Dataset | Success signal |
| --- | --- | --- | --- | --- | --- |
| M-00 | Support audit | Check sample size and coverage | none | processed transactions | clear counts by area/type/size/price/recency |
| M-01 | Recent median baseline | Establish simple benchmark | grouped median | 3/5/10-year windows | stable baseline and obvious weak segments |
| M-02 | Regularised regression | Test simple structured signal | ridge/elastic net or similar | core structured features | beats M-01 on temporal validation |
| M-03 | Main tree candidate | Main V1 model candidate | gradient-boosted trees | core structured features | beats M-02 without bad segment regressions |
| M-04 | Interval comparison | Pick interval method | residual vs quantile | M-03 predictions | acceptable coverage and width tradeoff |
| M-05 | Data policy sensitivity | Resolve data handoffs | M-03 variants | include/exclude flags | clear policy for unknown type/new-build/VAT |
| M-06 | Confidence calibration | Tune confidence states | chosen model | validation predictions | confidence state aligns with error/coverage |

## Required segment reports

Every predictive experiment from M-01 onward should report:

- all validation rows
- inference geography only
- training-only geography
- canonical area
- property type
- size band
- price band
- large houses
- recent vs older transactions

## Experiment record template

Add each completed run to `planning/modelling/experiment_log.md` with:

- experiment ID
- dataset version
- feature set version
- validation split
- overall metrics
- segment failures
- interval coverage if applicable
- decision

## Stop/go criteria

Proceed from baseline to main model only after:

- processed dataset QA passes
- leakage review is complete
- support audit shows enough inference-area coverage to evaluate

Proceed to product/reporting integration only after:

- chosen model has temporal validation results
- interval method has validation coverage summary
- confidence states identify low-support cases instead of hiding them

