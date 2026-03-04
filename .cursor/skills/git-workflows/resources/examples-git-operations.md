# Patterns: Git Workflows

Git workflow patterns and automation for GitHub and GitLab.

---

## Branch Strategy

```bash
# Feature branch workflow
git checkout -b feature/add-authentication
git commit -m "feat: add OAuth2 authentication"
git push origin feature/add-authentication
```

## Conventional Commits

```bash
# Format: type(scope): subject
git commit -m "feat(auth): add OAuth2 support"
git commit -m "fix(api): resolve timeout issue"
git commit -m "docs(readme): update installation steps"
```

---

## GitHub Patterns

### Issue Management

See `scripts/github_fetch_issues.py` and `scripts/github_manage_issue.py` for automation.

---

## GitLab Patterns

### Pipeline Management

GitLab CI/CD pipeline configuration and management patterns.

See `scripts/fetch_pipelines.py` and `scripts/manage_pipeline.py` for automation.

### Merge Request Management

Code review and approval workflows.

See `scripts/fetch_merge_requests.py` and `scripts/manage_merge_request.py` for automation.

### Issue & Epic Management

Project planning with issues, epics, and milestones.

See `scripts/gitlab_manage_issue.py`, `scripts/manage_epic.py`, and related scripts.

### Shared GitLab API

All GitLab scripts import from `scripts/gitlab_api.py` for consistent API access.
