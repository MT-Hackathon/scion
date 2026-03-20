# Checklist: Security Audit — Rust/Tauri + SvelteKit

Systematic security review for Rust/Tauri 2.0 desktop applications with SvelteKit frontend, MCP server with OAuth 2.1, and SQLite persistence.

References: DASVS v1.0 (Desktop Application Security Verification Standard, 2025/2026), ANSSI Secure Rust Guidelines, OWASP ASVS (desktop-mapped), and Wave 4 hardening mandates encoded in the [security skill](../SKILL.md).

---

## Audit Workflow

Copy this checklist and work through each category:

```
Security Audit Progress:
- [ ] 1. Authentication & OAuth 2.1
- [ ] 2. Tauri IPC & Capability Boundaries
- [ ] 3. Subprocess Execution & Input Validation
- [ ] 4. Token & Credential Storage
- [ ] 5. HTTP Transport (MCP Server)
- [ ] 6. SQLite & Data Persistence
- [ ] 7. Supply Chain & Dependencies
- [ ] 8. Auto-Updater Security
- [ ] 9. Frontend (SvelteKit) Security
- [ ] 10. Logging & Observability
```

---

## 1. Authentication & OAuth 2.1

Check: `src-tauri/src/oauth/`, `jwt.rs`, `token_store.rs`, `jti_store.rs`

| Check | What to Look For |
|-------|-----------------|
| JTI claim required | `jti` listed in `required_spec_claims`; JWT validation rejects tokens missing the claim |
| JTI replay prevention | `INSERT OR IGNORE` into `jti_used` table; rows-affected checked — zero rows = replay → `401 invalid_token` |
| JTI sweep | Hourly sweep of expired JTI records; sweep failure logs and continues, never panics or crashes the server |
| Refresh token hashing | Only BLAKE3 hash stored in DB; opaque token returned to client; plaintext never persisted |
| Access token TTL | Clamped: minimum 300 s, maximum 86 400 s; values outside range rejected at issuance |
| Refresh token TTL | Clamped: minimum 3 600 s, maximum 7 776 000 s (90 days) |
| PKCE enforcement | S256 challenge method required; `plain` method unconditionally rejected |
| Redirect URI validation | Scheme allowlist (`https`, `http` loopback, app-scheme) enforced at both client registration and authorization request; `javascript:`, `data:`, `file:` denied |
| Required spec claims | `jti`, `iss`, `sub`, `aud`, `exp`, `iat` all in `required_spec_claims`; missing any = rejected token |
| JWKS fetch safety | External JWKS fetch timeout-bounded (≤10 s); on timeout, falls back to last known key set — never fail-open to unauthenticated state |

**Common vulnerabilities:**
- `jti` not in `required_spec_claims` — attacker strips the claim, replay protection silently bypassed
- Refresh token stored plaintext — DB read is a full credential theft
- `plain` PKCE accepted — downgrades PKCE to eavesdropping-vulnerable method
- JWKS fetch without timeout — slow remote JWKS hangs the entire auth path

---

## 2. Tauri IPC & Capability Boundaries

Check: `src-tauri/src/commands/`, `src-tauri/capabilities/`, `src-tauri/tauri.conf.json`

| Check | What to Look For |
|-------|-----------------|
| Input validation in commands | Every `#[tauri::command]` validates inputs with guard clauses before any processing; no unguarded parameter access |
| No shell-string commands | No `#[tauri::command]` accepts a raw `String` that is passed to a shell or `Command::new`; argument arrays only |
| Minimum capability set | `capabilities/` files grant only what each window surface needs; no broad `shell: execute-all` or `fs: read-all` grants |
| Shell capability scope | If `shell` capability is present, it is restricted to explicit command entries — never open-ended `execute: true` |
| Filesystem scope | Restricted to `$APP_DATA` / `$APP_CONFIG`; `$HOME/.ssh`, `$HOME/.gnupg`, and unbounded `$HOME` denied |
| Frontend is untrusted | IPC boundary is the trust boundary; commands validate every argument as if the caller is hostile (DASVS §3.2) |
| Structured errors | `thiserror`-derived error types returned; no raw `anyhow` strings that might contain internal paths or credentials |
| `tauri_build::build()` | Called unconditionally in `build.rs`; omission causes Windows binary crash with no diagnostic |

