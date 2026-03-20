# Rust Edition 2024 Migration Guide

Read this before running `cargo fix --edition`. Edition migrations are generally low-risk, but a few
breaking changes require human judgment — `cargo fix` cannot reason about your intent, only your
syntax. This guide covers what will break, what `cargo fix` handles automatically, and what needs
deliberate review.

Requires Rust 1.85+ (stable, released February 2025). Cross-reference:
[guide-crate-architecture.md](guide-crate-architecture.md) for leaf-first migration ordering and
`edition.workspace = true` coordination across multi-crate workspaces.

---

## Breaking Changes

### 1. RPIT Lifetime Capture

**This is the most consequential change.** In Edition 2021, `impl Trait` in return position
captured only lifetimes explicitly mentioned in the function signature or trait bounds. In Edition
2024, it captures **all in-scope lifetimes** — including those inherited from the enclosing `impl`
block. `cargo fix` cannot resolve this; it requires human review of every `impl Trait` return.

```rust
// ─── Edition 2021 ─────────────────────────────────────────────────────────
struct Context<'a> {
    prefix: &'a str,
}

impl<'a> Context<'a> {
    // 2021: 'a is NOT captured in the return type — closure is 'static
    fn make_greeter(&self) -> impl Fn() -> String + 'static {
        || "hello".to_string()
    }
}

// ─── Edition 2024 ─────────────────────────────────────────────────────────
impl<'a> Context<'a> {
    // 2024: 'a IS captured — compile error because 'a ≠ 'static
    // error: hidden type captures lifetime that does not appear in bounds
    fn make_greeter(&self) -> impl Fn() -> String + 'static { // ← ERROR
        || "hello".to_string()
    }

    // Fix A: exclude lifetimes explicitly — use<> captures nothing
    fn make_greeter_fixed(&self) -> impl Fn() -> String + use<> + 'static {
        || "hello".to_string()
    }

    // Fix B: if the lifetime should be captured, remove the 'static bound
    fn make_greeter_borrowing(&self) -> impl Fn() -> String + use<'a> {
        let prefix = self.prefix;
        move || prefix.to_string()
    }
}
```

The `use<>` syntax (stable since 1.82) is the surgical fix. `use<>` captures no lifetimes.
`use<'a, T>` captures exactly those named. The general rule: if the returned opaque type does not
logically depend on a lifetime, exclude it explicitly.

**Where to look**: grep for `-> impl` across all crates, especially in trait implementations and
methods on types with lifetime parameters.

---

### 2. `unsafe_op_in_unsafe_fn` Warn-by-Default

In Edition 2021, calling an unsafe function or dereferencing a raw pointer inside an `unsafe fn`
required no additional annotation — the outer `unsafe fn` was the blanket permission. In Edition
2024, unsafe operations inside `unsafe fn` must still be wrapped in an inner `unsafe {}` block. This
narrows the blast radius of each unsafe fn and forces call-site documentation.

```rust
// ─── Edition 2021 ─────────────────────────────────────────────────────────
unsafe fn read_unchecked(ptr: *const u8) -> u8 {
    *ptr  // fine — outer unsafe fn covers this
}

// ─── Edition 2024 ─────────────────────────────────────────────────────────
unsafe fn read_unchecked(ptr: *const u8) -> u8 {
    // SAFETY: caller guarantees ptr is valid and aligned
    unsafe { *ptr }  // inner block required
}
```

`cargo fix` handles this automatically. Verify the added `SAFETY` comments accurately describe the
invariant the caller is responsible for — don't let auto-fix insert empty safety comments.

---

### 3. `gen` and `try` Keyword Reservation

`gen` is reserved as a keyword in Edition 2024 (for future `gen {}` block syntax). Code with
variables or functions named `gen` will not compile. `cargo fix` renames them to `r#gen`
automatically.

```rust
// 2021: valid identifier
let gen = generate_id();

// 2024: compile error — gen is reserved
// cargo fix produces:
let r#gen = generate_id();
```

