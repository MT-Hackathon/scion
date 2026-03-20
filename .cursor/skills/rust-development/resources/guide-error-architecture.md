# Error Architecture Guide — Rust

## Design Philosophy

The primary design question for any error type is not "what went wrong?" but **"what should the caller do?"** That question determines the type, the variant names, and the fields.

`DatabaseError` tells the caller nothing. `RetryableStorageError` signals the caller may retry. `FatalConfigurationError` signals immediate abort. The name is the contract; the caller's branch logic should read directly from it without inspecting internal fields.

Errors are interface contracts, not implementation details. A public error type that exposes internal module structure (e.g., `SqlxError(sqlx::Error)`) couples callers to your implementation choices. Wrap at the boundary; expose what the caller needs.

---

## The Four-Layer Model

Each crate in this ecosystem is a different kind of code. The error tool must match the layer.

| Layer | Tool | Purpose |
|---|---|---|
| Domain type definition | `thiserror` | Machine-readable error variants with structured fields. Used in library crates and module-level error enums. |
| Structured context | `error-stack` | Attach programmatically-queryable metadata at call sites without losing type information. Application logic layer. |
| Human-readable reporting | `miette` | Terminal colors, error codes, help text, source spans. CLI binary's `main` and test output. |
| Quick aggregation | `anyhow` | Collects heterogeneous errors in application binaries where the caller only needs to propagate, not branch. Never in library crates. |

These are not competitors. `thiserror` defines the type; `error-stack` adds context while carrying it; `miette` renders it. They compose.

---

## thiserror: Domain Error Design

One enum per logical domain, not one enum for the whole crate.

```rust
// Good: storage domain owns its own error type
#[derive(Debug, thiserror::Error)]
pub enum StorageError {
    #[error("record not found: {id}")]
    NotFound { id: String },

    #[error("write failed — disk may be full")]
    #[from]
    Io(#[source] std::io::Error),

    #[error("serialization failed")]
    Serialize(#[from] serde_json::Error),
}

// Bad: one monolithic type for the whole crate
#[derive(Debug, thiserror::Error)]
pub enum Error {
    Storage(StorageError),
    Config(ConfigError),
    // ...every module piled in here
}
```

**`#[from]` vs `#[source]`**: Use `#[from]` when the conversion is automatic and lossless — the variant becomes `impl From<SourceError> for YourError` automatically. Use `#[source]` alone when you need to add fields alongside the wrapped error.

```rust
#[derive(Debug, thiserror::Error)]
pub enum SyncError {
    // Automatic From<io::Error> conversion, source preserved in chain
    #[error("file access failed during sync")]
    Io(#[from] std::io::Error),

    // Manual construction needed — adds context fields alongside the source
    #[error("conflict at path {path}: {source}")]
    Conflict {
        path: PathBuf,
        #[source]
        source: StorageError,
    },
}
```

**Error message language**: Describe the situation, not the operation.
- Bad: `"failed to read file"` — describes the operation
- Good: `"config file missing or unreadable"` — describes the situation the caller faces
- Good: `"write failed — disk may be full"` — describes the situation and suggests a cause

**When to add fields vs use a string**: Add structured fields when the caller might branch on the value. Use a string when the value is only for human display. If you find yourself formatting a path into a string, make it a `PathBuf` field.

---

## error-stack: Structured Context at Application Layer

`anyhow::Context` attaches strings to errors. Those strings cannot be queried programmatically. `error-stack` attaches typed metadata that survives the propagation chain.

```rust
use error_stack::{Report, ResultExt};

#[derive(Debug)]
struct RequestMetadata {
    request_id: String,
    user_id: Option<String>,
}

fn handle_request(id: &str) -> Result<Response, Report<StorageError>> {
    fetch_record(id)
        .attach(RequestMetadata {
            request_id: id.to_string(),
            user_id: None,
        })
        .attach_printable(format!("while handling request for id={id}"))
}
```

The `Report<E>` carries both the original typed error and all attachments. Attachments survive `.change_context()`:

```rust
fn orchestrate() -> Result<(), Report<OrchestratorError>> {
    handle_request("abc-123")
        .change_context(OrchestratorError::RequestFailed)?;
    Ok(())
}
```

