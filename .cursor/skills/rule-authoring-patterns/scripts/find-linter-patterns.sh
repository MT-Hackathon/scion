#!/bin/bash
# Description: Identify common linter violations and patterns to fix
# Usage: 833-find-linter-patterns.sh [optional-path]

set -e

# Check for required tools
command -v rg >/dev/null 2>&1 || { echo "Error: ripgrep not found. Install: cargo install ripgrep"; exit 2; }

SEARCH_PATH="${1:-.}"

echo "Common Linter Patterns"

# Check for trailing whitespace
echo "Trailing whitespace:"
TRAILING_COUNT=$(rg --count ' $' --type py "$SEARCH_PATH" 2>/dev/null | wc -l || echo 0)
if [ "$TRAILING_COUNT" -gt 0 ]; then
  rg --count ' $' --type py "$SEARCH_PATH" 2>/dev/null | head -5 | while IFS=: read -r file count; do
    echo "  $file: $count instance(s)"
  done
else
  echo "  None found"
fi
echo "Long lines (>100 chars):"
LONG_LINES=$(rg --count '.{101,}' --type py "$SEARCH_PATH" 2>/dev/null | head -5)
if [ -n "$LONG_LINES" ]; then
  echo "$LONG_LINES" | while IFS=: read -r file count; do
    echo "  $file: $count instance(s)"
  done
else
  echo "  None found"
fi
echo "Multiple imports on one line:"
MULTI_IMPORTS=$(rg --count '^import .*, ' --type py "$SEARCH_PATH" 2>/dev/null | head -5)
if [ -n "$MULTI_IMPORTS" ]; then
  echo "$MULTI_IMPORTS" | while IFS=: read -r file count; do
    echo "  $file: $count instance(s)"
  done
else
  echo "  None found"
fi
echo "Priorities: 1) trailing whitespace 2) long lines 3) split imports"

exit 0
