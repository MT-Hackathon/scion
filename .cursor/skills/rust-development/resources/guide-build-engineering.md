# Rust Build Engineering Guide

Rust's default build configuration is tuned for correctness and broad compatibility, not developer iteration speed or production binary quality. This guide explains the settings that matter, the mechanisms behind them, and the platform-specific tradeoffs that are not obvious from the documentation.

Cross-reference: [reference-crate-catalog.md](./reference-crate-catalog.md) for build tool crate vetting. Quality gate sequencing is in the Quality Pipeline table in [SKILL.md](../SKILL.md).

---

## Why Build Configuration Matters

Rust compilation is slow by design: monomorphization expands generic code at compile time, LLVM performs expensive optimization passes per codegen unit, and proc-macros run as separate compiler invocations. The default profile makes conservative choices that favor reproducibility over speed. Tuning the profile is not about hacking around the language — it is about telling the compiler the right tradeoffs for the context you are actually in.

The key insight: **dev builds and release builds have opposite goals.** Dev builds prioritize fast iteration (low optimization, rich debug info). Release builds prioritize runtime speed and binary size (maximum optimization, strip debug info). Profile tuning fails when engineers mix these goals — applying release-level optimization to dev builds makes the inner loop slow, and retaining debug info in release adds size without production value.

---

## Dev Profile

The default dev profile compiles all code at `opt-level = 0` with full debug info. That combination is correct for debugging but expensive on large dependency graphs: zero optimization means more generated LLVM IR, and full debug info means more data for the linker to process.

The tuned dev profile targets fast iteration without sacrificing debuggability on first-party code:

```toml
# Cargo.toml
[profile.dev]
debug = "line-tables-only"     # Line numbers only — omits variable names and types
opt-level = 1                  # Minimal optimization; makes UI feel responsive during dev

[profile.dev.package."*"]
opt-level = 3                  # All dependencies compiled optimized
debug = false                  # No debug info for deps — dramatically shrinks target/

[profile.dev.build_override]
opt-level = 3                  # Build scripts and proc-macros compile fast
```

**Why `debug = "line-tables-only"`**: Full debug info (`debug = 2` or `true`) embeds variable names, type information, and scope data into the binary. This information drives the debugger's "inspect variable" UI, but it's expensive to generate and link. `line-tables-only` retains file and line number information — so stack traces, panic messages, and line-level breakpoints work — but skips the variable metadata. For most development work, you spend far more time reading stack traces than inspecting variables at breakpoints. The link time reduction is meaningful.

**Why `opt-level = 1` for first-party code**: Zero optimization produces more LLVM IR and can make UI interactions visibly sluggish in a desktop application. Opt-level 1 applies inlining and basic loop optimizations without the expensive analysis passes of level 2/3. First-party code changes frequently, so compile time matters more than runtime speed here.

**Why `opt-level = 3` for dependencies**: Dependencies change rarely. Compiling them once at level 3 means they land in the incremental cache and are not recompiled on most dev builds. The runtime cost of un-optimized dependencies — heavy async runtimes, serialization crates, GUI frameworks — accumulates into visible latency during interactive development. This is the single highest-leverage setting in the dev profile.

**Why `build_override opt-level = 3`**: Build scripts (`build.rs`) run as host-native binaries during compilation. Proc-macros are compiled and executed by the compiler at expansion time. Both run on the hot path of every build invocation. Compiling them at optimization level 3 is a one-time cost that reduces every subsequent build's overhead.

---

## Release Profile

```toml
# Cargo.toml
[profile.release]
lto = "thin"                   # ~90% of full LTO benefit at a fraction of the link time
codegen-units = 1              # Single LLVM module enables maximum cross-crate optimization
opt-level = 3                  # Speed-focused (use opt-level = "s" or "z" for binary size)
panic = "abort"                # No unwinding machinery — smaller binary, faster panics
strip = true                   # Strip debug symbols from the output binary
debug = false
```

**Why `lto = "thin"` not `lto = true`**: Link-Time Optimization allows LLVM to optimize across crate boundaries — inlining a function from a dependency into your hot path, devirtualizing trait calls, eliminating dead code that the compiler couldn't see earlier. Full LTO (`lto = true` or `lto = "fat"`) processes the entire program as one LLVM module, which is extremely effective but can take 10-20 minutes for a large workspace. Thin LTO processes modules in parallel with cross-module optimization, recovering roughly 90% of the binary quality improvement at a fraction of the cost. For production desktop builds, thin LTO is the right default.

**Why `codegen-units = 1`**: By default, Rust splits each crate into multiple codegen units to parallelize LLVM. More parallelism means faster compilation but worse optimization — LLVM cannot optimize across codegen unit boundaries. Setting `codegen-units = 1` tells LLVM to see the entire crate as one compilation unit, enabling the inlining and dead-code elimination that LTO relies on. This has no effect on compile time when combined with `lto = "thin"` (which already manages cross-crate boundaries); it matters for single-crate optimization quality.