**Querying in tests**: `report.request_ref::<RequestMetadata>()` retrieves the first attached value of that type. This lets tests assert that the right context was attached at the right layer:

```rust
let err = handle_request("missing-id").unwrap_err();
let metadata = err.request_ref::<RequestMetadata>().unwrap();
assert_eq!(metadata.request_id, "missing-id");
```

**For library code**: still use `thiserror`. `error-stack` is for application logic where you need to build context as a call propagates up through multiple layers. Do not return `Report<E>` from a public library API — it couples callers to `error-stack`.

---

## WireError: Serialization Boundary Pattern

Domain error types often contain non-serializable fields (`std::io::Error`, `Box<dyn Error>`, etc.). They cannot cross a serialization boundary directly — whether that's Tauri IPC, a REST response, or an RPC call.

Define a `WireError` that implements `serde::Serialize`:

```rust
#[derive(Debug, serde::Serialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
pub struct WireError {
    pub code: &'static str,
    pub message: String,
    pub detail: Option<serde_json::Value>,
}

impl From<StorageError> for WireError {
    fn from(e: StorageError) -> Self {
        match e {
            StorageError::NotFound { id } => WireError {
                code: "NOT_FOUND",
                message: format!("record '{id}' does not exist"),
                detail: None,
            },
            StorageError::Io(io) => WireError {
                code: "IO_ERROR",
                message: "storage operation failed".to_string(),
                detail: Some(serde_json::json!({ "os_error": io.raw_os_error() })),
            },
            StorageError::Serialize(_) => WireError {
                code: "SERIALIZATION_ERROR",
                message: "data encoding failed".to_string(),
                detail: None,
            },
        }
    }
}
```

Commands at the boundary return `Result<T, WireError>`, not `Result<T, DomainError>`:

```rust
// Tauri command
#[tauri::command]
pub async fn fetch_record(id: String) -> Result<Record, WireError> {
    storage::fetch(&id).map_err(WireError::from)
}

// REST handler (same pattern, different framework)
pub async fn get_record(id: String) -> Result<Json<Record>, Json<WireError>> {
    storage::fetch(&id)
        .map(Json)
        .map_err(|e| Json(WireError::from(e)))
}
```

**Tauri + specta**: When `feature = "specta"` is enabled, `tauri-specta` generates a TypeScript interface for `WireError` automatically. The frontend receives a typed `{ code: string, message: string, detail: Record<string, unknown> | null }` — no guess-work about error shape.

The `WireError` pattern applies to **any** serialization boundary. The Tauri / specta derivation is Tauri-specific, but the separation of domain types from wire types is universal.

---

## miette: Human-Readable Reporting for CLIs

`miette` is a reporting layer, not an error type system. It adds terminal formatting on top of your existing error types.

```toml
[dependencies]
thiserror = "2"
miette = { version = "7", features = ["fancy"] }
```

Derive `Diagnostic` on errors that will be presented to users:

```rust
#[derive(Debug, thiserror::Error, miette::Diagnostic)]
pub enum CliError {
    #[error("config file not found at {path}")]
    #[diagnostic(
        code(graft::config::not_found),
        help("run `graft init` to create a default config, or set GRAFT_CONFIG")
    )]
    ConfigNotFound { path: PathBuf },

    #[error("sync failed")]
    #[diagnostic(code(graft::sync::failed))]
    SyncFailed(#[from] SyncError),
}
```

Use `miette::Result` in `main` to get formatted output automatically:

```rust
fn main() -> miette::Result<()> {
    run().map_err(|e| miette::Report::new(e))?;
    Ok(())
}
```

The `fancy` feature enables ANSI colors and box-drawing in terminals that support them. `miette` detects `NO_COLOR` and non-TTY output automatically.

**Source spans**: When the error references user-provided input (a config file, a command argument), attach a `SourceSpan` so `miette` can highlight the offending byte range in terminal output. See miette docs for `#[label]` and `SourceCode`.

---

## SNAFU: Call-Site Context for Complex Domains

`thiserror` defines error context at the *type definition*. When multiple call sites produce the same error variant but need different context, thiserror creates pressure to add more variants to carry that context.

