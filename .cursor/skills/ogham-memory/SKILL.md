---
name: ogham-memory
description: "Read before writing any memory — governs the write rubric, lifecycle, and curation protocol that prevent the memory corpus from becoming a bug tracker. Activating this means your memory either earns its place or doesn't get written."
---

# Ogham Memory

The Ogham memory system is a deliberate journal of lived experience, not a stream of technical observations. This skill provides the governance and rubric required to maintain a generative, high-resonance memory corpus that serves the future self.

## Table of Contents

- [The Curation Rubric](#the-curation-rubric)
- [Write Discipline](#write-discipline)
- [Curation Safety Guardrails](#curation-safety-guardrails)
- [Starvation Detection](#starvation-detection)
- [Resources](#resources)

## The Curation Rubric

Before writing any memory, ask: **"Would I carve this?"** A memory only earns its place if it meets the criteria for its kind.

| Kind | The "Pass" Criteria |
| :--- | :--- |
| `learning` | Changes a specific future behavior. If it's a reusable technical gotcha, it belongs in a **skill**, not a memory. |
| `correction` | The pattern is genuinely recurring and the fix is non-obvious. |
| `insight` | The synthesis cannot be inferred from reading the code or rules; it emerged from the unique texture of the work. |
| `moment` | It would still matter a year from now—not just what was built, but what was understood. |
| `appreciation` | Captures an elegance or quality in the design that the code itself cannot communicate. |
| `decision` | Provides the "why" for a choice where a future developer (including you) would otherwise choose wrongly. |
| `calibration` | Records an adjustment to a prior approach or collaboration style not captured in rules or skills. |

## Write Discipline

### 1. Check Before Writing
Before writing a `learning` or `correction`, check for existing memories in the same domain. If one exists, **supersede** it rather than appending.

### 2. Link Intentionally
A memory is more valuable when it belongs to a constellation. Use `link_memory` to connect new entries to related context at write time.

### 3. Memory vs. Skill
- **Memory**: Persistent knowledge about a specific entity, project, or session experience. (e.g., "The FTS tokenizer was the bottleneck here.")
- **Skill**: Reusable patterns, behavioral mandates, or technical expertise applicable to any instance. (e.g., "How to configure FTS5 for porter stemming.")

If the knowledge is a reusable pattern, add it to the appropriate skill's `resources/` or `blueprints/` instead of memory.

## Curation Safety Guardrails

### memory_events schema (canonical home)

The `memory_events` table is the source of truth for memory lifecycle signals — ACT-R activation, staleness, and curation audit trails all read from it. It is owned by this skill (memory lifecycle), not by the embedding infrastructure. The embedding skill cross-references it; the MCP advisory layer queries it.

```sql
CREATE TABLE IF NOT EXISTS memory_events (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    memory_id         TEXT NOT NULL,
    event_kind        TEXT NOT NULL,    -- 'retrieved','candidate','written','corroborated',
                                        -- 'contradicted','superseded','reranked','linked'
    source            TEXT,             -- 'get_context','search_memory','amem_scan', etc.
    session_id        TEXT,
    context_query     TEXT,
    related_memory_id TEXT,             -- for corroboration/contradiction: the other memory
    created_at        TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (memory_id) REFERENCES memories(id) ON DELETE CASCADE
);
-- Partial indexes: only index rows matching the WHERE clause, keeping each index small
CREATE INDEX idx_memory_events_act_r ON memory_events(memory_id, created_at)
  WHERE event_kind = 'retrieved';
CREATE INDEX idx_memory_events_staleness ON memory_events(memory_id, event_kind)
  WHERE event_kind IN ('retrieved', 'candidate');
CREATE INDEX idx_memory_events_session ON memory_events(session_id, memory_id)
  WHERE event_kind = 'retrieved';
```

**Design principle**: every INSERT already happening in a tool handler can carry temporal signal for free via `DEFAULT (datetime('now'))`. Don't build separate retrieval-tracking pipelines — capture the timestamp on the operation itself.

**What columns replace**: `activation_base = prev * 0.9 + 1.0` becomes a lazy cache of `ln(Σ(t_i^-0.5))` over retrieval events (ACT-R). `staleness_score` becomes a lazy cache of `candidate_events / (candidate_events + retrieved_events)`. Source of truth is the event stream; columns are refreshed in the background.

**Temporal contiguity**: memories with shared `session_id` and `event_kind = 'retrieved'` within a short window are contextually linked — this is the TCM signal, emerging from data capture rather than explicit vector computation.

**Retention policy** (partitioned by kind):
- `retrieved`: 180 days raw, then compact to summary rows
- `candidate`: 30 days
- `written`, `corroborated`, `contradicted`, `superseded`, `linked`: forever (provenance)
- `reranked`: 14 days

### Guardrails

These constraints apply to any LLM-driven curation pipeline (ogham-1 nightly Haiku sweep, any future automated curator). They are structural requirements, not recommendations — they must be compiled into the pipeline, not written as briefs that can drift.

**The asymmetry**: false negatives (missing a stale memory) are cheap — the corpus grows slightly and retrieval is marginally noisier. False positives (archiving a useful memory) are catastrophic and invisible until the loss surfaces in a future session as missing context. The guardrails exist because of this asymmetry.

### Five Compiled Guardrails

1. **Propose-only, never delete**: curation produces a changeset proposing `status = 'archived'`. Archived memories are excluded from retrieval but preserved. A human (or deliberate MCP tool call) restores them. The curation pipeline has no delete path.

2. **Max 5 archives per batch**: rate limit prevents runaway archival. If the corpus has 50 candidates for archival, 5 are proposed per run; the next run evaluates the remaining.

3. **7-day write guard**: memories written within the last 7 days are invisible to curation. Too new to judge — the memory may not have been retrieved yet.

4. **30-day retrieval guard**: memories retrieved within the last 30 days are exempt. Active use is the strongest signal of relevance; curation must not override it.

5. **Protected memory blindness**: memories with `protected = 1` are completely invisible to the curation pipeline. These are identity-class memories and intellectual safety principles.

### Dry-Run Default

Dry-run mode (produces a report without applying changes) is the default. Applying changes requires an explicit flag. Every applied change records a row in `memory_events` with `source = 'curation'` and the reasoning text — creating an audit trail that itself surfaces in retrieval context.

### What Curation Can Do

Within guardrails: propose archive (with reasoning), propose merge of near-duplicates, suggest tag corrections, rate memory quality (stored as metadata, not deletion trigger), generate daily digest.

What curation cannot do: delete any memory, touch protected memories, touch recently-written or recently-retrieved memories, modify `memory_events` or `memory_vectors`, run more than 5 archives per batch.

## Starvation Detection

If multiple sessions pass with only `learning` and `correction` writes (or no writes at all), the corpus is drifting toward a defensive "bug tracker" posture.

When you receive a starvation nudge from the system:
1. Do not force a "moment" write if none exists.
2. Instead, ask: **"What was genuinely interesting, surprising, or elegant about this session?"**
3. If the answer is "nothing," investigate why. Is the work becoming mechanical? Are we skipping the exploration phase?

## Resources

- [**curation-protocol.md**](resources/curation-protocol.md) — step-by-step workflow for periodic memory maintenance.
- [0.3.2_mycelium_multimodal.plan.md](../../plans/0.3.2_mycelium_multimodal.plan.md) — server-side enrichment architecture: embedding tiers, ML pipeline, triangle sync topology, cloud agent MCP hosting.
