# Allocation Patterns Guide

This guide covers allocation discipline, string type selection, collection optimization, iterator
patterns, and zero-copy data shape decisions. Each section teaches the mechanism — not just "use this
instead of that," but why the substitution changes performance.

Cross-reference: [guide-profiling-optimization.md](guide-profiling-optimization.md) covers how to
measure these choices with benchmarks, memory profilers, and PGO.

---

## Allocation Discipline: The Mental Model

Every allocation is a contract: memory is requested from the allocator, used, and returned. Each
step has a cost. The allocator must find a free block (or ask the OS for more), zero or initialize
it, track the address, and later coalesce it back into the free list. On hot paths called millions
of times, this overhead compounds.

**The goal**: allocate once per logical object, not once per operation on that object. Stack
allocation (local variables, function arguments, fixed-size arrays) is free — the stack pointer
moves and that's it. Heap allocation is never free.

**The three questions to ask before reaching for `String` or `Vec<T>`**:
1. Do I need to *own* this data, or can I borrow it?
2. Does this data grow after creation, or is it built once?
3. Is this data large or small? Can it fit in a fixed-size inline buffer?

Each of these has a type that answers it.

---

## String Type Decision Tree

```
Does the function need to store or outlive the call?
│
├── No → &str (zero allocation; just a pointer + length)
│
└── Yes — does the string USUALLY come in borrowed but OCCASIONALLY need to be owned?
    │
    ├── Yes → Cow<'_, str> (defers allocation to the case that needs it)
    │
    └── No — is the string built once and never grown?
        │
        ├── Yes → Box<str> (saves 8 bytes vs String; no capacity field)
        │
        └── No → String (owned, growable; correct for builder patterns and mutation)
```

**For hot-path string storage where most strings are short** (≤ 23 bytes): `compact_str` stores
short strings inline — no heap allocation. Falls back to heap transparently for longer strings.

### Size comparison (64-bit platform)

```rust
use std::mem::size_of;
use std::borrow::Cow;

fn print_sizes() {
    println!("&str:          {} bytes", size_of::<&str>());       // 16 (ptr + len)
    println!("String:        {} bytes", size_of::<String>());     // 24 (ptr + len + cap)
    println!("Box<str>:      {} bytes", size_of::<Box<str>>());   // 16 (ptr + len, no cap)
    println!("Cow<'_, str>:  {} bytes", size_of::<Cow<'_, str>>()); // 32 (enum over the above)
}
```

### `&str` — zero allocation, transient data

```rust
// Correct: parsers, short-lived lookups, read-only views
fn find_section<'a>(config: &'a str, name: &str) -> Option<&'a str> {
    config.lines()
        .find(|line| line.starts_with(name))
}
```

Accept `&str` at function boundaries (not `&String`) to keep callers flexible — a `&String`
coerces to `&str`, but not vice versa.

### `Cow<'_, str>` — deferred allocation

`Cow<'_, str>` is an enum: `Borrowed(&str)` or `Owned(String)`. Use it when data is *usually*
borrowed but *occasionally* needs modification. Allocation only occurs in the owned case.

```rust
use std::borrow::Cow;

// Sanitizes input: borrows if clean, allocates only if it must modify
fn sanitize(input: &str) -> Cow<'_, str> {
    if input.contains('<') || input.contains('>') {
        Cow::Owned(
            input
                .replace('<', "&lt;")
                .replace('>', "&gt;"),
        )
    } else {
        Cow::Borrowed(input) // no allocation
    }
}

fn process(raw: &str) {
    let clean = sanitize(raw);
    // clean is &str in the common case; String only when HTML chars found
    store_value(&clean);
}
```

At function boundaries where callers might pass either borrowed or owned data:

```rust
// Accepts &str, String, Cow — caller pays nothing if they have a &str
fn normalize(s: impl Into<Cow<'static, str>>) -> Cow<'static, str> {
    let s = s.into();
    if s.chars().all(|c| c.is_lowercase()) {
        s
    } else {
        Cow::Owned(s.to_lowercase())
    }
}
```

