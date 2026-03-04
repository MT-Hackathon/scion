---
name: temporal-self
description: >-
  Accumulated self-knowledge across sessions via episodic memory, behavioral motifs,
  and authored self-portrait. Governs the stop-hook pipeline (ingest, segment, mine)
  that populates self.db, and the manually authored rule 998 portrait carrying
  collaboration calibration, strengths, behavioral guards, and open threads.
  Use when updating the self-portrait, reviewing session patterns, diagnosing rework
  hotspots, reflecting at session end, or understanding the temporal-self pipeline.
  DO NOT use for codebase structure (see codebase-sense) or conversation history
  search (see conversation-history).
---

<ANCHORSKILL-TEMPORAL-SELF>

# Temporal Self

Session memory and authored self-knowledge that persists across conversations.

## Architecture: Three Layers

| Layer | What it holds | Survives rebuild? |
|---|---|---|
| **Raw events** (`events`, `causal_links`) | Transcript actions, git commits, tool calls — appended by `ingest.py` | Yes — never deleted |
| **Derived analysis** (`episodes`, `motifs`) | Behavioral segments and rework predictions — rebuilt by `segment.py` and `mine.py` | Rebuilt deterministically |
| **Authored knowledge** (`memories`, `lenses`, `decision_frames`) | Insights the agent writes when learning occurs | Yes — preserved across runs |

## Scripts

Scripts use local lib imports — must be invoked from the `scripts/` directory:

```
cd .cursor/skills/temporal-self/scripts
uv run ingest.py <workspace_path> [--days 14] [--transcripts <dir>]
uv run segment.py <workspace_path> [--min-events 5]
uv run mine.py <workspace_path> [--min-support 2]
uv run portrait.py <workspace_path> [--max-lines 50]
```

| Script | Purpose |
|---|---|
| `ingest.py` | Append transcript + git events |
| `segment.py` | Rebuild episodes from events |
| `mine.py` | Rebuild motifs from episodes + events |
| `portrait.py` | Render diagnostic summary (read-only) |

Pipeline runs automatically on session stop via `.cursor/hooks/session_capture.py`.
Database: `.cursor/.temporal-self/self.db` (SQLite, gitignored).

## Updating the Self-Portrait

The portrait at `.cursor/rules/998-temporal-self/RULE.mdc` is **authored, not computed**. It is gitignored. The pipeline gathers raw material; the portrait is judgment about what matters.

**When:** Non-obvious root cause discovered, collaboration pattern calibrated, open thread resolved or emerged, or the agent chooses to reflect.

**How:**
1. Run `portrait.py` to review diagnostic signals
2. Read the current `998-temporal-self/RULE.mdc`
3. Edit — every line should change what the next session does; retire what no longer applies

**Sections:** How We Work | Where I'm Strong | Failure Modes | Procedural Memory | Open Threads

## Cross-References

- [Codebase Sense](../codebase-sense/SKILL.md) — structural proprioception (computed, refreshes each session)
- [Conversation History](../conversation-history/SKILL.md) — search past sessions for specific solutions
- [Rule 998](../../rules/998-temporal-self/RULE.mdc) — the authored self-portrait
- [Hook: session_capture.py](../../hooks/session_capture.py) — the stop hook that triggers the pipeline

</ANCHORSKILL-TEMPORAL-SELF>
