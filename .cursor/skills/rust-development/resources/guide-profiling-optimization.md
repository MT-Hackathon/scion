# Profiling and Optimization Guide

This guide covers benchmarking, memory profiling, and profile-guided optimization workflows. Each
section teaches how to measure performance behavior and optimize from evidence rather than intuition.

Cross-reference: [guide-allocation-patterns.md](guide-allocation-patterns.md) covers the allocation,
ownership, and iterator-shape decisions that profiling should validate before you optimize further.

---

## Benchmarking Workflow

### `divan` — the current standard

```toml
[dev-dependencies]
divan = "0.1"

[[bench]]
name = "analysis"
harness = false
```

```rust
// benches/analysis.rs
fn main() {
    divan::main();
}

#[divan::bench]
fn bench_analyze_file(bencher: divan::Bencher) {
    let path = std::path::PathBuf::from("tests/fixtures/sample.md");
    bencher.bench(|| analyze_file(&path));
}

// Parameterized: run the bench at multiple sizes
#[divan::bench(consts = [1, 8, 64, 512])]
fn bench_batch<const N: usize>(bencher: divan::Bencher) {
    let items: Vec<Item> = (0..N).map(|i| Item::new(i as u64)).collect();
    bencher.bench(|| process_batch(&items));
}
```

Run: `cargo bench --bench analysis`

### `iai-callgrind` — deterministic CI benchmarking

`divan` measures wall-clock time — accurate on a quiet dev machine, noisy in CI where CPU usage
varies. `iai-callgrind` counts CPU instructions via Callgrind. Instruction counts are deterministic:
the same code produces the same count regardless of machine load.

> **[Linux]:** Callgrind requires Valgrind, which is Linux-only. `iai-callgrind` falls back to
> estimate-mode on macOS/Windows, but the primary CI workflow requires a Linux runner.

```toml
[dev-dependencies]
iai-callgrind = "0.14"

[[bench]]
name = "ci_bench"
harness = false
```

```rust
// benches/ci_bench.rs
use iai_callgrind::{library_benchmark, library_benchmark_group, main};

#[library_benchmark]
fn bench_parse_policy() -> anyhow::Result<serde_json::Value> {
    let json = include_str!("../tests/fixtures/graft-policy.json");
    Ok(serde_json::from_str(json)?)
}

library_benchmark_group!(
    name = parse_group;
    benchmarks = bench_parse_policy
);

main!(library_benchmark_groups = parse_group);
```

**Interpreting results**: focus on instruction count changes between commits, not absolute numbers.
A 5% instruction count increase on a hot path is signal; a 0.1% change is noise. Callgrind also
reports cache miss rates — a function with low instruction count but high L1-miss rate is
memory-bound, not CPU-bound.

### What benchmark gaming looks like

The compiler will optimize across benchmark call sites if it can see through the function. Signs of
a gamed benchmark: results are suspiciously fast (< 1 ns per iteration for non-trivial work), and
removing the computation produces the same number. Fix: use `divan::black_box()` or
`std::hint::black_box()` to prevent dead-code elimination of the result.

```rust
#[divan::bench]
fn bench_real(bencher: divan::Bencher) {
    bencher.bench(|| {
        // Without black_box, the compiler may elide this entire call
        // if it can prove the result is unused
        divan::black_box(compute_expensive_result())
    });
}
```

---

## Memory Profiling Workflow

### `dhat-rs` — allocation hotspot finder

`dhat-rs` intercepts every allocation and tracks its call site. It answers: "which line of code
is allocating a 2 KB buffer 800,000 times?"

```toml
[dev-dependencies]
dhat = "0.3"
```

```rust
// In your test or main (not production — dhat has overhead)
#[cfg(test)]
#[global_allocator]
static ALLOC: dhat::Alloc = dhat::Alloc;

#[test]
fn test_allocation_profile() {
    let _profiler = dhat::Profiler::builder().testing().build();

    // Run the code you want to profile
    let _result = parse_and_analyze("tests/fixtures/large_corpus/");

    // Assert allocation budget
    let stats = dhat::HeapStats::get();
    assert!(
        stats.total_bytes < 5_000_000,
        "exceeded allocation budget: {} bytes allocated",
        stats.total_bytes,
    );
}
```

The `testing()` mode writes a `dhat-heap.json` file when the profiler drops. View it at
[nnethercote.github.io/dh_view/dh_view.html](https://nnethercote.github.io/dh_view/dh_view.html).

### `samply` — sampling profiler

`samply` records CPU samples and displays them in the Firefox Profiler UI. It shows where time
is spent, not where bytes are allocated.

> **[Platform]:** samply works on Windows (ETW), Linux (perf events), and macOS (Instruments).
> On Linux, may require `echo -1 | sudo tee /proc/sys/kernel/perf_event_paranoid`.

```toml
# Cargo.toml — add a profiling profile
[profile.profiling]
inherits = "release"
debug = true   # retain symbol names for readable stack traces
```

```bash
cargo build --profile profiling
samply record ./target/profiling/rootstock --mcp
```

Open the URL printed by `samply` in Firefox, or upload the `.json` to
[profiler.firefox.com](https://profiler.firefox.com). Look for:
- Tall bars in the flame graph (long-running functions)
- Functions that appear across many samples that you didn't expect (hidden overhead)
- Off-CPU time (waiting, I/O) distinguished from on-CPU time

### `heaptrack` — peak memory and leak analysis

> **[Linux]:** `heaptrack` is Linux-only. Use `dhat-rs` on Windows/macOS for allocation analysis.

```bash
heaptrack ./target/profiling/rootstock --analyze /tmp/corpus/
heaptrack_gui heaptrack.rootstock.*.zst
```

`heaptrack` shows peak live allocation (maximum memory in use simultaneously) and detects leaks
(allocations never freed). Useful after a long-running workload to confirm that memory usage
stabilizes rather than growing indefinitely.

---

## Profile-Guided Optimization (PGO)

PGO feeds runtime behavior data back into the compiler to guide branch prediction, inlining, and
code layout decisions. Typical result for CPU-bound logic: 10–25% performance improvement.

Used in production by: swc, ripgrep, tikv.

> **[Platform]:** `cargo-pgo` works on Windows (MSVC toolchain) and Linux. macOS support is
> limited; prefer BOLT on macOS for post-link optimization.

```bash
cargo install cargo-pgo

# Step 1: build an instrumented binary
cargo pgo build

# Step 2: run against representative workload to generate profile data
./target/profiling/rootstock sync --workspace /path/to/typical/project

# Step 3: recompile with profile data — compiler uses it for layout and inlining decisions
cargo pgo optimize
```

**When PGO is worth the effort**:
- CPU-bound logic on a known workload (sync, analysis, search)
- Release binary distributed to users — the profile is collected once, baked into CI
- The binary has already been profiled with `samply` and optimized at the source level

**When PGO is not worth it**: I/O-bound code (waiting on disk or network dominates; CPU optimization
is irrelevant), CLI tools with short runtime (startup cost exceeds optimization benefit), early
development phases (the code will change; profiles go stale).

---

## AVOID

**Fixing allocation problems by raising limits**: if a memory profiling test is failing because
`total_bytes` exceeds the budget, the correct response is to find and fix the allocation hotspot,
not to raise the assertion threshold. The threshold documents the contract; a rising threshold
documents accumulating technical debt.