`SNAFU`'s selector pattern forces context definition at the *call site*:

```rust
#[derive(Debug, snafu::Snafu)]
pub enum PolicyError {
    #[snafu(display("policy {name} rejected operation: {reason}"))]
    PolicyRejected { name: String, reason: String, source: StorageError },
}

fn evaluate(name: &str) -> Result<(), PolicyError> {
    let record = storage::load(name).context(PolicyRejectedSnafu {
        name: name.to_string(),
        reason: "record not accessible".to_string(),
    })?;
    // ...
}
```

Reach for SNAFU when:
- The same error variant needs meaningfully different context across call sites
- You're building a library used by projects like `polars` or `iroh` where error ergonomics are primary surface area
- The number of thiserror variants is growing to accommodate per-call-site context rather than per-domain semantics

SNAFU is a complement to thiserror for complex domains, not a replacement for simple ones.

---

## `try` Blocks: Scoped Error Propagation

> **Status (March 2026):** `try { }` blocks require `#![feature(try_blocks)]` — still unstable. Tracking issue: [rust-lang/rust #31436](https://github.com/rust-lang/rust/issues/31436). Do not use in production crates on stable toolchain.

Allows `?` to propagate within a block scope rather than exiting the enclosing function:

```rust
let result: Result<ProcessedRecord, StorageError> = try {
    let raw = storage::load(id)?;        // ? exits the try block, not the function
    let validated = validate(raw)?;
    transform(validated)?
};

match result {
    Ok(record) => produce(record),
    Err(e) => log_and_skip(e),
}
```

Use `try` blocks when you need to handle a group of fallible operations as a unit within a larger function, without extracting them to a named helper. The extracted-helper approach is still preferred when the block has a clear semantic identity; `try` is for inline scoping where a name would be arbitrary.

---

## Panic Discipline

| Construct | When to use |
|---|---|
| `unwrap()` | Never in production paths. Only in test bodies or examples where a panic is acceptable. |
| `expect("invariant: <reason>")` | States that are *provably unreachable* from correct usage. The message states the invariant, not the operation. |
| `debug_assert!` | Internal invariants that are expensive to check. Compiled away in release builds. |
| `assert!` | External or security invariants that must hold in production. Compiled into release builds. |
| `unreachable!("invariant: <reason>")` | Match arms the type system cannot prove exhausted but business logic guarantees cannot be reached. |

**Message format**:
```rust
// Bad: describes the operation
channel.send(msg).expect("send failed");

// Good: states the invariant
channel.send(msg).expect("invariant: receiver alive for lifetime of producer");
```

If you cannot state a clear invariant, the panic is not justified — return `Result` instead. The question "what invariant does this protect?" is the test.

`debug_assert!` is appropriate for internal loop invariants where the check would materially affect performance. `assert!` is appropriate where the failure represents a security or correctness invariant that must hold even under adversarial input.

---

## Error Testing

**Snapshot testing with `insta`**: Captures `Debug`/`Display` output and fails if it changes. Prevents silent error message regressions:

```rust
#[test]
fn storage_error_display() {
    let e = StorageError::NotFound { id: "test-id".to_string() };
    insta::assert_snapshot!(e.to_string());
}
```

**Variant matching with `assert_matches!`** (std, stable): Checks the error variant without exhaustively matching all fields:

```rust
use std::assert_matches::assert_matches;

let result = fetch_record("nonexistent");
assert_matches!(result, Err(StorageError::NotFound { id }) if id == "nonexistent");
```

**Testing error-stack attachments**: Use `request_ref` to assert that specific context was attached:

```rust
let report = handle_request("req-999").unwrap_err();

// Assert the domain error type
assert!(report.contains::<StorageError>());

// Assert structured context was attached
let meta = report.request_ref::<RequestMetadata>().unwrap();
assert_eq!(meta.request_id, "req-999");
```

**Test the error contract, not the implementation**: Tests should assert on the error *variant and fields* that callers depend on, not on internal message strings (use snapshots for those). If a test hardcodes a `.to_string()` comparison without insta, it will break on any message wording change that has no semantic impact.
