---
name: memory-embeddings
description: Read before implementing or modifying local vector embeddings — encodes model selection for March 2026, fastembed-rs API patterns, Windows runtime gotchas, cross-system compatibility with the central GPU server, RRF hybrid scoring design, and graceful degradation. Skipping this means re-deriving the same research under time pressure.
---

# Memory Embeddings & Local Inference

Institutional knowledge for implementing and maintaining local embedding inference within the Rootstock memory system. Vectors generated locally must be compatible with the central Ubuntu GPU server — this constraint shapes every architectural decision here.

## Table of Contents

- [Core Principles](#core-principles)
- [Embedding Purposes](#embedding-purposes)
- [Model Selection (March 2026)](#model-selection-march-2026)
- [Library: fastembed-rs](#library-fastembed-rs)
- [Windows Runtime Constraints](#windows-runtime-constraints)
- [Storage Schema](#storage-schema)
- [Write Path](#write-path)
- [Query Path and Hybrid Scoring](#query-path-and-hybrid-scoring)
- [Cross-System Compatibility](#cross-system-compatibility)
- [Model Versioning and Migration](#model-versioning-and-migration)
- [Graceful Degradation](#graceful-degradation)
- [Scope](#scope)

## Core Principles

1. **Model parity is absolute.** Embeddings are model-specific. A vector from Model A cannot be compared to a vector from Model B. Local and central instances MUST use the same model identifier.
2. **Inference never blocks the caller.** Embedding generation is a background side-effect of writes, not a gate. The MCP response returns before the embedding is generated.
3. **Degradation is silent.** If the embedding model is absent, inference fails, or the model_id mismatches, the system falls back to FTS + activation ranking without surfacing an error to the caller.

## Embedding Purposes

| Purpose | What | Model | When |
| ------- | ---- | ----- | ---- |
| 1. Query-time similarity | Memory retrieval via RRF | BGE-Small-EN | Every get_context/search_memory |
| 2. Offline enrichment | Clustering, contradiction, crystallization | BGE-M3 (hot-path), Nomic (GPU) | Background after each write |
| 3. Semantic routing | Knowledge artifact routing | BGE-Small + BGE-M3 | Tool calls that route to skills/rules |
| 4. Cross-domain A-Mem | Memory ↔ Knowledge similarity | BGE-Small | On write_memory, on knowledge re-index |

## Model Selection (March 2026)

**Shipped model (verified working):** `BGESmallENV15Q` → `model_id = "bge-small-en-v1.5-int8"`, 384 dims, INT8, ~24MB.

This is the canonical model_id stored in `memory_vectors`. ogham-1 and every other instance **must use the same model_id** for embedding space parity. If ogham-1 uses a different model, its vectors are incompatible with local queries and Turso sync will produce silent retrieval degradation.

### Compute Profile

The system uses a tiered `ComputeProfile` to balance latency and depth:

| Tier | Profile | Model | Dims | Role |
|---|---|---|---|---|
| **Hot Path** | `query_time` | BGE-Small-EN-V1.5 | 384 | 5-15ms CPU latency; query-time retrieval |
| **Enrichment** | `enrichment_embeddings` | BGE-M3 | 1024 | Multilingual, long-context (8192); background clustering |
| **GPU Deep** | `enrichment_embeddings` | Nomic-Embed-Text-V2-MoE | 768 | High-density retrieval; offline enrichment (ogham-1 only) |

Candidates evaluated (March 2026), all INT8 ONNX, 384 dims. The enum changes between minor releases — verify membership at build time, not from documentation:

| Model | `model_id` string | Dims | MTEB Retrieval | Context | fastembed 5.13.0 enum |
|---|---|---|---|---|---|
| GTE-ModernBERT-Small | `gte-modernbert-small-int8` | 384 | 58.0 | 8192 | Not present (March 2026) |
| Snowflake Arctic-XS | `snowflake-arctic-xs-int8` | 384 | 50.15 | 512 | Present in 5.13.0 |
| BGE-Small-EN-V1.5 | `bge-small-en-v1.5-int8` | 384 | ~48 | 512 | **Present — `EmbeddingModel::BGESmallENV15Q`** |
| all-MiniLM-L6-v2 | — | 384 | lower | 256 | Present — DO NOT USE, superseded |

Use the highest-MTEB model that is actually present in the installed enum. Do not assume a model is available from documentation alone — check the enum at build time. BGE-Small-EN-V1.5 is the confirmed fallback when GTE and Arctic-XS are absent.

**Do not use:**
- `nomic-embed-v1.5` — 130MB unquantized, too large for local CPU deployment
- Any model not available as an INT8 ONNX preset in fastembed-rs — custom ONNX loading adds maintenance surface

## Library: fastembed-rs

Use `fastembed-rs` (wraps `ort` / ONNX Runtime). Do NOT use `candle` — it is 2–5× slower than ort on CPU for BERT-style encoders due to ort's Intel/Microsoft kernel optimizations (OpenMP, MKL-DNN).

**Working Cargo.toml (verified fastembed 5.13.0 / ort 2.0.0-rc.11, March 2026):**

```toml
# The "ort" feature does NOT exist in fastembed v4. Use these exact feature names.
# Pin both packages — minor releases break the feature surface and version compatibility.
fastembed = { version = "=5.13.0", default-features = false, features = ["online", "ort-load-dynamic"] }
ort = { version = "=2.0.0-rc.11", features = ["load-dynamic"] }
```

**Initialization (fastembed v5 builder API):**

```rust
// v5 uses TextInitOptions for the builder pattern
let options = fastembed::TextInitOptions::new(fastembed::EmbeddingModel::BGESmallENV15Q)
    .with_cache_dir(app_data_dir.join("models"))
    .with_show_download_progress(false);
// Note: no thread-count setter exists in 5.13.0 API surface.
// ONNX Runtime thread count is controlled at the ort level, not fastembed level.

let model = fastembed::TextEmbedding::try_new(options)?;

// Embedding — returns Vec<Vec<f32>>, one inner Vec per input string
let embeddings: Vec<Vec<f32>> = model.embed(vec!["text to embed"], None)?;
// Note: embed() takes Vec<impl AsRef<str>> in v5
```

Tokenization is handled internally by fastembed-rs — do not pre-process the input text.

## Windows Runtime Constraints

Three rules, all required:

1. **Thread limit.** ONNX Runtime defaults to all CPU cores. In a Tauri GUI app this starves the UI thread and causes visible stutter. As of fastembed 4.9.1, there is **no thread-count setter in the `InitOptions` builder API** — this must be controlled at the `ort` session level if needed (advanced). The performance impact at typical memory corpus sizes (<10k memories) is acceptable without thread limiting.

2. **Dynamic linking.** Use `ort` with `load-dynamic` feature. Bundle `onnxruntime.dll` alongside the Tauri executable. Static linking adds ~15MB to the binary and causes conflicts with any other ort consumer in the process.

3. **Model file location.** Store model weights in `app_data_dir()/models/`. Do NOT bundle weights in Tauri `resources/` — Windows Defender's real-time scanner inspects resources on extraction, causing multi-second first-launch latency. Use `.with_cache_dir(app_data_dir.join("models"))` in the builder to control the download location explicitly.

## Storage Schema

```sql
CREATE TABLE IF NOT EXISTS memory_vectors (
    memory_id    TEXT NOT NULL,
    model_id     TEXT NOT NULL,    -- e.g., "gte-modernbert-small-int8", "snowflake-arctic-xs-int8"
    embedding    BLOB NOT NULL,    -- raw f32 little-endian bytes: 384 dims × 4 bytes = 1536 bytes
    generated_at TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (memory_id, model_id),
    FOREIGN KEY (memory_id) REFERENCES memories(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_memory_vectors_memory_id ON memory_vectors(memory_id);
```


**Serialization (store):**
```rust
let bytes: Vec<u8> = embedding.iter().flat_map(|f| f.to_le_bytes()).collect();
```

**Deserialization (load):**
```rust
let floats: Vec<f32> = bytes.chunks_exact(4)
    .map(|c| f32::from_le_bytes(c.try_into().unwrap()))
    .collect();
```

Storage size: 384 dims × 4 bytes = 1,536 bytes/memory. At 10,000 memories → ~15MB stored, ~15MB in RAM when full corpus is loaded for cosine search.

## Write Path

The caller must never wait for embedding generation:

```
write_memory() ──► INSERT memories ──► return OK to MCP caller
                        │
                        └──► push (memory_id, claim_text) to mpsc::Sender (non-blocking)

                   background worker (single tokio task, consuming Receiver)
                        │
                   model.embed(vec![claim_text])   // 5–15ms on CPU
                        │
                   INSERT or REPLACE memory_vectors
                        │
                   on error: WARN log, no retry (stale detection handles it later)
```

**Enrichment Pipeline**: In addition to the query-time embedding above, the enrichment pipeline (`store_enrichment_embeddings`) runs BGE-M3 + Nomic on every memory write in the background via the same mpsc pattern. These high-density vectors are used for offline clustering and contradiction analysis.

`RerankerBackend` trait is defined in `src-tauri/src/reranker.rs` — implementation pending.

**Burst protection**: a single `tokio::sync::mpsc` channel with one consumer. N concurrent `write_memory` calls queue their embed requests; only one ONNX call runs at a time. This prevents CPU saturation from concurrent inference.

**Re-embed trigger**: `supersede_memory` changes claim text → push to embed queue. `tag_memory` does NOT trigger re-embed (tags don't affect the claim embedding).

## Query Path and Hybrid Scoring

Three parallel ranking channels merged via Reciprocal Rank Fusion (k=60):

```
RRF(d) = 1/(60 + rank_activation(d)) + 1/(60 + rank_fts(d)) + 1/(60 + rank_vector(d))
```

k=60 is the standard constant from the RRF literature — it prevents high-ranked documents from dominating. Make it DB-configurable via the 0.2.6 config pass.

**RRF is naturally resilient to missing channels.** If the vector channel is absent, it contributes 0 to every document and the remaining two channels determine ranking. No special-casing.

**Cosine similarity implementation:**
```rust
fn cosine_similarity(a: &[f32], b: &[f32]) -> f32 {
    let dot: f32 = a.iter().zip(b).map(|(x, y)| x * y).sum();
    let norm_a: f32 = a.iter().map(|x| x * x).sum::<f32>().sqrt();
    let norm_b: f32 = b.iter().map(|x| x * x).sum::<f32>().sqrt();
    if norm_a == 0.0 || norm_b == 0.0 { 0.0 } else { dot / (norm_a * norm_b) }
}
```

For future optimization at >1,000 memories: `rayon::par_iter()` for parallel cosine computation. At 10,000 memories with plain iteration the computation is still <5ms.

**Integration with existing Phase 2 Ogham features**: Kind multipliers and tag bonus apply AFTER RRF merge, on the final ranked list. The RRF merger is purely about ranking; the Phase 2 scoring is a post-merge adjustment. This separation keeps each layer's responsibility clean.

**Parallelism**: run FTS query and vector corpus load concurrently via `tokio::join!`. The query embedding (5–15ms) is typically the bottleneck, not the similarity computation.

**Vector search scaling ceiling**: `load_all_vectors(model_id)` + brute-force cosine is O(N×D) — linear in corpus size. Acceptable to ~5,000 memories (sub-100ms). Beyond that:
- Short-term guard: cap scan at top-5,000 by `generated_at DESC` when corpus exceeds 5,000 for a model
- Medium-term: build an in-process HNSW index at startup from `memory_vectors`; update incrementally on writes. Libraries: `hnsw_rs` or `instant-distance` (pure Rust, no service). Query becomes O(log N). The `vector_global_search` function is the target — the RRF merge layer above it is already O(K×C).
- The index lives in process memory; no external service required. Survives process restart via rebuild from DB (seconds at current corpus size).

## Cross-System Compatibility

**The central Ubuntu server (GTX 970) must run the same model as the local app.**

Architecture:
- Local: fastembed-rs CPU inference (~5–15ms/embedding)
- Central: same model, GPU inference via fastembed-rs or sentence-transformers Python (~0.5–2ms/embedding)
- Turso sync carries `memory_vectors` rows (embedding BLOBs) — embeddings travel with memories
- When central enriches a memory and modifies its claim text, it MUST regenerate the embedding using the same model before sync
- Central handles batch re-embedding when the model is upgraded (GPU makes this fast); local re-embeds lazily on access

A local client encountering a `model_id` it does not run treats those rows as absent and falls back gracefully. This means model upgrades can roll out to central first; local clients degrade cleanly until they also upgrade.

## Model Versioning and Migration

The `model_id` column is the compatibility key and migration signal:

- **Stale detection**: a memory with no `memory_vectors` row for the current `model_id` is queued for background embedding
- **Upgrade path**: write new embeddings for new `model_id`, verify coverage, then delete old `model_id` rows
- **Atomic swap**: never delete old embeddings until new ones are confirmed written — the system uses whichever `model_id` matches the running model
- **Central-first upgrades**: central server (GPU) runs full migration, syncs new embeddings to local via Turso; local then switches `model_id` and old local rows become stale

## Graceful Degradation

`EmbeddingEngine::try_embed(text: &str) -> Option<Vec<f32>>`:
- Returns `None` if model not initialized, download in progress, or inference fails
- Callers treat `None` as absent vector channel — RRF collapses to two channels
- No error propagated to MCP caller under any inference failure condition
- Log `WARN` with error detail for observability

**CRITICAL: Graceful does not mean invisible.** The embedding pipeline was silently dead from 0.2.7 through 0.2.13 — `memory_vectors = 0` on both prod and dev — because `catch_unwind` + `Option::None` made the ORT DLL version mismatch invisible. Every search result was degraded and no one knew. After any change to the embedding path, verify `db_info` shows `memory_vectors > 0` within 60 seconds of the first `write_memory` call. If the count stays at 0, the model did not initialize — check `ORT_DYLIB_PATH` and the startup log for WARN entries. Silent degradation in a retrieval system is worse than a crash because the operator trusts output they shouldn't.

## Scope

This skill governs embedding inference for the memory retrieval system and the knowledge corpus. Out of scope:

- **Text generation / LLMs** — use a different approach
- **Code graph analysis** — the analysis engine uses a separate graph-based approach; code semantic similarity is a distinct problem
- **Image or multimodal embeddings** — not in scope for this system
- **Knowledge corpus embeddings (Purpose 3)**: Implemented in 0.2.15 via `KnowledgeEmbeddingService` in `src-tauri/src/knowledge/`. Knowledge vectors live in the runtime DB (`knowledge_vectors` table), separate from memory vectors.
