---
name: codebase-sense
description: "Generates codebase briefings from structural and behavioral graph analysis across sibling git repositories. Use when analyzing codebase structure, reviewing dependency graphs, understanding change hotspots, or generating session context briefings. DO NOT use for conversation history search (see conversation-history) or codebase-wide text search."
---

<ANCHORSKILL-CODEBASE-SENSE>

# Codebase Sense

Use this skill for codebase analysis, proprioception, structural graph checks, and briefing generation.

## Entry Point

- Script: `scripts/briefing.py`
- CLI: `uv run .cursor/skills/codebase-sense/scripts/briefing.py <workspace_path> --max-lines <n>`
- Required args: workspace path
- Optional args: `--max-lines` (default `120`)
- Output: markdown briefing to stdout
- Script: `scripts/generate-arch-diagram.py`
- CLI: `uv run .cursor/skills/codebase-sense/scripts/generate-arch-diagram.py [--workspace path] [--type dependency|module|risk] [--scope filter] [--output path] [--max-nodes N]`
- Required args: none
- Optional args: `--workspace`, `--type`, `--scope`, `--output`, `--max-nodes`
- Output: Mermaid architecture diagram from structural/risk analysis
- Script: `scripts/query-cascade.py`
- CLI: `uv run .cursor/skills/codebase-sense/scripts/query-cascade.py <file1> [file2] [file3] [--workspace path] [--format text|json]`
- Required args: at least one file path
- Optional args: `--workspace`, `--format`
- Output: Risk scores, co-change predictions, structural dependencies, and governing skills for specified files — fast cache lookup for pre-dispatch cascade intelligence

## Dependencies

- `networkx`
- `numpy`

## Known Limitations

- **Cascade predictions are commit correlation**: Co-change data captures commit patterns, not dependency cascades. Filters applied (commit-size cap ≤8, ubiquitous-file suppression >40%, min evidence ≥3), but the signal remains correlational. Apply appropriate skepticism.
- **Boundary health requires graph density**: Gated behind 30+ connected nodes. Sparse import graphs (few cross-file dependencies) produce unreliable community detection.

## Cross-References

- [Temporal Self](../temporal-self/SKILL.md) — authored self-portrait and session memory (behavioral layer)
- [Conversation History](../conversation-history/SKILL.md) — search past sessions for specific decisions or solutions
- [Rule 999](../../rules/999-codebase-briefing/RULE.mdc) — the generated session briefing injected at session start

</ANCHORSKILL-CODEBASE-SENSE>
