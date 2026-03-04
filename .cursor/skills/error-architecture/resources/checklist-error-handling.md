# Checklist: Error Handling

Error handling validation checklist.

---

## Error Codes

- [ ] All error codes from mandated list
- [ ] Code matches error type
- [ ] No custom error codes without documentation

## Error Envelope

- [ ] `status: "error"` present
- [ ] `error.code` present
- [ ] `error.message` present
- [ ] Envelope unchanged across layers

## Backend

- [ ] Exceptions mapped to error codes
- [ ] Logged once (with stack trace)
- [ ] No stack traces in response
- [ ] Guard clauses prevent errors

## Frontend

- [ ] Errors displayed by severity
- [ ] Message shown to user
- [ ] No technical details exposed
- [ ] User can dismiss/retry

## Testing

- [ ] Error envelope structure tested
- [ ] Error codes tested
- [ ] Error propagation tested
