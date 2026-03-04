# review

Perform a code review against the changes on the current branch.

**Default scope**: `git diff main..HEAD` — all committed-but-unmerged changes on the current branch against main. If already on main, use `git diff HEAD~1`. Override by naming scope in the invocation: a commit hash, branch name, file path, or natural language description.

**Scope detection**: Inspect the diff for file types — `.py` triggers backend review; `.svelte`/`.ts`/`.js` triggers frontend; both triggers full-stack. User-named scope in the invocation takes precedence.

**Protocol**: Run static analysis first (`ruff check src/` for backend, `npm run lint` for frontend) before reading code. Delegate execution to QA with fix authority — minor violations corrected in-place; architectural concerns escalated before fixing. If a plan is attached, review against that plan's acceptance criteria as well. Review is complete only when the system demonstrates its primary function end-to-end — a passing suite with a broken system is false green.

---

## Constitutional Checklist

### NASA Power of 10
- **#1 Single control flow**: No recursion; guard clauses before logic; max 3 nesting levels; one success path per function; zero `else` in logic functions
- **#2 Bounded iteration**: No unbounded loops or reactive chains; all async has timeout or cancellation
- **#3 Predictable resource lifecycle**: All subscriptions torn down; no leaked listeners; no orphaned timers
- **#4 Short functions**: ~60 LOC max; a section comment signals extraction needed; investigate at 40
- **#5 Input/output contracts**: Guard clauses validate all inputs; return contract validated before returning
- **#6 Smallest scope**: Declare at first use; `const`/`final` preferred; no `var`; no function-scope when block-scope suffices
- **#7 Check all returns**: Every external return (HTTP, DB, I/O) null/error-checked before chaining
- **#8 No magic metaprogramming**: No `eval`, no `Function()` constructor, no dynamic property access on typed objects
- **#9 Limit indirection**: Max one wrapper layer; tracing a call through 3+ files to find the logic is a refactor signal
- **#10 Compile clean**: Zero warnings; build and lint pass with no suppressions

### Tiger-Style
- Guard clauses handle all invalid/edge cases before any logic
- Linear flow: the success path reads top-to-bottom with no branching
- `else` on a guard clause is a smell — single success path per function

### Defense in Depth
- Every data path has: authoritative source → derived fallback → safe default
- Security gates fail closed (500, not silent null); data write paths reject with error; display paths degrade to typed empty state
- The tertiary fallback matches the criticality of the path it protects

### Contracts Over Wiring
- Every function signature, component prop, API request/response, and data model is a typed contract
- No `Any`/untyped bags at any boundary
- No exceptions used as control flow — they exit the return contract
- No implicit dependencies absent from the signature
- No inverted ownership (client carrying server identity; server carrying UI configuration)
- If mocking >2 dependencies in a test, hidden contracts exist — surface them

### No Silent Failures
- Every early return, redirect, and error-catch logs reason with context
- Infrastructure failures: catch, log, return safe default
- Guard clause violations: throw and fail fast — no silent swallowing
- Business exceptions: result types/data records, not exception branches

### Every Build Is An Inspection
- All errors and warnings found — including pre-existing — addressed or explicitly dispositioned
- "Not caused by us" is not a valid disposition
- No orphaned scripts: any new script lives inside a skill or rule folder

### Testing Mandates
- ≥1 unit test per public function
- Tests encode business rules and acceptance criteria, not framework wiring
- ≥90% coverage for core modules
- No `pass`/`skip`/try-except masking in test code
- No assertions weakened to match buggy behavior
- Parameterized tests for combinatorial logic (permissions, rules, boundary values)

---

### Backend (Python)
- `ruff check src/` zero errors
- No bare `except:`; all caught exceptions logged once with context and stack trace; no stack traces in HTTP responses
- HTTP errors use RFC 7807 shape (`status`, `error.code`, `error.message`)
- API boundaries typed with Pydantic; no `Any` at contract edges; request/response models are source of truth
- Pytest runs clean; error envelope structure, codes, and propagation tested

### Frontend (SvelteKit / Svelte 5)
- No `export let`, `$:`, or `onMount` redirects — Svelte 4 patterns are a hard reject
- No inline hex or per-component colors; all values from `var(--token)` or Tailwind utilities
- Loading / empty / populated states — exactly one rendered at a time; no stale content beneath loading state
- No function calls in template expressions; `$derived()` for computed display values; `$derived.by()` for complex derivations
- All props and events fully typed; no implicit `any`; TypeScript strict mode
- Every dynamic `{#each}` block uses a stable key (`item.id`), never array index

### Frontend Security
- No credentials in `localStorage` or `sessionStorage`
- No credentials in URL parameters, error messages, or unmasked console logs
- No `innerHTML` with dynamic content
- Payload validation with Zod before sending; schema errors handled gracefully

### Accessibility (Section 508 / WCAG 2.2 AA)
- All interactive elements keyboard accessible (Tab, Enter, Space, Arrow)
- Text contrast 4.5:1 minimum; UI components 3:1 against adjacent colors
- Semantic HTML: `<button>`, `<nav>`, `<main>`; headings in logical order (no skipping)
- ARIA labels where semantic HTML is insufficient; `aria-live` for async content
- Focus visible and trapped within modal dialogs
