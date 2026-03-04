# Checklist: Credential Security

Verify before implementing credential handling.

---

## Storage Verification

- [ ] All secrets are in environment variables or secret managers
- [ ] `.env` file is in `.gitignore`
- [ ] `.env.example` is checked in with placeholder values
- [ ] Required keys are validated at startup

## Exposure Prevention

- [ ] No secrets logged, printed, or returned in responses
- [ ] Logs redact credentials (first few chars + `***`)
- [ ] Error messages don't include secret values
- [ ] Connection strings are not exposed

## Code Review Gates

- [ ] No hardcoded credentials in code, tests, or configs
- [ ] No secrets in JSON/YAML files
- [ ] No secrets stored in DataFrames (use references)
- [ ] No plain HTTP for production data paths

## Authentication Implementation

- [ ] Auth type is configurable (header, query, oauth2)
- [ ] Credentials use `$ENV{VAR_NAME}` reference pattern
- [ ] TLS 1.2+ enforced for all outbound connections
- [ ] Certificate verification enabled (disable only in tests)