`try` was already reserved in earlier editions. If your code has not used it as an identifier, no
action is needed.

---

### 4. `if let` Temporary Rescoping

**This is the second change requiring human review.** In Edition 2021, temporaries created in an
`if let` condition lived until the end of the enclosing `if` statement — covering the body and the
`else` branch. In Edition 2024, they drop at the end of the condition expression, before the body
executes.

```rust
// ─── Edition 2021 ─────────────────────────────────────────────────────────
use std::sync::Mutex;

fn check_value(state: &Mutex<Vec<String>>, target: &str) -> bool {
    // The MutexGuard from .lock() lives through the body — this compiles
    if let Some(val) = state.lock().unwrap().iter().find(|s| s.as_str() == target) {
        println!("found: {val}");  // val borrows from the guard — guard still alive
        true
    } else {
        false
    }
}

// ─── Edition 2024 ─────────────────────────────────────────────────────────
// The MutexGuard drops at the end of the condition — val now dangles
// Compile error: borrow of temporary value does not live long enough

// Fix: bind the guard to a named variable before the if let
fn check_value(state: &Mutex<Vec<String>>, target: &str) -> bool {
    let guard = state.lock().unwrap();
    if let Some(val) = guard.iter().find(|s| s.as_str() == target) {
        println!("found: {val}");  // guard is in scope, val is valid
        true
    } else {
        false
    }
}
```

This is the change most likely to break lock-guarded patterns or builder chains. `cargo fix`
cannot identify these — the borrow checker surfaces them as errors during compilation.

---

### 5. Match Ergonomics (RFC 3627)

In some patterns where a `mut` binding inhibited automatic binding mode transitions, Edition 2024
applies stricter rules. Most code is unaffected; proc-macro-generated patterns that rely on specific
binding mode inference may need adjustment. `cargo fix` handles common cases; check macro-generated
code manually if you see binding mode errors.

---

### 6. Macro `expr` Fragment Specifier

The `expr` matcher in declarative macros (`macro_rules!`) now matches `const {}` blocks and `_`
expressions in addition to what it matched before. Macros that used `expr` in contexts where
`const {}` or `_` would be invalid will need the `expr_2021` specifier to preserve prior behavior.

```rust
// If your macro breaks on const expressions, change expr to expr_2021:
macro_rules! my_macro {
    ($e:expr_2021) => { /* ... */ }  // matches 2021 expr semantics
}
```

`cargo fix` converts `expr` to `expr_2021` where needed.

---

### 7. Prelude Additions

`std::future::Future` and `std::future::IntoFuture` are added to the Edition 2024 prelude. Name
collisions with locally defined `Future` or `IntoFuture` types will produce compile errors. Qualify
the local type with its full path or rename it.

---

### 8. Never Type Fallback

The never type `!` now falls back to `!` itself instead of `()` in inference contexts where no
concrete type is determined. This affects `let x = loop { break; }` and similar uninhabited
expressions. In practice this only affects code that relied on the `()` fallback implicitly — rare
outside of test utilities. `cargo fix` handles most cases.

---

## Migration Workflow

Migrate leaf crates first (those with no internal workspace dependents) and work inward. A failed
migration in a dependency crate produces cascading errors in everything that imports it.

```
1.  Verify toolchain: rustup update stable  (1.85+ required)

2.  For each crate (leaf → root):

    a.  cargo fix --prepare-for 2024 --all-features
        # Applies syntax-only fixes while still on the current edition

    b.  In Cargo.toml: change edition = "2021" to edition = "2024"

    c.  cargo fix --edition --all-features
        # Applies remaining mechanical fixes under the new edition

    d.  cargo test --all-features
        # Catch semantic breakage that fix cannot detect

3.  After all crates migrate:
    - Update workspace Cargo.toml: resolver = "3"   (new default in 2024)
    - Add to rustfmt.toml: style_edition = "2024"
    - Run: cargo fmt --all
```

**`--all-features` is mandatory.** `cargo fix` only sees code compiled under the active feature
set. Code gated behind non-default features will not be fixed unless those features are enabled.

