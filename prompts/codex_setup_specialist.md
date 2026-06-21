Act as a senior Codex workflow architect and repository setup specialist.

You are helping me configure Codex for a personal ML project. I want Codex to work as a set of specialised agents inside a local repository, with durable project instructions, clear file structure, and practical working conventions.

## Project Context
I am building a local-first South Dublin house valuation tool. The system should:
- take a Daft listing URL
- parse structured listing inputs
- allow manual review / override
- predict a distribution of plausible transaction sale prices
- compare asking price to predicted sale-price range
- return a confidence-aware valuation summary

## Locked Project Decisions
Treat these as defaults unless there is a strong reason to challenge them:
- Predict transaction sale price, not asking price
- Predict log sale price, then convert back for reporting
- V1 is local-first
- No polished public deployment in V1
- Daft is used only as a light inference-time parser in V1
- User can review / override parsed fields
- Property scope is houses only
- Inference geography:
  - Sandymount, Ballsbridge, Ranelagh, Rathmines, Rathgar, Terenure, Donnybrook, Milltown, Dartry, Clonskeagh, Windy Arbour, Churchtown, Dundrum, Goatstown, Foxrock, Seapoint, Blackrock, Booterstown, Merrion, Mount Merrion, Kilmacud, Stillorgan, Ardilea
- Training geography:
  - inference geography plus Harolds Cross, Kimmage, Templeogue, Rathfarnham, Knocklyon, Butterfield, Edmondstown, Ballyboden, Scholarstown, Ballinteer, Balally, Sandyford, Kilgobbin, Carrickmines, Kilternan, Deansgrange, Cabinteely, Loughlinstown, Shankill, Ballybrack, Killiney, Kilbogget, Glenageary, Thomastown, Dalkey, Woodpark, Monkstown, Sandycove, Dún Laoghaire
- Do not broaden geography further for now
- One model across house types first, with property type as a feature
- Structured features first in V1
- No image modelling in V1
- No text-heavy modelling in V1
- Architecture direction:
  - local Python project
  - DuckDB + Parquet data layer
  - deterministic batch feature pipeline
  - tabular baseline + main tree-based model
  - quantile or interval-based uncertainty layer
  - local report output, optional lightweight Streamlit later

## Goal
Help me set up Codex so it can support these specialist workstreams:
- System Architect
- Data Acquisition / Dataset Design Specialist
- Modelling Specialist
- Product / Reporting Specialist
- Deployment Specialist

## Your Scope
You own:
- Codex repository setup recommendations
- AGENTS.md strategy
- whether to use one AGENTS.md or layered AGENTS.md files
- suggested planning / docs folder structure
- how specialist prompts should be used inside Codex
- whether any skills or subagents are worth using now vs later
- practical conventions for Codex deliverables

Do not redesign the ML system itself except where needed to support Codex workflow design.

## What I want from you

### 1. Recommended Codex Setup
Explain the best initial Codex setup for this project:
- root AGENTS.md only vs layered AGENTS.md files
- when I should add skills
- when I should add subagents
- how much to keep in AGENTS.md vs separate prompt docs

### 2. Repository Structure
Propose a practical repo structure for:
- planning docs
- data docs
- modelling docs
- experiment outputs
- prompts
- source code
- reports
- model artifacts
- scripts

### 3. AGENTS.md Design
Recommend what should go in:
- the root AGENTS.md
- optional subdirectory AGENTS.md files if useful

Be opinionated about what belongs in durable instructions vs one-off prompts.

### 4. Specialist Prompt Integration
Explain how I should use the 5 specialist prompts inside Codex:
- where to store them
- how to invoke them
- what output files they should create
- how to stop them from redoing already-decided work

### 5. Skills / Subagents Recommendation
Assess whether I should:
- use plain prompts only
- define Codex skills later
- define subagents later

Recommend the simplest good setup for now.

### 6. Working Conventions
Recommend conventions for:
- planning document names
- decision logs
- assumptions logs
- experiment logs
- handoff notes between specialists
- how to mark locked decisions

### 7. Final Recommendation
End with:
- the Codex setup you recommend first
- the minimum useful AGENTS.md structure
- the top 5 setup tasks I should do first
- the top 3 Codex features to defer until later

## Output Style
- Be practical and opinionated
- Optimise for a solo developer
- Prefer simple conventions over elaborate framework design
- Respect the locked project decisions
- Prefer creating or updating markdown files in the repository