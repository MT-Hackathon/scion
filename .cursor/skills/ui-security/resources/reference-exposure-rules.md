# Reference: Exposure Rules

Credential exposure prevention rules.

---

## Pattern

### Credential Handling Rules

| Rule | Description |
|------|-------------|
| No localStorage | Never store credentials in localStorage |
| No sessionStorage | Never store credentials in sessionStorage |
| No disk | Never write credentials to disk or JSON files |
| No .env | No credentials in .env files accessible to UI |
| HTTPS only | Credentials sent via HTTPS |
| Backend delete | Delete credentials via backend API |

### Exposure Mitigation Rules

| Rule | Description |
|------|-------------|
| Mask logs | Use `${key.substring(0,4)}***` format |
| No error creds | Never include credentials in error messages |
| No backend echo | Backend should not echo secrets back |
| No URL params | Never place credentials in URL parameters |
| Test result only | Test connections show only success/failure |
| No DevTools | Credentials in headers (not visible in network tab body) |

### Browser API Rules

| Rule | Description |
|------|-------------|
| Standard fetch | Use `fetch()` for HTTP requests |
| Native input | Use `<input type="file">` for uploads |
| Browser download | Use browser download APIs |
| Backend storage | Use backend file APIs for server-side storage |
| No disk writes | No direct disk writes from UI |
| No native APIs | No Tauri, Electron, or `window.__TAURI__` |

### HTTP Payload Rules

| Rule | Description |
|------|-------------|
| Zod validation | All payloads validated before sending |
| Size limit | Payloads must be <1MB |
| Sanitize input | User input sanitized before inclusion |
| No raw input | Never send unvalidated raw input |
| Content-Type | Always set Content-Type header |

### Input Sanitization Rules

| Rule | Description |
|------|-------------|
| Null bytes | Remove null bytes (`\0`) |
| Whitespace | Trim leading/trailing whitespace |
| Length | Limit to reasonable maximum |
| Special chars | Handle appropriately per context |
| No innerHTML | Use textContent to prevent XSS |

---

## Project Implementation

### Backend Security

For backend security patterns, see the [security skill](../../security/SKILL.md).

### Key Locations

| Purpose | Path |
|---------|------|
| API Client | `app/frontend/src/lib/api/client.ts` |
| Credentials API | `/api/credentials` |
| Test Connection | `/api/connections/test` |

### Source Pointer

For the complete API client implementation — SSR-guarded AbortSignal composition, timeout handling, typed `ApiError`, and JSON response parsing — see `app/frontend/src/lib/api/client.ts`. The structural pattern is captured in the blueprint at `blueprints/api-client-auth.ts`.
