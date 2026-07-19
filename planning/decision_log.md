# Decision Log

This file records key project decisions, assumptions, and locked defaults.

---

## Status legend
- Proposed
- Accepted
- Locked
- Revisit later

---

## Core product decisions

### D-001 — Predict transaction sale price, not asking price
- Status: Locked
- Rationale: The tool is intended to estimate likely market sale value and compare that to the asking price.
- Notes: Asking price remains an input for reporting and comparison, not the target.

### D-002 — Predict log sale price
- Status: Locked
- Rationale: Log transformation should improve modelling stability and handle skew in sale prices.
- Notes: Convert back to euro scale for reporting.

### D-003 — Local-first V1
- Status: Locked
- Rationale: Simpler, cheaper, and better aligned with project constraints.
- Notes: Public web deployment is out of scope for V1.

### D-004 — Daft is inference-time parser only in V1
- Status: Locked
- Rationale: Avoid large-scale scraping scope in the first version.
- Notes: Daft is used to parse structured listing inputs on demand.

### D-005 — User can review / override parsed fields
- Status: Locked
- Rationale: Parser brittleness is expected, and user correction improves trust and usability.

---

## Scope decisions

### D-006 — Houses only in V1
- Status: Locked
- Included:
  - House
  - Detached House
  - Semi-Detached House
  - Terraced House
  - End of Terrace House
- Excluded:
  - Apartments
  - Other non-house property types

### D-007 — One model across house types first
- Status: Locked
- Rationale: Simpler initial setup.
- Notes: Property type will be included as a feature. Splitting later depends on error analysis.

### D-008 — Structured features first
- Status: Locked
- Rationale: Highest ROI for MVP.
- Notes: Image modelling and text-heavy modelling are deferred.

---

## Geography decisions

### D-009 — Inference geography
- Status: Locked
- Areas:
  - Sandymount
  - Ballsbridge
  - Ranelagh
  - Rathmines
  - Rathgar
  - Terenure
  - Donnybrook
  - Milltown
  - Dartry
  - Clonskeagh
  - Windy Arbour
  - Churchtown
  - Dundrum
  - Goatstown
  - Foxrock
  - Seapoint
  - Blackrock
  - Booterstown
  - Merrion
  - Mount Merrion
  - Kilmacud
  - Stillorgan
  - Ardilea

### D-010 — Training geography
- Status: Locked
- Areas:
  - all inference geography areas
  - plus Harolds Cross
  - Kimmage
  - Templeogue
  - Rathfarnham
  - Knocklyon
  - Butterfield
  - Edmondstown
  - Ballyboden
  - Scholarstown
  - Ballinteer
  - Balally
  - Sandyford
  - Kilgobbin
  - Carrickmines
  - Kilternan
  - Deansgrange
  - Cabinteely
  - Loughlinstown
  - Shankill
  - Ballybrack
  - Killiney
  - Kilbogget
  - Glenageary
  - Thomastown
  - Dalkey
  - Woodpark
  - Monkstown
  - Sandycove
  - Dún Laoghaire

### D-011 — Do not broaden geography further for now
- Status: Locked
- Rationale: Keep the training population relevant to the inference problem.

---

## Data and modelling decisions

### D-012 — Official transaction data is the target base
- Status: Locked
- Rationale: Better target quality than asking prices.

### D-013 — No hard >200m² training filter
- Status: Locked
- Rationale: Retain useful premium-house data where possible.
- Notes: Must evaluate large-house performance separately.

### D-014 — Explicit transaction cleaning policy required
- Status: Locked
- Includes:
  - obvious outlier filtering
  - suspicious low/high filtering
  - duplicate-like record handling
  - exclusion of non-standard transactions if detectable
  - handling incomplete location parsing
  - exclusion of dubious sales where possible

### D-015 — Core evaluation metrics
- Status: Locked
- Metrics:
  - median absolute percentage-style error
  - MAE in euros
  - interval coverage
  - segmented performance by area, property type, size band, and price band

### D-016 — Time treatment
- Status: Locked
- Approach:
  - rolling recent-window evaluation
  - compare 3-year / 5-year / 10-year windows
  - temporal weighting only later as a sensitivity experiment

### D-017 — Confidence states
- Status: Locked
- States:
  - normal confidence
  - low confidence
  - not enough comparable support

### D-018 — High confidence should depend partly on comparable support
- Status: Locked
- Factors:
  - recent nearby transactions
  - same broad property type
  - similar size band

---

## Architecture decisions

### D-019 — Architecture direction
- Status: Locked
- Stack:
  - local Python project
  - DuckDB + Parquet data layer
  - deterministic batch feature pipeline
  - tabular baseline + main tree-based model
  - quantile or interval-based uncertainty layer
  - local report output
  - optional lightweight Streamlit later

---

## Codex workflow decisions

