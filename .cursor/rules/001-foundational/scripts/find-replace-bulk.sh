#!/bin/bash
# Description: Find and replace patterns across codebase with parameters, process outside context
# Usage: 821-find-replace-bulk.sh [find_pattern] [replace_text] [optional-path] [optional-file-type]

set -e

# Check for required tools
command -v rg >/dev/null 2>&1 || { echo "Error: ripgrep not found. Install: cargo install ripgrep"; exit 2; }

if [ $# -lt 2 ]; then
  echo "Usage: $0 [find_pattern] [replace_text] [optional-path] [optional-file-type]"
  echo ""
  echo "Examples:"
  echo "  $0 'old_function' 'new_function'"
  echo "  $0 'from src.core' 'from src.backend.core' src/ py"
  exit 2
fi

FIND_PATTERN="$1"
REPLACE_TEXT="$2"
SEARCH_PATH="${3:-.}"
FILE_TYPE="${4:-}"

echo "Find-Replace Preview"
echo "Pattern: $FIND_PATTERN"
echo "Replace with: $REPLACE_TEXT"
echo "Path: $SEARCH_PATH"

# Build ripgrep command with optional file type filter
RG_CMD="rg --files-with-matches"
if [ -n "$FILE_TYPE" ]; then
  RG_CMD="$RG_CMD --type $FILE_TYPE"
fi

# Get affected files (respects .gitignore automatically)
FILES_FOUND=$($RG_CMD "$FIND_PATTERN" "$SEARCH_PATH" 2>/dev/null || echo "")

if [ -z "$FILES_FOUND" ]; then
  echo "No occurrences found"
  exit 1
fi

# Count occurrences per file
echo "Files affected:"
FILE_COUNT=0
TOTAL_COUNT=0
while IFS= read -r file; do
  count=$(rg --count "$FIND_PATTERN" "$file" 2>/dev/null | cut -d: -f2)
  TOTAL_COUNT=$((TOTAL_COUNT + count))
  FILE_COUNT=$((FILE_COUNT + 1))
  echo "$file: $count occurrence(s)"
done <<< "$FILES_FOUND" | sort -t: -k2 -rn
echo "Total: $FILE_COUNT files, $TOTAL_COUNT occurrences"

# Show sample changes (first 3 matches)
echo "Sample matches:"
rg --context 1 --max-count 3 "$FIND_PATTERN" "$SEARCH_PATH" 2>/dev/null || true
echo ""
echo "To apply changes:"
echo "WARNING: This script only shows preview. Use with caution!"
echo ""
echo "Recommended: Use 'sd' tool (install: cargo install sd) for safe string replacement:"
if [ -n "$FILE_TYPE" ]; then
  echo "  rg --type $FILE_TYPE --files-with-matches '$FIND_PATTERN' '$SEARCH_PATH' | xargs sd '$FIND_PATTERN' '$REPLACE_TEXT'"
else
  echo "  rg --files-with-matches '$FIND_PATTERN' '$SEARCH_PATH' | xargs sd '$FIND_PATTERN' '$REPLACE_TEXT'"
fi
echo ""
echo "Alternative (requires escaping special regex chars in FIND_PATTERN):"
echo "  # First escape special characters in FIND_PATTERN for sed"
echo "  ESCAPED_FIND=\$(echo '$FIND_PATTERN' | sed 's/[[\.*^$()+?{|]/\\\\&/g')"
echo "  ESCAPED_REPLACE=\$(echo '$REPLACE_TEXT' | sed 's/[[\.*^$()+?{|]/\\\\&/g')"
if [ -n "$FILE_TYPE" ]; then
  echo "  rg --type $FILE_TYPE --files-with-matches '$FIND_PATTERN' '$SEARCH_PATH' | xargs sed -i \"s/\$ESCAPED_FIND/\$ESCAPED_REPLACE/g\""
else
  echo "  rg --files-with-matches '$FIND_PATTERN' '$SEARCH_PATH' | xargs sed -i \"s/\$ESCAPED_FIND/\$ESCAPED_REPLACE/g\""
fi
echo ""
echo "NOTE: Patterns containing special regex characters (., *, ^, $, etc.) may not work correctly with sed."
echo "      Use 'sd' tool for reliable literal string replacement."

exit 0
