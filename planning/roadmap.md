# Project Roadmap

## Project

South Dublin House Valuation Tool

## Objective

Build a local-first ML tool that estimates plausible transaction sale prices for selected South Dublin houses and compares asking price to the predicted sale-price range.

---

## Phase 1 - MVP Foundation (Weeks 1-4)

### Primary goal

Establish a credible end-to-end MVP foundation:

- usable planning docs
- minimum viable dataset design
- first modelling plan
- clear evaluation protocol
- scoped local report output

### Must-have

- Finalise repo setup and Codex workflow.
- Create or update system architecture, roadmap, decision log, assumptions log, and handoff log.
- Define minimum viable data source stack.
- Define canonical dataset schema.
- Define cleaning and address/geography normalisation rules.
- Build validation design and experiment ladder.
- Define MVP report/output requirements.

### Should-have

- Draft local packaging approach.
- Draft source/module boundaries for implementation.
- Define assumptions log and experiment log usage.
- Define artifact naming conventions at a planning level.

### Nice-to-have

- Skeleton folder structure for code modules.
- Placeholder templates for future experiment summaries.
- Minimal CLI skeleton only if planning finishes early.

### Likely blockers

- Data access ambiguity.
- Address and geography normalisation complexity.
- Target quality issues in transaction data.
- Overly broad scope in early planning.

### Phase 1 exit criteria

- Locked decisions and fragile assumptions are documented.
- Cross-specialist handoffs are explicit.
- Data strategy is clear enough to begin implementation.
- Modelling plan and validation protocol are documented.
- MVP output/report scope is defined.

---

## Phase 2 - Data and Baseline Modelling (Weeks 5-8)

### Primary goal

Build a credible baseline pipeline and evaluation loop.

### Must-have

- Acquire and clean MVP dataset.
- Implement canonical data model.
- Build deterministic feature pipeline shared by training and inference.
- Train and evaluate baseline model.
- Train and evaluate first tree-based candidate model.
- Compare recent-window choices.
- Define initial confidence and unsupported-case logic.

### Should-have

- Segment analysis by area, size band, property type, and price band.
- Initial report generation from a fixed example input.
- Initial local runtime flow for inference.
- Save metrics and model artifacts in a repeatable structure.

### Nice-to-have

- Early benchmark summary document.
- Sensitivity checks on a small number of modelling choices.
- One or two high-ROI enrichment feature comparisons.

### Likely blockers

- Sparse support in some sub-areas.
- Poor data quality in size or address fields.
- Leakage risks in validation.
- Weak baseline performance in premium houses.

### Phase 2 exit criteria

- Baseline and main candidate model have been evaluated honestly.
- Metrics are available overall and by segment.
- Interval and confidence method has an initial version.
- A fixed example input can produce a draft local report.
- End-to-end local inference flow is conceptually defined.

---

## Phase 3 - MVP Usable Local Tool (Weeks 9-12)

### Primary goal

Turn the pipeline into a usable local valuation tool.

### Must-have

- Finalise best MVP model choice.
- Finalise confidence and unsupported-case logic.
- Implement local inference flow.
- Include manual review and override for parsed listing fields.
- Generate V1 report output.
- Document local runtime and packaging instructions.

### Should-have

- Lightweight local UI only if the CLI/report flow is already useful.
- Manual retraining workflow.
- Model artifact versioning.

### Nice-to-have

- Small number of useful report refinements.
- Lightweight Streamlit prototype for local use.

### Likely blockers

- Parser brittleness on Daft pages.
- Calibration issues in uncertainty intervals.
- Poor trust in unsupported or low-confidence cases.
- Packaging friction.

### Phase 3 exit criteria

- Tool can accept a listing URL or manual fields and produce a confidence-aware valuation summary.
- Output is useful for personal decision support.
- Local runtime is documented.
- Deferred items are clearly separated from MVP.

---

## Deferred Beyond MVP

- Public deployment.
- Image modelling.
- Text-heavy modelling.
- Automated retraining.
- Nationwide expansion.
- Apartments.
- Highly polished UI.

---

## Current Priorities

1. Run the Data Specialist prompt to define source stack, schema, and cleaning workflow.
2. Run the Modelling Specialist prompt to define validation, experiment ladder, and confidence rules.
3. Run the Product Specialist prompt to define local interaction flow and V1 report spec.
4. Run the Deployment Specialist prompt to define local runtime and artifact conventions.
5. Revisit the System Architect prompt only after specialist outputs materially change scope, risk, or sequencing.
6. Revisit Codex setup only after repeated workflow friction appears.

## Codex Setup Status

- Root `AGENTS.md` is the only durable instruction layer for now.
- Specialist prompts live in `/prompts`.
- Setup guidance lives in `planning/codex_setup.md`.
- System architecture lives in `planning/system_architecture.md`.
- Repo layout reference lives in `docs/repository_structure.md`.
- Cross-workstream coordination uses:
  - `planning/assumptions_log.md`
  - `planning/specialist_handoffs.md`
  - `planning/modelling/experiment_log.md`

---

## Notes

- This roadmap should be updated as specialist outputs become more concrete.
- If a phase changes materially, update the assumptions in `planning/assumptions_log.md` and decisions in `planning/decision_log.md`.
