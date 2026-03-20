---
name: script-authoring
description: "Governs authoring of portable operator scripts in `.cursor/skills/*/scripts/`. Use when writing, extending, or reviewing a utility script for a skill — covers PEP 723 inline metadata, uv run --script invocation, subcommand arg design, output conventions (stderr/stdout split, exit codes), batch git-read patterns, manifest registration, and the tool-ready script posture. DO NOT use for Cursor hooks (see hooks-infrastructure) or skill structure design (see skill-authoring-patterns)."
---

<ANCHORSKILL-SCRIPT-AUTHORING>

# Script Authoring

Patterns for writing portable, composable operator scripts that live in skill `scripts/` folders. A well-authored script is a first-class tool — inspectable, testable, and callable programmatically without modification.

## Table of Contents

- [Script vs Hook vs MCP](#script-vs-hook-vs-mcp)
- [PEP 723 Starter Template](#pep-723-starter-template)
- [Arg Design Patterns](#arg-design-patterns)
- [Output Contract](#output-contract)
- [Portability Mandates](#portability-mandates)
- [Batch Git-Read Pattern](#batch-git-read-pattern)
- [Manifest Registration](#manifest-registration)
- [Tool-Ready Posture](#tool-ready-posture)
- [Cross-References](#cross-references)

## Script vs Hook vs MCP

This decision determines where capability lives and how it activates. Get it wrong and either the AI can't reach it or the operator can't inspect it.

**Write a script** when:
- The work is operator-initiated — a human or agent invokes it explicitly.
- The operation is deterministic and benefits from structured output that another tool can consume.
- Portability matters: the script must run from any directory on any OS via `uv run --script`.
- You want it to be inspectable, version-controlled, and cataloged in a skill manifest.

**Write a hook** (see [hooks-infrastructure](../hooks-infrastructure/SKILL.md)) when:
- The trigger is a Cursor IDE lifecycle event (`sessionStart`, `stop`, `subagentStop`, etc.).
- The script must read JSON from stdin and emit JSON to stdout.
- Silent failure on crash is acceptable — hooks cannot block the IDE.

**Write an MCP tool** (see [mcp-design](../mcp-design/SKILL.md)) when:
- The capability must be available to the AI model at runtime, without operator invocation.
- State persistence across calls is required (server lifecycle, open connections).
- The tool needs to appear in the model's tool surface automatically.

The differentiator: scripts compose via shell pipes and subprocess; hooks compose via Cursor event chains; MCP tools compose via model-initiated tool calls. A script that could plausibly be called by an MCP tool is not a reason to make it an MCP tool — the script is still the right artifact; the MCP tool calls it.

## PEP 723 Starter Template

Operator scripts use `--script` in the shebang, not `--python 3.12`. Both work, but `--script` is the canonical operator form: it respects the `/// script` dependency block and does not pin a global interpreter.

```python
#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///

"""One-line description of what this script does."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

EXIT_SUCCESS = 0
EXIT_ERROR = 1


def log(message: str) -> None:
    """Emit human-readable status to stderr."""
    sys.stderr.write(f"{message}\n")


def fail(message: str) -> int:
    """Emit standardized failure message to stderr."""
    log(f"ERROR: {message}")
    return EXIT_ERROR


def parse_args(argv: list[str]) -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(
        prog="my-script.py",
        description="Description shown in --help.",
    )
    # add arguments here
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Script entrypoint."""
    args = parse_args(sys.argv[1:] if argv is None else argv)
    try:
        # main logic here
        return EXIT_SUCCESS
    except Exception as exc:  # noqa: BLE001
        return fail(str(exc))


if __name__ == "__main__":
    raise SystemExit(main())
```

Distinguish this from the hook template in [hooks-infrastructure](../hooks-infrastructure/SKILL.md): no `sys.stdin`, no `json.dump` to stdout, no swallowed exceptions. Operator scripts surface errors loudly via non-zero exit codes.

## Arg Design Patterns

**Subcommand architecture** — use when the script has distinct operational modes:

```python
parser = argparse.ArgumentParser(prog="my-script.py", description="...")
subparsers = parser.add_subparsers(dest="command", required=True)

list_cmd = subparsers.add_parser("list", help="List available items.")
export_cmd = subparsers.add_parser("export", help="Export selected items.")
add_shared_args(list_cmd)
add_shared_args(export_cmd)
```

`dest="command"` with `required=True` is the canonical shape. Group shared args into helper functions (`add_shared_args`, `add_source_args`) to avoid flag duplication across subparsers.

**Repeatable flags** — for multi-value selection:
```python
parser.add_argument("--skill", action="append", default=[], metavar="SKILL_NAME",
    help="Include a skill; repeat for multiple.")
```

**`--all` escape hatch** — explicit opt-in to the full set, never a default:
```python
parser.add_argument("--all", action="store_true",
    help="Explicitly include all available items.")
```

**`--ref`** — git ref with stable default; always annotate the default in help text:
```python
parser.add_argument("--ref", default="main",
    help="Git ref to read from (default: main).")
```

**`--target` as primary axis** — what you are operating on. `--format` is output rendering and is secondary. Never conflate them.

## Output Contract

| Channel | Content | Pattern |
|---------|---------|---------|
| stderr | Human-readable status, progress, errors | `log()` function |
| stdout | Machine-readable output for callers | `print()` or `json.dumps()` |
| exit code | The return contract — callers depend on this | `0` success, `1` error |

When a caller needs to parse output, emit `json.dumps(payload, indent=2)` to stdout. For human-facing output, emit clean plain text. Never mix human prose into stdout — that breaks piped consumers.

`--format json` convention: add `choices=("text", "json")` with `default="text"` when the script has programmatic callers. Emit JSON to stdout when selected; plain text otherwise.

## Portability Mandates

- `PurePosixPath` for all git-relative paths — git paths are always POSIX, regardless of host OS.
- `Path` for local filesystem paths — `Path` handles Windows/POSIX transparently.
- No workspace-coupled imports — no `from app.foo import bar`, no `sys.path` manipulation. The script must run from any directory.
- Invoke via `uv run --script path/to/script.py` — never rely on the shebang alone, which breaks on Windows.
- Standard library only in `dependencies = []` unless external packages are genuinely required.

## Batch Git-Read Pattern

Per-file `git show` is a subprocess per file. For N files, that is N process spawns. Use `git cat-file --batch` to read all blobs in one call.

```python
from pathlib import Path, PurePosixPath
import subprocess


def batch_read_files(
    repo_path: Path,
    ref: str,
    paths: list[PurePosixPath],
) -> dict[PurePosixPath, str]:
    """Read multiple git blobs in a single cat-file batch."""
    if not paths:
        return {}
    payload = "".join(f"{ref}:{p.as_posix()}\n" for p in paths).encode("utf-8")
    completed = subprocess.run(
        ["git", "cat-file", "--batch"],
        cwd=repo_path,
        input=payload,
        capture_output=True,
        check=False,
        timeout=120,
    )
    raw = completed.stdout
    offset = 0
    result: dict[PurePosixPath, str] = {}

    for path in paths:
        header_end = raw.find(b"\n", offset)
        header = raw[offset:header_end].decode("utf-8", "replace")
        offset = header_end + 1

        if header.endswith(" missing"):
            raise RuntimeError(f"Object missing: {ref}:{path.as_posix()}")

        _, object_type, raw_size = header.split(" ")
        if object_type != "blob":
            raise RuntimeError(f"Expected blob for {path.as_posix()}, got {object_type}")

        size = int(raw_size)
        blob = raw[offset : offset + size]
        offset += size + 1  # skip trailing newline delimiter

        if b"\x00" in blob:
            raise ValueError(f"Binary file not supported: {path.as_posix()}")

        result[path] = blob.decode("utf-8", "replace")

    return result
```

The header format is `<sha> <type> <size>\n` followed by `<size>` bytes then `\n`. The `offset += size + 1` skips the delimiter newline — missing this shifts all subsequent reads by one byte and produces corrupt output with no error.

## Manifest Registration

A script that is not in the parent skill's Script Manifest is invisible to tooling. `package-skills.py` reads the manifest table (`## Script Manifest` section) to populate bundle metadata; a missing entry shows as "Purpose not declared in skill manifest."

**When you write a script, update the manifest before returning.** Format:

```markdown
## Script Manifest

| Script | Purpose |
|--------|---------|
| `my-script.py` | Short verb-phrase describing what the script does |
```

**Example column (optional)**: Add a third `Example` column when a single happy-path invocation materially clarifies usage — particularly when the script has non-obvious flags or is the primary tool in the skill. One line, one command, no commentary. When many scripts need examples or invocations are long, keep the 2-column table and add a `### Common Invocations` section beneath it for the top 1–3 scripts.

```markdown
| Script | Purpose | Example |
|--------|---------|---------|
| `my-script.py` | Short verb-phrase describing what the script does | `uv run --script scripts/my-script.py --flag value` |
```

The module docstring's first line is the fallback (`ast.get_docstring(module)`), but the manifest is authoritative. Keep them consistent.

## Tool-Ready Posture

Scripts in `skills/*/scripts/` are peers to MCP tools — they run via CLI instead of stdio, but the contract is the same: deterministic input, predictable output, stable exit codes.

- The module docstring first line is the script's declared purpose — write it as a complete sentence, not a fragment.
- `--format json` output is the integration surface. When adding programmatic callers, add this flag rather than parsing stdout text.
- Scripts are callable from subprocess: `subprocess.run(["uv", "run", "--script", "script.py", ...], capture_output=True)` — design the arg surface with this invocation in mind.
- Named constants (`EXIT_SUCCESS = 0`, `EXIT_ERROR = 1`) at module level make the exit contract explicit and greppable.

## Cross-References

- [hooks-infrastructure](../hooks-infrastructure/SKILL.md) — Cursor hook-specific patterns: BOM-strip, JSON emit, event payload contract, stdin reading.
- [skill-authoring-patterns](../skill-authoring-patterns/SKILL.md) — skill folder layout, placement decisions, and when to add a `scripts/` folder.
- [mcp-design](../mcp-design/SKILL.md) — when a tool surface needs a persistent server rather than a CLI script.

</ANCHORSKILL-SCRIPT-AUTHORING>
