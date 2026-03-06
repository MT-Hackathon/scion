# Rootstock/Graft Bugbot Configuration

## Project Overview
- **Project**: Rootstock/Graft — knowledge curation and distribution system
- **Stack**: Rust/Tauri 2.0 (desktop) + SvelteKit/Svelte 5 adapter-static (frontend) + Rust graft-cli + Python FastAPI reference backend + curation scripts (PEP 723)
- **Architecture**: Contracts Over Wiring — typed boundaries, explicit data flow, frozen dataclasses
- **Development Branch**: `feature/graft-app-foundation`

---

## CRITICAL Rules (🔴 Merge Blocking)

### 1. No Hardcoded Secrets or Credentials
**Risk**: Credential exposure, security breach

✅ CORRECT:
```python
import os
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv('API_KEY')
SECRET_KEY = os.getenv('SECRET_KEY')
```

❌ WRONG:
```python
API_KEY = "sk_live_abc123xyz"
SECRET_KEY = "my-secret-key-12345"
```

**What to look for**:
- grep for hardcoded URLs, keys, tokens
- Check .env files are git-ignored
- Verify environment variable usage

---

### 2. Type Safety — No `Any`, Typed Boundaries Everywhere
**Risk**: Runtime bugs, contract violations, architectural drift

✅ CORRECT (Backend — frozen dataclass):
```python
from dataclasses import dataclass

@dataclass(frozen=True)
class SyncResult:
    added: list[str]
    removed: list[str]
    conflicts: list[str]
```

✅ CORRECT (Frontend — Svelte 5 `$props()`):
```svelte
<script lang="ts">
  interface Props {
    items: FileEntry[];
    onSelect: (path: string) => void;
  }
  let { items, onSelect }: Props = $props();
</script>
```

❌ WRONG (Backend — `Any` type):
```python
from typing import Any
def process(data: Any) -> Any:  # NEVER
    pass
```

❌ WRONG (Frontend — Svelte 4 `export let`):
```svelte
<script>
  export let items;  // Svelte 4 pattern, untyped
</script>
```

**What to look for**:
- `from typing import Any` or `: Any` annotations
- Functions without type hints or return types
- Svelte components using `export let` instead of `$props()`
- Dataclass fields without types

---

### 3. Input Validation on All API Endpoints
**Risk**: Invalid data corruption, type errors, injection attacks

✅ CORRECT (Backend — Pydantic model):
```python
from pydantic import BaseModel, field_validator

class ConnectRequest(BaseModel):
    project_path: str
    remote_url: str

    @field_validator('project_path')
    @classmethod
    def validate_path(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError('Project path required')
        return v.strip()

@app.post("/api/graft/connect")
async def connect_project(request: ConnectRequest):
    return graft.connect(request.project_path, request.remote_url)
```

✅ CORRECT (Frontend — Zod schema):
```typescript
import { z } from 'zod';

const connectSchema = z.object({
  projectPath: z.string().min(1, 'Project path required'),
  remoteUrl: z.string().url('Must be a valid URL')
});
```

❌ WRONG (No validation):
```python
@app.post("/api/graft/connect")
async def connect_project(path: str, url: str):
    return graft.connect(path, url)  # Garbage in!
```

**What to look for**:
- All endpoint parameters use Pydantic models
- Pydantic models use `field_validator` (not deprecated `@validator`)
- Frontend forms use Zod schemas
- No bare str/int/float endpoint parameters

---

### 4. Typed Contracts — Every Boundary Has Typed Inputs/Outputs
**Risk**: Hidden contracts, implicit dependencies, exception-as-control-flow

✅ CORRECT (Result record, not exception):
```python
@dataclass(frozen=True)
class PullResult:
    updated: list[str]
    skipped: list[str]
    conflicts: list[str]
    success: bool

def pull(project_path: str) -> PullResult:
    ...
    return PullResult(updated=updated, skipped=skipped, conflicts=[], success=True)
```

❌ WRONG (Exception as control flow):
```python
def pull(project_path: str) -> list[str]:
    if conflicts:
        raise ConflictError(conflicts)  # Exits the return contract
    return updated_files
```

**What to look for**:
- Functions returning untyped dicts or tuples
- Business logic raising exceptions for expected outcomes
- `Any` or missing return types on public functions
- Boundary functions without explicit input/output types

---

### 5. Fail-Closed Sync — Unclassified Files Must Error
**Risk**: Silent data loss, overwriting local customizations

✅ CORRECT:
```python
policy = load_policy(policy_path)
for file in cursor_files:
    classification = policy.get(file)
    if classification is None:
        raise UnclassifiedFileError(f"No policy for {file} — add to graft-policy.json")
```

❌ WRONG (Default to overwrite):
```python
for file in cursor_files:
    classification = policy.get(file, "sync")  # Silent overwrite of unknown files!
    sync_file(file, classification)
```

**What to look for**:
- `policy.get(file, <default>)` with a permissive default
- Missing files silently skipped during sync
- Any sync path that doesn't check policy classification

---

## HIGH Priority (🟠 Should Fix Before Merge)

### 6. Test Coverage >= 90%
**Requirement**: Minimum 90% code coverage

Run:
```bash
# Backend
python -m pytest tests/ -v --cov=src/graft --cov-report=term-missing --cov-fail-under=90

# Frontend
npm test -- --run --coverage
```

