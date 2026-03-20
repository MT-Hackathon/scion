# Telemetry Design

MCP includes a logging capability: `logging/setLevel` controls verbosity, and `notifications/message` carries log events using RFC 5424 severity levels. Use that channel for operational logging, not as a dumping ground for every kind of telemetry.

## Discovery Telemetry

If you want to know whether the surface design is working, instrument the discovery path:

- which gateways were unlocked
- which subtools were called after unlock
- which categories were opened and then abandoned
- which always-on tools dominate traffic

This is the data that answers whether the information architecture is helping or fighting the model.

## Control Plane vs Data Plane

Keep diagnostic tools separate from live log streaming.

- Control plane: status, health, counters, registry integrity, audit summaries
- Data plane: log events, traces, or external telemetry streams

One tool should not try to be both. Mixed responsibilities produce unreadable outputs and unstable trust boundaries.

## External Telemetry

Pulling telemetry from external projects requires an explicit adapter contract before implementation:

- registered source types
- authentication model
- redaction policy
- retention expectations
- trust boundaries around destructive or privileged actions

Without that contract, "just expose telemetry" becomes a data leak with a nice schema.
