# Specialist Prompts

This directory stores reusable Codex role briefs for project workstreams.

## How to invoke

Use a direct instruction such as:

```text
Execute @prompts/modelling_specialist.md
```

The specialist should inspect existing planning and docs files before writing, then create or update only the files in its scope.

## Prompt ownership

- `codex_setup_specialist.md`: Codex workflow and repo setup
- `system_architect.md`: overall architecture, roadmap, decisions, risk control
- `data_specialist.md`: sources, schemas, cleaning, raw-to-processed workflow
- `modelling_specialist.md`: modelling plan, validation, intervals, confidence logic
- `product_specialist.md`: local user flow, report spec, output schema
- `deployment_specialist.md`: local runtime, packaging, artifact handling

## Rules

- Do not duplicate an existing planning doc when the prompt names a preferred file.
- Do not reopen locked decisions unless there is a strong project-specific reason.
- Add cross-workstream dependencies to `/planning/specialist_handoffs.md`.
- Add new durable decisions to `/planning/decision_log.md`.