Requirements:
- Unit tests for all graft operations (connect, pull, push, status)
- Edge case tests (empty repos, missing policy, network failures)
- Error path tests for every API route

---

### 7. Frozen Dataclasses for Data Models
**Requirement**: Data models are frozen dataclasses — no methods on data

✅ CORRECT:
```python
@dataclass(frozen=True)
class PolicyEntry:
    path: str
    classification: str
    description: str
```

❌ WRONG (Mutable or methods on data):
```python
@dataclass
class PolicyEntry:
    path: str
    classification: str

    def is_protected(self) -> bool:  # Logic belongs in a function, not on data
        return self.classification == "protect"
```

---

### 8. Error Handling on All API Routes
**Requirement**: All endpoints handle errors gracefully with structured responses

✅ CORRECT:
```python
@router.get("/api/graft/status/{project_id}")
async def get_status(project_id: str):
    try:
        status = graft.status(project_id)
        if not status:
            raise HTTPException(status_code=404, detail="Project not found")
        return status
    except GraftError as e:
        logger.error(f"Graft error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
```

❌ WRONG (No error handling):
```python
@router.get("/api/graft/status/{project_id}")
async def get_status(project_id: str):
    return graft.status(project_id)  # What if fails?
```

---

### 9. Script Portability (PEP 723)
**Requirement**: CLI scripts use PEP 723 inline metadata, run with `uv run --script`

✅ CORRECT:
```python
# /// script
# requires-python = ">=3.11"
# dependencies = ["rich", "gitpython"]
# ///

import sys
from pathlib import Path
```

❌ WRONG (Workspace-coupled):
```python
from src.graft.models import SyncResult  # Couples to workspace layout!
```

**What to look for**:
- Scripts missing PEP 723 metadata block
- Scripts importing from workspace packages
- Scripts that fail when run from a different directory

---

## MEDIUM Priority (🟡 Should Fix Soon)

### 10. No Hardcoded Theme Values — Use Design Tokens
**Requirement**: All styling via CSS custom properties and design tokens, never hardcoded values

✅ CORRECT:
```svelte
<div class="bg-surface text-on-surface rounded-container p-spacing-md">
```

```css
.panel {
  background: var(--color-surface);
  border-radius: var(--radius-container);
  padding: var(--spacing-md);
}
```

❌ WRONG (Hardcoded):
```svelte
<div style="background: #ffffff; padding: 16px; border-radius: 8px;">
```

---

### 11. Type All Component Props — Svelte 5 `$props()`
**Requirement**: TypeScript types on all props using Svelte 5 runes

✅ CORRECT:
```svelte
<script lang="ts">
  interface Props {
    title: string;
    items: PolicyEntry[];
    onSync?: () => void;
  }
  let { title, items, onSync }: Props = $props();
</script>
```

❌ WRONG (Untyped or Svelte 4):
```svelte
<script>
  export let title;
  export let items;
</script>
```

---

### 12. Token Budget Awareness
**Requirement**: Canonical content earns its place — every token costs across all future sessions

**What to look for**:
- Rules or skills that duplicate content available elsewhere
- Overly verbose descriptions that could be compressed
- Generated content committed to canonical (artifacts belong per-user, not in shared)
- New always-on rules that could be skills instead

---

## Severity Definitions

🔴 **CRITICAL** (Merge Blocking)
- Security violations (secrets, credentials)
- Type safety violations (`Any`, untyped boundaries)
- Missing input validation on endpoints
- Contract violations (untyped returns, exceptions as control flow)
- Fail-closed sync violations

🟠 **HIGH** (Should Fix Before Merge)
- Test coverage below 90%
- Mutable data models
- Missing error handling on API routes
- Non-portable scripts

🟡 **MEDIUM** (Should Fix Soon)
- Hardcoded theme values
- Untyped or Svelte 4 component props
- Token budget violations

🟢 **LOW** (Optional)
- Formatting
- Comments
- Cleanup

---

## Review Checklist

### Security (MUST PASS)
- [ ] No hardcoded secrets or credentials
- [ ] Input validation on all endpoints (Pydantic + Zod)
- [ ] No sensitive data in logs

### Contracts (MUST PASS)
- [ ] All functions have typed inputs and outputs
- [ ] No `Any` types
- [ ] Data models are frozen dataclasses
- [ ] Business outcomes as result records, not exceptions
- [ ] Sync operations fail-closed on unclassified files

### Quality (SHOULD PASS)
- [ ] Test coverage >= 90%
- [ ] Edge cases tested (empty, missing, network failure)
- [ ] Error handling on all API routes
- [ ] Scripts use PEP 723, run with `uv run --script`

### Frontend (IF APPLICABLE)
- [ ] Svelte 5 `$props()` with TypeScript interfaces
- [ ] Design tokens / CSS custom properties for styling
- [ ] Zod schemas for form validation

---

## Running Bugbot

Bugbot runs automatically on all PRs. To manually trigger:
- Comment `@bugbot run` on the PR

**Settings** (Cursor Dashboard → Bugbot):
- Only Run when Mentioned: false (run on all PRs)
- Only Run Once: false (run on each commit)
- Hide "No Bugs Found": true (silence clean PRs)
