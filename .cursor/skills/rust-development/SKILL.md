---
name: rust-development
description: "Governs Rust development patterns: ownership and borrowing, lifetime design, typed error architecture with thiserror/anyhow, cargo quality gates, testing strategy, crate selection, and parallel compilation protocol. Use when implementing or reviewing Rust code, diagnosing borrow-checker failures, designing Result contracts, or hardening Rust CI and handoff gates. DO NOT use for Tauri command/window/state patterns (see tauri-development) or general delegation workflow policy (see delegation)."
---

<ANCHORSKILL-RUST-DEVELOPMENT>

# Rust Development

Governs core Rust engineering standards across the graft-core library, graft-cli binary, and Tauri host crate. Every section encodes a contract, not a suggestion — the compiler enforces memory safety, but this skill governs the design decisions that prevent "compiler appeasement" fixes: clones that mask ownership errors, `unwrap()` chains that defer panics, and untyped errors that lose context at boundaries.

## Table of Contents

- [Scope Boundary](#scope-boundary)
- [Core Mandates](#core-mandates)
- [Ownership & Borrowing Contract](#ownership--borrowing-contract)
- [Error Architecture Contract](#error-architecture-contract)
- [Testing Strategy Contract](#testing-strategy-contract)
- [Quality Pipeline Contract](#quality-pipeline-contract)
- [QA Protocol for Rust](#qa-protocol-for-rust)
- [Parallel Agent Compilation Protocol](#parallel-agent-compilation-protocol)
- [Debugging Profile](#debugging-profile)
- [Resources](#resources)
- [Blueprints](#blueprints)
- [Cross-References](#cross-references)

## Scope Boundary

This skill covers core Rust: ownership, lifetimes, traits, error handling, testing, and quality gates valid in any Rust crate. Tauri-specific patterns (commands, window management, app state, IPC serialization) belong in `tauri-development` when that skill exists. Delegation mechanics and agent briefing format belong in `delegation`.

## Core Mandates

- **Borrow first**: design for references; escalate to ownership transfer only when the callee must outlive the caller's scope.
- **Typed errors at library boundaries**: `thiserror`-derived enums for all public crate errors; `anyhow` for application-layer aggregation.
- **Zero warning tolerance**: `cargo clippy -- -D warnings` must pass clean; warnings are design signals, not noise.
- **Compiler-first debugging**: read the compiler error, apply its `help:` suggestion, then reason — not the reverse.
- **Tests encode contracts**: unit tests document the invariant they protect; their names state the condition, not the implementation.
- **Panics for invariants only**: `unwrap()` and `expect()` are reserved for states that are provably unreachable from correct usage; all recoverable paths return `Result`.
- **Parallel builds need isolated targets**: multiple cargo invocations on the same `target/` directory corrupt incremental state; set `CARGO_TARGET_DIR` per agent.
- **Crate selection is policy**: add a dependency only when it clears the vetting criteria in `reference-crate-catalog.md`.

## Ownership & Borrowing Contract

- Prefer `&T` for read-only access, `&mut T` for in-place mutation, ownership for consumed or stored values — in that priority order.
- Accept `&str` over `&String`, `&[T]` over `&Vec<T>` at function boundaries to keep callers flexible.
- Clone only when the clone is semantically meaningful (independent copy) or when the alternative is a lifetime annotation that obscures intent.
- If three or more `.clone()` calls appear in a function body to satisfy the borrow checker, the ownership design is wrong — restructure before adding more.
- Lifetime annotations belong on types and functions only when inference fails; anonymous lifetimes (`'_`) satisfy most return-borrow cases.
- Interior mutability (`RefCell`, `Mutex`, `RwLock`) is an escalation path for shared ownership across call sites, not a default for mutable state.
- `Arc<Mutex<T>>` is the correct pattern for shared mutable state across threads; prefer message passing (`mpsc`) when ownership can transfer rather than share.
- Struct fields that outlive their constructors need owned types; fields used only within a method call scope accept references with explicit lifetime bounds.

## Error Architecture Contract

- Define a `thiserror`-derived enum per logical domain in library crates; do not create a single monolithic error type for the whole crate.
- Use `#[from]` for automatic `From` conversions from std and third-party error types; avoid manual `From` impls unless the conversion requires transformation.
- Application binaries (`main.rs`, CLI entry points) use `anyhow::Result` to aggregate library errors without re-exporting their types.
- Add `.context("what the operation was trying to do")` at every `?` propagation site that crosses a significant abstraction boundary.
- `expect("invariant: <reason>")` is the only acceptable panic form; the message must state the invariant, not the operation.
- Never swallow errors with `let _ = result;` in production paths — log, propagate, or convert to a typed failure.
- IPC-facing errors (Tauri commands, CLI exit codes) require serialization; the serialization adapter belongs in the framework layer, not in the domain error type.

## Testing Strategy Contract

- Unit tests live in `#[cfg(test)]` modules in the same file as the code under test; integration tests live in `tests/` at the crate root.
- Test names state the scenario and expected outcome: `fn given_missing_config_returns_config_error` not `fn test_config`.
- Use builder patterns or helper constructors for test fixtures — never construct structs directly in test bodies when any field is likely to change.
- Mock only at external boundaries (filesystem, network, process exec); internal module boundaries use real implementations.
- Snapshot tests (`insta`) for structured output (JSON, TOML, CLI output) prevent silent formatting regressions.
- Apply mutation testing (`cargo mutants`) to high-risk logic (policy evaluation, sync conflict resolution) to verify test assertions actually catch defects.
- Integration tests for crate seams (graft-core API surface, CLI subcommands) run as separate binaries in `tests/`; they prove the public contract, not internal implementation.
- **Reference implementation as behavioral oracle**: When porting from a reference implementation (Python, JavaScript), the reference test suite is the behavioral specification — same fixtures, same scenarios, same expected outcomes. Divergence is a bug, not a design choice; the Rust type system creates pressure to narrow behavior (tighter validation, stricter types) that must be consciously resisted until the port is validated. Intentional tightening is a separate explicit decision after successful port verification.
- **Behavioral fidelity over structural coverage**: When porting, verify that Rust behavior matches reference edge cases, not just that automated gates pass — gates confirm compilation, not correctness against the reference contract.

## Quality Pipeline Contract

| Gate | Commands | When to run |
|------|----------|-------------|
| Fast loop | `cargo check --workspace` | After every non-trivial edit |
| Pre-handoff | `cargo fmt --all -- --check && cargo clippy --workspace --all-targets -- -D warnings && cargo test --workspace` | Before any agent handoff or PR |
| CI hardening | `cargo llvm-cov --workspace`, `cargo deny check`, `cargo machete` | Full CI run; gate on coverage delta, license compliance, unused deps |

## QA Protocol for Rust

Rust QA is qualitative-first because the compiler handles structural correctness between agent rounds. The borrow checker, type system, and `cargo clippy` catch the class of errors that would require intermediate static loops in dynamically-typed languages. That changes the QA shape: less gate-checking, more design review.

**Static QA cadence**: One terminal static pass after all executor changes are complete — not between agents, not after each executor round. If the executor returns with `cargo check` failing, it goes back to the executor, not QA. QA sees code that compiles.

Terminal static gate (run once, before qualitative):
```
cargo fmt --all -- --check && cargo clippy --workspace --all-targets -- -D warnings && cargo test --workspace
```

**Qualitative QA**: Runs after static passes clean. Applies the Two-Mode QA Protocol from the delegation skill. Checks Rust-specific design signals in addition to universal Power of 10 principles:
- Ownership design: three or more `.clone()` calls in one function is a redesign signal, not a fix
- Error propagation: every `?` at a significant abstraction boundary has `.context()`
- Panic usage: `unwrap()` and `expect()` only where the invariant is provably unreachable from correct usage
- IPC boundaries: serialization adapters belong in the framework layer, not in domain error types

QA has fix authority for qualitative violations. If fixes are made, the static gate above re-runs clean before the phase closes.

**The borrow checker is not QA**: Compilation failures between executor rounds are executor self-verification failures. Escalate back to the executor with the compiler error, not to QA. QA is not a build system.

## Parallel Agent Compilation Protocol

- Multiple agents compiling simultaneously against a shared `target/` directory produce race conditions in incremental build state — set `CARGO_TARGET_DIR` to an agent-specific path in every multi-agent brief.
- Heavy gates (`cargo test`, `cargo llvm-cov`) must be serialized across agents; fast gates (`cargo check`, `cargo clippy`) may run in parallel.
- Resolve the first compilation gate before delegating downstream agents that depend on the type-checked output — downstream agents cannot fix a type error they did not introduce.
- Briefing contracts must specify which crate(s) the agent owns; cross-crate edits without coordination produce merge conflicts at the type boundary.
- If an agent returns with `cargo check` failing, the orchestrator must resolve it before issuing any further implementation briefs.

## Debugging Profile

- Read compiler errors top-down; the first error is almost always the root cause — later errors are cascades from unresolved types.
- Compiler `help:` and `note:` suggestions are generated from the type system and are correct in the majority of cases — apply them before reasoning around them.
- Borrow checker errors: check whether the callee needs to own the value (move semantics) before reaching for a clone or a reference with a lifetime annotation.
- If `.clone()` calls are accumulating to silence errors, the mental model of ownership is wrong — stop and redesign the data flow.
- `cargo clippy` surfaces correctness and performance patterns the compiler does not flag (`clippy::unwrap_used`, `clippy::expect_used`, iterator inefficiencies) — run it before any code review.
- **Serde flat-vs-nested silent failure**: When deserializing JSON that has a nested structure (common when porting from Python dataclasses), flat serde field names succeed against a nested JSON tree but produce default/zero-value fields rather than a parse error. Symptom: valid JSON produces empty fields after deserialization. Diagnostic: read the actual `load_*` function's navigation path through the JSON tree — that path is the wire format, not the struct field names. Fix: either mirror the nesting in Rust with intermediate structs, or parse manually via `serde_json::Value` with explicit field extraction.
- Runtime diagnostics: instrument with `tracing` (structured spans and events), not `println!`; `println!` is acceptable only for intentional CLI output.
- Cross-reference: [testing-debugging](../testing-debugging/SKILL.md) for the universal two-attempt rule and diagnostic order protocol.

## Resources

- **reference-nasa-rust.md** — Power of 10 rules adapted for Rust safety model
- **guide-ownership-patterns.md** — borrow/move/clone decision heuristics with examples
- **guide-error-handling.md** — thiserror/anyhow boundaries and context-layering patterns
- **reference-crate-catalog.md** — vetted crates for common needs (async, CLI, serialization, testing)
- **checklist-quality-gate.md** — tiered verification checklist matching the three pipeline gates
- **guide-testing-patterns.md** — unit/integration fixtures, mocking boundaries, snapshot and mutation testing
- **guide-parallel-agents.md** — CARGO_TARGET_DIR isolation and briefing constraints for multi-agent builds

## Blueprints

- **error-type.rs** — `thiserror` enum with `#[from]` conversions and structured variant fields
- **cli-subcommand.rs** — `clap` subcommand skeleton with `Parser`/`Subcommand` derive pattern

## Cross-References

- [testing-debugging](../testing-debugging/SKILL.md): universal diagnostic methodology; Debugging Profile above extends it for Rust.
- [delegation](../delegation/SKILL.md): briefing format and circuit-breaker protocol for multi-agent Rust work.
- [error-architecture](../error-architecture/SKILL.md): cross-layer error handling mandates; Rust contract above is the Rust-specific expression.

</ANCHORSKILL-RUST-DEVELOPMENT>