**Common vulnerabilities:**
- Missing input validation on IPC commands — JS layer passes attacker-controlled values directly to Rust
- Overly broad capability grants — a compromised WebView can access the full filesystem
- Structured error types leaking internal paths — error message becomes a path traversal oracle

---

## 3. Subprocess Execution & Input Validation

Check: `src-tauri/src/git/`, `graft-core/src/`, any use of `std::process::Command`

| Check | What to Look For |
|-------|-----------------|
| Argument arrays | All `Command::new(...)` calls built with `.arg()` / `.args()`; no shell string construction, no `sh -c` with interpolation |
| URL scheme allowlist | Before `git clone`, `git remote add`, or any remote URL use: scheme validated against `["https", "http", "ssh", "git", "git@"]`; `file://`, `ext::`, `fd::`, and `-`-prefix values denied |
| `--end-of-options` insertion | `--end-of-options` inserted before every caller-controlled ref name in git commands (e.g., `git rev-parse --verify --end-of-options {ref}`) |
| Combined positional args | `ref:path`-style args passed as a single `.arg()` call — not split with `--`, which breaks git parsing |
| Process timeouts | All spawned processes have a timeout; `kill_on_drop(true)` set on every `Child` handle |
| Path canonicalization | All path inputs run through `dunce::canonicalize()`; result verified to remain under workspace root before use |

**Red flags to search for:**
```bash
# Shell invocation — must not accept user input
std::process::Command::new("sh")
std::process::Command::new("bash")
std::process::Command::new("cmd")

# Argument that might be user-controlled without --end-of-options
.arg(ref_name)     # Where ref_name comes from caller input

# Path use without canonicalization
Path::new(user_input)
PathBuf::from(user_input)
```

**Common vulnerabilities:**
- Argument injection via git ref names (e.g., `--upload-pack=evil`) — mitigated by `--end-of-options`
- `file://` URL accepted for git remote — allows reading arbitrary local files via git protocol
- Path traversal on workspace path inputs — canonicalize + prefix check closes this

---

## 4. Token & Credential Storage

Check: `src-tauri/src/db/`, `graft-core/src/db/`, DB schema migrations

| Check | What to Look For |
|-------|-----------------|
| No hardcoded secrets | No API keys, tokens, signing keys, or passwords in source code or config files |
| DB location | SQLite DB stored in `$APP_DATA` (`app_data_dir()`), not in the project root or a world-readable temp path |
| DB file permissions | DB not world-readable; created without `o+r` on Unix; on Windows, ACL scoped to current user |
| Refresh token hashing | `refresh_tokens` table stores BLAKE3 hash column, not plaintext; column name not `token_plaintext` |
| RSA key size | Private keys generated with 4096-bit modulus; 2048-bit keys are a finding |
| No secrets in IPC return | `#[tauri::command]` return values do not include signing keys, raw tokens, or connection strings |
| No secrets in error messages | `thiserror` error messages do not interpolate secrets or private key material |

**Common vulnerabilities:**
- DB stored in project root — gets committed or exposed via filesystem traversal
- Refresh token stored plaintext — DB read converts to full account takeover
- Signing keys in IPC responses — frontend (untrusted WebView) receives long-lived credential

---

## 5. HTTP Transport (MCP Server)

Check: `src-tauri/src/mcp/`, `graft-core/src/mcp_server/`, `axum` router setup

| Check | What to Look For |
|-------|-----------------|
| Loopback-only bind | Server bound to `127.0.0.1` (or `::1`) only; `0.0.0.0` binding is a critical finding |
| Missing `Host` header | Request without `Host` returns `400`; server does not attempt to route or authenticate the request |
| CORS origin allowlist | Explicit list of allowed origins; `null` (file-origin clients) and `http://localhost` variants allowed; `*` is never acceptable |
| Rate limiting on OAuth | `/oauth/token`, `/oauth/register`, `/oauth/authorize` protected with token-bucket or leaky-bucket; burst ≤5, replenish interval ≥10 s |
| Body size limit | Global body size limit ≤1 MB applied to all routes; unbounded acceptance enables memory-exhaustion DoS |
| Per-request timeout | Global timeout ≤60 s applied; prevents slow-loris style resource holding |
| Graceful shutdown timeout | Shutdown waits ≤30 s for in-flight requests before forceful exit |
| Bearer token on every request | MCP request handler validates `Authorization: Bearer` on every call; no unauthenticated paths except `/health` |