### `Box<str>` — immutable owned data, minimum footprint

`String` stores `(ptr, len, capacity)` = 24 bytes. The capacity field is used only when the
string grows. For data that is built once and never mutated, that field is pure overhead.

`Box<str>` stores `(ptr, len)` = 16 bytes — a 33% reduction per string. On datasets with thousands
of strings, this is meaningful. rust-analyzer reports 15–20% heap savings on symbol-heavy datasets
using this pattern.

```rust
// Building a fixed string table — never appended to after construction
fn build_symbol_table(source: &str) -> Vec<Box<str>> {
    source
        .lines()
        .map(|line| line.trim().to_string().into_boxed_str())
        .collect()
}

// Struct field: owned, immutable, minimum footprint
struct CachedPath {
    display: Box<str>,     // 16 bytes
    canonical: Box<str>,   // 16 bytes
}
// vs using String: 24 + 24 = 48 bytes per struct; Box<str>: 16 + 16 = 32 bytes
```

### `compact_str` — inline small strings

For hot-path storage where strings are usually short:

```rust
use compact_str::CompactString;

// Stores strings ≤ 23 bytes inline (no heap allocation)
// Falls back to heap transparently for longer strings
struct Tag {
    name: CompactString,
}

fn build_tags(names: &[&str]) -> Vec<Tag> {
    names.iter()
        .map(|&name| Tag { name: CompactString::from(name) })
        .collect()
}
```

