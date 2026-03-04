# Cross-References: Conversation History

Related skills, rules, and scripts.

---

## Related Skills

- [Temporal Self](../../temporal-self/SKILL.md) — authored self-knowledge and session motifs; conversation history provides the raw evidence that feeds portrait updates
- [Testing & Debugging](../../testing-debugging/SKILL.md) — Two-Attempt Rule triggers a history search before the third attempt
- [Planning](../../planning/SKILL.md) — pre-implementation research step benefits from history mining

## Related Rules

- **001-foundational** (`ANCHORRULE-FOUNDATIONAL`) — LEARN AND ENCODE mandate requires evidence from past sessions; TRACE BEFORE FIX mandates history check after two failed attempts

## Related Scripts

### Directory: `.cursor/skills/conversation-history/scripts/`

Core scripts documented in this skill:

- `check-last-chat.py`
- `trace-file-discussions.py`
- `find-solution-patterns.py`
- `analyze-failure-patterns.py`
- `export-project-knowledge.py`
- `extract-code-solutions.py`

Shared utilities:

- `db_utils.py` - Database access and parsing functions

## Cursor Database Schema

The scripts interact with Cursor's SQLite database (`state.vscdb`):

- Table: `cursorDiskKV`
- Key pattern: `bubbleId:{conversation_id}:{message_id?}`
- Value: JSON-encoded message data

## Environment Variables

- `CURSOR_DB_PATH`: Override default database location
- `USER` / `USERNAME`: Used for platform-specific path detection

## Use Cases

1. **Pre-Planning Research**: Check if similar features were previously implemented
2. **Debugging Recurring Issues**: Find past solutions to similar problems
3. **Architecture Decisions**: Review prior discussions about design choices
4. **Code Pattern Mining**: Extract working code from past sessions
5. **Knowledge Continuity**: Restore context after long breaks

## Limitations

- Database must be on accessible filesystem (may not work with cloud-synced Cursor)
- Very old conversations may have different schema (scripts handle gracefully)
- Large databases may have slow queries (scripts optimize with filters)
- Real-time conversation not accessible (only persisted state)
