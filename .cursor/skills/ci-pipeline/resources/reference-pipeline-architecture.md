# Pipeline Architecture Template

Use this template to document any project's CI/CD pipeline architecture for faster debugging.

## 1) Pipeline Overview
- **Repository/Project**: `<project-path>`
- **Pipeline purpose**: `<build/test/deploy intent>`
- **Execution model**: `<single pipeline | parent-child | downstream trigger>`

## 2) Stage Map
```text
stages: <stage-1> -> <stage-2> -> <stage-3>
```

For each stage, capture:
- Expected entry conditions (branch/tag/manual/schedule).
- Expected outputs (artifacts, images, deploy state, reports).
- Typical failure blast radius (local stage only vs downstream impact).

## 3) Job Inventory (Per Stage)
For each job, record:
- **Job name**: `<job-name>`
- **Type**: `<direct | trigger | manual>`
- **Dependencies**: `<needs/artifacts/downstream project>`
- **Primary logs**: `<where trace evidence is found>`
- **Failure ownership**: `<app code | infra | release config>`

## 4) Downstream and External Dependencies
- Triggered projects/pipelines and link conventions.
- Required runners/executors and capacity assumptions.
- External systems (registries, cloud, secrets, package feeds).

## 5) Operational Guardrails
- Timeout and retry policy by stage.
- Manual approval gates and release controls.
- Rollback or recovery path when deploy stage fails.

## 6) Debug Entry Points
- Command to list recent failed pipelines.
- Command to list jobs for a pipeline.
- Command to pull job trace.
- Rule for escalating to downstream investigation.
