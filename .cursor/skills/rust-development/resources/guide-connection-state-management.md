# Connection and State Management Guide

This guide covers the decision framework, patterns, and implementation contracts for shared state,
SQLite access, and lock escalation in this codebase. It answers "which pattern, and why" for
connection and ownership questions rather than "what the compiler will accept."

Cross-reference: [guide-parallelism-async-patterns.md](guide-parallelism-async-patterns.md) covers
concurrent work execution — rayon, channels, `JoinSet`, and the async/sync boundary.

---

## Decision Framework

The concurrency question in Rust is: *what are you sharing, why, and for how long?* That question maps
directly to the pattern. The table below is a decision tree, not a menu.

| Situation | Pattern | Why |
|-----------|---------|-----|
| Shared SQLite database (I/O bound) | `deadpool-sqlite` pool | Concurrent readers; WAL serializes writes; `busy_timeout` prevents surface errors |
| CPU-bound iteration over a collection | `rayon::par_iter()` | Work-stealing; saturates cores; no manual thread management |
| Fixed N tasks that need to borrow stack data | `std::thread::scope` | Scoped threads can borrow without `Arc`; lifetime-safe, no heap overhead |
| Async state shared across tokio tasks | `Arc<tokio::sync::Mutex<T>>` | Async-aware; does not block the tokio executor while waiting |
| Cross-component state, ownership can transfer | `tokio::sync::mpsc` channel | Message is ownership transfer; no lock, no contention |
| High-throughput inter-thread messaging | `kanal` or `flume` | Faster than `std::mpsc`; MPMC support |
| Concurrent hash map | `dashmap` | Sharded locks; stable, balanced, battle-tested |

**The design principle from Firecracker**: prefer channels over shared memory. If you can send the data
instead of sharing it, send it. `Arc<Mutex<T>>` is justified when ownership transfer is genuinely
impossible — that line is a design constraint, not a style preference.

### Narrative by category

**Database** (I/O bound): You want multiple concurrent readers and at most one writer. A connection pool
provides reader concurrency. WAL mode lets SQLite serve readers while a write is in progress. `busy_timeout`
absorbs brief write-lock contention without surfacing `SQLITE_BUSY` to the caller.

**CPU computation**: You want to saturate all cores over a known collection without managing threads
manually. Rayon's work-stealing scheduler does this. It has its own thread pool, independent of tokio,
and needs no async integration.

**Async task coordination**: When tasks exchange data and one is the logical owner, use channels. When
tasks genuinely share state with no clear owner, use `Arc<Mutex<T>>` — the async variant when the
critical section contains `.await` points, `std::sync::Mutex` when it does not.

---

## SQLite Connection Pooling

### Why `deadpool-sqlite`, not the alternatives

Three crates address async SQLite in Rust:

- **`r2d2-rusqlite`** (synchronous): requires `spawn_blocking` wrapping on every call. Aggressively
  closes idle connections, triggering expensive WAL checkpoints. Not suitable for async Tauri commands.
- **`tokio-rusqlite`** (single-connection): wraps one `rusqlite::Connection` behind a background thread
  and a channel. No pool, no concurrent reads. Bottlenecks under any read-heavy workload.
- **`deadpool-sqlite`** (correct for this stack): manages a pool of threads, each owning a synchronous
  `rusqlite::Connection`. Hands out `Object` wrappers that proxy calls through `interact()`. This is the
  correct shape for async Tauri commands — commands are `async` but SQLite is inherently synchronous.

### Pool creation with per-connection PRAGMA configuration

The `post_create` hook runs once per connection when it enters the pool. This is where PRAGMAs belong —
not in command handlers, not in a one-shot init that only reaches the first connection.

```rust
use deadpool_sqlite::{Config, Hook, HookError, Pool, Runtime};
use rusqlite::Connection;

pub async fn create_db_pool(
    db_path: impl AsRef<std::path::Path>,
) -> anyhow::Result<Pool> {
    let cfg = Config::new(db_path);
    let pool = cfg
        .builder(Runtime::Tokio1)?
        .post_create(Hook::async_fn(|obj, _metrics| {
            Box::pin(async move {
                obj.interact(|conn| configure_pragmas(conn))
                    .await
                    .map_err(|e| HookError::message(format!("interact error: {e}")))?
                    .map_err(|e| HookError::message(format!("pragma error: {e}")))?;
                Ok(())
            })
        }))
        .max_size(8) // 4–8 for desktop; web servers with high concurrency need 20–50+
        .build()?;
    Ok(pool)
}

fn configure_pragmas(conn: &Connection) -> rusqlite::Result<()> {
    // WAL: readers and a single writer can run simultaneously
    conn.pragma_update(None, "journal_mode", "WAL")?;
    // NORMAL sync: durable in WAL mode; faster than FULL (which fsyncs on every commit)
    conn.pragma_update(None, "synchronous", "NORMAL")?;
    // Wait 5 s before returning SQLITE_BUSY; absorbs momentary write-lock contention
    conn.pragma_update(None, "busy_timeout", "5000")?;
    // SQLite defaults foreign key enforcement to OFF — this corrects that
    conn.pragma_update(None, "foreign_keys", "ON")?;
    // 256 MB memory-mapped I/O for faster reads on SSD
    conn.pragma_update(None, "mmap_size", "268435456")?;
    // 64 MB page cache (negative value = kilobytes)
    conn.pragma_update(None, "cache_size", "-64000")?;
    // Temp tables in RAM, not disk
    conn.pragma_update(None, "temp_store", "MEMORY")?;
    Ok(())
}
```

