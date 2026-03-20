# Workspace Lints Reference — Rust

## Introduction Protocol (Critical)

**Never introduce deny-level lints to an existing codebase in a single step.** Existing violations
will immediately block compilation. The correct protocol:

1. **Introduce as warn** — add the lint at `"warn"` level and run `cargo clippy --workspace`
2. **Fix violations** — address every warning before promoting
3. **Promote to deny** — only after the workspace compiles clean at warn level

This applies especially to `perf` and `pedantic` groups, which catch violations across entire
codebases and will produce dozens of warnings in any existing project.

**For Executor briefs involving lint config changes**: scope is Cargo.toml files ONLY. If the
new lints introduce warnings in `.rs` source files, report them and stop — do NOT fix source
files as a side effect of a config change. Architectural changes require a separate brief.

## Quick Reference

Complete copy-pasteable configuration for `Cargo.toml` at workspace root:

```toml
[workspace.lints.clippy]
# Correctness — hard errors (safe to deny immediately; catch unambiguous mistakes)
dbg_macro           = "deny"
todo                = "deny"
unimplemented       = "deny"
enum_glob_use       = "deny"
wildcard_imports    = "deny"
manual_let_else     = "deny"

# Performance — START as warn, promote to deny after violations cleared
perf                = "warn"   # → "deny" once workspace is clean

# Async safety — warnings (catch real bugs, not style)
unused_async              = "warn"
await_holding_lock        = "warn"
await_holding_refcell_ref = "warn"

# Pedantic — warn with selective allows
pedantic            = { level = "warn", priority = -1 }
must_use_candidate      = "allow"
cast_precision_loss     = "allow"
missing_errors_doc      = "allow"
module_name_repetitions = "allow"
similar_names           = "allow"

[workspace.lints.rustdoc]
broken_intra_doc_links     = "deny"
private_intra_doc_links    = "warn"
missing_crate_level_docs   = "warn"
```

Member crate `Cargo.toml` (inherits all of the above):

```toml
[lints]
workspace = true
```

---

## Clippy Lint Rationale

### Correctness — Deny

| Lint | Level | What it catches | Why deny, not warn |
|---|---|---|---|
| `dbg_macro` | deny | `dbg!()` calls left in committed code | Debug output in production is never intentional; warn lets it slip |
| `todo` | deny | `todo!()` macro marking unfinished code | Unfinished code in committed work is a build contract violation |
| `unimplemented` | deny | `unimplemented!()` macro | Same as todo — panics at runtime if reached |
| `enum_glob_use` | deny | `use MyEnum::*` polluting local namespace | Name collisions are silent; deny forces explicit variant paths |
| `wildcard_imports` | deny | `use module::*` namespace pollution | Same failure mode as enum_glob_use; discovery requires grep |
| `manual_let_else` | deny | Hand-rolled `let x = match ... { None => return }` instead of `let ... else` | Rust 2021+ has `let-else`; manual expansion is strictly less readable |

### Performance — Target: Deny (introduce as `"warn"` first — see Introduction Protocol above)

| Lint group | Level | What it covers | Why deny |
|---|---|---|---|
| `perf` | deny | Slow vector initialization, needless clones on iterators, `Box<T>` in `Extend` calls, unnecessary allocation paths | Performance regressions in hot paths are harder to detect in review than correctness bugs; hard denial forces the fix at the source |

Notable lints inside `perf`: `clippy::slow_vector_initialization`, `clippy::needless_pass_by_value` (in some configurations), `clippy::large_stack_arrays`.

### Async Safety — Warn

See **Async Safety** section below for code examples.

| Lint | Level | What it catches |
|---|---|---|
| `unused_async` | warn | `async fn` that does not contain any `.await` — the `async` wrapper adds state machine overhead for no benefit |
| `await_holding_lock` | warn | `std::sync::MutexGuard` or `RwLockWriteGuard` held across an `.await` point — deadlock risk |
| `await_holding_refcell_ref` | warn | `RefCell` borrow (`Ref` or `RefMut`) held across `.await` — runtime panic in `current_thread` executors |

