# Rootstock/Graft Bugbot Configuration

## Project Overview
- **Project**: Rootstock/Graft — knowledge curation and distribution system
- **Stack**: Rust `graft-core` sync engine + Rust/clap `graft-cli` + Rust/axum `graft-http` (test adapter) + Rust/Tauri 2.0 desktop (`src-tauri`) + SvelteKit/Svelte 5 + TypeScript + Zod + Tailwind CSS 4 frontend + skill scripts (PEP 723)
- **Architecture**: Contracts Over Wiring — typed boundaries, explicit data flow, immutable value models
- **Development Branch**: `refactor/rust-port`

---

## CRITICAL Rules (🔴 Merge Blocking)

### 1. No Hardcoded Secrets or Credentials
**Risk**: Credential exposure, security breach

✅ CORRECT:
```rust
fn get_config() -> GraftResult<Config> {
    let token = std::env::var("GITLAB_TOKEN")
        .map_err(|_| GraftError::Config("GITLAB_TOKEN not set".into()))?;
    Ok(Config { token })
}
```

❌ WRONG:
```rust
const GITLAB_TOKEN: &str = "glpat-abc123xyz"; // NEVER
```

**What to look for**:
- Hardcoded string literals that look like tokens
- URLs with embedded credentials
- `.env` files not in `.gitignore`

---

### 2. Type Safety — No `Any`, Typed Boundaries Everywhere
**Risk**: Runtime bugs, contract violations, architectural drift

✅ CORRECT (Backend — typed struct):
```rust
#[derive(Debug, serde::Serialize, serde::Deserialize)]
pub struct SyncResult { pub added: Vec<String>, pub removed: Vec<String> }
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

❌ WRONG (Backend — untyped return):
```rust
pub fn sync() -> serde_json::Value { ... }
```

❌ WRONG (Frontend — untyped `any`):
```typescript
function render(result: any) { /* ... */ }
```

**What to look for**:
- `serde_json::Value` where a typed struct should exist
- TypeScript `any`
- Svelte components using `export let` instead of `$props()`

---

### 3. Input Validation on All API Endpoints
**Risk**: Invalid data corruption, type errors, injection attacks

✅ CORRECT (Backend — Rust/axum):
```rust
async fn connect_handler(Json(req): Json<ConnectRequest>) -> Result<Json<ConnectResult>, AppError> {
    if req.target_repo.is_empty() {
        return Err(AppError::Validation("target_repo required".into()));
    }
    run_connect(...).map_err(AppError::Graft)
}
```

✅ CORRECT (Frontend — Zod schema):
```typescript
import { z } from 'zod';

