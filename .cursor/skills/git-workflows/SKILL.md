---
name: git-workflows
description: "Provides scripts for GitHub/GitLab issue, pull request, MR, pipeline, and epic management via gh and API. Use when creating issues, managing PRs, checking pipeline status, or automating git platform operations. DO NOT use for general git CLI commands — use the terminal directly for commits, branches, and merges."
---

<ANCHORSKILL-GIT-WORKFLOWS>

# Git Workflows

Automate issue management, pipelines, and cross-platform sync across our multi-repo ecosystem using consolidated scripts.

## Contents

- [Core Concepts](#core-concepts)
- [Script Reference](#script-reference)
- [Library Architecture](#library-architecture-_core)
- [Common Workflows](#common-workflows)
- [Environment Configuration](#environment-configuration)
- [Resources](#resources)

## Core Concepts
- **GitLab.com**: Primary origin for issues, MRs, and pipelines.
- **GitHub**: Stakeholder mirror for visibility.
- **State GitLab (git.mt.gov)**: Used *only* when explicitly requested for state deployments.
- **Layer Labels**: `layer::backend`, `layer::frontend`, `layer::infra`, `layer::docs`, `layer::contract`.
- **Absolute URLs**: Always use full URLs (e.g., `https://gitlab.com/.../69`) for cross-linking to ensure portability between GL/GH.
- **Unified Interface**: All new scripts follow a standard `<action> [args]` pattern and share core options.

## Script Reference
All scripts run via `uv run .cursor/skills/git-workflows/scripts/<script_name>.py`.

### git-issue.py
Manage issues across GitLab/GitHub. Create, update, close, list, comment, and bulk triage.

`uv run git-issue.py <action> [args]`

| Action | Usage |
|--------|-------|
| `create` | `--title "Title" [--body "inline"] [--body-file path.md] [--labels bug,high]` |
| `update` | `<iid> [--title] [--labels add:x,remove:y] [--state close]` |
| `close` | `<iid> [--comment "Reason"]` |
| `list` | `[--state open] [--labels] [--limit 20]` |
| `get` | `<iid>` |
| `comment` | `<iid> [--body "inline"] [--body-file path.md]` |
| `triage` | `--source <project> [--mirror] [--dry-run]` |

Shared: `--provider gitlab|github|state`, `--project <path>`, `--dry-run`, `-v`

### git-mr.py
Manage merge/pull requests across GitLab, GitHub, and State.

`uv run git-mr.py <action> [args]`

| Action | Usage |
|--------|-------|
| `create` | `--source feat --target main --title "Title" [--body "Body"] [--draft]` |
| `merge` | `<iid> [--message "Commit message"]` |
| `close` | `<iid> [--comment "Reason"]` |
| `reopen` | `<iid>` |
| `comment` | `<iid> --body "Comment"` |
| `list` | `[--state opened] [--limit 20]` |
| `get` | `<iid>` |
| `notes` | `<iid> [--author <substr>] [--full] [--limit N]` |
| `resolve-threads` | `<iid> [--author <substr>]` |

Shared: `--provider gitlab|github|state`, `--project <path>`, `--dry-run`, `-v`

### git-pipeline.py
Manage CI pipelines and jobs for GitLab and State projects.

`uv run git-pipeline.py <action> [args]`

| Action | Usage |
|--------|-------|
| `trigger` | `--ref main [--variables KEY=VAL]` |
| `cancel` | `<id>` |
| `retry` | `<id>` |
| `list` | `[--status failed] [--limit 10]` |
| `jobs` | `<pipeline_id>` |
| `trace` | `<job_id> [--tail 100]` |

Shared: `--provider gitlab|state`, `--project <path>`, `--dry-run`, `-v`

### git-label.py
Manage labels across repositories with provider-specific handling.

`uv run git-label.py <action> [args]`

| Action | Usage |
|--------|-------|
| `create` | `--name "New Label" --color "#FF0000" [--description "Text"]` |
| `update` | `--name "Old" --new-name "New" [--color "#00FF00"]` |
| `delete` | `--name "Label"` |
| `list` | `[--search "term"]` |

Shared: `--provider gitlab|github|state`, `--project <path>`, `--dry-run`, `-v`

### git-epic.py
Manage GitLab epics and issue hierarchy.

`uv run git-epic.py <action> [args]`

| Action | Usage |
|--------|-------|
| `create` | `--title "Epic" --body "Desc" [--labels "L1"] [--parent-iid 123]` |
| `list` | `[--state opened] [--limit 20]` |
| `get` | `<iid>` |
| `link` | `<epic-iid> <issue-iid>` |
| `pull` | `<epic-iid> [--format brief/json] [--include-closed] [--project-id ID]` |

Shared: `--provider gitlab|state`, `--project <path>`, `--dry-run`, `-v`

### git-milestone.py
Manage milestones across providers.

`uv run git-milestone.py <action> [args]`

| Action | Usage |
|--------|-------|
| `create` | `--title "Phase 1" [--description "Goal"]` |
| `list` | `[--state active] [--limit 20]` |
| `delete` | `--title "Phase 1"` |

Shared: `--provider gitlab|github|state`, `--project <path>`, `--dry-run`, `-v`

### git-project.py
Query project metadata, branches, members, and create new repositories.

`uv run git-project.py <action> [args]`

| Action | Usage |
|--------|-------|
| `create` | `--name "repo-name" [--group "group-or-org"] [--visibility private\|internal\|public] [--description "Text"]` |
| `info` | No args required |
| `branches` | `[--search "feat"]` |
| `members` | `[--search "user"]` |

Shared: `--provider gitlab|github|state`, `--project <path>`, `--dry-run`, `-v`

### git-ci-usage.py
Query GitLab CI/CD compute minutes usage via GraphQL.

`uv run git-ci-usage.py <action> [args]`

| Action | Usage |
|--------|-------|
| `summary` | Current month usage with per-project breakdown and quota |
| `history` | `[--months 6]` monthly usage trend |

Shared: `--provider gitlab`, `--project <path>`, `--dry-run`, `-v`

### git-sync.py
Utilities for cross-platform synchronization and content patching.

`uv run git-sync.py <action> [args]`

| Action | Usage |
|--------|-------|
| `mirror` | `--source gitlab --target github [--issues "1,2,3"]` |
| `backlog` | No args required |
| `crossrefs` | `--issues "1,2,3"` |

Shared: `--provider gitlab|github|state`, `--project <path>`, `--dry-run`, `-v`

### create_settings_issues.py / create_settings_issues.sh
Legacy bulk-issue bootstrap helpers for GitHub project setup. Kept for historical automation and one-time project bootstrapping tasks.

## Library Architecture (`_core/`)
The scripts are built on a shared internal library to ensure consistent behavior:
- `args.py`: Standardized argument parsing and environment resolution.
- `http.py`: Resilience-focused HTTP client with retries and logging.
- `output.py`: Consistent formatting for console output and error reporting.
- `providers.py`: Provider-specific implementation logic (GitLab, GitHub, State).

## Common Workflows

### 1. Feature Lifecycle
Create issue → Branch → Develop → Create MR.
```bash
# 1. Create issue
uv run git-issue.py create --title "feat: search" --body "Implement X" --labels "layer::frontend"

# 2. Mirror to GitHub (optional)
uv run git-sync.py mirror --source gitlab --target github

# 3. Create MR after push
uv run git-mr.py create --source feature-branch --target main --title "feat: search"
```

### 2. Debugging Pipelines
```bash
# Find failing job
uv run git-pipeline.py list --status failed --limit 1
# Get logs
uv run git-pipeline.py trace <job_id> --tail 500
```

## Environment Configuration
Credentials and Project IDs are loaded from `.env`.
- `GITLAB_PERSONAL_ACCESS_TOKEN`: Primary GL auth.
- `GITHUB_PERSONAL_ACCESS_TOKEN`: GitHub auth for mirrored operations.
- `CDO_GITLAB_PROJECT_ID_FRONTEND`: GL `procurement-web` (default context).
- `CDO_GITLAB_PROJECT_ID_BACKEND`: GL `procurement-api`.

### Credential Handling Mandates
- Scripts auto-load credentials via `python-dotenv`; never hardcode tokens.
- NEVER read, cat, grep, or source `.env` directly in commands or scripts.
- If required auth variables are missing, fail fast with explicit startup errors.
- For full variable registry and environment conventions, see [environment](../environment/SKILL.md).

## Resources

- [Reference: Release Management](resources/reference-release-management.md)

</ANCHORSKILL-GIT-WORKFLOWS>
