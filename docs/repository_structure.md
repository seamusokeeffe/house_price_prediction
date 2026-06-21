# Repository Structure

This repository uses a simple split between working plans, durable specs, source code, local data, and generated artifacts.

## Top-level directories

- `/planning`: working plans, decision logs, assumptions, handoffs, and workstream roadmaps
- `/docs`: durable technical and product specs that implementation should follow
- `/prompts`: reusable Codex specialist prompts
- `/src`: Python package source code
- `/scripts`: runnable utilities and command-line workflows
- `/data`: local data assets, if used in repo conventions
- `/artifacts`: generated reports, model outputs, metrics, and local run outputs

## Planning directories

- `/planning/data`: data acquisition, source selection, cleaning, and dataset construction plans
- `/planning/modelling`: modelling roadmap, experiment matrix, and experiment log
- `/planning/product`: local user flow, report roadmap, and decision-support requirements
- `/planning/deployment`: local packaging, runtime, and artifact handling plans

## Docs directories

- `/docs/data`: dataset schema, raw-to-processed workflow, and cleaning rules
- `/docs/modelling`: evaluation protocol, interval method, and error analysis template
- `/docs/product`: report spec, output schema, and confidence explanation
- `/docs/deployment`: local runtime, artifact versioning, and repo/package structure

## File ownership rule

Planning files may contain open questions and options. Docs files should contain the current accepted specification. When a planning decision becomes stable, promote the relevant detail into `/docs`.

