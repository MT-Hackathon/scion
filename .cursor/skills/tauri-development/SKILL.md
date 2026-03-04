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

- **Dual-Mode Transport Safety**: When implementing a fallback transport (Tauri + HTTP), you must discriminate between framework errors and domain errors.
- **Framework Error**: `invoke()` throws a string if a command is not registered (e.g., "Command X not found").
- **Domain Error**: The command exists but returned a `CommandError` struct.
- **Anti-Pattern**: An indiscriminate `catch {}` that falls through to HTTP on any error, swallowing typed domain errors from implemented commands.
- **Contract**: Check the error message pattern. Only fall through to fallback transport if the error is "not found"; surface domain errors immediately.

## Capability Security Boundaries

Tauri 2.0 uses capability-based security via `tauri.conf.json` and capability JSON files. Permissions are granted per command in the `capabilities/` directory to define the window's allowed IPC surface.

## System Tray & Lifecycle

System tray integration uses `@tauri-apps/plugin-tray-icon`. The standard pattern is to hide to tray on window close and provide an explicit quit option to stop the application.

## Testing & Verification

Test Tauri commands by testing the underlying `graft-core` functions directly. Command wrappers should be thin enough to require no independent tests beyond IPC contract verification.

## Blueprint Manifest

| Blueprint | Purpose |
|---|---|
| `blueprints/tauri-command.rs` | Minimal `#[tauri::command]` with serializable error and state access |

## Cross-References

- [rust-development](../rust-development/SKILL.md) — core Rust patterns, ownership, error handling, testing
- [svelte-ui](../svelte-ui/SKILL.md) — frontend IPC call site (`invoke()`) patterns
- [delegation](../delegation/SKILL.md) — delegation workflow policy

</ANCHORSKILL-TAURI-DEVELOPMENT>
