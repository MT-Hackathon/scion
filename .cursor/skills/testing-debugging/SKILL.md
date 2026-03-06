---
name: testing-debugging
description: "Governs cross-layer testing and debugging doctrine: diagnostic order, two-attempt rule, specification-driven testing, coverage-first diagnosis, and anti-gaming mandates. Use when applying systematic diagnosis methodology, choosing testing strategy, or establishing debugging discipline. DO NOT use for language-specific debugging patterns (see each language skill's Debugging Profile) or Angular-specific test patterns (see angular-testing)."
---

<ANCHORSKILL-TESTING-DEBUGGING>
# Testing & Debugging
## 1. Core Mandates
- **Two-Attempt Rule**: If a bug survives 2 fix attempts, STOP. Observe with Visual QA or DevTools before the 3rd attempt.
- **Specification-Driven Testing**: Write tests and implementation together per acceptance criterion. Tests encode business rules; implementation satisfies them.
- **Test Before Fix**: Verify coverage before fixing regressions. Write the test first to document the contract and prevent re-regression.
- **Coverage Baseline**: Target >=1 unit test per public function and >=90% coverage for core modules.
- **Coverage-First Diagnosis**: Coverage is a diagnostic tool, not just a metric. Use scoped tests to identify likely regression paths in high-churn, low-coverage modules.
- **Parameterized Testing for Combinatorial Logic**: For combinatorial logic (rules, permissions), use parameterized tests with boundary values and type mismatches.
- **Dead Code Triage**: Identify and remove dead code before writing tests. Reducing the denominator is more valuable than testing what should be deleted.
- **Coverage Ratchet**: Thresholds only move up. Structure work to maintain a green build at every step rather than relaxing constraints for partial signal.
- **Coverage Resistance as Design Signal**: Elevated to 001-foundational as a core discipline. When branch coverage is hard to achieve, decompose the code — the architecture has too many responsibilities, not too few tests.
- **Territory Principle**: Establish fact from authoritative runtime evidence before assuming cause in code.
- **UI Verification Mandate**: UI fixes require BEFORE vs AFTER screenshot evidence with explicit state differences.
- **Backend Debug Flow**: Bug -> logging/observability -> focused unit test -> stack trace -> code fix -> re-test.
- **UI Debug Flow**: Bug -> navigate -> snapshot -> console/network -> interact -> read code -> fix -> verify state diff -> re-test.
## 2. Diagnostic Order
When tests fail, use this sequence:
1. **Test validity**: confirm assertions/expectations are correct.
2. **Environment sanity**: toolchain/version/activation (`nvm`, `uv`, `gradle`, conda).
3. **Configuration**: env vars, keys, and runtime config.
4. **Test infrastructure**: runner/tooling health.
5. **Implementation bug**: investigate code path and fix.
## 3. Silent Failure Prevention
- **Mandate**: Every early return, redirect, or error-catch MUST log a reason with context.
- **Catching Guidelines**: Infrastructure failures are VALID (log and return safe defaults); guard clause throws are VALID (fail fast); business exceptions used to branch behavior are INVALID (use result types/data records).
- **Logger**: Use the language-appropriate logger (e.g., Angular's `LoggerService`, Spring's `CorrelationFilter` MDC).
## 4. Language Debugging Profiles
Language-specific debugging patterns, tool commands, and common defect taxonomies live in each language's skill:
- Angular: [angular-testing](../angular-testing/SKILL.md)
- Java/Spring: [java-spring-boot](../java-spring-boot/SKILL.md)
- Python/FastAPI: (pending dedicated skill)
- SvelteKit: [svelte-ui](../svelte-ui/SKILL.md)
- Rust: [rust-development](../rust-development/SKILL.md)
Each language skill includes a Debugging Profile with:
- Error interpretation specific to that language/framework
- Pre-third-attempt verification commands
- Common defect patterns
- Test runner and coverage workflow

## 5. Anti-Gaming Mandate
- **Prohibited**: Reading existing tests to reverse-engineer implementation.
- **Specification-Driven Delivery**: Follow the mandate in Section 1. Write tests and code together per acceptance criterion to maintain build signal and prevent abstraction churn.
- **Prohibited**: try/except test masking, weakening assertions to match buggy behavior, and any "make tests pass" quality downgrade.
- **Code review reject**: fixes submitted without diagnostic-order evidence or without UI verification artifacts for UI issues.
## 6. Resources
- [Checklist: Test Debugging](resources/checklist-test-debugging.md)
- [Examples: Test Patterns (general)](resources/examples-test-patterns.md)
- [Examples: Python Test Patterns](resources/examples-test-patterns-python.md) - migration target: dedicated Python skill
- [Examples: Angular Test Patterns](resources/examples-test-patterns-angular.md) - migration target: `angular-testing`
- [Cross-References](resources/cross-references.md)
- [Reference: Telemetry & Tracing](resources/reference-telemetry.md) - likely home: `error-architecture`
</ANCHORSKILL-TESTING-DEBUGGING>
