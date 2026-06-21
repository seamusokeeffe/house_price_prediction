# System Architecture

## Architecture stance

The V1 system should be a local Python project with a deterministic batch pipeline and a simple local inference/reporting path.

The project should optimise for:

- trustworthy data construction
- honest validation
- confidence-aware reporting
- low maintenance
- fast iteration by one developer

It should not optimise for public deployment, UI polish, automated retraining, or broad geographic coverage in V1.

## MVP scope

### Must-have

- Ingest official transaction records for the locked training geography.
- Store raw and processed data in a local DuckDB plus Parquet workflow.
- Produce a canonical training table with structured house features.
- Train a baseline model and one main tree-based candidate on log sale price.
- Evaluate with temporal validation and segmented error analysis.
- Generate a local valuation summary for a manually reviewed listing input.
- Show median predicted sale price, interval, asking-price comparison, and confidence state.
- Mark unsupported or low-support cases clearly.

### Should-have

- Lightweight Daft URL parser for inference-time structured fields.
- Manual override step before valuation.
- Comparable-support features for confidence logic.
- Versioned model and report artifacts under `/artifacts`.
- Plain local command flow before any richer UI.

### Nice-to-have

- Local Streamlit prototype after the CLI/report flow is useful.
- Small number of enrichment features if data acquisition is straightforward.
- Experiment summary templates and benchmark snapshots.

## End-to-end flow

```text
Official transaction data
  -> raw local storage
  -> cleaning and address/geography normalisation
  -> canonical processed dataset
  -> deterministic feature pipeline
  -> train/evaluate baseline and tree model
  -> save model, metrics, feature metadata, interval method
  -> parse listing URL or accept manual listing fields
  -> user review/override
  -> feature construction for inference
  -> price distribution and confidence state
  -> local valuation report
```

## Component boundaries

### Data layer

Owns source acquisition, raw snapshots, cleaning, canonical schemas, and reproducible processed outputs.

The data layer should not decide model family or report language.

### Feature layer

Owns deterministic transformation from canonical records to model-ready features.

Feature code should be reusable for both training and inference. Avoid one-off notebook transformations becoming the only source of truth.

### Modelling layer

Owns target transformation, model training, validation, interval generation, and failure analysis.

The modelling layer should output both predictions and metadata needed for confidence reporting.

### Inference layer

Owns listing input collection, Daft parsing where available, manual review/override, and conversion into model features.

The inference layer should tolerate parser failure by allowing fully manual input.

### Reporting layer

Owns the local valuation summary and presentation of uncertainty.

The report should be decision-useful, not dashboard-like. It should avoid false precision and make unsupported cases visible.

## Fragile assumptions

The locked decisions are coherent. The fragile assumptions are practical rather than strategic:

- Official transaction records may not contain enough reliable structured detail for all target areas.
- Address and area normalisation may be harder than expected.
- Floor area, beds, baths, and property type may be incomplete or inconsistent across sources.
- The locked training geography may still be sparse for premium or unusual houses.
- A single model may underperform in distinct micro-markets; split models should wait for error analysis.
- Interval calibration may be weaker than point prediction accuracy at first.
- Daft parsing may be brittle, so manual override must be treated as core V1 behavior, not a fallback afterthought.

## Risks and mitigations

| Risk | Impact | Mitigation |
| --- | --- | --- |
| Sparse comparable sales in some areas | Overconfident estimates | Use confidence states and comparable-support thresholds. |
| Address/geography normalisation drift | Wrong area features and bad comparables | Define canonical area mapping before modelling. |
| Data leakage through time or derived features | Inflated validation performance | Use temporal validation and document feature availability. |
| Premium houses behave differently | Poor estimates for high-value searches | Segment by price band, size band, and area; avoid hard size filter. |
| Parser brittleness | Failed or wrong listing inputs | Require review/override and allow manual-only input. |
| Scope creep into UI/deployment polish | Delayed model learning | Ship local report first; defer polished Streamlit/public deploy. |
| Too many enrichment ideas early | Slow dataset construction | Build structured baseline first, then add only high-ROI features. |

## Phase architecture priorities

### Phase 1 - MVP foundation, Weeks 1-4

Must-have:

- Complete system, data, modelling, product, and deployment planning docs.
- Define canonical data sources and schema.
- Define cleaning and normalisation policy.
- Define validation and confidence design.
- Define V1 local report scope.

Should-have:

- Draft module boundaries for `src`.
- Draft artifact naming conventions.
- Create experiment and handoff templates.

Nice-to-have:

- Minimal CLI skeleton if planning finishes early.

### Phase 2 - Data and baseline modelling, Weeks 5-8

Must-have:

- Build raw-to-processed dataset workflow.
- Implement deterministic feature pipeline.
- Train simple baseline and first tree-based model.
- Run temporal validation and segment analysis.
- Draft interval and confidence method from observed errors.

Should-have:

- Save metrics and model artifacts in a repeatable structure.
- Generate first report from a fixed example input.

Nice-to-have:

- Compare a small number of enrichment features.

### Phase 3 - Usable local tool, Weeks 9-12

Must-have:

- Finalise model choice for V1.
- Finalise confidence and unsupported-case rules.
- Implement local inference flow with manual review/override.
- Produce local valuation report.
- Document local runtime and retraining steps.

Should-have:

- Lightweight Streamlit only if CLI/report flow is already useful.
- Model artifact versioning and repeatable report generation.

Nice-to-have:

- Report refinements based on actual house-search usage.

## Recommended specialist sequencing

1. Data Specialist: source stack, schema, cleaning, geography normalisation.
2. Modelling Specialist: validation protocol, experiment ladder, confidence rules.
3. Product Specialist: user flow, report schema, confidence explanation.
4. Deployment Specialist: local runtime, packaging, artifact conventions.

The System Architect prompt should be rerun only after one of those workstreams materially changes scope, risk, or sequencing.

