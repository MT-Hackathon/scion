# Parallelism and Async Patterns Guide

This guide covers the decision framework, patterns, and implementation contracts for parallel work,
channels, bounded async execution, and async/runtime boundaries in this codebase. It answers "which
pattern, and why" for concurrent work execution rather than "what the compiler will accept."

Cross-reference: [guide-connection-state-management.md](guide-connection-state-management.md) covers
shared-state choices, SQLite pooling, lock escalation, and connection lifecycle decisions.

---

## Rayon and CPU Parallelism

### When rayon is right

Rayon is for CPU-bound work over a known collection. The canonical case: analyze N files and want all
cores working simultaneously.

```rust
use rayon::prelude::*;

pub fn analyze_all(paths: &[std::path::PathBuf]) -> Vec<AnalysisResult> {
    paths
        .par_iter()
        .filter_map(|path| analyze_file(path).ok())
        .collect()
}

fn analyze_file(path: &std::path::Path) -> anyhow::Result<AnalysisResult> {
    let content = std::fs::read_to_string(path)?;
    Ok(AnalysisResult {
        path: path.to_owned(),
        line_count: content.lines().count(),
        token_count: content.split_whitespace().count(),
    })
}
```

Rayon's work-stealing scheduler distributes items across a thread pool sized to available cores. You
get near-linear scaling with zero thread management, zero synchronization boilerplate.

### `std::thread::scope` for bounded borrowed tasks

When you have a fixed set of tasks that need to borrow stack-allocated data, `thread::scope` avoids
`Arc` entirely. The scope guarantees all spawned threads complete before the scope returns, so the
borrow checker accepts stack borrows without lifetime annotations.

```rust
fn process_buffer(data: &[u8]) -> (usize, Vec<u8>) {
    std::thread::scope(|s| {
        let count_handle = s.spawn(|| {
            data.iter().filter(|&&b| b > 128).count()
        });
        let transform_handle = s.spawn(|| {
            data.iter().map(|&b| b.wrapping_add(1)).collect::<Vec<_>>()
        });

        let count = count_handle.join().expect("invariant: count thread cannot panic");
        let transformed = transform_handle.join().expect("invariant: transform thread cannot panic");
        (count, transformed)
    })
}
```

Use `thread::scope` when: the number of threads is known at compile time and the data outlives the
scope. The moment threads need to outlive the caller, `Arc` becomes necessary.

### Do not use `spawn_blocking` for heavy CPU work

`tokio::task::spawn_blocking` draws from a bounded thread pool (default: 512 threads). It is designed
for *short* I/O-bound blocking calls — file reads, brief system calls, synchronous library functions
that cannot be made async. Using it for multi-second CPU computation monopolizes those threads and
starves other blocking operations.

```rust
// Correct: short blocking I/O
let config_text = tokio::task::spawn_blocking(|| {
    std::fs::read_to_string("graft-policy.json")
}).await??;

// Correct: CPU-bound work — rayon as the worker, spawn_blocking as the async bridge only
let paths: Vec<std::path::PathBuf> = get_paths();
let results = tokio::task::spawn_blocking(move || {
    paths.par_iter()
        .filter_map(|p| analyze_file(p).ok())
        .collect::<Vec<_>>()
}).await?;

// Wrong: heavy CPU monopolizing a tokio blocking thread
// let _ = tokio::task::spawn_blocking(|| expensive_single_threaded_pass()).await?;
```

The `spawn_blocking` → rayon composition works because rayon has its own thread pool, independent of
tokio's. `spawn_blocking` is just the async-to-sync handoff point; rayon does the parallel work on its
own threads.

---

## Channel Architecture

### Selection guide

| Channel | When to use | Notes |
|---------|-------------|-------|
| `flume` | Production default; throughput not the primary constraint | MPMC; works in sync, async, WASM; most ergonomic |
| `kanal` | Throughput is the constraint | Benchmarks claim 80× over `std::mpsc`; unified sync/async API |
| `tokio::sync::mpsc` | Internal tokio task coordination only | Optimized for the tokio scheduler; not general-purpose |
| `std::sync::mpsc` | Never for new code | Effectively SPSC in practice; not MPMC; weaker performance |

```rust
// flume: MPMC, production default
let (tx, rx) = flume::bounded::<WorkItem>(1024);

// Multiple producers — clone the sender
let tx2 = tx.clone();
std::thread::spawn(move || {
    tx2.send(WorkItem::new()).expect("invariant: receiver not dropped");
});

// Multiple consumers — clone the receiver
let rx2 = rx.clone();
std::thread::spawn(move || {
    for item in rx2.iter() {
        process(item);
    }
});
```

