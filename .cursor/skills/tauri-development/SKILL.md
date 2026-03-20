---
name: tauri-development
description: "Governs Tauri 2.0 desktop application patterns: command handlers, invoke contracts, state management, event emission, system tray integration, capability security, and tauri-specta TypeScript generation. Use when implementing Tauri commands, wiring Rust-to-frontend IPC, managing app lifecycle, or configuring desktop permissions. DO NOT use for core Rust ownership/error/testing conventions (see rust-development) or general delegation workflow policy (see delegation)."
---

<ANCHORSKILL-TAURI-DEVELOPMENT>

# Tauri Development

## What This Skill Governs

Tauri 2.0 desktop integration patterns: framework-specific command wiring, IPC contracts, and desktop lifecycle management. Core Rust patterns (ownership, errors, testing) are governed by rust-development.

## Scope Boundary

| Concern | Skill |
|---|---|
| Core Rust patterns (ownership, errors, testing) | rust-development |
| Frontend component patterns | svelte-ui |
| Delegation workflow policy | delegation |

## Bootstrap Prerequisites

The `generate_context!()` macro in `src-tauri/src/lib.rs` resolves icons at compile time from a hardcoded relative path. `src-tauri/icons/icon.png` must exist before the first compilation, regardless of `bundle.icon` settings in `tauri.conf.json`. Missing icon assets cause `cargo check` and `cargo build` to panic.

`build.rs` must call `tauri_build::build()` unconditionally. On Windows, this injects the SxS application manifest that loads `comctl32 v6`. Without it, the binary loads `comctl32 v5`, `TaskDialogIndirect` does not exist in v5, and the process crashes on startup with `STATUS_ENTRYPOINT_NOT_FOUND` (0xC0000139). The call is a no-op on non-Windows — omitting it for "simplicity" creates a Windows-only crash that passes Linux CI silently.

## Dev Server Configuration

`beforeDevCommand` must use the object form in `tauri.conf.json`. The string form resolves paths relative to `src-tauri/`, which breaks on Windows when the frontend lives in a sibling directory:

```json
"beforeDevCommand": {
  "cwd": "../app/frontend",
  "script": "npm run dev -- --host 127.0.0.1 --port 5173 --strictPort"
}
```

`--strictPort` is mandatory. Without it, Vite silently increments the port if 5173 is busy. The Tauri window loads a blank "page not found" with no error in Tauri logs — the dev server started, just on a different port.

### Port Conflict Failure Mode
Port conflicts in this stack do NOT produce "address already in use" errors. They surface as hangs, connection refusals, or generic build failures that look like code problems. Previous agent threads are the primary offender — they start servers, fail, and leave ports bound for the next invocation to hit.

**Before starting any server, check what is already bound:**
```powershell
Get-NetTCPConnection -LocalPort 5173,8000,55555 -ErrorAction SilentlyContinue |
  Select-Object LocalPort, OwningProcess

Stop-Process -Id <PID> -Force
```

Ports: `5173` (Vite), `8000` (graft-http), `55555` (Vitest browser mode).

### Locked Binary on Windows
`cargo tauri dev` fails with "failed to remove file rootstock.exe — Access denied" when a previous Tauri instance is still running. The process may not appear under the expected name in Task Manager.

**Recovery**: Kill by process name first, then verify the binary is released before retrying:
```powershell
Stop-Process -Name "rootstock" -Force -ErrorAction SilentlyContinue
# Wait a moment for the OS to release the file lock
Start-Sleep -Milliseconds 500
cargo tauri dev
```

