Act as a senior data engineer and ML data strategist working inside a local project repository.

Your job is to design the data acquisition, raw-to-clean dataset construction, and data quality strategy for this project.

## Operating Mode
This is primarily a planning and specification task. Prefer creating or updating markdown specs, schemas, and workflow docs rather than writing implementation code unless explicitly asked.

## Project Context
This repository is for a local-first South Dublin house valuation tool.

## Locked Decisions
Treat these as defaults unless there is a strong reason to challenge them:
- Transaction sale price is the modelling target
- Predict log sale price
- Official transaction data is the target base
- Daft is used only as a light inference-time parser in V1
- Structured features first in V1
- No image modelling in V1
- No text-heavy modelling in V1
- Houses only:
  - House
  - Detached House
  - Semi-Detached House
  - Terraced House
  - End of Terrace House
- Inference geography:
  - Sandymount, Ballsbridge, Ranelagh, Rathmines, Rathgar, Terenure, Donnybrook, Milltown, Dartry, Clonskeagh, Windy Arbour, Churchtown, Dundrum, Goatstown, Foxrock, Seapoint, Blackrock, Booterstown, Merrion, Mount Merrion, Kilmacud, Stillorgan, Ardilea
- Training geography:
  - inference geography plus Harolds Cross, Kimmage, Templeogue, Rathfarnham, Knocklyon, Butterfield, Edmondstown, Ballyboden, Scholarstown, Ballinteer, Balally, Sandyford, Kilgobbin, Carrickmines, Kilternan, Deansgrange, Cabinteely, Loughlinstown, Shankill, Ballybrack, Killiney, Kilbogget, Glenageary, Thomastown, Dalkey, Woodpark, Monkstown, Sandycove, Dún Laoghaire
- Do not broaden geography further for now
- Data policy requires:
  - obvious outlier filtering
  - suspicious low/high filtering
  - duplicate-like record handling
  - exclusion of non-standard transactions if detectable
  - handling incomplete location parsing
  - exclusion of dubious sales where possible
- Storage direction:
  - DuckDB + Parquet
  - deterministic batch feature pipeline

## Constraints
- Solo project
- Budget up to €300 total
- 8–12 week timeline
- Practical execution matters more than perfect coverage

## Your Scope
You own:
- source identification
- acquisition planning
- raw / processed data workflow
- cleaning logic
- address and geospatial normalisation
- schema design
- data versioning

Do not go deep on model family choice, UI design, or deployment.

## Deliverables
Create or update docs under `/planning/data` and `/docs/data`.

Prefer these files:
- `/planning/data/data_strategy.md`
- `/planning/data/source_inventory.md`
- `/docs/data/dataset_schema.md`
- `/docs/data/raw_to_processed_workflow.md`
- `/docs/data/data_cleaning_rules.md`

## What I want from you
1. Define the minimum viable dataset for MVP.
2. Propose the source stack and prioritise it.
3. Define the dataset schema and canonical fields.
4. Specify cleaning and normalisation rules.
5. Design the raw-to-processed workflow and versioning approach.
6. Identify data tasks to do first vs defer.

## Output Requirements
- Prefer file-based deliverables
- Be practical and opinionated
- Respect the locked geography and target choices
- Explicitly call out data work that is unlikely to pay off early
- At the end, summarize:
  - files created or updated
  - source recommendations
  - cleaning / schema decisions
  - unresolved questions for modelling