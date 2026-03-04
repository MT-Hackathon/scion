# Examples: Search-First Patterns

Examples of applying search-first discipline.

---

## Good: Targeted Search

1. Search for symbol: `grep "calculateTotal" src/`
2. Read surrounding context: `read_file target_file="src/utils.ts" offset=100 limit=20`
3. Expand if needed based on discovery.

## Bad: Broad/Blind Changes

- Editing a file without checking where else the function is used.
- Creating a new utility without checking if it already exists.
