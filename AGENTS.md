# AGENTS.md

## Project
South Dublin House Valuation Tool

Local-first ML tool for selected South and South-East Dublin houses.
Primary goal: decision-useful valuation support for personal house search.

## Working mode
- Default to practical execution over broad brainstorming.
- Prefer creating or updating files in the repository over long chat-only responses.
- For planning tasks, create or update markdown docs instead of code unless asked otherwise.
- Before making large changes, inspect the relevant existing files.
- Do not create duplicate planning docs when an appropriate file already exists.
- State assumptions explicitly when information is missing.
- Respect locked decisions unless there is a strong project-specific reason to challenge them.

## Locked decisions
- Predict transaction sale price, not asking price.
- Predict log sale price, then convert back for reporting.
- V1 is local-first.
- No polished public deployment in V1.
- Daft is used only as a light inference-time parser in V1.
- User can review / override parsed fields.
- Houses only:
  - House
  - Detached House
  - Semi-Detached House
  - Terraced House
  - End of Terrace House
- Inference geography:
  - Sandymount, Ballsbridge, Ranelagh, Rathmines, Rathgar, Terenure, Donnybrook, Milltown, Dartry, Clonskeagh, Windy Arbour, Churchtown, Dundrum, Goatstown, Foxrock, Seapoint, Blackrock, Booterstown, Merrion, Mount Merrion, Kilmacud, Stillorgan, Ardilea, Monkstown
- Training geography:
  - inference geography plus Harolds Cross, Kimmage, Templeogue, Rathfarnham, Knocklyon, Butterfield, Edmondstown, Ballyboden, Scholarstown, Ballinteer, Balally, Sandyford, Kilgobbin, Carrickmines, Kilternan, Deansgrange, Cabinteely, Loughlinstown, Shankill, Ballybrack, Killiney, Kilbogget, Glenageary, Thomastown, Dalkey, Woodpark, Sandycove, Dún Laoghaire
- Do not broaden geography further for now.
- One model across house types first, with property type as a feature.
- Split later only if justified by error analysis.
- No hard >200m² training filter.
- Structured features first in V1.
- No image modelling in V1.
- No text-heavy modelling in V1.
- Architecture direction:
  - local Python project
  - DuckDB + Parquet
  - deterministic batch feature pipeline
  - tabular baseline + main tree-based model
  - quantile or interval-based uncertainty layer
  - local report output
  - optional lightweight Streamlit later

## Repository priorities
1. Strong planning
2. Strong modelling and evaluation
3. Reliable dataset construction
4. Useful local report output
5. Lightweight packaging

## Directory conventions
- `/planning/` for working plans, roadmaps, decision logs, and specialist deliverables
- `/docs/` for durable specs and reference docs
- `/src/` for source code
- `/scripts/` for runnable scripts and utilities
- `/data/` for local data assets if included in repo conventions
- `/artifacts/` for model outputs and reports if tracked locally
- `/prompts/` for specialist prompts and orchestration notes

## Preferred planning files
- `/planning/decision_log.md`
- `/planning/roadmap.md`
- `/planning/system_architecture.md`
- `/planning/data/`
- `/planning/modelling/`
- `/planning/product/`
- `/planning/deployment/`

## Specialist workflow
When asked to act as a specialist:
- keep within the assigned scope
- create or update the relevant files
- avoid redoing other specialists’ work
- note unresolved questions for handoff
- use the matching prompt in `/prompts/` as the task brief when one exists
- inspect existing deliverables before creating new ones
- record cross-specialist dependencies in `/planning/specialist_handoffs.md`

## Codex setup conventions
- Use the root `AGENTS.md` as the main durable instruction file for now.
- Add subdirectory `AGENTS.md` files only when a directory needs rules that would be noisy at root level.
- Keep durable project rules in `AGENTS.md`; keep role-specific task briefs in `/prompts/`.
- Prefer plain specialist prompts for V1 planning work.
- Defer custom skills and subagents until repeated workflows become stable enough to automate.
- For planning outputs, update the relevant preferred file instead of creating a near-duplicate.
- For experiments, create one dated or numbered entry in the relevant experiment log and link artifacts.

## Output expectations
At the end of a task, summarize:
- files created or updated
- key recommendations
- open questions or follow-ups

## Constraints
- Solo project
- Budget up to €300 total
- 8–12 week timeline
- Prefer low-maintenance solutions
- Avoid overengineering
