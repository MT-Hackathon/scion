# Common Pipeline Failure Patterns

Use this quick reference to map a failure signal to likely cause and next action.

## Failure Reasons

| Failure reason | Meaning | First action |
|---|---|---|
| `script_failure` | Job command exited non-zero. | Pull trace and locate first explicit error. |
| `stuck_or_timeout_failure` | Job could not start or exceeded runner wait window. | Retry once; then investigate runner availability. |
| `runner_system_failure` | Runner infrastructure failed. | Retry and check runner health before code changes. |
| `job_execution_timeout` | Job exceeded runtime limit. | Profile step duration; optimize or raise timeout. |
| `unknown_failure` | Provider did not classify root cause. | Treat trace as primary evidence and correlate with recent changes. |

## Frequent Root-Cause Buckets

- **Test/validation**: assertion failures, lint/type checks, missing test fixtures.
- **Browser test environment**: `vitest` browser mode (`@vitest/browser-playwright`) requires system libraries (libatk, libcups, libdrm, libgbm) absent from bare `node:XX` Docker images. Fix: add `npx playwright install --with-deps chromium` as a step before the test command. Symptom: cryptic native library errors mid-test, not a code assertion failure.
- **Build/package**: dependency resolution errors, registry auth, Docker build failures.
- **Deploy/release**: missing environment variables, permissions, target environment unavailable.
- **Trigger/downstream**: parent job fails because downstream pipeline failed; inspect downstream job trace.
- **Intermittent infrastructure**: runner/network flakiness; verify repeatability before changing code.

## Triage Heuristics

1. Prefer the first deterministic error in trace over the final generic failure line.
2. Distinguish code failure from infrastructure failure before proposing fixes.
3. If failure is non-deterministic, retry once to classify as flaky vs reproducible.
