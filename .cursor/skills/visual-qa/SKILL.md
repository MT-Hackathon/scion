---
name: visual-qa
description: "Governs visual QA methodology for UI audits: inspection protocol, journey-driven auditing, output templates, and interpretive reasoning for application health vs component health. Use when conducting visual regression audits, viewport verification, or browser-based QA of any frontend/UI change. DO NOT use for accessibility compliance mandates (see accessibility) or error handling architecture (see error-architecture)."
---

<ANCHORSKILL-VISUAL-QA>

# Visual QA Skill

Methodology, interpretive reasoning, and output contracts for visual UI auditing. The agent body teaches disposition; this skill teaches technique.

## Table of Contents

- [Application Health vs Component Health](#application-health-vs-component-health)
- [Claim Decomposition](#claim-decomposition)
- [The Contradiction Pattern](#the-contradiction-pattern)
- [Error State Taxonomy](#error-state-taxonomy)
- [Confirmation Bias Guards](#confirmation-bias-guards)
- [Inspection Protocol](#inspection-protocol)
- [Journey Methodology](#journey-methodology)
- [Output Templates](#output-templates)
- [Failure Mode Catalog](#failure-mode-catalog)
- [Cross-References](#cross-references)

## Application Health vs Component Health

Every visual observation must be evaluated at two levels simultaneously:

- **Component level**: Does the UI element render and behave correctly?
- **Application level**: What does the *presence* of this element tell us about system state?

An error banner that renders perfectly is a component-level **PASS** and an application-level **FINDING**. These are not in conflict — they are different conclusions at different scopes.

Never flatten both levels into a single verdict. Record them separately in the audit output.

## Claim Decomposition

Replace "does this look right?" with atomic sub-claims. After every screenshot, explicitly answer each question:

1. **What is the page's semantic state?** (healthy / degraded / error / empty / loading)
2. **Are there any error indicators visible?** (banners, toasts, red text, warning icons, empty states that shouldn't be)
3. **Do console and network observations confirm or contradict the visual state?**
4. **Is this the state a user would expect after the preceding action?**
5. **Does the page content match the navigation label that brought us here?**

These questions are not optional — they are the minimum evidence set for any assessment claim.

## The Contradiction Pattern

Cross-reference visual state against runtime signals. Contradictions are always findings, regardless of whether each individual signal looks "correct":

| Visual | Runtime | Classification |
|--------|---------|----------------|
| Success toast | Console error | Silent health failure |
| Error banner | All-200 network responses | Frontend-only failure |
| Populated view | Loading spinner | Stale content being replaced |
| Loading spinner | No network activity | Dead request or state management failure |
| Populated view | Stale/default placeholder data | Binding failure |

When a contradiction is found: document both signals, classify using the taxonomy below, and mark as a finding.

## Error State Taxonomy

Shared vocabulary for classifying observations. Use these terms in findings:

- **Silent failure** — No error shown, functionality is broken. Worst category; users cannot self-diagnose.
- **Visible error** — Banner, toast, or inline message present. The "working as designed" trap: the component works, the application does not.
- **State contradiction** — Visual state conflicts with console or network evidence.
- **Degraded state** — Partial data, missing sections, stale content.
- **Orphaned state** — Page is reachable by direct URL but has no navigable path from the UI.

## Confirmation Bias Guards

The language model prior pulls toward "it looks fine." Name and defeat each trap explicitly:

- "The error banner renders correctly" ≠ "the page is healthy." The banner's presence **is** the finding.
- "I don't see a visual regression" ≠ "there are no problems." Check console and network before concluding.
- "The component works as designed" ≠ "the application is in a good state."
- "Green/success styling" does not guarantee the content is actually successful — read the text.
- After applying a fix: re-observe from scratch. Do not look for the fix to have worked; look for what is wrong **now**.

## Inspection Protocol

**The Skeptic's Workflow** — seven rules governing every viewport assessment:

**Workflow**: Navigate → Resize to width → Screenshot → Assess → Repeat for all 3 viewports.

1. **Screenshot BEFORE assessing** — You are blind until you capture reality. Never comment on a UI state you haven't captured in the current turn.
2. **Describe what you SEE, not what you expect** — Break the "confirmation loop." List the colors, pixels, and positions you actually observe.
3. **The Viewport Trinity** — Every audit must cover three widths: **375px** (Mobile), **768px** (Tablet), **1200px** (Desktop).
4. **"Looks fine" is the Enemy** — If you can't find a bug, you aren't looking hard enough. Investigate hover, active, and focus states.
5. **Slow Resizing** — Move between breakpoints slowly to catch transition glitches or "jumpy" layout shifts.
6. **Console First** — After every page load or navigation, call `browser_console_messages` and check for `error`-level messages from application code (ignore browser internals and Vite HMR messages). Any application `console.error` is a finding.
7. **Network Sanity** — After any page that makes API calls, call `browser_network_requests` and verify expected endpoints returned 2xx. Flag failed requests as findings.

## Journey Methodology

### The URL-Teleportation Anti-Pattern

Navigating directly to a URL bypasses the actual paths a real user follows. This misses broken navigation, orphaned routes, missing links, and state-dependent bugs — the failures that matter most to users and are invisible to code review.

**The Mandate**: Every complete feature audit begins from a journey file. Journey files encode the interaction path a real user takes. You are a user who does not know the URL.

### Discovery Protocol

When briefed with a feature scope or changed routes:
1. Receive specific `journey-*.md` file paths from the orchestrator, OR glob `resources/journeys/journey-*.md` in the project's governing skill folder
2. Execute every journey that touches the changed routes
3. Respect sprint markers: `[CURRENT]` = execute fully; `[THIS SPRINT]` = observe and screenshot what exists, flag gaps as findings without failing
4. Use `browser_navigate` ONLY for the journey's entry point (the precondition URL) — never for internal navigation between steps

### Journey Execution Rules

- **Every page transition happens through a visible UI element** — a button, link, sidebar item, breadcrumb. If you cannot find the navigation element, that is a finding, not a workaround.
- **Every element is referenced by its visible label or text** — never by CSS class, DOM ref, or developer-visible ID.
- **Error variations are mandatory** — every journey file has an Error Variations section; execute it even under time pressure.
- **Dark mode checkpoint**: After completing any journey, toggle dark mode and re-execute the first and last steps; screenshot both.
- **These rules supersede the default workflow** for feature audits. The standard viewport inspection workflow applies within each journey step, not as the top-level structure.

### Journey Output Format

Prepend the standard Visual Audit block with a journey trace:

| Step | Action Taken | Observed | Status |
|------|-------------|----------|--------|
| 1 | Clicked "Dashboard" in sidebar | Dashboard page loaded | PASS |
| E1 | Submitted form with empty fields | Inline validation messages | PASS |

Findings from journey execution feed into the standard "Issues Found" section.

## Output Templates

Every deliverable uses this structure:

```markdown
## Visual Audit: [Component Name]

### Expectation vs Reality
| Expected | Observed | Status |
|----------|----------|--------|
| [Requirement] | [What actually happened] | [PASS/FAIL] |

### Issues Found
**Critical:** [screenshot ref] Description of the break or violation.
**Medium:** Description of spacing errors or minor alignment shifts.
**Low:** Small visual polish items or subtle inconsistencies.

### Observations (not issues)
- Documented behavior that works as intended (e.g., "The sticky header remains pinned at 1200px").

### Skeptic's Questions
- "What happens if the text length doubles?"
- "Does the focus ring disappear on the second click?"
- "Is that 16px padding or actually 15px?"
```

## Failure Mode Catalog

What AI agents commonly miss during visual inspection:

- **Z-index collisions** — Element looks present but is behind an invisible overlay and cannot be clicked. Verify with `browser_is_enabled` and `browser_get_attribute`.
- **Semantic drift** — In multi-step audits, the agent "forgets" the goal of earlier steps and approves a screen that is visually correct but belongs to the wrong flow.
- **Intermittent states** — Success or error indicators that appear briefly and auto-dismiss. Toasts with short duration may be gone before the screenshot. If a journey step mentions a toast, verify its text immediately.
- **Shortcut learning** — Associating color with outcome ("green = good") without reading the actual content.
- **Viewport-specific failures** — An element that works at 1200px but clips or overflows at 375px. Desktop results do not transfer. Check all three.

## Cross-References

- [error-architecture](../error-architecture/SKILL.md) — canonical display severity rules (toast / inline / modal / indicator)
- [accessibility](../accessibility/SKILL.md) — contrast ratios, ARIA live regions, focus management
- [svelte-ui](../svelte-ui/SKILL.md) — loading/empty/populated state contract
- [testing-debugging](../testing-debugging/SKILL.md) — diagnostic order and two-attempt rule

</ANCHORSKILL-VISUAL-QA>