> **Windows:** Code inside `#[cfg(target_os = "windows")]` blocks will not be processed when `cargo fix`
> runs on Linux (CI). Run the migration locally on a Windows machine, or use a Windows CI runner for
> the fix pass if your codebase has substantial platform-specific code.

### DRY edition configuration

Once all crates in the workspace share the same edition, move it to the workspace manifest:

```toml
# Cargo.toml (workspace root)
[workspace.package]
edition = "2024"
resolver = "3"

# Each crate's Cargo.toml
[package]
edition.workspace = true
```

---

## New Patterns Available

### Precise Capturing with `use<>`

The mechanism behind the RPIT fix above is also a new capability: you can now declare exactly
which lifetimes and type parameters an opaque return type captures, eliminating accidental variance
in library APIs.

```rust
// Precise: captures 'a and T, nothing else
fn items_of<'a, T>(data: &'a [T]) -> impl Iterator<Item = &'a T> + use<'a, T> {
    data.iter()
}
```

This is especially valuable for trait authors — it makes the contract explicit at the definition
site rather than relying on inference.

### Async Closures

Edition 2024 stabilizes `async || {}` closures (stabilized in 1.85). Previously, async closures
required workarounds with `move || async move {}` that had different capture semantics.

```rust
// Before (2021 workaround): awkward capture semantics
let handler = move || async move { fetch_data().await };

// After (2024): direct, captures work as expected
let handler = async || fetch_data().await;

// Practical use — map over a collection of async operations:
let results: Vec<_> = urls.iter()
    .map(async |url| reqwest::get(url).await?.text().await)
    .collect::<FuturesUnordered<_>>()
    .collect()
    .await;
```

### `#[diagnostic::on_unimplemented]` for Library Authors

Customize the compiler error message when a trait is not implemented. Stable since 1.78.

```rust
#[diagnostic::on_unimplemented(
    message = "`{Self}` cannot be used as a sync target",
    label = "must implement `SyncTarget` to participate in pull/push cycles",
    note = "derive `SyncTarget` or implement it manually — see guide-crate-architecture.md"
)]
pub trait SyncTarget: Send + Sync {
    fn sync_key(&self) -> &str;
}
```

### Let-Chains

`if let ... && let ...` chains are stable (1.88+) and available in all editions. They eliminate
nested `if let` pyramids when multiple patterns must match:

```rust
// Before: nested — hard to read, extra indentation
fn process(record: Option<Record>) -> Option<String> {
    if let Some(r) = record {
        if let Status::Active = r.status {
            return Some(r.key.clone());
        }
    }
    None
}

// After: flat — reads as one logical guard
fn process(record: Option<Record>) -> Option<String> {
    if let Some(r) = record && let Status::Active = r.status {
        Some(r.key.clone())
    } else {
        None
    }
}
```

---

## Cargo.toml Changes Summary

```toml
# workspace Cargo.toml
[workspace.package]
edition = "2024"
resolver = "3"          # New default for edition 2024; enables version-aware resolution

# rustfmt.toml (workspace root)
style_edition = "2024"  # Activates 2024 formatting rules; run cargo fmt --all after adding
```

`resolver = "3"` activates the version-aware dependency resolver. It considers `rust-version`
fields when selecting dependency versions — crates can now declare minimum Rust version requirements
that the resolver respects rather than silently building incompatible combinations.

---

## Estimated Effort

| Workspace size | Estimated time | Primary time sink |
|---|---|---|
| 1–2 crates, no `impl Trait` in pub APIs | 1–2 hours | Running the workflow, reviewing tests |
| 4-crate workspace (typical) | 4–6 hours | RPIT review, `if let` guard patterns |
| 10+ crates with complex pub APIs | 1–2 days | Systematic `-> impl` audit, trait impl review |

Most time is spent on RPIT lifetime review and `if let` temporary patterns. The mechanical steps
(`cargo fix`, `cargo fmt`) take minutes. Budget the rest for reading compiler errors and
understanding whether each change preserves intent.
