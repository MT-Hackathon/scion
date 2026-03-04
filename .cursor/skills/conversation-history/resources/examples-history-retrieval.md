# Patterns: Conversation History

Usage examples and output formats for conversation history scripts.

---

## Script Reference

| Script | Purpose |
|--------|---------|
| `check-last-chat.py PROJECT` | Print most recent conversation for project |
| `trace-file-discussions.py FILE` | Find all discussions about a specific file |
| `find-solution-patterns.py` | Mine patterns from past problem-solving |
| `analyze-failure-patterns.py` | Identify recurring failure modes |
| `export-project-knowledge.py` | Export project-specific knowledge |
| `extract-code-solutions.py` | Extract code blocks from conversations |

### Shared Utilities
`db_utils.py` provides: `load_database()`, `extract_conversations()`, `is_project_conversation()`, `search_text_in_conversation()`, `find_files_in_conversation()`

---

## Common Usage Patterns

### Pattern 1: Check Recent Conversation

**When to use**: Need context from most recent project conversation

**Command**:

```bash
uv run .cursor/skills/conversation-history/scripts/check-last-chat.py procurement-web
```

**Output sample**:

```
================================================================================
Conversation: abc123def456
Last updated: 2026-01-05T10:23:45
Messages: 12  Files referenced: 3
Files:
  - src/app/core/services/navigation.service.ts
  - src/app/core/layout/app-shell/app-shell.ts
  - .cursor/rules/140-angular-foundation/RULE.mdc
--------------------------------------------------------------------------------
01. [user] 2026-01-05T10:20:00
    How do I implement signals in this component?
    
02. [assistant] 2026-01-05T10:21:30
    Based on the Angular signal patterns...
```

**Options**:

- `--limit N`: Show N most recent conversations (default: 1)
- `--message-limit M`: Show M most recent messages per conversation (default: 40)

### Pattern 2: Trace File History

**When to use**: Need all discussions about a specific file or pattern

**Command**:

```bash
uv run .cursor/skills/conversation-history/scripts/trace-file-discussions.py "src/app/core/services/*"
```

**Output**:

```
Found 3 conversations discussing files matching: src/app/core/services/*

Conversation 1: xyz789abc123
Date: 2026-01-03T14:30:00
Matched files:
  - src/app/core/services/navigation.service.ts
  - src/app/core/services/theme.service.ts
Messages: 8
```

**Options**:

- `--project PROJECT`: Filter to specific project
- File patterns support wildcards: `*.ts`, `src/*/layout/*`

### Pattern 3: Search for Solutions

**When to use**: Mining past solutions for similar problems

**Command**:

```bash
uv run .cursor/skills/conversation-history/scripts/find-solution-patterns.py "signal testing"
```

**Output**:

```
Found 2 conversations matching: signal testing

Match 1: conversation_456def
Date: 2025-12-28T09:15:00
Snippet: "...when testing signals, create the signal outside beforeEach for manipulation..."
Files: src/app/core/services/navigation.service.spec.ts
```

**Options**:

- `--project PROJECT`: Limit to specific project
- `--days DAYS`: Limit search to last N days (default: 90)

## Integration with Planning

### Example: Pre-Implementation Research

Before implementing a new feature, search for prior work:

```bash
# Check if we've solved similar problems
uv run .cursor/skills/conversation-history/scripts/find-solution-patterns.py "http interceptor" --project procurement-web

# Find files we modified for related features
uv run .cursor/skills/conversation-history/scripts/trace-file-discussions.py "src/app/core/interceptor/*" --project procurement-web

# Review most recent architecture decisions
uv run .cursor/skills/conversation-history/scripts/check-last-chat.py procurement-web --limit 3
```

## Script Invocation from Plans

When creating plans that require context from prior sessions:

```markdown
## Step 1: Research Prior Solutions

Run conversation history search:
```bash
uv run .cursor/skills/conversation-history/scripts/find-solution-patterns.py "signal state management"
```

Review output to identify:

- Previously attempted approaches
- Performance patterns encountered
- Test patterns that worked

```

## Error Handling

All scripts handle missing database gracefully:

```

Error: Cursor database not found.
Set CURSOR_DB_PATH environment variable to your database location:
  Linux: ~/.config/Cursor/User/globalStorage/state.vscdb
  Windows: C:\Users\<USERNAME>\AppData\Roaming\Cursor\User\globalStorage\state.vscdb
  macOS: ~/Library/Application Support/Cursor/User/globalStorage/state.vscdb

```

**Fix**: Set environment variable or check default locations exist.