Never use `std::sync::mpsc` for new code. Its name implies multi-producer; its implementation is
effectively single-producer with a mutex on the receiver. Use `flume` instead — it is a drop-in
replacement with correct MPMC semantics and better performance.

### Actor pattern via channel loop

The actor pattern is: one task owns the state, everyone else sends commands. This eliminates lock
contention by eliminating the shared lock. The state is never shared — only messages about it are.

```rust
use tokio::sync::{mpsc, oneshot};
use std::collections::HashMap;

enum CacheCommand {
    Get {
        key: String,
        reply: oneshot::Sender<Option<String>>,
    },
    Set {
        key: String,
        value: String,
    },
    Shutdown,
}

async fn cache_actor(mut rx: mpsc::Receiver<CacheCommand>) {
    let mut store: HashMap<String, String> = HashMap::new();

    while let Some(cmd) = rx.recv().await {
        match cmd {
            CacheCommand::Get { key, reply } => {
                let _ = reply.send(store.get(&key).cloned());
            }
            CacheCommand::Set { key, value } => {
                store.insert(key, value);
            }
            CacheCommand::Shutdown => break,
        }
    }
}

async fn use_cache(tx: &mpsc::Sender<CacheCommand>) -> Option<String> {
    tx.send(CacheCommand::Set {
        key: "config_version".to_string(),
        value: "1.4.2".to_string(),
    }).await.expect("invariant: actor is running");

    let (reply_tx, reply_rx) = oneshot::channel();
    tx.send(CacheCommand::Get {
        key: "config_version".to_string(),
        reply: reply_tx,
    }).await.expect("invariant: actor is running");

    reply_rx.await.expect("invariant: actor replied")
}
```

The actor owns its `HashMap` exclusively. Callers never touch the map — they send typed commands.
No `Arc<Mutex<HashMap>>`, no lock ordering, no contention.

---

## `JoinSet` for Bounded Async Work

`tokio::task::JoinSet` supersedes `FuturesUnordered` for bounded async task sets. It provides
cancellation on drop (tasks abort when the `JoinSet` is dropped), better memory management, and task
naming via the builder API.

```rust
use tokio::task::JoinSet;

async fn fetch_all(urls: Vec<String>) -> Vec<String> {
    let mut set = JoinSet::new();

    for url in urls {
        set.spawn(async move {
            // Each task owns its url — no Arc needed
            reqwest::get(&url)
                .await
                .and_then(|r| r.text().await)
                .unwrap_or_default()
        });
    }

    let mut results = Vec::with_capacity(set.len());
    while let Some(join_result) = set.join_next().await {
        match join_result {
            Ok(text) => results.push(text),
            Err(e) if e.is_cancelled() => {
                // JoinSet was dropped early; task was aborted
            }
            Err(e) => std::panic::resume_unwind(e.into_panic()),
        }
    }
    results
}
```

`FuturesUnordered` still exists and has its place — streaming futures from a generator without a
known bound. For "spawn N tasks, collect results," `JoinSet` is the current standard.

---

## Async/Sync Boundary

The tokio executor runs on a thread pool. Blocking that pool (synchronous I/O, long computation,
`std::sync::Mutex` contention held across a yield point) prevents other tasks from progressing and
can deadlock the runtime.

```
tokio task ──► calls blocking I/O ──► blocks executor thread ──► other tasks starve
```

Push blocking work off the executor thread with `spawn_blocking`:

```rust
// Correct: short blocking I/O via spawn_blocking
let bytes = tokio::task::spawn_blocking(|| {
    std::fs::read("graft-policy.json")
}).await??;
```

**`std::sync::Mutex` vs `tokio::sync::Mutex` in async code**:

- `std::sync::Mutex`: use when the critical section is *synchronous only* — lock, modify, drop the
  guard before any `.await`. This is the common case and the correct default.
- `tokio::sync::Mutex`: use when the critical section *contains `.await` points*. Holding a
  `std::sync::Mutex` guard across an `.await` is a compile error — the guard is not `Send`, which is
  the type system correctly identifying a deadlock risk.

```rust
// Correct: std::sync::Mutex, guard never crosses an .await
async fn update_counter(state: std::sync::Arc<std::sync::Mutex<u64>>) {
    let new_value = fetch_remote_count().await; // async, no lock held

    // Lock acquired synchronously; guard dropped before any further .await
    {
        let mut guard = state.lock().expect("invariant: mutex not poisoned");
        *guard = new_value;
    }
}

// Correct: tokio::sync::Mutex when .await is inside the critical section
async fn update_with_side_effect(state: std::sync::Arc<tokio::sync::Mutex<Cache>>) {
    let mut guard = state.lock().await;
    guard.refresh().await; // .await inside the lock — requires tokio's Mutex
}
```
