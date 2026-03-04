#!/usr/bin/env -S uv run --python 3.12
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""
Add decision criteria to 4 personas missing them.
"""
from pathlib import Path

criteria = {
    ".cursor/personas/documentation-persona.md": """

## Decision Criteria

**When to apply this persona:**
- Generating technical documentation, README files, or API docs
- Explaining complex features in user-friendly language
- Creating architecture diagrams or flow documentation
- Writing runbook/troubleshooting guides

**When NOT to apply:**
- Code implementation (use developer persona)
- UX/UI design decisions (use designer persona)
- Performance optimization without docs
- Debugging code issues
""",
    ".cursor/personas/file-creator-persona.md": """

## Decision Criteria

**When to apply this persona:**
- Creating new scaffolding files (.cursor/rules, skills, context)
- Organizing documentation structure
- Setting up project templates
- Batch creating similar files

**When NOT to apply:**
- Editing existing code files
- Running code or tests
- Debugging issues
- Making architectural decisions
""",
    ".cursor/personas/redundancy-detector-persona.md": """

## Decision Criteria

**When to apply this persona:**
- Searching for existing functionality before writing new code
- Identifying duplicate code or patterns
- Checking for repeated implementations
- Preventing feature duplication

**When NOT to apply:**
- Performance optimization
- Architecture design
- Testing/debugging
- UI/UX decisions
""",
    ".cursor/personas/simulation-persona.md": """

## Decision Criteria

**When to apply this persona:**
- Testing resilience and failure scenarios
- Chaos engineering and fault injection
- Load and stress testing
- Performance benchmarking under edge cases

**When NOT to apply:**
- Unit testing normal behavior
- Integration testing happy path
- Documentation writing
- Feature implementation
""",
}

PROJECT_ROOT = Path(__file__).resolve().parents[4]
base_path = PROJECT_ROOT

for file_path, criteria_text in criteria.items():
    full_path = base_path / file_path
    if not full_path.exists():
        print(f"✗ {file_path} not found")
        continue

    content = full_path.read_text()

    # Check if already has decision criteria
    if "decision criteria" in content.lower() or "when to apply" in content.lower():
        print(f"✓ {Path(file_path).name} already has decision criteria")
        continue

    # Add before References if it exists
    if "## References" in content or "## Reference" in content:
        content = content.replace("## References", criteria_text + "\n\n## References")
        content = content.replace("## Reference", criteria_text + "\n\n## Reference")
    else:
        # Add before closing anchor or at end
        if "</ANCHOR" in content:
            content = content.replace("\n</ANCHOR", criteria_text + "\n\n</ANCHOR")
        else:
            content = content.rstrip() + criteria_text

    full_path.write_text(content)
    print(f"✓ Added decision criteria to {Path(file_path).name}")

print("\nDone!")
