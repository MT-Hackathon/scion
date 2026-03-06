# Plan: MasterDetail Layout Refactor + Stability Fixes

**Slug**: `master-detail-layout` (filename: `.cursor/plans/master-detail-layout.md`)  
**Triggered by**: Stability walk — drawer sandwiching between header/footer, theme cascade revealing fragmented component architecture, open quality items from prior review  
**Status**: Draft

---

## Context

ListPage currently owns both content rendering (table, filters, pagination) and layout coordination (drawer split, height distribution). The drawer ends up as a flex sibling of the inner content column rather than the full page, creating a "sandwich" between the page header and pagination footer. This same anti-pattern has recurred across Angular and Svelte implementations — the problem is conceptual, not framework-specific.

The desktop app header is a 56px bar holding only the theme switcher, wasting vertical space. The theme switch itself produces a visible cascade because `transition-colors` is applied inconsistently, and component-tier token resolution varies in indirection depth.

The fix is a separation of concerns: a new `MasterDetailLayout` component owns the horizontal split, ListPage becomes a pure list, DrawerPeek becomes a pure panel, and the app shell loses its dead-chrome header.

---

## Requirements and Acceptance Criteria

| # | Requirement | Status | Notes |
|---|-------------|--------|-------|
| R1 | Drawer spans full available height (top of content area to bottom of viewport, minus sidebar) | LOCKED | Eliminates sandwich effect |
| R2 | Page header (title + action buttons) stays full width when drawer is open | LOCKED | Already partially implemented but tied to ListPage |
| R3 | Desktop header bar removed; ThemeSwitcher relocated to sidebar footer | LOCKED | Recovers 56px vertical space |
| R4 | Mobile hamburger bar retained as sidebar trigger | LOCKED | No change to mobile nav pattern |
| R5 | Drawer mode auto-switches: push when container >= ~1160px (760 + 400), overlay below that, near-fullscreen on mobile | LOCKED | Container query, not viewport breakpoint |
| R6 | Master panel scrolls as one unit (stats + title + filters + table + pagination) | LOCKED | Eliminates fixed header/footer chrome within content |
| R7 | Remove `transition-colors` from structural elements; keep only on interactive elements (buttons, links, nav items) | LOCKED | Eliminates theme cascade visual |
| R8 | All existing tests pass (268 tests) | LOCKED | |
| R9 | Zero svelte-check errors, lint clean | LOCKED | |
| R10 | Replace `globalThis.confirm` in Disconnect flow with a proper Dialog component | LOCKED | Blocks Playwright testing, inconsistent UX — flagged in original review |
| R11 | Eliminate duplicate DB load in `graft_pull_all`/`graft_push_all` Tauri commands | N/A | Pure performance — commands build name map then re-query for operation filter. Consolidate to single query. |
| R12 | Settings page stability walk: policy table, add/delete pattern, scion path, auto-push toggle | LOCKED | Never completed — must verify during QA |

---

## Cascade Analysis

**Order 1 — Direct dependents** (impacted immediately by this change):
- Risk: `ListPage` API changes break `dashboard/+page.svelte` and `settings/+page.svelte` usage. Both pages currently pass `drawer` and `drawerTitle` snippets to ListPage. These move to `MasterDetailLayout`.

**Order 2 — Consequential modules** (likely to require coordinated change):
- Risk: `ListPage` tests that assert drawer behavior (open/close, push mode) will need updating since ListPage no longer owns the drawer. ~6 tests in `ListPage.svelte.test.ts` likely affected.
- Risk: `DrawerPeek` tests that test overlay mode with portal — these should be stable since DrawerPeek's API doesn't change, but integration context changes.

**Order 3 — Conditional failures** (if assumptions break):
- Risk: Scroll containment regressions (`min-h-0`, `overflow-hidden` chains). The new layout must preserve correct scroll behavior — table body scrolls, page doesn't double-scroll, drawer content scrolls independently. Easy to break, hard to detect without visual testing.
- Risk: z-index conflicts between sidebar mobile overlay (z-50) and drawer overlay mode (z-50). May need z-index audit.

---

## Risk Inventory

| Risk | Likelihood | Impact | Verification Step |
|------|------------|--------|-------------------|
| Scroll containment regression | Medium | High | Visual QA: open dashboard, fill table beyond viewport, verify single scroll bar on master panel, independent scroll in drawer |
| ListPage test breakage | High | Low | `npm test -- --run` — failures expected and mechanical to fix |
| z-index sidebar/drawer conflict | Low | Medium | Open drawer in overlay mode while sidebar is collapsed on mobile viewport |
| Theme switcher relocation breaks mobile layout | Low | Medium | Resize to <768px, verify hamburger menu still works, theme toggle accessible |
| Container query browser support | Low | Low | Tauri uses Chromium >=120; container queries fully supported. Verify with `@container` in dev tools |

