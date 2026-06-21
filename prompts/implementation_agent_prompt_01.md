# First Implementation Agent Prompt (Revised)

Act as a senior ML engineer working inside this local repository.

Your job is to implement the **smallest credible end-to-end MVP skeleton** for the South Dublin House Valuation Tool, based on the existing planning documents already created in this repo.

## Operating Mode
This is an implementation task.

You should:
- read the existing planning documents first
- treat the planning documents and decision log as the source of truth
- follow the locked decisions already recorded in the repo unless something is clearly inconsistent
- implement a narrow vertical slice of the pipeline
- prefer clean, simple, maintainable code over ambitious architecture
- avoid UI work unless explicitly required
- avoid overengineering

Before making major changes, inspect the repository structure and existing planning docs.

## Project Goal
Build the first working code skeleton for a local-first ML valuation tool that will eventually:
- take a Daft listing URL
- parse structured fields
- allow manual correction
- estimate a distribution of plausible transaction sale prices
- compare asking price with predicted sale-price range
- return a confidence-aware summary

## Repository Guidance
Use the planning documents under:
- `/planning/`
- `/docs/`

especially the decision log, roadmap, data planning docs, and modelling planning docs.

Treat the locked decisions already documented there as the default implementation requirements.
Do **not** restate or redefine them unless you find a clear inconsistency or blocking ambiguity.

## Scope for this task
Implement only the **core MVP skeleton**.

### In scope
- project module structure under `src/`
- config structure
- dataset loading interface
- cleaned dataset contract / typed schema where useful
- feature pipeline skeleton for structured data
- training script for the baseline model
- validation / evaluation script
- inference input schema for a single property
- simple prediction output schema
- simple report payload builder
- placeholders / stubs for confidence logic and interval logic if full implementation is not yet justified
- sensible tests for key pure functions if easy to add

### Out of scope
- full Daft scraping/parser implementation
- UI
- Streamlit
- packaging
- advanced multimodal features
- automated retraining
- production-grade optimisation

## What I want you to do

### 1. Read existing planning documents
Read the relevant planning docs already in the repo, especially anything under:
- `/planning/`
- `/docs/`

Use them to guide implementation.

### 2. Create a clean MVP code structure
Create or update a simple structure under `src/` that supports:
- config
- data access
- schemas / types
- feature generation
- model training
- evaluation
- inference
- reporting

Keep it simple and avoid unnecessary abstraction.

### 3. Implement the first vertical slice
Implement a minimal working flow that supports:
- loading a modelling dataset from a configurable location
- filtering to supported house types
- basic target preparation with log sale price
- simple structured feature preparation
- train / validation split entry point
- baseline model training
- prediction on validation data
- basic metric calculation
- generation of a simple structured inference result payload

### 4. Use the planned baseline
Use the baseline specified in the planning docs unless implementation constraints make that unreasonable.

If you need to deviate from the documented baseline, do all of the following:
- explain why
- choose the simplest reasonable alternative
- record the deviation in an implementation-facing doc or note

### 5. Add simple interfaces
Implement clear interfaces for:
- training input data
- inference input record
- prediction output
- report payload

These should make later UI work easier.

### 6. Keep confidence / intervals lightweight for now
Do not overbuild this part.

If the planning docs do not yet justify a full interval implementation, create:
- a simple placeholder interface, or
- a minimal initial implementation with explicit TODOs

### 7. Update documentation
Create or update implementation-facing docs, for example:
- `/docs/implementation/mvp_code_structure.md`
- `/docs/implementation/how_to_run_baseline.md`

Also update existing planning docs only if necessary to reflect implementation choices.

## Preferred file outcomes
Use your judgment, but a good outcome might include files like:

- `src/house_valuation/config.py`
- `src/house_valuation/data/loaders.py`
- `src/house_valuation/data/filters.py`
- `src/house_valuation/features/build_features.py`
- `src/house_valuation/models/baseline.py`
- `src/house_valuation/evaluation/metrics.py`
- `src/house_valuation/evaluation/validation.py`
- `src/house_valuation/inference/schemas.py`
- `src/house_valuation/inference/predict.py`
- `src/house_valuation/reporting/build_report.py`
- `scripts/train_baseline.py`
- `scripts/run_validation.py`

You do not have to use exactly these names, but keep the structure coherent.

## Engineering preferences
- Python only
- Prefer standard library + small, sensible dependencies
- Type hints where useful
- Clear docstrings for public functions
- Avoid complicated class hierarchies unless necessary
- Prefer functions and simple modules
- Fail clearly on missing required columns / invalid inputs
- Make assumptions explicit

## Output requirements
At the end:
1. Summarize the files created or updated
2. Explain the implemented vertical slice
3. Note any assumptions made
4. List TODOs that should be handled in the next implementation pass
5. Flag any blocking ambiguities discovered in the planning docs

## Important
Do not build the full product.

Build the **smallest credible code skeleton** that turns the planning work into a runnable MVP foundation.
