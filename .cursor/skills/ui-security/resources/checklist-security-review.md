# Checklist: UI Security

Security validation checklist for UI code.

---

## Credential Handling

- [ ] No credentials in localStorage or sessionStorage
- [ ] No credentials written to disk or JSON files
- [ ] No credentials in .env files accessible to UI
- [ ] Credentials sent to backend immediately via HTTPS
- [ ] Credentials deleted via backend API call
- [ ] No credential persistence in browser after use

## Exposure Mitigation

- [ ] Credentials masked in console logs (`${key.substring(0,4)}***`)
- [ ] No credentials in error messages
- [ ] No credentials echoed from backend responses
- [ ] No credentials in URL parameters
- [ ] Test connection results show only success/failure (not credential)
- [ ] No credentials in browser DevTools network tab (use headers)

## Browser API Limits

- [ ] Using standard `fetch()` for HTTP requests
- [ ] Using native `<input type="file">` for file uploads
- [ ] Using browser download APIs for file downloads
- [ ] Using backend file APIs for server-side storage
- [ ] No direct disk writes from UI
- [ ] No Tauri, Electron, or native APIs (`window.__TAURI__`)

## HTTP Payload Validation

- [ ] All payloads validated with Zod before sending
- [ ] Payload size checked (<1MB limit)
- [ ] User input sanitized before inclusion in payloads
- [ ] No unvalidated raw input sent to backend
- [ ] Schema validation errors handled gracefully
- [ ] Content-Type header set correctly

## Input Sanitization

- [ ] Null bytes removed from input (`\0`)
- [ ] Whitespace trimmed
- [ ] Input length limited (reasonable max)
- [ ] Special characters handled appropriately
- [ ] No script injection vulnerabilities (use text content, not innerHTML)

## HTTPS/Transport

- [ ] All API calls use HTTPS (check `API_URL` protocol)
- [ ] No sensitive data in GET request URLs
- [ ] Credentials in headers (not query params or body for GET)
- [ ] CORS configured correctly on backend
