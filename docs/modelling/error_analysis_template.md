# Error Analysis Template

Use this template after each meaningful modelling experiment.

## Experiment

- Experiment ID:
- Dataset version:
- Feature set:
- Model:
- Validation period:
- Training period:

## Overall metrics

- Median percentage-style error:
- MAE EUR:
- Log-scale MAE:
- Interval coverage:
- Median interval width EUR:

## Segment results

| Segment | Rows | Median error | MAE EUR | Coverage | Notes |
| --- | ---: | ---: | ---: | ---: | --- |
| Inference geography | | | | | |
| Training-only geography | | | | | |
| Large houses | | | | | |
| Premium price band | | | | | |
| Low confidence | | | | | |
| Not enough support | | | | | |

## Worst segments

List the worst 5-10 segments by:

- high median error
- high MAE EUR
- poor interval coverage
- suspiciously narrow intervals
- unexpectedly high error in normal-confidence cases

## Failure modes

Check all that apply:

- sparse comparable support
- poor area mapping
- missing floor area
- unknown property type
- large-house extrapolation
- premium-market underprediction
- new-build or VAT status mismatch
- temporal market shift
- likely non-standard transaction

## Decision

- Keep:
- Reject:
- Investigate:
- Required follow-up:

