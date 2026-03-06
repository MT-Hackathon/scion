# Plan: Frontend Route Testing Gap Close

**Slug**: `testing-gap-close`
**Triggered by**: Coverage audit — 0/7 route pages tested despite full infrastructure being in place
**Status**: Ready

---

## Context

The rootstock frontend has 20/20 UI components tested and 5/5 utils tested, but zero route-level tests of any kind. The testing infrastructure is fully wired and waiting: Playwright config exists (`playwright.config.ts`), a `test:e2e` npm script exists, the `graft-http` crate provides a real HTTP backend that mirrors Tauri commands, and the `transport.ts` layer automatically falls back to HTTP when outside Tauri — meaning every route works in a plain browser against `graft-http`. The `tests/` directory referenced by `playwright.config.ts` was never created.

### What Already Works

| Layer | Status | Notes |
|-------|--------|-------|
| `transport.ts` dual-mode | Operational | `isTauri` false in test → all calls go HTTP |
| `graft-http` on :8000 | Operational | Real Rust backend, same `graft-core` logic as Tauri |
| Vite proxy `/api` → :8000 | Configured | In `vite.config.ts` server.proxy |
| `playwright.config.ts` | Configured | webServer: `npm run build && npm run preview`, port 4173, testDir: `tests/` |
| `test:e2e` script | Exists | Runs `playwright test` |
| Vitest browser mode | Operational | 21 `.svelte.test.ts` files running in Chromium |

### What's Missing

1. The `tests/` directory (Playwright E2E test files)
2. A test fixture/seed mechanism for `graft-http` (projects to list, policies to edit)
3. Actual test scenarios for the 4 substantive routes

---

## Route Inventory

| Route | File | Lines | Complexity | Priority |
|-------|------|-------|------------|----------|
| `/dashboard` | `src/routes/dashboard/+page.svelte` | ~470 | 5 loading states, derived filters, drawer with 4 action sections, drift badge, bulk ops | P0 |
| `/settings` | `src/routes/settings/+page.svelte` | ~370 | Scion path config, auto-push toggle, policy table with inline edit + CRUD | P0 |
| `/settings/connect` | `src/routes/settings/connect/+page.svelte` | ~280 | Multi-step form, Zod validation, preflight checks, repo discovery | P1 |
| `/` | `src/routes/+page.svelte` | ~10 | Redirect to /dashboard | P2 |
| `/dev` | `src/routes/dev/+page.svelte` | ~180 | Component showcase, not in nav | P3 (skip) |
| `+layout.svelte` | `src/routes/+layout.svelte` | ~227 | Sidebar nav, mobile bar, git-unavailable banner, theme switcher | P1 |
| `+error.svelte` | `src/routes/+error.svelte` | ~20 | Error boundary | P2 |

---

## Testing Strategy

### Approach: Playwright E2E against standalone frontend + `graft-http`

This is the path the codebase was designed for. The Playwright config, transport layer, HTTP backend, and vite proxy are all wired. We write standard Playwright page tests.

### Test Environment Setup

```
# Terminal 1: Start graft-http backend
cargo run -p graft-http

# Terminal 2: Build and preview frontend (Playwright does this automatically via webServer config)
cd app/frontend && npm run build && npm run preview
```

Playwright's `webServer` config in `playwright.config.ts` handles terminal 2 automatically. Terminal 1 (`graft-http`) needs to be running before tests start — either manually or by extending the Playwright config to start it.

### Fixture Strategy

`graft-http` operates against real filesystem state (scion repo, connected projects). Tests need a known starting state. Options:

1. **Recommended**: Add a `POST /api/test/reset` endpoint to `graft-http` (test-only, behind a feature flag or `#[cfg(test)]` equivalent) that resets the DB and creates a known fixture set
2. **Alternative**: Use a temp directory as scion path and pre-populate it in a Playwright `globalSetup` script
3. **Minimum viable**: Test against whatever state exists — works for read-only tests but not for CRUD operations

---

## Test Scenarios

### Dashboard (`tests/dashboard.test.ts`)

**Data display:**
- Page loads and shows project list (or empty state if no projects)
- Summary stats bar shows correct counts (total, synced, drifted, error)
- Status filter dropdown filters the project list
- Column headers align with row data (Bug 2 regression)
- Dark mode: all text readable, no hardcoded colors (Bug 3 regression)

**Drawer interaction:**
- Click project row → drawer opens (push mode, not overlay)
- Drawer shows project details: status badge, timestamps, drift count
- Close drawer: ✕ button works, Escape key works
- Drawer pushes list aside (not overlays)

**Actions (require connected projects):**
- Pull Now → loading state → success/error toast
- Push Now → loading state → success/error toast
- Contribute to Scion → separate loading state → toast
- Pull Preview → shows file count breakdown
- Check Status → refreshes status display
- Disconnect → removes project from list

**Bulk operations:**
- Pull All button → per-project loading → aggregate toast
- Push All button → per-project loading → aggregate toast
- Bulk buttons disable per-project buttons during operation

**Drift badge:**
- Project with >5 modified files shows "Curation Recommended" badge

### Settings (`tests/settings.test.ts`)

**Scion path:**
- Displays current scion path (or empty state)
- Edit path → save → success feedback

**Auto-push:**
- Toggle auto-push on/off
- Debounce input accepts numeric value

**Policy table:**
- Displays policy rows with pattern + classification columns
- Inline classification editing via Select dropdown
- Add Pattern → dialog opens → enter pattern + classification → row appears
- Add Pattern validation: empty pattern rejected, duplicate rejected
- Delete pattern → confirm → row removed
- Both add/delete show toast feedback
- Error rollback: if API fails, optimistic change reverts

### Settings/Connect (`tests/settings-connect.test.ts`)

**Multi-step form:**
- Step 1: Enter project path → preflight validation
- Step 2: Configure connection options
- Step 3: Confirm and connect
- Back button returns to previous step
- Invalid path shows validation error
- Successful connect redirects to dashboard

### Layout (`tests/layout.test.ts`)

**Navigation:**
- Sidebar shows Dashboard and Settings links
- Active route is visually highlighted
- Navigation between routes works
- Root `/` redirects to `/dashboard`

**Theme:**
- Theme switcher toggles between light/dark
- Dark mode applies correct CSS variables

**Responsive:**
- Mobile viewport: top bar replaces sidebar

---

## Cascade Considerations

- `graft-http` may need a new route for `graft_pull_preview` (Issue #15 added the Tauri command but the HTTP adapter may not have a matching route yet — verify before writing pull preview tests)
- `graft-http` may need bulk operation routes (`/api/graft/pull/all`, `/api/graft/push/all`) — verify
- The connect flow calls `graft_preflight_connect` and `graft_discover_repos` — verify these have HTTP routes
- `playwright.config.ts` currently doesn't start `graft-http` — consider adding it to `webServer` as a second server or to `globalSetup`

---

## Execution Plan

| Phase | What | Agent |
|-------|------|-------|
| 0 | Verify `graft-http` route coverage — ensure all Tauri commands used by routes have HTTP equivalents. Add missing routes. | Executor (Rust) |
| 1 | Create `tests/` directory, write dashboard tests (P0) | Executor (TS) |
| 2 | Write settings + layout tests (P0/P1) | Executor (TS) |
| 3 | Write connect flow tests (P1) | Executor (TS) |
| 4 | Update `playwright.config.ts` to auto-start `graft-http` if feasible | Executor (TS) |
| 5 | Run full suite, fix any failures | QA |

### Verification Commands

```bash
# Start backend
cargo run -p graft-http &

# Run E2E tests
cd app/frontend && npm run test:e2e

# Component + unit tests still pass
cd app/frontend && npm test -- --run

# Rust tests still pass
cargo test --workspace
```

---

## Rust Test Gaps (Separate Follow-Up)

These are documented but NOT in scope for this plan. They should be a separate effort:

| Module | Gap | Risk Level |
|--------|-----|------------|
| `workflows.rs` | No direct tests; partially covered by integration tests | High (top complexity hotspot) |
| `db.rs` | No tests; SQLite schema, migrations, CRUD | High (100% cascade predictor) |
| `commands.rs` | No tests; Tauri IPC boundary | Medium (thin layer) |
| `mcp/tools.rs` | No tests; 17 tool handlers | Medium (just changed) |
| `graft-http/routes.rs` | No tests; HTTP handlers | Medium (thin layer) |
| `tray.rs` | No tests; system tray logic | High (top risk hotspot) |

---

## Notes

- The `graft-http` crate is explicitly a TEST ADAPTER — it exists to enable exactly this testing pattern. It's not a production server.
- `transport.ts` Tauri branches are marked `/* v8 ignore */` — Tauri IPC code paths are intentionally excluded from coverage. Testing them requires `@tauri-apps/api/mocks` or `tauri-driver`, both of which are lower priority than getting route coverage.
- The dual-transport pattern means every route test simultaneously validates both the frontend logic AND the `graft-core` backend logic through `graft-http`.