---

## Delegation Structure

| Phase | Agent | Brief Summary | Handoff Criteria | Verification Command |
|-------|-------|---------------|------------------|----------------------|
| 0 | Researcher | Research container query patterns for push/overlay switching in Svelte/Tailwind 4 | Summary of pattern + working example | N/A |
| 1 | Executor | Create MasterDetailLayout component, refactor ListPage, update +layout.svelte | Compiles, tests adapted, lint clean | `npm test -- --run && npm run lint` |
| 2 | Executor | Theme cascade cleanup — audit transition-colors usage, remove from structural elements | Theme switch is instant (no visible cascade) | Visual inspection + `npm run lint` |
| 2.5 | Executor | Replace globalThis.confirm with Dialog component; fix duplicate DB load in Tauri commands | Compiles, tests pass | `cargo check --workspace && npm test -- --run` |
| 3 | QA | Full pass: scroll containment, z-index audit, responsive breakpoints, theme switch, settings walk, all tests | All acceptance criteria R1-R12 verified | `npm test -- --run && npx svelte-check && cargo clippy --workspace` |

---

## Phase Detail

### Phase 0: Researcher — Container Query Patterns

**Task**: Research how to implement container-query-driven push/overlay switching for a side panel in SvelteKit + Tailwind CSS 4. Specifically:
- Can `@container` queries drive a Svelte component's mode (push vs overlay) without JavaScript?
- Or should a `ResizeObserver` on the container set a reactive `mode` state?
- What's the Tailwind 4 syntax for container queries (`@container` utilities)?
- Any anti-patterns for container queries in Tauri's Chromium WebView?

**Deliverable**: Summary with recommended pattern and a minimal code example.

---

### Phase 1: Executor — MasterDetailLayout + App Shell Refactor

**Files in scope**:
- `app/frontend/src/lib/ui/frameworks/MasterDetailLayout.svelte` (NEW)
- `app/frontend/src/lib/ui/frameworks/ListPage.svelte` (MODIFY — remove drawer, remove header from flex-row)
- `app/frontend/src/lib/ui/frameworks/index.ts` (MODIFY — export MasterDetailLayout)
- `app/frontend/src/routes/+layout.svelte` (MODIFY — remove desktop header, move ThemeSwitcher to sidebar footer)
- `app/frontend/src/routes/dashboard/+page.svelte` (MODIFY — wrap ListPage in MasterDetailLayout, move drawer snippet)
- `app/frontend/src/routes/settings/+page.svelte` (MODIFY — verify no drawer usage, adapt if needed)
- `app/frontend/src/lib/ui/frameworks/__tests__/ListPage.svelte.test.ts` (MODIFY — remove drawer-related tests)
- `app/frontend/src/lib/ui/frameworks/__tests__/MasterDetailLayout.svelte.test.ts` (NEW)

**MasterDetailLayout component contract**:
```svelte
<MasterDetailLayout
  open={drawerOpen}
  onclose={closeDrawer}
  drawerWidth="400px"
  minMasterWidth="760px"
>
  {#snippet master()}
    <ListPage ...>...</ListPage>
  {/snippet}
  {#snippet detail()}
    <DrawerContent ... />
  {/snippet}
  {#snippet detailTitle()}
    <span>...</span>
  {/snippet}
</MasterDetailLayout>
```

The component:
1. Uses CSS grid with two columns: `1fr` master + width-transitioning detail
2. Container query (or ResizeObserver — per Phase 0 research) determines push vs overlay
3. In push mode: detail is a grid column, master compresses
4. In overlay mode: detail uses portal + fixed positioning (reuses existing DrawerPeek overlay pattern)
5. Owns the `DrawerPeek` instance internally — pages pass content, not the component
6. Full available height (`flex-1` in the app shell, no header above)

**App shell changes**:
- Remove `<header class="hidden md:flex h-14...">` (desktop-only header bar)
- Move `<ThemeSwitcher />` into sidebar footer, next to collapse toggle
- `<main>` becomes `flex-1` filling from top of content area to bottom

**Verification**:
```powershell
cd app/frontend && npx svelte-kit sync && npx svelte-check --tsconfig ./tsconfig.json
cd app/frontend && npm run lint
cd app/frontend && npm test -- --run
```

**Handoff criteria**: All tests pass (some rewritten), zero svelte-check errors, lint clean.

---

### Phase 2: Executor — Theme Cascade Cleanup

**Files in scope**:
- `app/frontend/src/lib/tokens/tokens.css` — audit component-tier dark overrides for completeness
- All `.svelte` component files — grep for `transition-colors` and `transition-[color]`

