# Specialist Handoffs

Use this file to pass unresolved questions between specialist prompts without reopening settled decisions.

## Status legend

- Open
- In progress
- Resolved
- Deferred

## Template

```markdown
### H-001 - Short handoff title
- Status: Open
- From: Source specialist
- To: Target specialist
- Question: What needs to be answered.
- Context: Why it matters.
- Needed by: Phase or milestone.
- Resolution:
```

## Current handoffs

### H-001 - Minimum viable source stack
- Status: Resolved
- From: Codex Setup
- To: Data Specialist
- Question: Which data sources are required for the first useful dataset, and which should be deferred?
- Context: The project needs a practical source stack before implementation starts.
- Needed by: Phase 1
- Resolution: Use official transaction data, project canonical area lookup, and manual inference input as required V1 sources. Treat CSO Census 2022 and Tailte Eireann open geography/boundary data as should-have. Defer paid address products, historical listing archives, and amenity enrichment.

### H-002 - Confidence rules depend on comparable support
- Status: Resolved
- From: Codex Setup
- To: Modelling Specialist
- Question: What exact thresholds define normal confidence, low confidence, and not enough comparable support?
- Context: Product reporting and unsupported-case logic depend on this.
- Needed by: Phase 2
- Resolution: Start with 15+ comparable transactions in the last 5 years for normal confidence, 5-14 for low confidence, and fewer than 5 after allowed backoff for not enough support. Validate and tune using temporal validation coverage and error by confidence state.

### H-003 - Canonical geography mapping
- Status: Resolved
- From: System Architect
- To: Data Specialist
- Question: How should raw address and area strings map into the locked inference and training geography?
- Context: Modelling, validation segmentation, and comparable-support confidence all depend on stable geography features.
- Needed by: Phase 1
- Resolution: Maintain a project-owned canonical area lookup with aliases and scope flags. Map deterministically first, then use a manual override table for ambiguous records. Exclude out-of-scope records rather than broadening geography.

### H-004 - Shared training/inference feature contract
- Status: Resolved
- From: System Architect
- To: Data Specialist / Modelling Specialist
- Question: What feature table contract should be shared by training and inference?
- Context: A single deterministic feature path reduces leakage and training-serving mismatch.
- Needed by: Phase 2
- Resolution: Use the shared core structured fields from `docs/data/dataset_schema.md`: canonical area, geo scope, property type, beds, baths, floor area, BER if available enough, missingness flags, valuation/time features where valid, and comparable-support fields. Exclude target-derived or inference-unavailable fields from model inputs.

### H-005 - Unknown property type handling
- Status: Resolved
- From: Data Specialist
- To: Modelling Specialist
- Question: Should records with unknown but plausible house type be retained with a missingness flag, or excluded from the first training dataset?
- Context: Official transaction data may not reliably identify house subtype. Excluding unknowns improves purity but may reduce support.
- Needed by: Phase 2
- Resolution: Retain unknown-but-plausible house records for the first broad baseline with an `unknown` category and missingness flag, then run a sensitivity check excluding them before final V1 model selection.

### H-006 - VAT-exclusive and new-build transaction treatment
- Status: Resolved
- From: Data Specialist
- To: Modelling Specialist
- Question: Should VAT-exclusive and new-build records be excluded, modelled with flags, or evaluated as a sensitivity split?
- Context: These records may not match resale inference cases but can add useful data in sparse areas.
- Needed by: Phase 2
- Resolution: Retain with explicit flags for the first broad baseline if cleaning permits, then run sensitivity checks excluding VAT-exclusive and new-build records. Do not make default exclusion until validation shows distortion.

### H-007 - Confidence wording for report
- Status: Open
- From: Modelling Specialist
- To: Product Specialist
- Question: How should normal confidence, low confidence, and not enough comparable support be worded in the V1 report?
- Context: The report needs to communicate uncertainty without implying valuation certainty or hiding unsupported cases.
- Needed by: Phase 3
- Resolution:

### H-008 - PPR Checkpoint 2 source-standardised output
- Status: Resolved
- From: Data Engineering
- To: Data Specialist / Modelling Specialist
- Question: What can later checkpoints safely consume from PPR Checkpoint 2?
- Context: Checkpoint 2 intentionally produces an all-dwelling, source-standardised dataset only. It preserves raw source fields, parses dates/prices/status fields, creates unique source-row IDs and duplicate fingerprints, and applies a provisional 13.5% house VAT adjustment for records marked `VAT Exclusive = Yes`.
- Needed by: Checkpoint 3
- Resolution: Use `data/interim/ppr/20260621/ppr_source_standardised.parquet` as the Checkpoint 3 input. Do not treat it as house-only or training-candidate. Geography mapping, house/apartment eligibility, multi-property detection, duplicate resolution, exclusions, and baseline-compatible output remain later steps. Evidence is in `artifacts/data_quality/20260621/ppr_checkpoint_2_report.md`.
