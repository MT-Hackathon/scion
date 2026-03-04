---
name: ci-pipeline
description: "Governs CI/CD pipeline troubleshooting for GitLab pipelines. Use when debugging pipeline, CI/CD, build failure, deploy failure, job trace, or pipeline debugging issues. DO NOT use for git operations (issues, MRs, labels, project admin); use git-workflows instead."
---

<ANCHORSKILL-CI-PIPELINE>

# CI Pipeline

Use this skill to troubleshoot failed or unstable CI/CD pipelines, interpret job traces, and choose corrective actions.

## Scope
- Focus: pipeline architecture, failure diagnosis, and recovery actions.
- Platforms: any GitLab instance via provider selection.
- Excludes: issue/MR/label/project workflows (handled by `git-workflows`).

## Pipeline Troubleshooting Loop
1. Identify failed or flaking pipelines.
2. Inspect jobs within the target pipeline.
3. Find failed jobs and failure reasons.
4. Read trace output for root cause signals.
5. Apply corrective action (retry, trigger, code fix, config fix).

## Script Tooling (From `git-workflows`)
Use the unified script:
`uv run .cursor/skills/git-workflows/scripts/git-pipeline.py <action> [args]`

Core actions:
- `list`: find recent failed/running pipelines.
- `jobs`: enumerate jobs in a pipeline.
- `trace`: read job logs for root cause details.
- `retry`: rerun a failed pipeline.
- `trigger`: run a new pipeline on a target ref.
- `cancel`: stop a stuck or obsolete run.

Provider examples:
- GitLab.com: `--provider gitlab`
- Other configured GitLab instance: `--provider state`

## Resources
- [Pipeline Architecture Template](resources/reference-pipeline-architecture.md)
- [Common Failure Patterns](resources/reference-common-failures.md)
- [Pipeline Debug Checklist](resources/checklist-pipeline-debug.md)

## Cross-Reference
- [git-workflows](../git-workflows/SKILL.md): Owns script operations and broader git platform automation.

</ANCHORSKILL-CI-PIPELINE>
