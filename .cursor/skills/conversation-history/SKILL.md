---
name: conversation-history
description: "Provides scripts to mine past agent sessions: trace decisions, find prior solutions, analyze failure patterns, and search session transcripts. Use when searching for how a past problem was solved, reviewing previous decisions, or auditing session history. DO NOT use for real-time session context (see temporal-self) or structural codebase analysis (see codebase-sense)."
---

<ANCHORSKILL-CONVERSATION-HISTORY>

# Conversation History

## Table of Contents & Resources

- [Core Concepts](#core-concepts)
- [Available Scripts](#available-scripts)

### Resources

- **examples-history-retrieval.md** - When: needing past session context; What: script usage, command patterns
- **checklist-history-analysis.md** - When: analyzing conversation patterns; What: failure detection, solution mining steps
- **troubleshooting-database.md** - When: scripts fail; What: database location, common errors
- **cross-references.md** - When: finding related skills; What: links to planning, debugging skills

## Core Concepts

Cursor stores conversation history in a SQLite database (`state.vscdb`). Scripts in `.cursor/skills/conversation-history/scripts/` provide retrieval and analysis.

### Database Location

- **Windows**: `%APPDATA%\Cursor\User\globalStorage\state.vscdb`
- **WSL**: `/mnt/c/Users/<USER>/AppData/Roaming/Cursor/User/globalStorage/state.vscdb`
- **Linux**: `~/.config/Cursor/User/globalStorage/state.vscdb`
- **macOS**: `~/Library/Application Support/Cursor/User/globalStorage/state.vscdb`
- **Override**: Set `CURSOR_DB_PATH` environment variable

## Proactive Triggers

These scripts are not just on-demand tools — they should be used proactively in specific situations:

### Before Investigating a Bug
Run `find-solution-patterns.py` with the error message or symptom before starting a new investigation. Past sessions may already contain the root cause.

### After Multi-Attempt Debugging
When the Two-Attempt Rule fires (a bug survives 2+ fix attempts), run `analyze-failure-patterns.py` to check if this is a recurring pattern that needs a lesson or rule update.

### During Planning
Before major architectural decisions or complex feature work, run `export-project-knowledge.py` to gather historical context about related areas of the codebase.

### Periodic Health Checks
Run `map-patterns-to-rules.py` periodically (weekly or after a cluster of debugging sessions) to identify gaps in the rules system where lessons could prevent future issues.

### Session Retrospective Support
At the end of substantive sessions, these scripts support the foundational LEARN AND ENCODE mandate by providing evidence for what was learned and which skills or rules should be updated.

## Script Reference

All scripts: `uv run .cursor/skills/conversation-history/scripts/<script> [args]`

### check-last-chat.py
Print the most recent Cursor conversation for a project.

`uv run .cursor/skills/conversation-history/scripts/check-last-chat.py <project_path> [--limit N] [--message-limit N]`

| Arg | Purpose |
|-----|---------|
| `<project_path>` | Project path or name (e.g., procurement-web) |
| `--limit` | Number of conversations to print (default: 1) |
| `--message-limit` | Number of trailing messages to show per conversation (default: 40) |

### find-solution-patterns.py
Search conversations for technical patterns (errors, APIs, solutions).

`uv run .cursor/skills/conversation-history/scripts/find-solution-patterns.py <search_term> [--project <path>] [--days N]`

| Arg | Purpose |
|-----|---------|
| `<search_term>` | Text pattern to search for in conversations |
| `--project` | Filter by project path |
| `--days` | Number of days to search back (default: 90) |

### trace-file-discussions.py
Find all conversations mentioning specific files.

`uv run .cursor/skills/conversation-history/scripts/trace-file-discussions.py <file_pattern> [--project <path>]`

| Arg | Purpose |
|-----|---------|
| `<file_pattern>` | File pattern to search for (e.g., config.py, *.yaml) |
| `--project` | Filter by project path |

### export-project-knowledge.py
Export structured knowledge base from project conversations.

`uv run .cursor/skills/conversation-history/scripts/export-project-knowledge.py <project_path> <format> [output_file]`

| Arg | Purpose |
|-----|---------|
| `<project_path>` | Project path or name |
| `<format>` | Output format (json, csv, markdown) |
| `[output_file]` | Optional output file path |

### extract-code-solutions.py
Extract reusable code blocks and solutions from past conversations.

`uv run .cursor/skills/conversation-history/scripts/extract-code-solutions.py <project_path> [language] [min_length]`

| Arg | Purpose |
|-----|---------|
| `<project_path>` | Project path to extract from |
| `[language]` | Filter by programming language |
| `[min_length]` | Minimum code length in lines (default: 20) |

### analyze-project-evolution.py
Analyze project-scoped development patterns and file change frequency.

`uv run .cursor/skills/conversation-history/scripts/analyze-project-evolution.py <project_path> [--days N]`

| Arg | Purpose |
|-----|---------|
| `<project_path>` | Project path to analyze |
| `--days` | Number of days to analyze (default: 60) |

### analyze-failure-patterns.py
Analyze chat history for failure patterns and identify gaps in rules system.

`uv run .cursor/skills/conversation-history/scripts/analyze-failure-patterns.py`

### analyze-subagent-usage.py
Analyze chat history for subagent usage patterns.

`uv run .cursor/skills/conversation-history/scripts/analyze-subagent-usage.py`

### map-patterns-to-rules.py
Map failure patterns to existing rules and identify gaps.

`uv run .cursor/skills/conversation-history/scripts/map-patterns-to-rules.py`

### enhance-report.py
Enhance the failure pattern report with specific examples and detailed analysis.

`uv run .cursor/skills/conversation-history/scripts/enhance-report.py`

### backup-cursor-data.py
Comprehensive backup of Cursor data including chat history, settings, and config files.

`uv run .cursor/skills/conversation-history/scripts/backup-cursor-data.py [--output-dir <path>] [--dry-run]`

| Arg | Purpose |
|-----|---------|
| `--output-dir` | Output directory for backup |
| `--dry-run` | Show what would be backed up |

### analyze-skill-gaps.py
Cross-reference conversation failure patterns with skill/rule coverage to identify knowledge gaps.

`uv run .cursor/skills/conversation-history/scripts/analyze-skill-gaps.py [--project path] [--sessions N] [--cursor-dir path] [--format text|json]`

| Arg | Purpose |
|-----|---------|
| `--project` | Filter to conversations about a specific project |
| `--sessions` | Number of recent sessions to analyze (default: 20) |
| `--cursor-dir` | Path to .cursor directory for skill scanning |
| `--format` | Output format: `text` (default) or `json` |

### delegation-retro.py
Analyze past delegations to identify patterns that correlate with clean delivery vs. rework. Examines brief quality signals, agent type success rates, and rework triggers.

`uv run .cursor/skills/conversation-history/scripts/delegation-retro.py [--project path] [--sessions N] [--format text|json]`

| Arg | Purpose |
|-----|---------|
| `--project` | Filter by project |
| `--sessions` | Number of recent sessions to analyze (default: 30) |
| `--format` | Output format: `text` (default) or `json` |


</ANCHORSKILL-CONVERSATION-HISTORY>
