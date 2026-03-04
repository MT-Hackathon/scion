# Reference: Project Entry Points

Quick reference for main project entry points and directory structure.

---

## Environment Activation

```bash
# Node.js (for Angular development)
nvm use 22

# Python rule scripts use uv (no activation needed)
# See environment skill for uv setup
```

## Frontend Entry Point

`src/app/` contains the Angular application.

- Development: `npm start` or `ng serve`
- Production Build: `ng build --configuration=production`
- Tests: `npm test`

---

## Directory Structure

### UI / Frontend (Angular)

| Purpose | Location |
|---------|----------|
| Core Services | `src/app/core/services/` |
| Core Layout | `src/app/core/layout/` |
| Interceptors | `src/app/core/interceptor/` |
| Directives | `src/app/core/directives/` |
| Features | `src/app/features/` |
| Environments | `src/environments/` |
| Styles | `src/style.scss` |
| Themes | `src/themes/` |

**Examples:**

- New component: `src/app/features/my-feature/my-feature.component.ts`
- New service: `src/app/core/services/my-service.service.ts`
- New route: Add to `src/app/app.routes.ts`

### Rule Scripts (Python)

| Purpose | Location |
|---------|----------|
| Git Workflows | `.cursor/skills/git-workflows/scripts/` |
| Rule Validation | `.cursor/skills/rule-authoring-patterns/scripts/` |
| Conversation History | `.cursor/skills/conversation-history/scripts/` |

**Examples:**

- Run GitLab script: `uv run .cursor/skills/git-workflows/scripts/fetch_project.py`