**Common vulnerabilities:**
- `0.0.0.0` binding — exposes MCP server to other processes and network interfaces
- No `Host` validation — request smuggling and ambiguous routing
- Missing OAuth rate limit — brute-force of token endpoints; critical on loopback (no network firewall)
- Missing body size limit — malicious client sends unbounded payload, causing OOM

---

## 6. SQLite & Data Persistence

Check: `src-tauri/src/db/migrations/`, schema setup, query sites throughout `graft-core`

| Check | What to Look For |
|-------|-----------------|
| WAL mode | `PRAGMA journal_mode=WAL` applied at connection open; `busy_timeout` set (e.g., 5 000 ms) |
| Idempotent migrations | Every `CREATE TABLE` guarded with `IF NOT EXISTS`; every column addition uses `table_has_column()` check before `ALTER TABLE` |
| Fresh-install path | Full schema created correctly from zero; test with empty DB, not just upgrade from prior version |
| Upgrade path | Migrations applied sequentially; tested from N-1 to N; schema version check and migration in same transaction |
| Parameterized queries | No user-controlled input concatenated into SQL strings; `rusqlite` named/positional params used throughout |
| DB path not leaked | DB path not included in error messages, IPC return values, or log output |

**Red flags to search for:**
```rust
// String concatenation in queries — always a finding
format!("SELECT * FROM {} WHERE", table_name)
format!("INSERT INTO jti_used VALUES ('{}')", jti)

// Raw SQL with interpolation
conn.execute(&format!("...{user_input}..."), [])
```

**Common vulnerabilities:**
- Non-idempotent migrations crash on fresh install or double-apply
- Parameterized query bypass via format! — SQLite injection on desktop is a local privilege escalation vector

---

## 7. Supply Chain & Dependencies

Check: `Cargo.lock`, `Cargo.toml` workspace, `app/frontend/package-lock.json`, `.cargo/deny.toml`

| Check | What to Look For |
|-------|-----------------|
| `cargo audit` | Run `cargo audit`; no known advisories in `Cargo.lock` |
| `cargo deny` | Run `cargo deny check`; all license, ban, and advisory policies pass |
| `npm audit` | Run `npm audit` in `app/frontend/`; no high or critical findings |
| `unsafe` discipline (ANSSI §3) | No `unsafe` block without a documented justification comment and reviewer sign-off in the same block |
| Integer arithmetic (ANSSI §2) | No unchecked casts (`as usize`, `as i32`); all arithmetic uses `checked_*`, `saturating_*`, or explicit bounds with documented invariant |
| Serde boundary validation | Every `serde` deserialization boundary validates the deserialized shape (field ranges, enum variants, string patterns) — not just that it parses |
| Pinned triplet crates | `tauri-specta`, `specta`, `specta-typescript` pinned as a triplet with `=` prefix in `Cargo.toml` |

**Run commands:**
```bash
cargo audit
cargo deny check
cd app/frontend && npm audit
cargo clippy --workspace --all-targets -- -D warnings
```

**Common vulnerabilities:**
- Unpinned `tauri-specta` triplet — minor version bump breaks the generated TypeScript bindings silently
- Unchecked `as usize` cast — integer overflow truncates to 0 or wraps; ANSSI classifies as memory safety risk
- `unsafe` without justification — review burden, audit gap, and potential UB

---

## 8. Auto-Updater Security

Check: `src-tauri/tauri.conf.json` updater block, `src-tauri/src/updater/` if present — DASVS §6 priority

| Check | What to Look For |
|-------|-----------------|
| HTTPS-only manifest | Update manifest URL is `https://`; `http://` manifest fetch is a critical finding |
| Certificate verification | TLS verification never disabled for updater fetch (`danger_accept_invalid_certs` absent or false) |
| Signature verification | Update payload signature verified against a pinned public key before installation; no signature = no install |
| WebView isolation | Updater not invocable from WebView JS; no `#[tauri::command]` that triggers an install without OS-level privilege confirmation |
| Rollback path | Failed update leaves the app in prior working state; partial writes do not corrupt the install |

**Common vulnerabilities (DASVS §6.1–6.4):**
- HTTP manifest fetch — MITM delivers malicious update payload
- Disabled TLS verification — equivalent to HTTP; certificate pinning bypass
- No signature check — any file served by the update endpoint is installed without verification
- WebView-accessible install trigger — compromised renderer escalates to code execution at OS level