These are `warn` not `deny` because they occasionally have legitimate explanations (e.g., intentional guard-held await with a documented rationale). The developer should see the warning and make an explicit decision.

### Pedantic — Warn with Selective Allows

`pedantic` is enabled as a `warn` group because it catches real issues (missing `#[must_use]`, lossy casts, unnecessary iteration inefficiencies) while also producing actionable false positives that are domain-appropriate to allow. It is not elevated to `deny` because that would require blanket `#[allow]` attributes scattered through code rather than a policy-level decision.

---

## Rustdoc Lint Rationale

| Lint | Level | What it catches | Why this level |
|---|---|---|---|
| `broken_intra_doc_links` | deny | Doc comment links like `` [`SomeType`] `` that resolve to nothing | A broken link is a documentation bug — it misdirects the reader with no runtime signal |
| `private_intra_doc_links` | warn | Public doc comments linking to private items that external callers cannot access | Common in re-export patterns; warn allows review before deny-elevation |
| `missing_crate_level_docs` | warn | No doc comment on the crate root (`lib.rs` or `main.rs`) | Entry point docs are the first thing `cargo doc` readers see; warn keeps the issue visible without blocking CI |

---

## Async Safety: Code Examples

### `await_holding_lock` — Deadlock

```rust
use std::sync::Mutex;

// WRONG — MutexGuard held across .await
async fn process(shared: &Mutex<State>) {
    let guard = shared.lock().unwrap();   // <-- guard acquired
    do_async_work().await;                // <-- .await here; guard not released
    // Another task trying to lock `shared` will deadlock here
    println!("{:?}", *guard);
}

// CORRECT — release the guard before awaiting
async fn process(shared: &Mutex<State>) {
    let snapshot = {
        let guard = shared.lock().unwrap();
        guard.clone()                      // extract what you need
    };                                     // guard dropped here
    do_async_work().await;
    println!("{:?}", snapshot);
}
```

For async-aware locking across await points, use `tokio::sync::Mutex` instead of `std::sync::Mutex`.

### `await_holding_refcell_ref` — Runtime Panic

```rust
use std::cell::RefCell;

// WRONG — RefMut held across .await in a single-threaded executor
async fn update(cell: &RefCell<State>) {
    let mut borrow = cell.borrow_mut();    // <-- RefMut acquired
    async_io().await;                      // <-- .await; RefCell doesn't implement Send
    borrow.field = 42;
    // In current_thread executor: if the executor re-enters this future
    // while the borrow is held, borrow_mut() panics at runtime
}

// CORRECT — complete RefCell work before awaiting
async fn update(cell: &RefCell<State>) {
    cell.borrow_mut().field = 42;          // borrow acquired, mutated, dropped
    async_io().await;                      // safe to await with no active borrow
}
```

### `unused_async` — Wasted State Machine

```rust
// WRONG — async adds a state machine allocation for nothing
async fn compute(x: u32) -> u32 {
    x * 2       // no .await — this is just a synchronous function
}

// CORRECT — remove async; callers can still .await a plain fn returning a value
fn compute(x: u32) -> u32 {
    x * 2
}
```

---

## Member Crate Inheritance

**Standard inheritance** (all member crates):

```toml
# crates/my-crate/Cargo.toml
[lints]
workspace = true
```

This inherits all `[workspace.lints.clippy]` and `[workspace.lints.rustdoc]` settings without repetition.

**Per-crate override** (when a crate legitimately needs different rules):

```toml
# crates/ffi-crate/Cargo.toml
[lints]
workspace = true

[lints.clippy]
unsafe_code = "allow"      # FFI crate requires unsafe; justification in SAFETY comments
```

**When overrides are justified vs technical debt**:

| Override | Justified | Technical debt |
|---|---|---|
| `unsafe_code = "allow"` in FFI crate | Yes — unsafe is the whole point | If in application logic without documented invariants |
| `cast_precision_loss = "allow"` in geometry crate | Yes — domain-appropriate lossy casts with deliberate precision tradeoffs | If used to silence unreviewed casts |
| `missing_errors_doc = "allow"` in internal-only crate | Yes — private API, no external callers | If on a public library crate |
| `pedantic = "deny"` promotion in stable crate | Legitimate tightening | If forcing `#[allow]` sprinkled through call sites |

