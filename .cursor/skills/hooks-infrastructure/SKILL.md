---
name: hooks-infrastructure
description: "Governs Cursor hook authoring: BOM-safe stdin parsing, event payload contracts, subagent_type normalization, artifact-driven gating, and the 4-hook infrastructure inventory. Use when writing, debugging, or extending Cursor hooks. DO NOT use for rule design (see rule-authoring-patterns) or environment setup (see environment)."
---

<ANCHORSKILL-HOOKS-INFRASTRUCTURE>

# Hooks Infrastructure

Patterns and mandates for writing Cursor IDE hooks. Every hook that reads stdin JSON must apply these patterns — silent failure is the alternative.

## Hook Inventory

| Event | Script | Purpose |
|-------|--------|---------|
| `sessionStart` | `session_briefing.py` | Generates codebase briefing into a rule file |
| `stop` | `session_capture.py` | Temporal-self pipeline: ingest + segment |
| `subagentStop` | `catalog_agent.py` | Catalogs agent completions to `handoffs/agent-catalog.md` |
| `subagentStop` | `executor-quality-gate.py` | Static analysis + linting + coverage gate |

All hooks use PEP 723 inline metadata and run via `uv run`. Registration lives in `.cursor/hooks.json`.

## Critical: BOM-Safe Stdin Parsing

**Cursor prepends a UTF-8 BOM (`\xef\xbb\xbf`) to stdin payloads on Windows.** Python's `sys.stdin` on Windows defaults to cp1252, decoding those 3 bytes as `ï»¿` instead of the Unicode replacement character. `json.loads()` then fails — silently, because hooks wrap everything in `try/except`.

**Mandatory pattern — apply before every `json.loads()` call:**

```python
raw = sys.stdin.read()
brace = raw.find("{")
if brace > 0:
    raw = raw[brace:]
event = json.loads(raw)
```

This is not optional. Every hook that reads stdin was silently broken until this fix was applied (root cause discovered Feb 2026). The sessionStart briefing hook survived only because it has a fallback path that bypasses stdin entirely.

## Event Payload Contract

All fields are optional and may be absent or empty. Never assume presence.

| Field | Type | Notes |
|-------|------|-------|
| `status` | `str \| None` | `"completed"` when subagent finished cleanly |
| `subagent_type` | `str \| None` | Runtime class, NOT persona name (see below) |
| `result` | `str \| None` | May be absent, empty, or truncated |
| `task` | `str \| None` | May be absent |
| `description` | `str \| None` | May be absent |
| `agent_transcript_path` | `str \| None` | May be absent or point to a nonexistent file |
| `conversation_id` | `str \| None` | Also check `conversationId` (camelCase variant) |

**Defensive access:**
```python
result_text = str(event.get("result") or "")
transcript_path = event.get("agent_transcript_path")  # check path.exists() before use
```

## subagent_type Normalization

Hook events carry the **runtime class**, not the custom persona name.

| What the event contains | What it means |
|---|---|
| `"general-purpose"` | Any agent on the generalPurpose runtime: the-executor, the-architect, the-curator, the-qa-tester — and the literal generalPurpose agent |

**Never filter by persona name.** `"the-executor"` will never appear as `subagent_type`. All custom agents run on `general-purpose` underneath. Identity-based filtering will always miss its target.

## Artifact-Driven Gating

Gate behavior on **what changed**, not **who changed it**.

```python
# WRONG — identity filtering never fires
if event.get("subagent_type") == "the-executor":
    run_quality_gate()

# RIGHT — artifact filtering fires for any agent that touched source files
changed_files = _discover_changed_files(event, workspace)
if changed_files:
    run_quality_gate()
```

The quality gate's file discovery priority chain (see `executor-quality-gate.py`):
1. Extract from `result` text — regex for backtick-wrapped paths + supported extension match
2. Parse the agent transcript's final assistant message for file paths
3. `git diff --name-only HEAD` — staged and unstaged changes
4. `git ls-files --others --exclude-standard` — untracked files

## Output Contract

Hooks write JSON to stdout. Return `{}` for a no-op. Use `followup_message` to inject context into the agent conversation after the subagent completes.

```python
def _emit(payload: dict) -> None:
    json.dump(payload, sys.stdout)
    sys.stdout.write("\n")
    sys.stdout.flush()

_emit({})                                              # no-op
_emit({"followup_message": "Quality gate: 3 issues"}) # injects into conversation
```

Wrap the entire `main()` body in `try/except Exception` and emit `{}` on any error. A crashing hook blocks the IDE action it wraps.

## PEP 723 Starter Template

```python
#!/usr/bin/env -S uv run --python 3.12
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
from __future__ import annotations

import json
import sys
from typing import Any


def _emit(payload: dict[str, Any]) -> None:
    json.dump(payload, sys.stdout)
    sys.stdout.write("\n")
    sys.stdout.flush()


def main() -> int:
    try:
        raw = sys.stdin.read()
        brace = raw.find("{")
        if brace > 0:
            raw = raw[brace:]
        if not raw.strip():
            _emit({})
            return 0
        event: dict[str, Any] = json.loads(raw)
        if not isinstance(event, dict):
            _emit({})
            return 0
        # hook logic here
        _emit({})
        return 0
    except Exception:
        _emit({})
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

## Cross-References
- [delegation](../delegation/SKILL.md) — quality gate architecture and subagentStop design rationale
- [rule-authoring-patterns](../rule-authoring-patterns/SKILL.md) — RULE.mdc structure and PEP 723 script standards
- [environment](../environment/SKILL.md) — Windows/PowerShell encoding context

</ANCHORSKILL-HOOKS-INFRASTRUCTURE>