**Pool size reasoning**: Desktop apps have bounded concurrency — UI interactions and a handful of
background tasks. 4–8 connections is the sweet spot. Each connection has memory overhead and holds a
WAL slot; never size to "more is better."

### Tauri state management

Initialize the pool once in the Tauri `setup` hook and store it as managed state. Creating a pool
inside a command handler is a correctness error — it creates a new pool on every invocation, each with
its own connections, bypassing the PRAGMA hook and leaking connections.

```rust
use tauri::Manager;

fn main() {
    tauri::Builder::default()
        .setup(|app| {
            let db_path = app
                .path()
                .app_data_dir()?
                .join("graft_runtime.db");

            let pool = tauri::async_runtime::block_on(
                create_db_pool(db_path),
            )?;
            app.manage(pool);
            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("invariant: Tauri application setup must not fail");
}
```

The pool lives for the application lifetime. Sleep/resume is handled gracefully by the OS — SQLite is
a local file, not a network socket. No reconnect logic is needed.

### Command handler pattern

```rust
use deadpool_sqlite::Pool;
use tauri::State;

#[tauri::command]
async fn list_memories(pool: State<'_, Pool>) -> Result<Vec<Memory>, String> {
    let conn = pool.get().await.map_err(|e| e.to_string())?;
    conn.interact(|conn| {
        let mut stmt = conn.prepare(
            "SELECT id, content, created_at FROM memories ORDER BY created_at DESC",
        )?;
        let rows = stmt.query_map([], |row| {
            Ok(Memory {
                id: row.get(0)?,
                content: row.get(1)?,
                created_at: row.get(2)?,
            })
        })?;
        rows.collect::<rusqlite::Result<Vec<_>>>()
    })
    .await
    .map_err(|e| e.to_string())?
    .map_err(|e| e.to_string())
}
```

### Write transactions: `BEGIN IMMEDIATE`

WAL mode allows only one writer at a time. Without `BEGIN IMMEDIATE`, two transactions can both start
as readers (`BEGIN DEFERRED`), then both attempt to escalate to writer simultaneously — each waits for
the other to release, deadlocking. `Immediate` acquires the write lock at transaction start, making the
intent unambiguous from the first statement.

```rust
#[tauri::command]
async fn save_memory(content: String, pool: State<'_, Pool>) -> Result<i64, String> {
    let conn = pool.get().await.map_err(|e| e.to_string())?;
    conn.interact(move |conn| {
        let tx = conn.transaction_with_behavior(
            rusqlite::TransactionBehavior::Immediate,
        )?;
        tx.execute(
            "INSERT INTO memories (content, created_at) VALUES (?1, datetime('now'))",
            rusqlite::params![content],
        )?;
        let id = tx.last_insert_rowid();
        tx.commit()?;
        Ok::<i64, rusqlite::Error>(id)
    })
    .await
    .map_err(|e| e.to_string())?
    .map_err(|e| e.to_string())
}
```

---

## Lock Escalation Ladder

Start at zero. Escalate only when the invariant demands it. Each step adds complexity and contention
surface.

| Level | Mechanism | When justified |
|-------|-----------|----------------|
| 0 | No shared state | Data owned by one task; passed by value or moved |
| 1 | Message channels (`flume`, `mpsc`) | Data can transfer ownership; actor pattern |
| 2 | `Arc<T>` (immutable) | Read-only data built once, accessed by many |
| 3 | `Arc<RwLock<T>>` | Mostly reads, rare writes; readers are numerous and brief |
| 4 | `Arc<Mutex<T>>` | Reads and writes equally mixed; critical section is brief |
| 5 | `deadpool-sqlite` / external pool | I/O resource with its own built-in contention semantics |
| 6 | `dashmap` | High-frequency concurrent map access where sharded locking beats a single `Mutex<HashMap>` |

Starting at level 4 because it "feels safe" skips levels with zero contention. The goal is the lowest
level that satisfies the invariant.

**`RwLock` pitfall**: Read locks are not free. Most implementations use write-preferring policy — if
a writer is waiting, subsequent readers block behind it. In a write-heavy workload, `RwLock` performs
*worse* than `Mutex` because every writer has to wait for all readers to clear, then blocks all new
readers. Profile before choosing `RwLock` over `Mutex`.

---

## Crate Versions (Q1 2026)

| Crate | Version | Notes |
|-------|---------|-------|
| `deadpool-sqlite` | 0.9.x | Tracks deadpool 0.12; verify crates.io for latest |
| `rayon` | 1.10.x | Stable |
| `flume` | 0.11.x | Stable |
| `kanal` | 0.1.x | Production-ready; verify before adopting |
| `dashmap` | 6.x | Stable |
| `tokio` | 1.x | Stable |

All additions require clearance through `reference-crate-catalog.md` before use in this codebase.
