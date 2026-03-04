#!/bin/bash
# Description: Locate TODO/FIXME comments with context and file locations
# Usage: 831-find-todos.sh [optional-type] [optional-path]

set -e

# Check for required tools
command -v rg >/dev/null 2>&1 || { echo "Error: ripgrep not found. Install: cargo install ripgrep"; exit 2; }

TYPE="${1:-TODO|FIXME}"
SEARCH_PATH="${2:-.}"

echo "Searching for: $TYPE"

# Use ripgrep with line numbers (respects .gitignore automatically)
RESULTS=$(rg --line-number "$TYPE" "$SEARCH_PATH" 2>/dev/null || echo "")

if [ -z "$RESULTS" ]; then
  echo "No $TYPE items found"
  exit 1
fi

echo "Items found:"

# Group by file
current_file=""
while IFS= read -r line; do
  file=$(echo "$line" | cut -d: -f1)
  lineno=$(echo "$line" | cut -d: -f2)
  content=$(echo "$line" | cut -d: -f3-)
  
  if [ "$file" != "$current_file" ]; then
    if [ -n "$current_file" ]; then
      echo ""
    fi
    echo "$file:"
    current_file="$file"
  fi
  
  echo "  Line $lineno:$content"
done <<< "$RESULTS"

TODO_COUNT=$(echo "$RESULTS" | grep -c "TODO" || echo 0)
FIXME_COUNT=$(echo "$RESULTS" | grep -c "FIXME" || echo 0)
FILE_COUNT=$(echo "$RESULTS" | cut -d: -f1 | sort -u | wc -l)

echo "Total: $((TODO_COUNT + FIXME_COUNT)) items in $FILE_COUNT files"

exit 0
