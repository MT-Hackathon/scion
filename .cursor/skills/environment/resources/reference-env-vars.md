# Environment Variables Registry

Environment variable documentation for procurement-web.

---

## Variable Categories

| Category | Location | Purpose |
|----------|----------|---------|
| Angular | `src/environments/environment.ts` | App configuration |
| Okta | `src/environments/environment.ts` | Authentication |
| Scripts | `.env` (project root) | Rule script credentials |

---

## Angular Environment Variables

Configured in `src/environments/environment.ts` as named exports:

| Export | Purpose | Example |
|--------|---------|---------|
| `oktaConfig` | Okta authentication configuration | See below |
| `apiConfig` | API base URL and mock settings | See below |
| `shellConfig` | App shell branding and navigation | See dev-project-architecture |
| `feedback` | Feedback form configuration | FormStack URL |

### Environment File Pattern

The environment file uses **named exports** (not a single `environment` object):

```typescript
// src/environments/environment.ts
import OktaAuth from '@okta/okta-auth-js';

// Okta authentication
export const oktaConfig = {
  oktaAuth: new OktaAuth({
    issuer: 'https://oktapreview.loginmt.com/',
    clientId: '0oar333jeihIdfrLN1d7',
    redirectUri: `${window.location.origin}/login/callback`,
    scopes: ['openid', 'profile', 'email'],
  }),
};

// API configuration
export const apiConfig = {
  baseUrl: '/api',           // Proxied in dev, absolute in prod
  mockEnabled: true,         // Toggle for mock vs real API
};

// App shell configuration
export const shellConfig: AppShellConfig = {
  branding: { /* ... */ },
  navigation: { /* ... */ },
};
```

### Production Environment

For production builds, create `environment.prod.ts` with:

```typescript
export const apiConfig = {
  baseUrl: 'https://api.mt.gov/procurement',
  mockEnabled: false,
};
```

---

## Rule Script Variables

Stored in `.env` at project root, loaded via `python-dotenv`:

| Variable | Purpose | Required |
|----------|---------|----------|
| `GITLAB_PERSONAL_ACCESS_TOKEN` | GitLab.com API access | For GitLab scripts |
| `GITHUB_PERSONAL_ACCESS_TOKEN` | GitHub API access | For GitHub scripts |
| `STATE_GITLAB_PERSONAL_ACCESS_TOKEN` | State GitLab (git.mt.gov) API access | For State GitLab scripts |

### .env Example

```bash
# .env (DO NOT COMMIT)
GITLAB_PERSONAL_ACCESS_TOKEN=glpat-xxxxxxxxxxxx
GITHUB_PERSONAL_ACCESS_TOKEN=ghp_xxxxxxxxxxxx
```

### Project Identifiers

| Variable | Value | Purpose |
|----------|-------|---------|
| `CDO_GITLAB_PROJECT_ID` | `cdo-office/procurement-web` | Origin GitLab project (default) |
| `CDO_GITLAB_PROJECT_ID_BACKEND` | `cdo-office/procurement-api` | Origin GitLab backend |
| `CDO_GITLAB_PROJECT_ID_FRONTEND` | `cdo-office/procurement-web` | Origin GitLab frontend |
| `CDO_GITHUB_PROJECT_ID` | `mt-hackathon/procurement-web` | Origin GitHub project (default) |
| `CDO_GITHUB_PROJECT_ID_BACKEND` | `mt-hackathon/procurement-api` | Origin GitHub backend |
| `CDO_GITHUB_PROJECT_ID_FRONTEND` | `mt-hackathon/procurement-web` | Origin GitHub frontend |
| `STATE_GITLAB_PROJECT_ID` | `procurement-web` | State GitLab project (default) |
| `STATE_GITLAB_PROJECT_ID_BACKEND` | `procurement-api` | State GitLab backend |
| `STATE_GITLAB_PROJECT_ID_FRONTEND` | `procurement-web` | State GitLab frontend |

Scripts should use these environment variables instead of hardcoding project paths.

### .env.example (Commit This)

```bash
# .env.example
GITLAB_PERSONAL_ACCESS_TOKEN=your-gitlab-token-here
GITHUB_PERSONAL_ACCESS_TOKEN=your-github-token-here
STATE_GITLAB_PERSONAL_ACCESS_TOKEN=your-state-gitlab-token-here

# Project identifiers (these have defaults in scripts but can be overridden)
CDO_GITLAB_PROJECT_ID=cdo-office/procurement-web
CDO_GITLAB_PROJECT_ID_BACKEND=cdo-office/procurement-api
CDO_GITLAB_PROJECT_ID_FRONTEND=cdo-office/procurement-web
CDO_GITHUB_PROJECT_ID=mt-hackathon/procurement-web
CDO_GITHUB_PROJECT_ID_BACKEND=mt-hackathon/procurement-api
CDO_GITHUB_PROJECT_ID_FRONTEND=mt-hackathon/procurement-web
STATE_GITLAB_PROJECT_ID=procurement-web
STATE_GITLAB_PROJECT_ID_BACKEND=procurement-api
STATE_GITLAB_PROJECT_ID_FRONTEND=procurement-web
```

### Usage in Scripts

```python
from dotenv import load_dotenv
import os

load_dotenv()

gitlab_token = os.getenv("GITLAB_PERSONAL_ACCESS_TOKEN")
if not gitlab_token:
    raise ValueError("GITLAB_PERSONAL_ACCESS_TOKEN not set in .env")
```

---

## Security Rules

1. **Never commit `.env`** - Add to `.gitignore`
2. **Use `.env.example`** - Document required variables without values
3. **No secrets in environment.ts** - Only non-sensitive config
4. **Okta client ID is public** - But issuer URL may reveal org info

---

## Troubleshooting

### Script can't find environment variable

```bash
# Verify .env exists
ls -la .env

# Verify variable is set
grep "GITLAB_PERSONAL_ACCESS_TOKEN" .env
```

### Angular environment not loading

```bash
# Check you're using the right import
import {environment} from '@env/environment';

# Not
import {environment} from 'src/environments/environment';
```

### Production config not applied

```bash
# Build with production configuration
ng build --configuration=production
```
