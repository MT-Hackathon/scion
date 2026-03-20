# Rust Crate Architecture Guide

Workspace decomposition is one of the highest-leverage early decisions in a Rust project — it
determines parallelism during compilation, forces API surface clarity, and sets the cost of future
refactoring. This guide answers the "when to split, and why" question with real signals, not theory.

Cross-reference: [guide-edition-2024-migration.md](guide-edition-2024-migration.md) for the
`edition.workspace = true` pattern that eliminates per-crate edition drift once you split.

---

## When to Split

Split when one of these signals is present. If none are, don't.

### 1. Parallelization Bottleneck

Cargo parallelizes compilation at the crate level. If one crate's build is the "long pole" that
every other crate waits on — typically the library that everything imports — that crate is a
candidate for decomposition. Not because it's too big philosophically, but because its compile time
is serializing the entire dependency graph.

Measure with `cargo build --timings` (generates an HTML report in `target/`). A crate that accounts
for 60%+ of sequential compile time is a bottleneck worth addressing. Pure logic with no heavy
macro expansion splits cleanly and benefits from parallelism.

### 2. Dependency Tree Divergence

When a subset of your code needs a dependency that the rest doesn't, the dependency's compile cost
is paid by everything that imports the umbrella crate.

```
graft-core (wants: serde, rusqlite, deadpool-sqlite)
graft-cli  (also needs: clap, miette)

vs.

graft-core (serde, rusqlite, deadpool-sqlite)
graft-cli  (graft-core + clap + miette)
```

The CLI needs clap and miette only for its binary entry point. A library consumer of `graft-core`
should not transitively pull in terminal rendering crates. Split when the extra dependencies have
no meaning for downstream consumers.

### 3. Platform Gates

`no_std` crates and `wasm32` targets have strict constraints on what they can import. If you have
logic that must run in embedded or browser contexts alongside logic that uses OS facilities, they
cannot share a crate. The boundary is architectural, not organizational.

### 4. Independent Consumers

If external users need your library without your CLI, server, or application shell — the library
must stand alone. Bundling library and binary code in one crate forces every library consumer to
compile your binary entry point's dependency tree. Keep `lib.rs` and `main.rs` in separate crates.

---

## When NOT to Split

### 5. Co-Change Coupling

If changes to crate A always require changes to crate B, they are one logical unit regardless of
how they are packaged. The crate boundary adds ceremony — `pub` APIs, version bumps, inter-crate
import paths — without architectural gain.

Look at your git log. If `crate-a/` and `crate-b/` appear in the same commit 80% of the time,
they're coupled. That coupling should live at a module boundary inside a single crate, not across
a crate boundary that makes refactoring more expensive.

### 6. The "Minimize the Cut" Principle

From matklad's workspace design writing: **a crate split is worth doing only if the cut is narrow.**
If moving 1,000 lines of code into a new crate requires exposing 200 lines of previously internal
types as `pub`, the split is too wide. It trades private implementation details for a public API
that now must be maintained, tested, and evolved with care.

The correct question before splitting: "How many new `pub` items does this cut require?" If the
answer is large relative to what actually needs to be public, reorganize within the existing crate
until the cut narrows.

### 7. Test Binary Bloat

Every crate in a workspace produces its own test binary for `cargo test`. Debug test binaries are
large — a workspace with 50 small crates can easily accumulate 5–10 GB of test artifacts. This is
not a reason to never split, but it is a constraint: crate granularity has a real cost in disk
usage and CI cache pressure.

`cargo-nextest` mitigates this by running tests from multiple binaries concurrently, but the
binaries still exist. Use this as a counterweight against splitting for purely organizational
reasons.

---

## Feature Flags vs. Separate Crates

Feature flags and crate splits solve different problems. Choosing the wrong tool creates either
a dependency mess or unnecessary compilation overhead.

| Scenario | Tool | Reason |
|---|---|---|
| Optional serde support | Feature flag (`serde`) | Nearly zero cost when disabled; standard Rust convention |
| Alternative backends (e.g., sqlite vs. postgres) | Feature flag | Compile exactly one backend |
| Optional optimization (e.g., `simd`, `jemalloc`) | Feature flag | Additive, no API surface change |
| Large dependency tree needed by only one consumer | Separate crate | Keeps consumers from paying compile cost |
| Platform-specific code (`wasm32`, `no_std`) | Separate crate | Constraints cannot be satisfied in one compilation unit |
| Independent external consumers | Separate crate | Library must stand alone |