**Task**:
1. Search all Svelte files for `transition-colors` class usage
2. Remove from structural/container elements (divs, sections, aside, main, layout wrappers)
3. Keep on interactive elements: buttons, links, nav items, form controls
4. Audit `tokens.css` component tier: ensure every component section that references semantic variables has a `[data-theme='dark']` block with direct primitive references (eliminating extra indirection hop)

**Verification**: Toggle theme in running app — all colors should change simultaneously with no visible ripple or cascade.

---

### Phase 2.5: Executor — Quality Fixes

**Files in scope**:
- `app/frontend/src/routes/dashboard/+page.svelte` (MODIFY — replace `confirm()` with Dialog)
- `app/frontend/src/lib/ui/ConfirmDialog.svelte` (NEW — if no Dialog component exists yet; otherwise use existing)
- `src-tauri/src/commands.rs` (MODIFY — `graft_pull_all`, `graft_push_all` duplicate DB load)

**Task**:

1. **Replace `globalThis.confirm`**: The `handleDisconnect` function in `dashboard/+page.svelte` uses `confirm()` which blocks the UI thread and cannot be tested by Playwright. Replace with a proper Dialog component (check if one already exists in `$lib/ui/`). The dialog should:
   - Show the same message text currently in the `confirm()` call
   - Have Cancel and Disconnect buttons
   - Call `disconnectProject` only on explicit Disconnect confirmation
   - Be async/promise-based or callback-based, matching existing component patterns

2. **Fix duplicate DB load**: In `src-tauri/src/commands.rs`, the `graft_pull_all` and `graft_push_all` commands:
   - First call `db::list_projects()` to build a name map for results
   - Then call `workflows::run_pull_all()` / `run_push_all()` which internally also loads the project list
   - Consolidate: either pass the already-loaded list into the workflow function, or restructure so only one query occurs

**Verification**:
```powershell
cargo check --workspace --all-targets
cargo clippy --workspace --all-targets -- -D warnings
cd app/frontend && npm test -- --run
```

---

### Phase 3: QA — Full Verification Pass

**Scope**: All acceptance criteria R1-R12.

**Checklist**:
- [ ] Drawer spans full height (sidebar bottom to window bottom)
- [ ] Page header stays full width with drawer open
- [ ] No desktop header bar; theme switcher in sidebar footer
- [ ] Mobile: hamburger bar present, theme toggle accessible
- [ ] Drawer push mode at wide viewport
- [ ] Drawer overlay mode at narrow viewport
- [ ] Drawer near-fullscreen on mobile
- [ ] Master panel scrolls as one unit
- [ ] Theme switch is instant — no cascade
- [ ] Disconnect uses Dialog component (no `globalThis.confirm`)
- [ ] Settings page walk: policy table loads, add/delete pattern works, scion path, auto-push toggle
- [ ] 268+ tests passing
- [ ] Zero svelte-check errors
- [ ] Lint clean, clippy clean
- [ ] No scroll containment regressions (table scrolls, no double scroll)
- [ ] z-index: drawer overlay doesn't conflict with mobile sidebar

---

## Notes and Open Questions

**Settled decisions (do not re-derive)**:
- Option A (MasterDetailLayout component) with Option B (CSS grid) as implementation. Confirmed by Architect.
- Desktop header removed. ThemeSwitcher to sidebar footer. Mobile hamburger bar stays.
- Push/overlay switching by container width, not viewport breakpoint. Threshold: ~1160px.
- ListPage loses all drawer responsibility. DrawerPeek stays as pure panel chrome.

**Open for Phase 0 research**:
- Container query vs ResizeObserver for mode switching — research needed for Tailwind 4 + SvelteKit best practice.
- Whether `@container` can drive Svelte reactive state or needs a JS bridge.

**UX finding from stability walk — push/pull naming ambiguity**:
In the dashboard drawer, "Sync from Scion" = pull, "Push Now" = push to contributor branch. But when the user sees "Pull Preview: 513 files will be copied," it's unclear which direction files are moving. "Push" and "Pull" are git-centric terms that don't map to the user's mental model of "update my project" vs "share my changes." Consider renaming to directional labels: "Update from Scion" / "Contribute to Scion" or "Download" / "Upload" or similar. The action buttons in the drawer ("Sync from Scion" is better than "Pull") and the stat label ("Drift" is ambiguous — drift from what, in which direction?) need a naming pass. This is a UX task, not a code task — the buttons work, the words don't.

**Related work**:
- Telemetry instrumentation (Rust `tracing` crate + frontend wrapper) — issue filed separately. Pattern settled: instrument freely, `tracing` with no subscriber is zero-cost (one atomic load). No `max_level_release` — desktop app benefits from being able to attach a subscriber without recompile.
- Issue #70 (Learning onboarding) — MasterDetailLayout is a prerequisite for good onboarding UX.
- Issue #69 (Auto-sync daemon) — not in scope here but affects dashboard data freshness.
