# Rust Crate Catalog

Vetted crates for common needs in this codebase. Every entry reflects the vetting criteria from SKILL.md: maintenance status, soundness record, API ergonomics, and fitness for the specific problem it solves. "Current" means stable and widely adopted as of early 2026.

**Adding a dependency not listed here requires explicit vetting.** Check crates.io for recent commit activity, open soundness issues in the issue tracker, and RustSec for any advisories. `cargo deny check` enforces the AVOID list in CI — add newly banned crates to `deny.toml` when a vetting decision produces an AVOID classification.

Cross-reference: [guide-build-engineering.md](./guide-build-engineering.md) for build tool crates (cargo-nextest, sccache, cargo-deny). Supply chain tools are listed in both files; build tools that are dev/CI-only are in the guide.

---

## Concurrency & Async

The selection philosophy here distinguishes two problem spaces: CPU-bound parallelism (data processing, batch work) and I/O-bound concurrency (network, filesystem, IPC). Using an async runtime for CPU-bound work — or Rayon for I/O-bound work — is the most common category mistake.

| Name | Version | Purpose | Use When | Notes |
|---|---|---|---|---|
| `tokio` | 1.x | Async runtime: task scheduler, I/O reactor, timers, channels | Any async application code; mandatory when using async/.await in a binary | Do not use tokio in library crates unless the library is explicitly async-only; prefer `async-trait` abstractions at library boundaries |
| `rayon` | 1.x | CPU-parallel iterators via work-stealing thread pool | CPU-bound parallelism on data collections; batch processing, indexing, compression | Not for I/O-bound work — rayon threads block, which starves the pool; combine with tokio via `spawn_blocking` when bridging |
| `dashmap` | 6.x | Concurrent hash map with fine-grained shard locking | Shared mutable map accessed from multiple threads without wrapping in `Mutex<HashMap>` | Slightly higher memory overhead than `HashMap`; use only when contention on a single `Mutex<HashMap>` is measured, not assumed |
| `kanal` | 0.1.x | High-performance MPMC channel (async + sync) | When channel throughput is a measured bottleneck; hot-path message passing between async tasks | Younger ecosystem; prefer `flume` when ergonomics matter more than raw throughput |
| `flume` | 0.11.x | Ergonomic MPMC channel (async + sync) | Default channel choice when `std::sync::mpsc` is too limited (need MPMC or async) | Excellent ergonomics; slightly lower throughput than `kanal` but faster than `crossbeam-channel` in most benchmarks |
| `deadpool-sqlite` | 0.9.x | Async connection pool for `rusqlite` | When SQLite access must happen from async code without blocking the async executor | `rusqlite` is synchronous; this pool manages spawning blocking tasks. Use instead of raw `tokio-rusqlite` for any multi-connection workload |
| `tokio::JoinSet` | (stdlib) | Collect and await a dynamic set of async tasks | When spawning a variable number of tasks whose results must be collected | Part of tokio 1.x; not a separate crate. Use `FuturesUnordered` from `futures` crate only when ordering constraints require it |

---

## Error Handling

The selection philosophy follows the library/application split from the Error Architecture Contract in SKILL.md. Library crates define typed errors; application binaries aggregate them. The crates below map to these two roles.

| Name | Version | Purpose | Use When | Notes |
|---|---|---|---|---|
| `thiserror` | 2.x | Derive macro for typed library errors | All `pub` error enums in library crates (`graft-core`); any crate that other crates import | First choice for domain-level typed errors. `#[from]` handles `From` impls automatically; `#[source]` preserves the error chain |
| `anyhow` | 1.x | Opaque error aggregation for application code | Binary entry points (`main.rs`, CLI handlers, Tauri commands) where exact error types don't cross an API boundary | Do not use in library crates — erases type information that callers need to match on |
| `error-stack` | 0.5.x | Structured error context with attachment points | When you need to attach structured data (request IDs, file paths, operation context) to errors as they propagate | More powerful than `.context()` on `anyhow`; heavier API. Justified when context data needs to be machine-readable, not just human-readable |
| `miette` | 7.x | Human-friendly CLI error reporting with source spans | CLI-facing error display; diagnostic output that highlights the problematic input | Replace `anyhow` at the CLI boundary, not throughout the application. `miette::Diagnostic` derives on top of existing error types |
| `snafu` | 0.8.x | Call-site error context with `ensure!` and `whatever!` macros | When errors need rich context at each call site and `thiserror` + `.context()` feels insufficient | More verbose than `thiserror`; the ergonomics pay off in large codebases where call-site context is critical for debugging production issues |