---

## 9. Frontend (SvelteKit) Security

Check: `app/frontend/src/`, Svelte components, `+page.svelte`, `+layout.svelte`, IPC call sites

| Check | What to Look For |
|-------|-----------------|
| No `@html` with user input | No `{@html userContent}` where `userContent` is caller-controlled; Svelte does not sanitize `@html` |
| No dynamic code execution | No `eval()`, `Function()` constructor, or `innerHTML` assignment with user-controlled strings |
| Token storage | Tokens not stored in `localStorage` or `sessionStorage`; held in memory (Svelte stores) scoped to the session |
| Typed IPC bindings | All `invoke()` calls use specta-generated typed bindings; no raw string command names constructed at runtime |
| Open redirect prevention | Navigation targets validated before `goto()`; external URLs rejected or confirmed by user |
| Error display | Generic messages to users; raw API error detail never rendered directly in the DOM |

**Search patterns:**
```
@html                  # Unescaped HTML — verify source is not user-controlled
localStorage           # Token/secret storage check
sessionStorage         # Token/secret storage check
eval(                  # Code injection
innerHTML              # DOM manipulation risk
Function(              # Dynamic code execution
goto(userInput         # Open redirect risk
invoke("              # Raw string command — should use specta-generated wrapper
```

---

## 10. Logging & Observability

Check: `tracing` subscriber setup, all `tracing::info!/warn!/error!` call sites, `src-tauri/src/`

| Check | What to Look For |
|-------|-----------------|
| `RUST_LOG` gating | `tracing_subscriber` initialized only when `RUST_LOG` is set or in a debug build; production binary emits no log output by default |
| Auth event logging | Auth events (token issued, refresh exchanged, token rejected) logged with outcome and user/client ID — not token value |
| Failed IPC logging | Failed `#[tauri::command]` calls logged with command name and structured error code — not with argument values that might contain user data |
| No secrets in traces | No `tracing::info!/debug!` call includes token strings, BLAKE3 hash input, private key material, or filesystem paths containing user data |
| JTI sweep logging | Sweep success/failure logged at `DEBUG`/`WARN` level respectively; sweep failure never silenced |

**Red flags to search for:**
```rust
tracing::info!("{}", token)          # Token in log output
tracing::debug!("{:?}", request)     # Full request struct (may include auth headers)
tracing::info!("{}", db_path)        # DB path with user home directory
println!("{}", secret)               # Println — bypasses log level gating entirely
```

---

## Red Flags — Quick Search Reference

Run these searches across the workspace before marking the audit complete:

```bash
# Rust — safety and secrets
rg "unwrap()" src-tauri/src/ --type rust          # Unchecked unwrap outside test code
rg " as usize" src-tauri/src/ --type rust         # Unchecked integer cast (ANSSI §2)
rg "unsafe \{" --type rust                        # Unsafe block (requires justification)
rg 'format!.*token' --type rust                   # String interpolation that might include tokens
rg 'Command::new\("sh"\)' --type rust             # Shell invocation
rg 'Command::new\("bash"\)' --type rust           # Shell invocation
rg '0\.0\.0\.0' --type rust                       # Loopback bind violation

# Rust — SQL safety
rg 'format!.*SELECT' --type rust                  # String-concatenated SQL
rg 'format!.*INSERT' --type rust                  # String-concatenated SQL

# Frontend
rg '@html' app/frontend/src/                      # Unescaped HTML in Svelte
rg 'localStorage' app/frontend/src/               # Token/secret storage
rg 'sessionStorage' app/frontend/src/             # Token/secret storage
rg 'eval(' app/frontend/src/                      # Code injection
rg 'innerHTML' app/frontend/src/                  # DOM manipulation risk
rg 'invoke\("' app/frontend/src/                  # Raw string IPC command (should use typed wrapper)
```

---

## Report Template

After completing the audit, produce a report:

```markdown
# Security Audit Report — [Date] — Rust/Tauri

## Summary
- Critical: [count]
- High: [count]
- Medium: [count]
- Low: [count]

## Findings

### [CRITICAL/HIGH/MEDIUM/LOW] — Finding Title
- **Location:** file:line
- **Description:** What the vulnerability is
- **Impact:** What an attacker could do
- **Recommendation:** How to fix it
- **Reference:** DASVS §X.Y / ASVS §X.Y / ANSSI §X / CWE-XXX
```
