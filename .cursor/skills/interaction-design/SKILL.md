---
name: interaction-design
description: "Governs temporal UX and interaction design: state machine contracts for multi-step flows, loading feedback tiers (skeleton/spinner/progress), form lifecycle phases, credential management UX (reveal/edit/batch-import/delete), destructive action graduation (3 tiers), transition contracts (enter/exit/transform), toast notification rules, and settings-class information architecture. Use when building or reviewing any multi-step user flow, loading state, form lifecycle, credential management pattern, or destructive action confirmation. DO NOT use for spatial layout and overlay decisions (see ui-architecture), Svelte component implementation (see svelte-ui), or accessibility compliance (see accessibility)."
---

<ANCHORSKILL-INTERACTION-DESIGN>

# Interaction Design

Temporal UX governs how users experience interfaces **through time** — the sequence of states, the feedback between them, and the rules that make transitions feel intentional rather than arbitrary. `ui-architecture` owns space. This skill owns time.

**Grounded in**: Nielsen Norman Group interaction research, Material Design 3 interaction patterns, Apple HIG, 1Password/AWS Console/HashiCorp Vault UI patterns.

## Table of Contents

- [When to Use This Skill](#when-to-use-this-skill)
- [1. State Machine Contracts](#1-state-machine-contracts)
- [2. Loading Feedback Hierarchy](#2-loading-feedback-hierarchy)
- [3. Form Lifecycle Contracts](#3-form-lifecycle-contracts)
- [4. Credential Management UX](#4-credential-management-ux)
- [5. Destructive Action Graduation](#5-destructive-action-graduation)
- [6. Transition Contracts](#6-transition-contracts)
- [7. Notifications and Toasts](#7-notifications-and-toasts)
- [8. Information Architecture Patterns](#8-information-architecture-patterns)
- [Anti-Patterns](#anti-patterns)
- [Cross-References](#cross-references)

---

## When to Use This Skill

Read this skill before building or reviewing:
- Any UI flow with more than one user-facing phase (paste → preview → import, input → submitting → result)
- Any loading state: page load, button action, batch operation
- Any form that submits data and needs a result state
- Vault credential flows (reveal, edit, batch import, delete)
- Any destructive action (delete, revoke, purge)
- Any modal, dialog, toast, or in-context error
- Settings or configuration page information architecture decisions

---

## 1. State Machine Contracts

**Rule**: Every multi-step UI flow must define its states as an explicit enum before implementation begins. States must be mutually exclusive — no state is a superset of another. Each transition must specify what enters, what exits, and what transforms in place.

### Why This Matters

Without an explicit state machine, flows accumulate conditional visibility logic (`if (loading && !error && results.length > 0)`). This produces invisible states, untestable branches, and UX behavior no one designed. The state machine is the design specification.

### Vault Import — Canonical State Machine

```
idle      → paste     (user clicks "Import Credentials")
paste     → importing  (user clicks "Import N credentials")
importing → complete   (all items processed)
complete  → idle       (auto after 5s, or user dismisses)
```

**`idle`**: Action buttons visible. Credential list displayed below. No form, no progress.

**`paste`**: Paste textarea visible. Reactive preview panel renders below textarea in real time — splits valid/invalid lines as user types. No separate "Preview" button. The transition from idle → paste slides the textarea in from the top with a 150ms ease-out.

**`importing`**: Textarea and preview panel collapse (150ms fade + height collapse). Per-item progress bar visible with explicit count label: `"Importing 3 of 12..."`. No cancel affordance — the operation is atomic. List below is read-only, grayed.

**`complete`**: Progress bar replaced by a summary banner: `"12 imported, 0 failed"`. Banner auto-dismisses after 5s. Credential list below has already refreshed to reflect new entries (refresh triggered when last item completes, not when banner dismisses). After auto-dismiss or manual dismiss, state returns to idle.

### General State Machine Template

For any multi-step flow, specify before writing a single component:

```
States: [state-a, state-b, state-c, ...]
Triggers: [event → state transition]

state-a:
  visible: [element list]
  hidden: [element list]
  disabled: [element list]

state-b:
  enters: [what + animation]
  exits: [what + animation]
  transforms: [element + property change]
```

A state definition that says "show everything except the loading bar" is not a state — it is absence of discipline. Be explicit about every visible region.

---

## 2. Loading Feedback Hierarchy

Three tiers. Each has a specific scope. Mixing them produces incoherent feedback.

### Tier 1 — Skeleton Screens

**Scope**: Initial page load where content structure is known.

**When**: The page renders for the first time and is fetching the data that will fill it. The user has never seen this content.

**Rule**: Skeleton shape must match the actual content layout — same number of rows, same approximate proportions. A skeleton that bears no resemblance to the loaded content causes a layout jump that feels like a bug.

**Example**: The Credentials page skeleton shows 4 credential rows (shimmer animation, ~40px height each) with icon placeholders at left and action button placeholders at right — matching the actual `CredentialRow` layout exactly.

**Never use for**: Actions triggered by the user after page load. Use inline spinners for those.

### Tier 2 — Inline Spinners

**Scope**: Single-action feedback. One button, one operation.

**When**: User triggers a discrete action (save, connect, test, delete one item). The feedback scope is the trigger element.

**Rule**: The button that triggered the action becomes the loading state immediately — replace label with spinner, disable pointer events, maintain button dimensions. Do not show a global page spinner for a localized action.

**Timing rule**: Do not show a spinner for anything that resolves in under 100ms. A spinner that flashes for 80ms is more disruptive than no spinner. Use a 100ms debounce before revealing.

**Example**:
```
[Save Credential] → clicked → [⟳] (button dims to 70% opacity, spinner replaces label)
                             → success → [✓ Saved] (800ms) → [Save Credential]
                             → error   → [Save Credential] + inline error below field
```

### Tier 3 — Progress Bars with Count

**Scope**: Batch operations where N is known before the operation starts.

**When**: Importing N credentials, deleting N items, syncing N files. The user submitted a known quantity.

**Rule**: Always show `current / total` — not percentage only, not spinner only. `"Importing 3 of 12"` tells the user the operation is alive and how much remains. A bare percentage (`25%`) provides less information and is harder to reason about.

**Rule**: The progress bar replaces the action form — it does not appear alongside it. The form's submit action is the last thing the user does before the form collapses and progress takes over.

**Never use for**: Actions where N is unknown before the operation begins. Use an inline spinner with status text instead: `"Connecting..."`.

### The 300ms Rule

No user action may leave the user with zero feedback for more than 300ms. If an action takes longer than 300ms to even begin processing, the trigger must respond immediately (spinner, disabled state, status text). The user's perception of responsiveness is set by the gap between their action and any feedback — not by how long the operation actually takes.

---

## 3. Form Lifecycle Contracts

Every form that submits data passes through four distinct phases. The phases must be visually distinct — the user should always know which phase they are in without reading text carefully.

### Phase 1 — Input

User is composing. All fields are editable. Primary action button is enabled only when minimum validity requirements are met (Zod validation passes on required fields). No results are visible.

### Phase 2 — Preview (Reactive)

For flows where the output of the form is non-trivial (credential import, search query, bulk operation), show a reactive preview that derives from the current input without a user action.

**Rule**: Preview is a read-only derivation, not a second step. It appears automatically as input changes. It is not an intermediate "Preview" button click. The preview collapses if input is cleared.

**Example**: Paste textarea for credential import — as lines are pasted, the preview panel below the textarea immediately shows: `"12 valid, 3 invalid (line 4, 8, 11 — missing service name)"`. The user sees what will be imported before clicking Import.

### Phase 3 — Submitting

The primary action button is clicked. The form becomes read-only or collapses entirely. The primary feedback mechanism (spinner, progress bar) takes over.

**Rule**: The form field values must remain visible during submission if the operation can fail and the user may need to correct their input. If the operation is atomic and cannot be partially undone, collapsing the form is acceptable.

**Rule**: If the form collapses, it must collapse with a visual transition (150ms height animation) — not disappear instantly. Instant disappearance breaks the user's spatial model.

### Phase 4 — Resolution

**Success**: The form clears entirely. A transient success state appears (see Notifications). The results of the operation are the new state of the page — a refreshed list, an updated status indicator. The form does not reappear automatically.

**Error**: The form returns to Phase 1 (Input) with an inline error message under the relevant field or at the top of the form for non-field errors. The user's input is preserved. The form does not reset on error.

### The Append Anti-Pattern

**Never append a results section below the form that submitted it.**

```
❌ Wrong:
[Form: paste textarea]
[Import button] ← clicked
[Form: paste textarea] ← still visible
[Results: 12 imported ✓] ← appended below
```

```
✓ Correct:
[importing state: progress bar, no form]
→ complete state: [summary banner, refreshed list]
```

On success, the form transitions away. The results ARE the new page state — they do not coexist with the form that produced them.

---

## 4. Credential Management UX

Pattern consensus from 1Password, AWS Console IAM, macOS Keychain, HashiCorp Vault UI.

### Reveal

- Credential is masked by default: `••••••••••••`
- Explicit "Reveal" button (eye icon + label) adjacent to the masked field.
- On click: secret becomes visible. Timer starts (30 seconds). Button label changes to "Hide".
- Auto-hides on: timer expiry, window blur, navigation away from the page.
- Clipboard copy available during the reveal window. Copy icon appears alongside the revealed value.
- After auto-hide, the "Reveal" button is restored. Timer is not shown to the user (it is a security backstop, not a UX feature).

### Edit

- Inline form appears below the credential row on "Edit" click. Not a modal.
- **Service name is read-only** — it is the key. Display it as a non-editable label at the top of the inline form to confirm which credential is being edited.
- Editable fields: Secret, Description.
- "Save" commits changes and collapses the inline form.
- "Cancel" discards changes and collapses the inline form.
- The inline form does not affect the layout of other credential rows — it expands within the row's space via a height animation.

### Batch Import

Follows the canonical state machine from Section 1:

1. **paste** — Paste textarea with reactive preview (valid/invalid split shown in real time).
2. **Single action**: `"Import 12 credentials"` button — count shown on button from preview.
3. **importing** — Textarea and preview collapse. Per-item progress: `"Importing 3 of 12..."`.
4. **complete** — Summary banner: `"12 imported, 0 failed"`. Auto-dismisses after 5s. List refreshed.

The paste textarea is never visible during or after import. It is a staging area, not a persistent UI element.

### Delete (Single Credential)

- Tier 2 confirmation (see Section 5).
- Confirm dialog: `"Remove [service-name]?"` — service name is shown so the user knows exactly what will be deleted.
- Action button label: `"Remove Credential"` — not "Yes", not "OK", not "Confirm".
- Cancel is the safe default: first tab stop, focused on dialog open.

---

## 5. Destructive Action Graduation

Three tiers, calibrated to consequence severity. The friction must match the reversibility.

### Tier 1 — Reversible (No Confirmation)

**Consequence**: Action can be undone within a short window.

**Pattern**: Execute immediately. Show an undo toast for 3–5 seconds: `"Credential removed. Undo"`. Undo toast click reverses the operation. After 5s, toast dismisses and the action is committed.

**When to use**: Moving items, archiving (when archive is recoverable), dismissing notifications.

**Never use for**: Permanent deletions. "Reversible" means the system has an undo path, not just that the user will probably be okay.

### Tier 2 — Not Easily Reversible (Confirm Dialog)

**Consequence**: Action cannot be undone by the user without support intervention, but is not catastrophic.

**Pattern**: Confirm dialog with:
- Clear description of what will be deleted/revoked: `"Remove credential for [service-name]?"`
- **Action button label is the action verb**: `"Remove Credential"`, `"Revoke Sync"`, `"Disconnect Workspace"` — never "Yes", "OK", or "Confirm"
- **Cancel is the safe default**: focused on dialog open, first tab stop
- No delay on confirm button

**When to use**: Vault credentials, cloud sync revocation, workspace disconnection, API key deletion.

### Tier 3 — Permanent, High-Stakes (Typed Confirmation)

**Consequence**: Data cannot be recovered. The operation affects the user's account, workspace, or irreversible external state.

**Pattern**: Typed confirmation + delayed confirm button:
- Instruction: `"Type [service-name] to confirm"` or `"Type DELETE to confirm"`
- Confirm button is disabled until typed text matches exactly (case-sensitive).
- Once enabled, a 1–2 second delay before the button accepts a click (prevents rage-clicking through the confirmation).
- Cancel remains the safe default throughout.

**When to use**: Account deletion, workspace data purge, irreversible migrations, billing cancellation.

**For this app specifically**:
- Vault credential delete → Tier 2
- Cloud sync revocation → Tier 2
- Account or workspace deletion → Tier 3

---

## 6. Transition Contracts

Before implementing any state change, answer three questions:

1. **What enters the DOM?** — with what animation (fade, slide-down, expand-height)
2. **What exits the DOM?** — with what animation (fade-out, slide-up, collapse-height)
3. **What transforms in place?** — with what property change (opacity, color, label text)

### Duration Rules

| Context | Max Duration | Rationale |
|---|---|---|
| Operational UI (data actions, loading states) | 200ms | Feedback must feel immediate, not decorative |
| Navigation transitions | 250ms | Spatial movement needs a beat to register |
| Decorative / onboarding | 400ms | User is watching, not waiting |
| Progress bar fill | proportional to actual progress | Must reflect real state |

**Never exceed 200ms for anything the user is waiting on.** A 400ms collapse animation on a form that just submitted makes the interface feel slow.

### The Mid-Read Rule

Never remove content the user is currently reading. If a state transition would cause visible text to disappear while it is the primary focus (a summary, a result label, an error message), use a fade-out delay of at least 300ms or a slide-away animation so the content leaves gracefully.

**Counter-example (wrong)**: The summary banner disappears instantly when the user clicks dismiss. The user's eye was on the banner text.

**Correct**: The banner fades out over 200ms after a click on dismiss, or after the 5s auto-dismiss timer fires.

### Immediate Trigger Response

**Rule**: Loading states must immediately replace the trigger — no delay before feedback starts.

When a button is clicked, the button itself becomes the loading indicator in the same frame. Do not show the original button while waiting for a network response to arrive before showing the spinner. The feedback begins before the response, not after.

### Vault Import Transition Spec

```
idle → paste:
  enters: [paste-textarea (slide-down, 150ms), preview-panel (fade-in after 50ms delay)]
  exits:  [action-buttons (fade-out, 100ms)]
  transforms: [section-height (expand, 150ms ease-out)]

paste → importing:
  enters: [progress-bar (fade-in, 100ms)]
  exits:  [paste-textarea (collapse-height, 150ms), preview-panel (fade-out, 100ms)]
  transforms: [import-button → spinner label (same frame)]

importing → complete:
  enters: [summary-banner (fade-in, 150ms)]
  exits:  [progress-bar (fade-out, 100ms)]
  transforms: [credential-list refreshes in place (no animation on individual rows)]

complete → idle (auto or dismiss):
  exits:  [summary-banner (fade-out, 200ms)]
  transforms: [section-height (collapse, 150ms)]
```

---

## 7. Notifications and Toasts

### By Severity

| Type | Auto-dismiss | Duration | Action required |
|---|---|---|---|
| Success | Yes | 3–5s | None |
| Info | Yes | 4–6s | None |
| Warning | Yes | 5–8s | Optional dismiss |
| Error | **No** | Until dismissed | Explicit user dismiss |

**Error toasts do not auto-dismiss.** Errors require attention. An error that disappears before the user notices it has happened communicates nothing. When an error is tied to a specific form field or page section, prefer an **in-context error** over a toast entirely.

### In-Context Errors (Preferred)

When an error is localized to a specific element, show the error inline under that element — not as a toast. In-context errors are more scannable and do not compete for attention with unrelated page content.

```
[Secret field]
[•••••••]
↳ "Secret cannot be empty"   ← inline, under the field, in error color
```

In-context errors clear when the user edits the relevant field. They do not require an explicit dismiss action.

### Toast Stacking

Maximum 3 toasts visible simultaneously. Queue additional toasts; each queued toast displays when a preceding toast dismisses. Show newest toast at the top of the stack (or bottom — pick one and never switch).

### Toast Content Rules

- Success: what happened. `"12 credentials imported"` — not `"Success!"`.
- Warning: what needs attention and why. `"Sync paused — vault key mismatch"`.
- Error: what failed and what to do. `"Import failed — check your network connection"`. Never just `"Error"`.
- Undo actions in toasts must be a clearly labeled text link or button: `"Undo"` — not an icon.

---

## 8. Information Architecture Patterns

Applies to settings-class pages and top-level navigation structure.

### Goal-Based Navigation (Not Module-Based)

**Top-level nav items represent distinct user goals** — things users set out to do. They do not represent implementation modules or backend services.

| Wrong (module-based) | Correct (goal-based) |
|---|---|
| Database | Storage |
| Auth | Security |
| Config | Settings |
| Vectors | — (implementation detail, not a goal) |

A user navigating to "Vectors" does not know why they are there. A user navigating to "Storage" has a clear reason: they want to understand or change where data lives.

### Co-Located Configuration

**Related configuration concerns belong on the same page.**

If "where data is stored" and "how that data is secured" are related concerns for the user, they belong in the same page — likely under "Storage" — not split across "Storage" and "Security". Navigation friction between related settings creates cognitive overhead and is a common cause of misconfiguration.

Diagnostic: if the user needs to visit more than one nav page to complete a single configuration task, those pages are over-split.

### Settings vs Status

**Settings**: Configuration the user visits deliberately to change something. Authentication tokens, sync endpoints, display preferences.

**Status/Operational health**: What the system is doing right now. Sync progress, embedding pipeline health, connection state. This belongs on a "Storage" or "Dashboard" page — not buried inside Settings.

A user who opens Settings to find a real-time health indicator is in the wrong place. They came to configure, not to monitor.

### Nav Status Indicators

Colored dots, badges, or status icons in nav items should reflect the health of **that page's primary concern**:
- "Storage" nav item dot → reflects sync/storage health
- "Security" nav item dot → reflects vault unlock state or key validity
- "Settings" nav item dot → should almost never have a status indicator (Settings is configuration, not health)

Status indicators in nav are a contract: clicking the item with the indicator takes the user to where they can act on the problem the indicator surfaced.

---

## Anti-Patterns

These are the specific behaviors this skill exists to prevent:

| Anti-Pattern | Why It Fails | Correct Alternative |
|---|---|---|
| Appending results below the submitting form | Form and results coexist — user can't tell if they're in input or result state | Transition away from form on success; results replace it |
| "Yes / OK / Confirm" button labels on destructive dialogs | No specificity — user must read the dialog body to understand the action | Button label IS the action: "Remove Credential", "Revoke Sync" |
| Typed confirmation for Tier 2 actions (credentials) | Over-friction for the consequence level; users route around it | Typed confirmation reserved for Tier 3 (account/workspace deletion) |
| Spinner that appears for <100ms | Attention-grabbing flash with no signal value | 100ms debounce before revealing any loading indicator |
| No feedback for >300ms | User assumes the action failed or the UI is broken | Trigger must respond immediately (spinner, disabled state) |
| Percentage-only progress bar for batch operations | "25%" tells you nothing about what's happening | Always show current/total: "Importing 3 of 12" |
| Skeleton screen that doesn't match content shape | Layout jump on load; looks like a bug | Skeleton must mirror actual content layout |
| Reveal-once credential display (no timer) | Revealed secret stays visible indefinitely | 30s auto-hide + blur/navigation trigger |
| Error toast that auto-dismisses | User misses the error; retries without understanding why | Error toasts never auto-dismiss |
| Generic error messages in toasts | "Error" tells the user nothing actionable | State what failed and what to do about it |
| Module-based top-level navigation | Users navigate by goal, not by system architecture | Goal-based nav items; co-locate related configuration |
| Status health indicators inside Settings nav | Settings is for configuration, not monitoring | Health indicators belong on Storage/Dashboard pages |
| State definitions that are supersets of other states | Invisible intermediate states; untestable transitions | States are mutually exclusive; each defines its full visible set |
| Instant disappearance of content mid-read | Disorienting; user loses spatial context | Fade-out (≥200ms) or slide-away before removal |

---

## Cross-References

- [ui-architecture](../ui-architecture/SKILL.md) — spatial layout, overlay decisions, push vs overlay panels, z-index layering. The spatial complement to this skill's temporal focus.
- [svelte-ui](../svelte-ui/SKILL.md) — Svelte 5 implementation of the patterns defined here: reactive state, form components, loading states.
- [accessibility](../accessibility/SKILL.md) — keyboard navigation for multi-step flows, focus management on state transitions, ARIA live regions for progress feedback.
- [error-architecture](../error-architecture/SKILL.md) — error modeling and propagation contracts that feed the error display patterns in Section 7.

</ANCHORSKILL-INTERACTION-DESIGN>