const connectSchema = z.object({
  targetRepo: z.string().min(1, 'Target repo required'),
  scionRepo: z.string().min(1, 'Scion repo required'),
  projectName: z.string().min(1, 'Project name required'),
  contributor: z.string().min(1, 'Contributor required')
});
```

❌ WRONG (raw params, no validation):
```rust
async fn connect_handler(target: String) -> Json<Value> { ... }
```

**What to look for**:
- Tauri commands or HTTP routes with raw `String` parameters and no guard-clause validation
- Frontend forms without Zod schemas

---

### 4. Typed Contracts — Every Boundary Has Typed Inputs/Outputs
**Risk**: Hidden contracts, implicit dependencies, exception-as-control-flow

✅ CORRECT:
```rust
pub fn run_pull(target: &Path, dry_run: bool) -> GraftResult<PullResult> {
    Ok(PullResult { updated, skipped, conflicts })
}
```

❌ WRONG (panic or untyped return):
```rust
pub fn run_pull(target: &Path) -> Vec<String> { ... }
```

**What to look for**:
- Functions returning `serde_json::Value` or raw strings at domain boundaries
- `unwrap()` / `expect()` on paths that could realistically fail
- Missing `GraftResult<T>` wrappers on public `graft-core` functions

---

### 5. Fail-Closed Sync — Unclassified Files Must Error
**Risk**: Silent data loss, overwriting local customizations

✅ CORRECT:
```rust
fn classify(path: &str, policy: &Policy) -> GraftResult<Classification> {
    policy.get(path).ok_or_else(|| GraftError::UnclassifiedFiles(vec![path.to_string()]))
}
```

❌ WRONG:
```rust
fn classify(path: &str, policy: &Policy) -> Classification {
    policy.get(path).cloned().unwrap_or(Classification::Overwrite)
}
```

**What to look for**:
- `unwrap_or` defaults that silently overwrite unknown files
- Missing classification checks before sync operations
- Any sync path that does not fail on unknown policy entries

---

## HIGH Priority (🟠 Should Fix Before Merge)

### 6. Test Coverage >= 90%
**Requirement**: Minimum 90% code coverage

Run:
```bash
cargo test --workspace
npm test -- --run --coverage
```

Requirements:
- Unit tests for all graft operations (connect, pull, push, status)
- Edge case tests (empty repos, missing policy, network failures)
- Error path tests for every route and Tauri command boundary

---

### 7. Rust Struct Immutability — Data Models Are Value Types
**Requirement**: Data models are immutable value types — no mutation methods on data

✅ CORRECT:
```rust
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct PolicyEntry { pub path: String, pub classification: Classification }
```

❌ WRONG:
```rust
impl PolicyEntry { pub fn promote(&mut self) { ... } }
```

---

### 8. Error Handling on All Routes
**Requirement**: All routes and command handlers return typed errors and avoid panic paths

✅ CORRECT:
```rust
async fn status_handler(Query(p): Query<StatusParams>) -> Result<Json<StatusDto>, AppError> {
    run_status(&p.target_repo, None, false).map(|r| Json(r.into())).map_err(AppError::Graft)
}
```

❌ WRONG:
```rust
async fn status_handler(Query(p): Query<StatusParams>) -> Json<StatusDto> {
    Json(run_status(&p.target_repo, None, false).unwrap().into())
}
```

---

### 9. Guard Clause Efficiency (🟡 MEDIUM)
**Risk**: Hidden performance costs and repeated expensive operations

❌ WRONG (repeats expensive setup):
```rust
fn run_pull(target: &Path) -> GraftResult<PullResult> {
    let repo = Repository::open(target)?; // expensive
    if repo.head_is_unborn() { return Err(...); }
    let context = build_sync_context(target, ...)?; // opens again
}
```

✅ CORRECT (build once, guard on context):
```rust
fn run_pull(target: &Path) -> GraftResult<PullResult> {
    let context = build_sync_context(target, ...)?;
    if context.repo.head_is_unborn() { return Err(...); }
}
```

**What to look for**:
- `Repository::open()` called more than once in a call chain
- File I/O in guards repeated again in main body
- JSON deserialization in a guard followed by re-deserialization

---

### 10. No Composition Duplication (🟠 HIGH)
**Risk**: Validation drift, inconsistent behavior across surfaces

❌ WRONG (duplicated domain validation in composition layer):
```rust
async fn connect_handler(Json(req): Json<ConnectRequest>) -> ... {
    if !Path::new(&req.target_repo).exists() { return Err(...); } // graft-core checks this
    run_connect(...)
}
```

✅ CORRECT:
```rust
async fn connect_handler(Json(req): Json<ConnectRequest>) -> ... {
    run_connect(...).map_err(AppError::Graft)
}
```

**What to look for**:
- Path existence checks duplicated across `graft-http`, `graft-cli`, or Tauri commands
- Git repo validation duplicated outside `graft-core`
- Policy loading and classification logic repeated in surface layers

---

### 11. Script Portability (PEP 723)
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

❌ WRONG (workspace-coupled):
```python
from src.graft.models import SyncResult
```

**What to look for**:
- Scripts missing PEP 723 metadata block
- Scripts importing from workspace packages
- Scripts that fail when run from a different directory

---

## MEDIUM Priority (🟡 Should Fix Soon)

### 12. No Hardcoded Theme Values — Use Design Tokens
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

❌ WRONG:
```svelte
<div style="background: #ffffff; padding: 16px; border-radius: 8px;">
```

---

### 13. Type All Component Props — Svelte 5 `$props()`
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

❌ WRONG (untyped or Svelte 4):
```svelte
<script>
  export let title;
  export let items;
</script>
```

---

### 14. Token Budget Awareness
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
- Missing error handling on routes
- Non-portable scripts
- Composition duplication across layers

🟡 **MEDIUM** (Should Fix Soon)
- Hardcoded theme values
- Untyped or Svelte 4 component props
- Guard clause inefficiency and duplicated expensive setup
- Token budget violations

🟢 **LOW** (Optional)
- Formatting
- Comments
- Cleanup

---

## Review Checklist

### Security (MUST PASS)
- [ ] No hardcoded secrets or credentials
- [ ] Input validation on all endpoints (Rust guard clauses + Zod)
- [ ] No sensitive data in logs

### Rust Backend (IF APPLICABLE)
- [ ] All public graft-core functions return GraftResult<T>
- [ ] No unwrap()/expect() on non-fatal paths
- [ ] Error variants carry path and source context for actionable messages
- [ ] No serde_json::Value returns where typed structs exist
- [ ] No logic duplication between graft-http/graft-cli/Tauri and graft-core
- [ ] Guards do not re-open git repos or re-parse JSON the body will also parse
- [ ] Data structs derive Debug, Clone, Serialize, Deserialize — no mutation methods

### Quality (SHOULD PASS)
- [ ] Test coverage >= 90%
- [ ] Edge cases tested (empty, missing, network failure)
- [ ] Error handling on all routes
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
