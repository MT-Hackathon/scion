# Telemetry Implementation Reference

Implementation details for the W3C Trace Context observability stack.

## W3C Trace Context Flow

```
Frontend                          Backend
────────                          ───────
trace-id.util.ts                  CorrelationFilter.java
  ↓ generates traceparent           ↓ extracts trace ID
tokenInterceptor                  MDC populated:
  ↓ adds header                     - traceId
httpErrorInterceptor              - userId
  ↓ logs with traceId               - agencyId
GlobalErrorHandler                GlobalExceptionHandler
  ↓ captures uncaught               ↓ logs + adds traceId to response
```

## Key Files

| Layer | File | Purpose |
|-------|------|---------|
| FE | `trace-id.util.ts` | Generates W3C traceparent headers |
| FE | `tokenInterceptor` | Injects traceparent into all API requests |
| FE | `httpErrorInterceptor` | Logs 4xx/5xx with trace context |
| FE | `GlobalErrorHandler` | Captures uncaught errors |
| BE | `CorrelationFilter.java` | Extracts traceparent, populates MDC |
| BE | `GlobalExceptionHandler.java` | Logs all exceptions, returns traceId in RFC 7807 |
| BE | `logback-spring.xml` | JSON logging (prod), console (dev) |

## Backend SQL Debugging

Enable in `application-dev.yml` to see query parameter values:
```yaml
logging.level.org.hibernate.orm.jdbc.bind: TRACE
```

## Runtime Log Level Changes

Use Actuator to change log levels without restart:
```bash
curl -X POST -H "Content-Type: application/json" \
  -d '{"configuredLevel": "DEBUG"}' \
  http://localhost:8080/actuator/loggers/doa.procurement
```

## Anti-Patterns

| Anti-Pattern | Problem | Fix |
|--------------|---------|-----|
| Log-and-Throw | Duplicate log entries with different contexts | Let `GlobalExceptionHandler` handle logging |
| Manual Trace Generation | Inconsistent IDs, breaks correlation | Use `trace-id.util.ts` or interceptors |
| Stripping Trace Context | Users can't correlate errors to logs | Always show traceId in error messages |
| Silent HTTP Retries | Masks systemic instability | Log retry attempts with original traceId |

## Future Migration

When OpenTelemetry adoption is ready, the migration path is: replace `trace-id.util.ts` + `CorrelationFilter.java` with OTEL SDK instrumentation, propagate `traceparent` via OTEL context, and switch `logback-spring.xml` to OTEL log appender. The interceptor and MDC patterns above remain structurally compatible.