**Why `panic = "abort"`**: When a panic occurs in Rust's default mode, the runtime unwinds the stack, running `Drop` implementations as it goes. This requires the compiler to generate unwinding tables (DWARF or SEH) for every function. `panic = "abort"` replaces unwinds with an immediate process abort, eliminating all unwinding machinery from the binary. For a desktop application or CLI binary where a panic is an unrecoverable programming error (not a caught exception), the unwinding machinery adds binary size with no practical benefit.

**Why `strip = true`**: Release builds compiled with `debug = false` still contain symbol information used by the linker. Stripping removes these symbols from the final binary output, reducing its size. On some platforms, stripping is what makes a 50MB binary a 10MB binary. Debug symbols for production crash reporting should come from a separate `.pdb` (Windows) or `.dsym` (macOS) file archived during the build, not embedded in the shipped binary.

---

## `.cargo/config.toml`

Project-level cargo configuration belongs in `.cargo/config.toml` at the workspace root. This file is version-controlled and applies to all contributors on all platforms. Use target-triple sections to apply platform-specific flags without forcing other platforms to parse or reject them.

```toml
# .cargo/config.toml

[alias]
check-all   = "check --workspace --all-targets"
clippy-all  = "clippy --workspace --all-targets -- -D warnings"
test-all    = "nextest run --workspace"

[target.x86_64-unknown-linux-gnu]
# LLD is default on Linux since Rust 1.90 (Sep 2025) — no linker config needed.
# This section is present for CI-specific flags only.
rustflags = ["-C", "symbol-mangling-version=v0"]

[target.x86_64-pc-windows-msvc]
# Use the default MSVC linker. rust-lld is unstable on Windows MSVC as of March 2026
# (PDB generation failures, open metabug rust-lang/rust #71520). Do not override.
rustflags = ["-C", "target-feature=+crt-static"]

[http]
multiplexing = true

[registries.crates-io]
protocol = "sparse"   # Default since 1.68; explicit here for clarity in older toolchain contexts
```

The aliases make the quality gate commands in this skill's SKILL.md runnable without remembering the full flag sequence. They also make CI and local development use the same invocation.

---

## Platform Setup

### Linux

> **Linux:** No linker configuration is needed. `rust-lld` has been the default linker since Rust 1.90 (stable, September 2025). It delivers ~7x link time improvement over the previous `bfd` linker without any configuration. If you are on an older toolchain pinned below 1.90 for other reasons, you can explicitly configure mold: install `mold` from your package manager, then add `linker = "clang"` and `rustflags = ["-C", "link-arg=-fuse-ld=mold"]` under your target triple.

### Windows

