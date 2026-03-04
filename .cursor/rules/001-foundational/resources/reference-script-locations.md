# Reference: Script Locations

Where rule-owned scripts live and what they do.

---

## Tool Selection Decision Tree

1. Is this a repeatable task? → **Script**
2. Does it require multiple tool calls to synthesize data? → **Script**
3. Is it a one-off simple file read/grep? → **Native Tool**

## Git Operations Scripts

Location: `.cursor/rules/030-git-workflows/scripts/`

### GitHub
- `fetch_issues.py`: List/fetch issues (supports `--issue`, `--label`, `--state`)
- `manage_issue.py`: Close, reopen, comment on issues

### GitLab
- `gitlab_api.py`: Shared API module
- `gitlab_issues.py`: Issue management
- `fetch_pipelines.py`, `manage_pipeline.py`: CI/CD automation
- `fetch_merge_requests.py`, `manage_merge_request.py`: MR workflows

**Note**: All scripts auto-load credentials via `python-dotenv`.