---

## Testing

The selection philosophy: each tool occupies a distinct testing niche. Snapshot tests catch formatting regressions. Property tests find edge cases. Fuzz tests find security-relevant inputs. Benchmarks answer "is this fast?" Deterministic benchmarks answer "did this get slower?" Reaching for multiple tools per codebase is expected; they are not alternatives to each other.

| Name | Version | Purpose | Use When | Notes |
|---|---|---|---|---|
| `insta` | 1.x | Snapshot testing for structured output | JSON output, TOML serialization, CLI stdout, any text format that must not change silently | Run `cargo insta review` to update snapshots interactively. Snapshot files commit to the repo; they are the source of truth, not generated artifacts |
| `proptest` | 1.x | Property-based testing with shrinking | High-risk logic (policy evaluation, sync conflict resolution, serialization round-trips) | Generates random inputs and shrinks failures to minimal reproducible cases. Pair with `cargo-fuzz` for coverage-guided exploration on security-sensitive paths |
| `derive_fuzztest` | 0.1.x | Bridge between `proptest` and `cargo-fuzz` | When you want to run the same test as both a proptest (fast, CI) and a cargo-fuzz target (slow, coverage-guided) | From Google, v0.1.4. Eliminates the maintenance cost of maintaining two separate test implementations |
| `cargo-fuzz` | (CLI tool) | Coverage-guided fuzzing via libFuzzer | Security-sensitive parsing (network input, file format parsing, config parsing) | Requires nightly for the libFuzzer integration; the fuzz targets themselves are stable Rust. Run locally or in a separate CI job — not in the main test suite |
| `divan` | 0.1.x | Ergonomic micro-benchmarks | Measuring throughput of hot-path code; comparing algorithm implementations | Simpler API than Criterion; less statistical rigor. Use Criterion if you need full statistical analysis of latency distributions |
| `iai-callgrind` | 0.14.x | Deterministic instruction-count benchmarks via Valgrind | CI-stable benchmark gates where wall-clock variability would cause false failures | Measures CPU instructions, not wall time — results are reproducible across CI runs. Requires Valgrind; Linux-only. |

> **Linux:** `iai-callgrind` requires Valgrind. Install via your package manager (`apt install valgrind`, `dnf install valgrind`).
> **Windows:** `iai-callgrind` is not supported on Windows. Use `divan` or `criterion` for benchmarks on Windows.
> **macOS:** `iai-callgrind` is available via Homebrew Valgrind (`brew install valgrind`), but Valgrind on macOS lags behind kernel versions and may not support your macOS release. Verify compatibility before committing it to CI.

---

## Performance

The selection philosophy: reach for these crates only when profiling identifies a specific bottleneck. Premature use of `smallvec` or arena allocators increases code complexity without measurable benefit at typical input sizes.

| Name | Version | Purpose | Use When | Notes |
|---|---|---|---|---|
| `smallvec` | 1.x | Stack-allocated small vector with heap fallback | Collections that are almost always small (≤8 items) but occasionally large; hot allocation paths | Profile first. The API is largely compatible with `Vec`; migration is mechanical once the bottleneck is confirmed |
| `compact_str` | 0.8.x | Inline-stored string for short strings (≤24 bytes on 64-bit) | Short string keys in hot maps; tag values; identifiers that fit in the inline buffer | Fully compatible with `String` API. Prefer over `smol_str` when `String` API compatibility matters |
| `smol_str` | 0.3.x | Immutable, clone-cheap small string | Read-heavy string keys; symbol table entries; AST node labels | Clone is O(1) via reference counting for large strings, O(N) copy for inlined ones. Choose over `compact_str` when immutability is the invariant you want enforced |
| `bumpalo` | 3.x | Arena allocator for short-lived objects | Parsing phases where many small objects are created and all freed together | Objects allocated in a `Bump` arena cannot hold references to each other without unsafe code. The arena frees all allocations at once — no individual dealloc |
| `rkyv` | 0.8.x | Zero-copy deserialization (access archived data without copying) | Performance-critical deserialization of binary formats; network protocols; mmap'd data | Significant API complexity. Requires explicit alignment considerations. Benchmark against `bincode` before committing — the zero-copy benefit only materializes for large, frequently-accessed datasets |

