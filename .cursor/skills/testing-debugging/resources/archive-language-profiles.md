# Archived Language Debugging Profiles

These sections were removed from SKILL.md during the doctrine kernel refactor.
Each section should be absorbed into its respective language skill as a "Debugging Profile" section.
Content below is preserved verbatim for migration.

## 4. Angular Debugging
- **Lazy Routes**: Check grandparent `paramMap` for IDs (`parent.parent`).
- **RxJS merge()**: Filter for valid data before taking the first emission.
- **Inputs**: Use `fixture.componentRef.setInput()` for signal-based `input()`.

## 4.5 Java/Backend Debugging

- **Before fix #3**: Run `./gradlew checkstyleMain spotbugsMain` to verify your mental model against static analysis.
- **Clean verification**: `./gradlew clean test --no-daemon` (stale daemon/classpath issues cause phantom failures).
- **Common Java defect patterns**: NPE via `.equals()` on null receiver, broad `catch(Exception)`, missing `@Valid`, `Integer.valueOf()` autoboxing, enum `.equals()` instead of `==`.
- **ArchUnit as diagnostic**: Run `./gradlew test --tests '*ArchitectureTest*'` to check structural constraints.

## 4.6 Python/SvelteKit Debugging

- **Before fix #3**: Run `ruff check` and `mypy` to verify your mental model against static analysis.
- **Clean verification**: `pytest --tb=short` with fresh conda env activation (`conda activate Universal-API`).
- **Common Python defect patterns**: mutable default arguments (`def f(x=[])`), f-string debug leftovers, unclosed file handles (use context managers), missing `await` on async calls.

## 4.7 SvelteKit Component Testing

- **Two-project Vitest config**: Component tests (`*.svelte.test.ts`) run in browser mode (real Chromium via Playwright). API/logic tests (`*.test.ts`) run in node mode. Both contribute to a single coverage report.
- **Coverage aggregation is single-job**: vitest multi-project config aggregates coverage across all projects in one run. Splitting into separate CI jobs breaks this — requires coverage merging tooling (e.g., `c8 merge`) to recover a unified threshold. Keep as a single CI job until scale explicitly forces the complexity trade-off.
- **vitest-browser-svelte**: Replaces `@testing-library/svelte` for component tests. `render()` returns the screen object; use locators with `await expect.element(locator).toBeVisible()`.
- **No browser API mocks**: In browser mode, `matchMedia`, `crypto.randomUUID`, `localStorage`, `ResizeObserver` are all real. Never mock them in `*.svelte.test.ts` files.
- **Portal components**: bits-ui Dialog/Select/Tooltip render content via Portal to `document.body`. Browser mode exercises these rendering paths — jsdom cannot. This is the primary reason for browser mode.
- **Test wrappers**: Svelte 5 snippet props require wrapper components (`*TestWrapper.svelte`) even in browser mode. The wrapper bridges the gap between TypeScript test code and Svelte snippet syntax.
- **Anti-pattern**: `expect(container).toBeTruthy()` smoke tests. Every test must assert behavior, not just existence. If a component has conditional rendering (`{#if}`), test both sides.
- **The testing pyramid**: Unit (node, fast) → Component (browser, medium) → Visual QA (MCP browser, manual). Each layer catches different classes of bugs.
- **Journey-driven Visual QA**: The Visual QA layer uses persistent `journey-*.md` interaction scripts rather than direct URL navigation. This catches broken navigation, orphaned routes, and flow gaps invisible to component tests. See [Visual QA Agent](../../agents/visual-qa.md) for the execution protocol and [Journey-to-QA Template](../business-analyst/resources/template-journey-qa.md) for the format.