### D-020 - Use one root AGENTS.md for initial Codex instructions
- Status: Locked
- Rationale: A single durable instruction file is enough for the current solo planning phase and avoids contradictory layered guidance.
- Notes: Add subdirectory `AGENTS.md` files only when implementation or artifact handling needs directory-specific rules.

### D-021 - Use specialist prompts as role briefs
- Status: Locked
- Rationale: The five workstreams need different scopes and deliverables, but not enough repetition exists yet to justify custom skills or subagents.
- Notes: Store reusable role prompts in `/prompts` and invoke them directly from Codex.

### D-022 - Defer Codex skills and subagents
- Status: Locked
- Rationale: The project is still defining workflows. Automation should wait until experiment, data validation, or report-generation routines are repeated and stable.
- Notes: Revisit after the first modelling and reporting loop.

### D-023 - Use explicit assumptions, handoff, and experiment logs
- Status: Locked
- Rationale: These lightweight logs reduce repeated context setting between specialist prompts without adding heavy process.
- Notes: Use `/planning/assumptions_log.md`, `/planning/specialist_handoffs.md`, and `/planning/modelling/experiment_log.md`.

---

## System architecture decisions

### D-024 - Build the canonical local data workflow before UI polish
- Status: Locked
- Rationale: Dataset reliability and validation quality are the biggest V1 risks. UI polish cannot compensate for weak training data or overconfident estimates.
- Notes: The local report can be plain markdown/HTML initially.

### D-025 - Treat manual inference input as a first-class path
- Status: Locked
- Rationale: Daft parsing is intentionally light in V1 and may fail or parse fields incorrectly. The tool must remain usable with manual entry and review.
- Notes: The parser should accelerate input, not become a hard dependency for valuation.

### D-026 - Keep one deterministic feature path for training and inference
- Status: Locked
- Rationale: Separate ad hoc transformations increase leakage and mismatch risk.
- Notes: Training and inference should share feature definitions wherever practical.

### D-027 - Use a project-owned canonical area lookup
- Status: Locked
- Rationale: Raw address and area strings will not be stable enough on their own for modelling, segmentation, or confidence support.
- Notes: The lookup should include locked area names, aliases, and scope flags for inference vs training-only areas.

### D-028 - Defer paid address and broad enrichment sources
- Status: Locked
- Rationale: The first data milestone should prove the target dataset and validation loop before adding cost, licensing, or complex joins.
- Notes: Revisit after support counts and first baseline error analysis.

---

## Modelling decisions

### D-029 - Use temporal validation as the primary evaluation design
- Status: Locked
- Rationale: The tool needs to estimate future transaction performance. Random splits would overstate usefulness for a market that changes over time.
- Notes: Random splits may be used only for debugging.

### D-030 - Use grouped recent median as the first modelling baseline
- Status: Locked
- Rationale: A grouped median benchmark exposes data sparsity and sets a transparent lower bar before fitting complex models.
- Notes: Use canonical area/property type backoff where support is thin.

### D-031 - Use a tree-based tabular model as the V1 sweet-spot candidate
- Status: Locked
- Rationale: Gradient-boosted or histogram tree models are strong for structured tabular data without requiring image/text modelling or heavy infrastructure.
- Notes: Exact library can be decided during implementation based on packaging constraints.

### D-032 - Start with residual-calibrated intervals
- Status: Locked
- Rationale: Residual-calibrated intervals are easier to audit and calibrate than quantile models in sparse segments.
- Notes: Compare quantile models later only if residual intervals are inadequate.

### D-033 - Confidence states must be validated against observed error and coverage
- Status: Locked
- Rationale: Confidence labels are only useful if they correspond to real differences in uncertainty and support.
- Notes: Initial comparable-support thresholds are documented in `docs/modelling/interval_confidence_method.md`.

### D-034 - PPR Checkpoint 4 conservative cleaning policy

- Status: Accepted
- Decision: Auto-exclude only high-precision multi-property evidence; keep
  medium evidence review-only. For exact raw-fingerprint duplicate groups,
  retain the lowest source row and exclude later occurrences while preserving
  all rows in the cleaning-assessed dataset. Explicit apartment/flat/APT-with-ID
  records are outside house scope; ambiguous UNIT and otherwise unresolved PPR
  property scope remain eligible with flags under H-005. Preserve every
  applicable exclusion reason and select the primary reason using the documented
  deterministic priority.
- Rationale: This balances single-house purity with recall while keeping every
  consequential decision inspectable and reversible before Checkpoint 5.
- Approved by: User during Checkpoint 4 evidence review on 2026-07-18.

---

## Open questions
- How exactly should addresses be standardised and canonicalised?
- What minimum set of enrichment features belongs in MVP?
- What baseline and tree-based model should be the first model pair?
- What interval-generation method is best for MVP?
- What is the best local interface for V1: CLI, notebook, or local Streamlit?

---

## Usage notes
- Add new decisions with IDs in sequence.
- Move a decision from Proposed to Accepted to Locked as confidence increases.
- If a locked decision changes, keep the old entry and add a new superseding entry.