---

## Supply Chain

These are not library dependencies — they are development and CI tools enforcing dependency hygiene. All belong in CI as blocking gates.

| Name | Version | Purpose | Use When | Notes |
|---|---|---|---|---|
| `cargo-deny` | 0.19.x | License compliance, banned crates, advisory checks, duplicate detection | All projects; mandatory CI gate | Configured via `deny.toml`. The AVOID entries in this catalog should be reflected in the `[bans]` section. Version 0.19.0 (January 2026) improved license expression parsing |
| `cargo-audit` | 0.21.x | CVE check against RustSec advisory database | Before releases; periodic CI job | Checks `Cargo.lock` — requires a lock file. Complements `cargo deny` (which enforces policy) with reactive CVE detection |
| `cargo-vet` | 0.10.x | Supply chain trust via auditor network | High-assurance codebases; when you need third-party audit evidence for dependencies | Significant operational overhead — requires maintaining audit records or importing trusted auditor sets. Skip for internal tools; consider for externally-distributed software |
| `cargo-machete` | 0.7.x | Detects unused `Cargo.toml` dependencies | Release preparation; periodic cleanup | False positives exist for proc-macro-only and optional-feature crates. Review output; do not blindly remove flagged entries |

---

## Defensive Programming

These crates enforce invariants at code boundaries beyond what the type system alone expresses.

| Name | Version | Purpose | Use When | Notes |
|---|---|---|---|---|
| `contracts` | 0.6.x | Pre/postcondition macros (`#[requires]`, `#[ensures]`, `#[invariant]`) | Library functions with non-trivial invariants that panic if violated; correctness-critical paths | Conditions compile to `debug_assert!` in release builds — zero overhead in production, active guards during development and test |
| `assert2` | 0.3.x | Enhanced assertion macros with structured diff output | Test assertions where the default `assert_eq!` output is hard to read (structs, long strings, nested values) | Drop-in improvement over `assert_eq!` and `assert_ne!`; no runtime overhead beyond the standard macros |
| `proptest` | 1.x | Property-based testing (see Testing section) | Defensive verification of invariants under arbitrary input | Cross-listed; the defensive use case is verifying that invariants hold under inputs you did not think to test by hand |

---

## AVOID

These crates are explicitly disqualified. Do not add them as dependencies. If they appear in a dependency audit, treat it as a signal to find an alternative or vendor the functionality.

| Name | Reason |
|---|---|
| **`beef`** | **AVOID** — Known soundness bugs in its `Cow` replacement. Unmaintained since 2022; no response to soundness reports in the issue tracker. Use `std::borrow::Cow` instead — it is not slower for any realistic workload. |
| **`mobc`** | **AVOID** — Legacy connection pool predating modern async ecosystem maturity. Maintenance activity has stalled. Use `deadpool` (general-purpose, actively maintained) or `deadpool-sqlite` (SQLite-specific) instead. `bb8` is also acceptable for tokio-integrated pool use cases. |
| **`tokio-rusqlite` (as a pool)**  | **AVOID for multi-connection workloads** — `tokio-rusqlite` wraps a single `rusqlite::Connection` in a `spawn_blocking` queue. It is a correct single-connection async adapter, not a connection pool. Using it as a pool involves wrapping it in `Arc<Mutex<...>>` which serializes all access to one connection. Use `deadpool-sqlite` for actual connection pooling. |
| **`beef` (any fork)** | **AVOID** — Soundness issues are in the design, not just the original implementation. Forks inherit the structural risk. |