**Always `default-features = false` in workspace dependencies.** Feature unification means the
workspace compiles each dependency once with the union of all requested features. `default-features
= true` (the default) opts every crate into every feature that any other crate enables — including
features your crate never uses.

```toml
# Cargo.toml (workspace root)
[workspace.dependencies]
serde = { version = "1", default-features = false }
tokio = { version = "1", default-features = false, features = ["rt-multi-thread", "macros"] }
```

---

## API Surface Design

Visibility is the primary tool for controlling what users of a crate can depend on. More public
surface means more things that must remain stable.

```rust
// Correct visibility hierarchy:

pub(crate) struct InternalBuffer { ... }  // default — not in the public API
pub(super) fn sibling_helper() { ... }    // accessible to parent module only
pub fn external_api() { ... }             // part of the crate's contract

// Items that must be pub for sibling crates but not for external consumers:
#[doc(hidden)]
pub fn workspace_internal_only() { ... }  // visible to workspace, hidden from docs
```

### `#[non_exhaustive]` on All Public Enums and Structs

Every public enum in a library crate must be `#[non_exhaustive]`. Omitting it locks you into never
adding variants — downstream users writing `match` expressions will get a compile error when you
add one, turning an additive change into a breaking change.

```rust
#[non_exhaustive]
pub enum SyncError {
    NotFound { path: std::path::PathBuf },
    PermissionDenied,
    PolicyViolation { rule: String },
    // Adding a new variant here is not a semver break — users must have a `_` arm
}

#[non_exhaustive]
pub struct SyncConfig {
    pub timeout: std::time::Duration,
    pub retry_count: u32,
    // Adding new fields here is not a semver break
}
```

### Sealed Traits

When a trait is part of your public API but you want to control which types implement it —
preventing downstream users from implementing it on their own types — use the sealed trait pattern:

```rust
// In a private module:
mod sealed {
    pub trait Sealed {}
}

// The public trait:
pub trait SyncTarget: sealed::Sealed {
    fn sync_key(&self) -> &str;
}

// Only types you implement sealed::Sealed for can implement SyncTarget.
// Users see SyncTarget and its methods but cannot implement the trait.
impl sealed::Sealed for LocalProject {}
impl SyncTarget for LocalProject {
    fn sync_key(&self) -> &str { &self.id }
}
```

### The `unreachable_pub` Lint

Enable this lint to catch items declared `pub` that are not reachable from the crate root — items
that are technically public but effectively dead API surface because no module path leads to them.

```toml
# workspace Cargo.toml
[workspace.lints.rust]
unreachable_pub = "warn"
```

---

## Workspace Architecture Patterns

### Standard Naming Conventions

| Crate name | Role | Notes |
|---|---|---|
| `project-core` | Pure logic, no I/O | No `tokio`, no filesystem; testable in isolation |
| `project-cli` | Binary entry point | Thin: parse args, call core, render output |
| `project-http` / `project-server` | HTTP adapter | Axum/actix handlers wiring core types to HTTP |
| `project-macros` | Proc-macros | **Must** be a separate crate — the compiler requires it |

Proc-macro crates must set `proc-macro = true` in `Cargo.toml`. They compile to a host-native
shared library loaded by `rustc` at compile time. The Rust compiler enforces this boundary.

### Virtual Workspace Pattern

A virtual workspace has no `src/` at the root — only a `Cargo.toml` that declares `[workspace]`
with no `[package]`. Used by ripgrep, deno, axum, zed, and most large Rust projects.

```toml
# Cargo.toml (workspace root — no [package] section)
[workspace]
members = [
    "crates/graft-core",
    "crates/graft-cli",
    "src-tauri",
]
resolver = "3"

[workspace.package]
edition = "2024"
authors = ["Rootstock Contributors"]
license = "MIT"

[workspace.dependencies]
# Pin shared dependencies here — all crates inherit versions
serde = { version = "1", default-features = false, features = ["derive"] }
tokio = { version = "1", default-features = false, features = ["rt-multi-thread", "macros"] }
thiserror = "2"
anyhow = "1"
```