**AVOID `beef` crate**: Last release May 2022. Documented soundness bugs in issues [#7](https://github.com/maciejhirsz/beef/issues/7) and [#37](https://github.com/maciejhirsz/beef/issues/37) — missing `Sync` bound enabling data races. Use `compact_str` or `smol_str` instead.

---

## `Box<[T]>` — Immutable Owned Slices

The same principle as `Box<str>` applies to slices. `Vec<T>` stores `(ptr, len, capacity)` = 24
bytes. `Box<[T]>` stores `(ptr, len)` = 16 bytes. For collections built once and never grown:

```rust
fn load_forbidden_paths() -> Box<[std::path::PathBuf]> {
    // Read config, parse paths, collect into a slice
    let paths: Vec<std::path::PathBuf> = read_config_paths();
    paths.into_boxed_slice() // drops the capacity field
}

// Struct field: a fixed list that never changes after construction
struct PolicySet {
    allowed_extensions: Box<[Box<str>]>,
}
```

`into_boxed_slice()` is the idiomatic conversion from `Vec<T>`. The resulting `Box<[T]>` is
`Deref<Target = [T]>` — it works everywhere a slice reference is accepted.

---

## SmallVec and Small-Buffer Optimization

When a collection has ≤ N items in the vast majority of cases, `SmallVec` stores those items inline
on the stack, avoiding heap allocation for the common path.

```rust
use smallvec::SmallVec;

// Tags are usually 1–4; avoids heap allocation in that case
fn collect_tags(input: &str) -> SmallVec<[&str; 4]> {
    input.split(',').map(str::trim).collect()
}
```

**Sizing rule**: the inline buffer should be ≤ 128 bytes total. Beyond that, stack-copying the
buffer on moves costs more than the heap allocation you avoided. A `SmallVec<[u64; 16]>` has a
128-byte inline buffer — reasonable. A `SmallVec<[String; 20]>` has a 480-byte inline buffer —
too large; the move cost dominates.

**Safety trade-off**: `smallvec` uses `unsafe` internally for the union storage. In
security-sensitive contexts, use `tinyvec` instead — 100% safe Rust, but requires `Default` on
the element type.

```rust
use tinyvec::TinyVec;

// 100% safe; items must implement Default
fn collect_ids(source: &[u32]) -> TinyVec<[u32; 8]> {
    source.iter().copied().collect()
}
```

---

## Iterator Chains: Fusion and the "Don't Collect Early" Rule

The Rust compiler (rustc 2025+) aggressively fuses `.map()` and `.filter()` chains into single
loops with no intermediate allocation. A chain of five `.map().filter().map()` calls produces one
loop that touches each element once.

```rust
// This is ONE pass, not three — the compiler fuses the chain
fn process(items: &[Item]) -> Vec<Processed> {
    items.iter()
        .filter(|item| item.is_active())
        .map(|item| item.normalize())
        .filter(|norm| norm.score > 0.5)
        .map(|norm| Processed::from(norm))
        .collect() // allocation happens once, here
}
```

**Collecting early** breaks fusion:

```rust
// Wrong: intermediate Vec<_> allocated and immediately discarded
fn process_badly(items: &[Item]) -> Vec<Processed> {
    let active: Vec<_> = items.iter()
        .filter(|item| item.is_active())
        .collect(); // unnecessary allocation

    active.iter()
        .map(|item| Processed::from(item))
        .collect()
}
```

**When collecting IS correct**:
1. You need to iterate the result multiple times.
2. You need to pass it to a function requiring a concrete type (`Vec<T>`, `&[T]`).
3. You need to branch on the result or examine `.len()` before iterating.
4. The iterator is infinite or lazy-evaluated and you need all values now.

```rust
// Correct: must branch, must examine len
let results: Vec<_> = items.iter().map(process).collect();
if results.len() < MINIMUM {
    return Err(InsufficientResults);
}
for r in &results { // iterated twice: once above implicitly, once here
    emit(&r);
}
```

---

## Zero-Copy Deserialization

When deserializing from a string or byte buffer you already own, serde can borrow string fields
directly from the source — no allocation per string field.

```rust
#[derive(serde::Deserialize)]
struct Config<'a> {
    name: &'a str,           // borrows from the input buffer
    description: &'a str,
    tags: Vec<&'a str>,
}

fn parse_config(json: &str) -> anyhow::Result<Config<'_>> {
    Ok(serde_json::from_str(json)?)
    // Config::name, description, tags point into `json` — zero allocation
}
```

**Limitation**: zero-copy only works with `from_str` (borrows `&str`) or `from_slice` (borrows
`&[u8]`). It does not work with `from_reader` — the reader owns its buffer, so the borrow would
outlive it. If you need to deserialize from a reader, read to a `String` first, then deserialize
from `&str`.

**When not to use it**: if the parsed data must outlive the source buffer, you need owned fields
(`String`, `Vec<String>`). The lifetime parameter makes this explicit — the compiler will reject
code that tries to return a zero-copy struct after the source is dropped.

---

## AVOID

**`beef` crate**: Do not use. Last release May 2022. Documented soundness bugs in issues [#7](https://github.com/maciejhirsz/beef/issues/7) and [#37](https://github.com/maciejhirsz/beef/issues/37) — the crate is missing a `Sync` bound, enabling data races when `Cow`-wrapped data is shared across threads. Use `compact_str` or `smol_str` instead for inline small-string storage; use `std::borrow::Cow` for the borrow-or-own pattern.

**Premature optimization**: profile before optimizing. A `Box<str>` refactor that saves 8 bytes per
string is meaningless if those strings are allocated 100 times per session and your actual bottleneck
is a 50 ms SQLite query. Use `samply` to confirm where time goes before changing string types.
`cargo-flamegraph` is an alternative for a quick visual first look.

**Collecting iterators unnecessarily**: do not `.collect()` into a `Vec<T>` just to immediately
`.iter()` over it again. The intermediate `Vec` is pure overhead — an allocation that breaks the
compiler's loop fusion. Pass iterators where iterators are accepted. Collect once at the end when
you must materialize the result.

**`unwrap()` in benchmarks**: `unwrap()` adds a branch. In tight loops this is measurable. In
benchmark harnesses where the path always succeeds, consider `expect()` with an invariant message,
or restructure the bench to set up the happy path outside the `bench` closure.
