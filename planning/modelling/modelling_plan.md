# Modelling Plan

## Objective

Predict plausible transaction sale prices for houses in the locked inference geography.

The model should:

- train on log sale price
- report euro-scale predictions after inverse transform
- produce a median estimate and interval
- expose confidence state based on model evidence and comparable support
- avoid false precision for sparse or unusual properties

The modelling goal is decision support, not automated bidding advice.

## Training geography assessment

The locked training geography is a reasonable first expansion around the inference geography. It adds adjacent and related South/South-East Dublin areas without drifting into a citywide model.

Strengths:

- increases training support for nearby markets
- keeps training examples plausibly relevant
- supports one model across house types first
- allows segment-level checks for inference vs training-only areas

Risks:

- premium inference areas may still have sparse comparable sales
- training-only areas may not transfer cleanly to the highest-value micro-markets
- unknown property type and missing floor area could become material
- area labels may encode too much if canonical mapping is noisy

Required validation:

- report metrics separately for inference areas and training-only areas
- report support counts by area, property type, size band, price band, and recency
- flag low-support areas before trusting intervals
- evaluate large houses separately; do not filter them out by default

## Feature usage strategy

### MVP features

Use only structured features that can be produced for training and inference:

- canonical area
- geo scope
- property type, including unknown only if retained by policy
- beds
- baths
- floor area square metres
- BER rating if available enough
- transaction date features for training/validation
- valuation date features where needed for inference
- missingness flags
- comparable-support counts

### Approved handling of data handoffs

Unknown property type:

- retain unknown-but-plausible house records for the first broad baseline with an `unknown` category and missingness flag
- run a sensitivity check excluding unknown property type records
- if unknown type materially hurts validation, exclude or downweight in the main V1 training table

VAT-exclusive and new-build records:

- retain with flags for the first broad baseline if target cleaning permits
- run sensitivity checks excluding VAT-exclusive and new-build records
- do not make them the default exclusion until error analysis shows they distort resale valuation

### Defer

- image features
- listing description embeddings
- automated text quality scoring
- heavy geospatial kernels
- separate models per house type
- deep learning
- automated model ensembling

## Recommended baseline

Baseline 1 should be a transparent grouped benchmark:

- predict median log sale price by canonical area and broad property type where support exists
- back off to broader area group or global median when support is weak
- optionally adjust with simple floor-area bands if enough data exists

Purpose:

- expose data sparsity
- set a credible lower benchmark
- reveal whether canonical area mapping is usable

## Recommended sweet-spot model

The main V1 candidate should be a gradient-boosted tree model on log sale price, likely LightGBM, XGBoost, or scikit-learn HistGradientBoosting depending on packaging constraints.

Rationale:

- handles nonlinear relationships and interactions
- works well with tabular structured data
- supports missingness reasonably
- is inspectable enough for a solo local project
- avoids premature complexity

Use regularisation and conservative tuning. Do not chase leaderboard-style improvements before validation and interval quality are trustworthy.

## Experiment ladder

1. Data support audit
   - no predictive model
   - counts and distributions by geography, recency, size, price, property type

2. Naive recent median baseline
   - median log price by area/property type with backoff
   - establishes first benchmark

3. Linear or regularised regression baseline
   - log sale price target
   - structured features and missingness flags
   - checks whether simple smooth effects are enough

4. Main tree-based model
   - gradient-boosted trees or histogram gradient boosting
   - structured features only
   - conservative hyperparameter search

5. Interval method comparison
   - residual-based intervals vs quantile model
   - calibrate by temporal validation

6. Sensitivity checks
   - 3-year vs 5-year vs 10-year windows
   - exclude vs retain unknown property type
   - exclude vs retain new-build/VAT-exclusive records
   - with vs without small area-level enrichment if available

7. Confidence and unsupported-case validation
   - compare confidence states to observed error/coverage
   - tune comparable-support thresholds

## MVP modelling tasks

Must-have:

- support audit
- baseline model
- main tree-based candidate
- temporal validation
- segment error analysis
- first interval method
- first confidence rules

Should-have:

- sensitivity checks for recent windows and transaction subsets
- calibration summary by confidence state
- feature importance or partial-dependence sanity checks

Nice-to-have:

- area-level enrichment comparison
- lightweight conformal interval experiment

## Later modelling tasks

Defer:

- separate models by house type
- micro-market clustering
- text/image modelling
- advanced spatial smoothing
- automated retraining
- complex ensembling