The virtual workspace pattern enforces that the root is never accidentally imported as a library.
Version pinning at the workspace level prevents dependency version drift between crates.

---

## Compile-Time Implications

These are not abstract concerns — they determine iteration speed on every build.

**Public API changes force recompilation of dependent crates.** When you change a `pub` function
signature or type in `graft-core`, every crate that imports `graft-core` must recompile. When you
change a `pub(crate)` function in `graft-core`, only `graft-core` recompiles. Smaller public API
surface = faster incremental builds across the workspace.

**Feature unification compiles each dependency once.** If `graft-core` enables `serde/derive` and
`graft-cli` enables `serde/derive` + `serde/rc`, the workspace compiles serde with both features
enabled, once. This is efficient. The hazard: if two crates request incompatible feature
combinations (the feature model doesn't allow disjunction), you may get unexpected feature
enablement in a crate that didn't opt in.

**Integration test files in `tests/` each compile as separate crates.** A common mistake: a `tests/`
directory with 50 `.rs` files becomes 50 test crates, each linking independently. This generates
enormous binary bloat and slow compile times. Use a single entry point:

```
tests/
  integration.rs          # main entry point: pub mod subtest; pub mod other;
  helpers/
    mod.rs
  api/
    mod.rs
```

```rust
// tests/integration.rs
mod helpers;
mod api;
```

One file at the `tests/` root, all other test modules `mod`'d in. One test binary per crate.

**`dev-dependencies` feature leakage.** `dev-dependencies` can activate features that are not
available to normal library users. If `graft-core`'s `dev-dependencies` enable `serde/rc`, your
unit tests compile with that feature but your library's published users do not. Use `cargo-hack`
to verify each feature combination compiles independently:

```bash
cargo install cargo-hack
cargo hack check --workspace --each-feature
```

---

## rmcp: A Case Study in Decomposition

`rmcp` (the Rust MCP protocol library) demonstrates these principles on a public codebase where
the cut points are visible and justified.

**Core split**: `rmcp` (protocol types + traits) and `rmcp-macros` (proc-macros) are separate
crates. This is mandatory — proc-macros must compile as a host-native shared library independent
of the crate that uses them. There is no design choice here; it is a compiler constraint.

**Feature-gated transports**: Transports (`transport-io` for stdio, `transport-streamable-http-server`
for the HTTP streaming variant) are feature flags rather than separate crates. The core protocol
is useful without any transport; the transports are optional components that bring their own
dependency trees (axum, tokio-util) only when enabled.

```toml
# rmcp's Cargo.toml (simplified)
[features]
transport-io = ["dep:tokio"]
transport-streamable-http-server = ["dep:axum", "dep:tokio", "dep:tower"]
```

**The `#[tool]` macro pattern**: Instead of manually implementing a dispatch table (a flat `match`
over method names), rmcp-macros generates it. The annotated handler methods become the source of
truth; the macro synthesizes the boilerplate:

```rust
// Without rmcp-macros: manual dispatch
async fn handle_tool_call(&self, name: &str, args: Value) -> Result<Value> {
    match name {
        "write_memory" => self.write_memory(args).await,
        "search_memory" => self.search_memory(args).await,
        _ => Err(McpError::ToolNotFound(name.to_string())),
    }
}

// With rmcp-macros: the macro generates the dispatch from annotations
#[derive(McpServer)]
struct RootstockServer { ... }

#[tool(description = "Write a persistent memory entry")]
async fn write_memory(&self, #[argument] content: String) -> Result<CallToolResult> { ... }

#[tool(description = "Search memories by semantic query")]
async fn search_memory(&self, #[argument] query: String) -> Result<CallToolResult> { ... }
```

The macro is justified here because the dispatch table is mechanical, high-churn (every new tool
requires an entry), and error-prone (misspelled match arms compile but silently fail at runtime).
Proc-macros are the correct tool when the alternative is boilerplate with no design content.

**What this teaches**: The rmcp split is motivated by compiler constraints (proc-macros), dependency
isolation (transports bring heavy async I/O crates), and ergonomics (the `#[tool]` macro reduces
per-tool boilerplate from ~5 lines to 1). Each split has a concrete cause. No split exists to
"organize" code that could live in one module.