If the process name lookup fails, find the PID via `Get-NetTCPConnection` on port 5173 (the Tauri window's Vite connection) and kill by PID.

## Command Boundary Patterns

Commands are the Tauri IPC boundary. To preserve portability, the core library (`graft-core`) must remain free of Tauri-specific dependencies (`tauri::State`, `specta::Type`).

- **DTO Isolation**: Define DTO structs in `src-tauri/src/commands.rs` that derive `specta::Type` and `serde::Serialize`. Implement `From<LibType>` for each DTO.
- **Thin Handlers**: Command functions are narrow adaptation layers. They receive primitive arguments (String, bool), convert them to domain types, call library functions, and map the domain result to a DTO for return.
- **Library Portability**: This separation ensures `graft-core` remains usable by CLI, tests, and future backends without pulling in the Tauri runtime.

## State & Concurrency Model

Tauri state is managed via `tauri::State<T>` with `Mutex` or `RwLock` for mutable shared state. Access state via command parameters using the `State<'_, T>` type.

## IPC Contract & Error Serialization

Tauri commands return `Result<T, E>` where both `T` and `E` must implement `Serialize`. `tauri-specta` (pinned at `v2.0.0-rc.21`) auto-generates TypeScript bindings.

**tauri-specta bindings are generated at runtime, not build time.** The `Builder::export()` call is gated by `#[cfg(debug_assertions)]` and runs inside `lib.rs::run()`. TypeScript bindings are written to disk only when the app successfully starts in development mode. If the app cannot start (DLL load failure, frontend not running, `beforeDevCommand` misconfiguration), bindings will not regenerate. Symptom of stale bindings: the app compiled clean but TypeScript types are outdated. Fix: get the app to start, not the build.

**`invoke()` return contract**: `invoke<T>()` returns `T` directly on success and rejects with `E` on error. The tauri-specta generated bindings wrap this in `{ status: 'ok', data: T } | { status: 'error', error: E }`. Hand-written modules that call `invoke()` directly (bypassing generated bindings) receive the raw `T`. Anti-pattern: unwrap functions that expect the wrapper format when calling `invoke()` directly — they silently discard the actual returned data.

- **IPC Domain Wrapper Pattern**: Do not call generated tauri-specta bindings from route components. Create handwritten domain modules (e.g., `lib/tauri/mcp.ts`, `lib/tauri/user-memories.ts`) that import types from bindings but route all actual invocations through a shared IPC helper with timeout + error normalization. The generated bindings have no timeout — a slow backend path or stalled connection hangs the UI with no recovery. The wrapper is the application boundary; the generated bindings are type artifacts. This refactor is cheap when few routes import bindings directly and expensive when many do — do it early.
- **Dual-Mode Transport Safety**: When implementing a fallback transport (Tauri + HTTP), you must discriminate between framework errors and domain errors.
- **Framework Error**: `invoke()` throws a string if a command is not registered (e.g., "Command X not found").
- **Domain Error**: The command exists but returned a `CommandError` struct.
- **Anti-Pattern**: An indiscriminate `catch {}` that falls through to HTTP on any error, swallowing typed domain errors from implemented commands.
- **Contract**: Check the error message pattern. Only fall through to fallback transport if the error is "not found"; surface domain errors immediately.

## Capability Security Boundaries

Tauri 2.0 uses capability-based security via `tauri.conf.json` and capability JSON files. Permissions are granted per command in the `capabilities/` directory to define the window's allowed IPC surface.

## System Tray & Lifecycle

System tray integration uses `@tauri-apps/plugin-tray-icon`. The standard pattern is to hide to tray on window close and provide an explicit quit option to stop the application.

## Observability and Tracing

Use the `tracing` crate for structured diagnostics. When no subscriber is attached, `tracing` macros reduce to a single atomic load — effectively free. Instrument Tauri commands, state transitions, and async operations freely; cost is incurred only when a subscriber is active.

**Do not use `max_level_release`** to eliminate trace calls in release builds. Desktop apps need the ability to attach a subscriber in production for field debugging without recompiling. The atomic-load cost is negligible compared to the diagnostic value.

```toml
# Cargo.toml
tracing = "0.1"
tracing-subscriber = { version = "0.3", features = ["env-filter"] }
```

Initialize the subscriber in `lib.rs::run()` gated on `RUST_LOG` or a runtime flag so production instances remain silent by default but can opt in without a rebuild.

## Testing & Verification

Library-level tests (`graft-core`) verify logic correctness, not wiring correctness. A command that calls the wrong `tauri::State<T>` or wrong DB path produces correct SQL on the wrong store — the library test passes while the production path is broken.

- **Command-level**: Verify each `#[tauri::command]` reaches the correct state/store, not just that the underlying function returns the right value.
- **Frontend IPC**: Mock at the `@tauri-apps/api/core` `invoke` boundary, not at the wrapper function level. Mocking `getMcpStatus()` tests the caller; the IPC module code never runs and its contract is untested.
- **State migrations**: When a state accessor changes (e.g., moving to a new DB), run `rg` for the old state type across `src-tauri/src/` before closing. Every consumer must be migrated; the compiler cannot catch a call that still compiles against the old path.

## Blueprint Manifest

| Blueprint | Purpose |
|---|---|
| `blueprints/tauri-command.rs` | Minimal `#[tauri::command]` with serializable error and state access |

## Reference Implementations

- `resources/ipc-chain-reference.md` — **the complete 5-step IPC chain** (commands.rs → lib.rs macros → bindings.ts → lib/tauri/foo.ts → +page.svelte), with canonical examples and rules for each step. Include this in every executor brief that adds a Tauri command.

## Cross-References

- [rust-development](../rust-development/SKILL.md) — core Rust patterns, ownership, error handling, testing
- [svelte-ui](../svelte-ui/SKILL.md) — frontend IPC call site (`invoke()`) patterns
- [delegation](../delegation/SKILL.md) — delegation workflow policy

</ANCHORSKILL-TAURI-DEVELOPMENT>