> **Windows:** The most impactful build speedup on Windows is excluding project directories from Windows Defender real-time scanning. Without exclusions, Defender intercepts every `.exe` and `.pdb` write in `target/`, which can consume 30–40% of total build time. This is not a compiler issue — it is filesystem I/O being serialized through the antivirus scan queue.
>
> Run the following in an elevated PowerShell session (replace the project path with your actual workspace root):
>
> ```powershell
> Add-MpPreference -ExclusionPath "C:\path\to\your\project"
> Add-MpPreference -ExclusionPath "$env:USERPROFILE\.cargo"
> Add-MpPreference -ExclusionPath "$env:USERPROFILE\.rustup"
> ```
>
> Do **not** configure `rust-lld` as the linker on Windows MSVC. As of March 2026, rust-lld on the MSVC target has documented PDB generation failures and an open metabug (rust-lang/rust #71520) active since 2019. The default MSVC linker is correct for this target.

### macOS

> **macOS:** The default Apple ld linker is fast enough for most workspaces. No linker configuration is needed. If link times become a bottleneck on large workspaces, `lld` via the LLVM toolchain is available but requires manual installation via Homebrew. For most projects, profile tuning (above) delivers more improvement than linker changes.

---

## Build Tools

### cargo-nextest

The de facto test runner in 2026. Runs each test binary in a separate process, enabling true parallelism across test suites and preventing one test's global state from contaminating another's.

**Speed**: 1.5–3x faster than `cargo test` on multi-crate workspaces. Adopted by Tauri, Zed, and most major Rust projects.

```bash
# Install
cargo install cargo-nextest
# or: cargo binstall cargo-nextest

# Run
cargo nextest run --workspace

# CI profile (structured output, no progress bars)
cargo nextest run --workspace --profile ci
```

The SKILL.md quality gate table uses `nextest run --workspace` as the canonical test command. `cargo test` remains valid for quick single-crate checks but is not the workspace standard.

### sccache

Shared compilation cache for CI environments. Caches compiled artifacts by content hash; unchanged crate + flags = cache hit. Version 0.10+ (late 2025) improved the S3 and GCS backends significantly.

```bash
cargo install sccache
```

In CI, set `RUSTC_WRAPPER=sccache` in the environment before any cargo invocation. The cache backend (S3, GCS, Redis, local filesystem) is configured via `sccache --config` or environment variables.

sccache is a CI tool. For local development, Cargo's built-in incremental compilation is more appropriate — sccache adds overhead per-invocation that hurts the inner loop.

### cargo-deny

License compliance and dependency vetting. Checks every crate in the dependency tree against configured policies: allowed licenses, banned crates, advisory database, and duplicate version detection.

```bash
cargo install cargo-deny
cargo deny init          # Generates deny.toml
cargo deny check         # Runs all checks
```

This is a mandatory gate for supply chain security. See `reference-crate-catalog.md` for the AVOID list that `cargo-deny` enforces via its ban list. Add to CI as a blocking check.

### cargo-audit

Checks `Cargo.lock` against the RustSec advisory database for known vulnerabilities in any dependency version you have pinned.

```bash
cargo install cargo-audit
cargo audit
```

Run before releases and periodically in CI. Unlike `cargo deny`, which enforces policy, `cargo audit` catches CVEs discovered after your `Cargo.lock` was last updated.

### cargo-machete

Finds dependencies declared in `Cargo.toml` that are never actually imported by the crate. False positives exist (proc-macro-only crates, optional features), but it catches genuine dead weight before release.

```bash
cargo install cargo-machete
cargo machete
```

Run as a release preparation step, not in the inner development loop. Review its output — do not blindly remove every flagged crate.

---

## Diagnosing Slow Builds

When a build takes longer than expected, the cause is almost always one of three things: a full recompile triggered by a metadata change, an unbounded proc-macro expansion, or a build script running expensive work on every invocation.

### `cargo report rebuild-reasons`

Available in Cargo 1.94 (March 2026). Reports which file change triggered a crate recompile, showing exactly which artifact was invalidated and why.

```bash
cargo report rebuild-reasons
```

Use this when a seemingly unrelated change causes many crates to recompile. Common causes: a `Cargo.toml` field changed (triggers recompile of dependents), a `build.rs` output changed (triggers the crate's recompile), or a file listed in `rerun-if-changed` was touched.

### `build.rs` `rerun-if-changed` Discipline

Every `build.rs` that reads external files must emit `rerun-if-changed` directives for exactly those files. Without them, Cargo re-runs the build script on every build invocation because it cannot know if the inputs changed. With an overly broad directive (`rerun-if-changed=.`), any change anywhere triggers a recompile.

```rust
// build.rs — correct
fn main() {
    println!("cargo:rerun-if-changed=proto/schema.proto");
    println!("cargo:rerun-if-changed=build.rs");
}
```

If `rerun-if-changed` is never emitted, Cargo re-runs the script on every build. This is the most common cause of "why does everything recompile when I change nothing important?"

---

## What NOT to Do

### Do not configure `rust-lld` on Windows MSVC

rust-lld on the `x86_64-pc-windows-msvc` target has documented PDB generation failures as of March 2026. The failure mode is silent: the linker may succeed but produce incomplete or incorrect debug symbol files. This is tracked in the open metabug rust-lang/rust #71520, active since 2019. Use the default MSVC linker. This is reflected in the `.cargo/config.toml` template above, which explicitly leaves Windows MSVC on the default linker.

### Do not configure `rust-lld` explicitly on Linux

On Linux with Rust 1.90+, `rust-lld` is already the default. Adding an explicit linker configuration adds maintenance burden without benefit and can interfere with targets that need different linker behavior.

### Do not use `-Z share-generics=y`

This flag enables sharing of monomorphized generics across crate boundaries, which can reduce compile time by deduplicating work. However, `-Z` flags are nightly-only compiler features. There is no stable equivalent. Using it pins the project to a nightly toolchain, which creates upgrade friction and CI complexity that is not worth the build time savings for most projects.

### Do not add `cargo-hakari` for small workspaces

`cargo-hakari` solves a specific problem: in large workspaces with many crates, the same dependency may be compiled multiple times with different feature sets (one crate enables feature A, another enables feature A + B). hakari generates a "workspace hack" crate that unifies feature sets so each dependency compiles once. This is valuable at 15+ crates. For a workspace with 4 crates (graft-core, graft-cli, src-tauri, graft-http), the overhead of maintaining the workspace hack crate exceeds the compile time saved. Add it when the workspace grows past 12–15 crates and incremental builds are consistently slow due to feature-set churn.

### Cranelift: nightly-only, not a recommendation

The Cranelift backend for `rustc` (`rustup component add rustc-codegen-cranelift-preview`) can speed up debug compilation by replacing LLVM with a simpler code generator that produces slower but quickly generated machine code. It requires the `-Zcodegen-backend` flag, which is nightly-only. It is not supported on all targets. It is a valid tool for engineers who already commit to a nightly toolchain for other reasons, but it should not be introduced for the sole purpose of speeding up builds — the profile tuning above achieves meaningful speedup on stable.
