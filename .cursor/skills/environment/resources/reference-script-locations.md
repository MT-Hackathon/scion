# Reference: Script Locations

Where rule-owned scripts live and what they do.

---

## Tool Selection Decision Tree

1. Is this a repeatable task? → **Script**
2. Does it require multiple tool calls to synthesize data? → **Script**
3. Is it a one-off simple file read/grep? → **Native Tool**

## Core Workflow Scripts

| Script | Location | Purpose |
|--------|----------|---------|
| `dev-stack.py` | `.cursor/skills/dev-startup/scripts/` | Manage dev environment (start/stop/status) |
| `remote-sync.py` | `.cursor/skills/dev-project-architecture/scripts/` | Sync between CDO and State GitLab |
| `mock-server.py` | `.cursor/skills/api-design/scripts/` | OpenAPI-based mock server |

## Git Operations Scripts

Location: `.cursor/skills/git-workflows/scripts/`

### GitHub
- `fetch_issues.py`: List/fetch issues (supports `--issue`, `--label`, `--state`)
- `manage_issue.py`: Close, reopen, comment on issues

### GitLab
- `gitlab_api.py`: Shared API module
- `gitlab_issues.py`: Issue management
- `fetch_pipelines.py`, `manage_pipeline.py`: CI/CD automation
- `fetch_merge_requests.py`, `manage_merge_request.py`: MR workflows

## Linter & Quality Scripts

Location: `.cursor/skills/linter-integration/scripts/`

- `find-todos.py`: Locate TODO/FIXME comments
- `find-linter-patterns.py`: Identify common linter violations
- `check-local-config.py`: Detect personal linter overlays

## Rule Management Scripts

Location: `.cursor/skills/rule-authoring-patterns/scripts/`

- `generate-new-rule.py`: Scaffolding for new rules/skills
- `validate-frontmatter.py`: Quality check for rule descriptions
- `scan-project-references.py`: Identify local specifics for rule transfer

**Note**: All scripts are run via `uv run <script_path>` and auto-load credentials via `python-dotenv`.