A per-crate override should have a comment explaining why it diverges from workspace policy. Unexplained overrides are auditable technical debt.

---

## Lint Group Hierarchy

Clippy organizes lints into groups with an inheritance relationship. Understanding this prevents misconfiguration:

| Group | Scope | Typical use |
|---|---|---|
| `all` | Every lint clippy knows | Too aggressive — includes nursery (unstable) lints |
| `correctness` | Lints catching likely bugs | Enabled by default; deny in CI |
| `suspicious` | Patterns that are probably wrong | Enabled by default |
| `style` | Idiomatic Rust style | Enabled by default |
| `complexity` | Needlessly complex code | Enabled by default |
| `perf` | Performance anti-patterns | Not enabled by default — explicitly deny here |
| `pedantic` | Stricter versions of the above | Not enabled by default — warn with selective allows |
| `nursery` | Unstable / experimental | Not enabled by default — avoid in CI (may change between releases) |
| `restriction` | Restrictive lints for safety-critical contexts | Not enabled by default — opt-in individually |

**Why `pedantic`-with-allows rather than `all`**:
- `all` includes `nursery`, which changes between minor clippy releases and breaks CI unpredictably.
- `all` also includes `restriction` lints designed for embedded/no-std contexts that would require `#[allow]` on normal Rust code.
- `pedantic`-with-explicit-allows is the documented approach used by production projects (tokio, axum, rust-analyzer).

**Priority field**: When enabling a lint group with overrides, the group declaration uses `priority = -1` so individual lint overrides (higher default priority of 0) take precedence. Without this, the group setting wins and your `allow` declarations are silently ignored.

```toml
pedantic = { level = "warn", priority = -1 }
must_use_candidate = "allow"    # priority = 0 (default) > -1; this allow wins
```

---

## Checking Lint Status

**Workspace-wide** (CI and QA gate):
```bash
cargo clippy --workspace --all-targets -- -D warnings
```

`--all-targets` includes `tests`, `examples`, and `benches` — lint-only checking the `lib` target misses test-specific patterns.

**Single crate** (executor pre-handoff gate):
```bash
cargo clippy --package my-crate --all-targets -- -D warnings
```

**Interpreting output**:
- `error[clippy::lint_name]` — a deny-level lint; blocks CI. Fix before commit.
- `warning[clippy::lint_name]` — a warn-level lint; visible but does not block. Address or document an explicit allow.
- `note: ...` lines under a lint — the compiler's suggestion; apply it unless you have a documented reason not to.

**Applying suggestions automatically**:
```bash
cargo clippy --fix --workspace --all-targets
```

Review the diff — `--fix` applies all machine-fixable suggestions. Not all suggestions are correct for every context.

---

## Common Pedantic False Positives

These are the `pedantic` lints most routinely allowed at workspace policy level, with the rationale:

| Lint | Why allowed at workspace level |
|---|---|
| `must_use_candidate` | Marks every function whose return value *could* be meaningful as `#[must_use]`. Produces thousands of warnings on `From`/`Into` implementations and simple getters where ignoring the return is intentional. Opt-in per function instead: add `#[must_use]` explicitly where the caller *must* handle the return. |
| `cast_precision_loss` | Flags `f64 as f32` and `u64 as f64` conversions. Often intentional in geometric, statistical, or display code. Suppress globally; add `#[allow(clippy::cast_precision_loss)]` with a comment only where non-obvious. |
| `missing_errors_doc` | Requires every `Result`-returning public function to document its error conditions in rustdoc. Useful for public library APIs; redundant for internal or private-API crates. Enable selectively on public-facing library crates via per-crate override. |
| `module_name_repetitions` | Flags `user::UserRecord` as repetitive. The repetition is often deliberate for disambiguation when the module is re-exported or when callers use `use module::*` (which we deny — but the flag predates that policy). The `user::Record` alternative is less clear when the type is used outside the module. |
| `similar_names` | Flags pairs like `id` and `idx`, or `path` and `paths`, as too similar. Too aggressive for domain code where these are distinct and appropriate short names. |
