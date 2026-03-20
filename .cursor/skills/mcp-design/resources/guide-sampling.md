# Sampling Design

Sampling, sometimes exposed as `createMessage`, lets the server ask the client to obtain an AI completion on its behalf. The server does not need its own API key, but it also gives up determinism and may introduce approval latency.

## Appropriate Uses

Use sampling for AI reasoning over structured data, such as:

- semantic overlap between candidate memories or skills
- dependency reasoning across loosely connected evidence
- judgment calls where heuristic ranking is materially weaker than model synthesis

Do not use sampling for infrastructure queries, health checks, index lookups, or anything that should be deterministic and easy to debug.

## Mode Contract

Sampling changes semantics, so make it explicit:

- add a `mode` parameter
- default it to `heuristic`
- allow `sampled` only as an explicit opt-in
- declare in the response which engine actually produced the result

## Fallback Contract

If the client does not support sampling and `mode="sampled"`:

- fall back to the heuristic path
- state that fallback happened
- avoid pretending the sampled path ran

This keeps behavior safe under mixed-capability clients while still preserving intent.

## Human-In-The-Loop Reality

Some clients may present sampling requests for approval. That adds latency and breaks the mental model of "tool call equals deterministic compute." Treat sampling as a special-purpose reasoning path, not a convenient way to outsource ordinary server logic.
