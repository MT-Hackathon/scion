# Delegation Script Reference

These scripts help manage and discover agents in a multi-agent environment.

| Script | Purpose |
|--------|---------|
| `build-brief.py` | Brief builder that auto-populates delegation briefs with context from codebase-sense, git history, and skill manifests. |
| `build_agent_catalog.py` | Generates a persistent markdown catalog of agents and their topics for cross-thread memory. |
| `list_agents.py` | Lists available agents for a project or discovers all project hashes in the environment. |
| `search_agents.py` | Searches agent prompt history for keywords to find specialists for resume/briefing. |

## Usage Details

### build_agent_catalog.py
Builds a persistent agent catalog to help navigate which agents handled which domains.

`uv run build_agent_catalog.py <project_hash> [--output <path>] [--limit N]`

| Arg | Purpose |
|-----|---------|
| `<project_hash>` | 32-character hex string identifying the project |
| `--output` | Path where the markdown catalog will be written (default: .cursor/handoffs/agent-catalog.md) |
| `--limit` | Maximum number of agents to include in the catalog (default: 30) |

### build-brief.py
**DEPRECATED** — use `query-cascade.py` in codebase-sense for pre-dispatch intelligence.

Brief builder that auto-populates delegation briefs with context from codebase-sense, git history, and skill manifests.

`uv run .cursor/skills/delegation/scripts/build-brief.py --task "description" --agent executor [--files path1 path2] [--workspace path]`

### list_agents.py
Lists agents for a specific project with creation dates and names.

`uv run list_agents.py [project_hash] [--list-projects] [--limit N] [--with-prompts] [--json]`

| Arg | Purpose |
|-----|---------|
| `[project_hash]` | Project hash (required unless --list-projects is used) |
| `--list-projects` | Lists all available project hashes instead of agents |
| `--limit` | Maximum number of agents to display (default: 20) |
| `--with-prompts` | Includes a preview of the initial prompt for each agent |
| `--json` | Returns the output in JSON format |

### search_agents.py
Searches the conversation history (initial prompts) of all agents in a project for specific keywords.

`uv run search_agents.py <project_hash> <query> [--limit N] [--json]`

| Arg | Purpose |
|-----|---------|
| `<project_hash>` | 32-character hex string identifying the project |
| `<query>` | Keyword or phrase to search for (case-insensitive) |
| `--limit` | Maximum number of matches to return (default: 10) |
| `--json` | Returns the output in JSON format |
