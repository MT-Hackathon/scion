#!/bin/bash
# Description: Batch update import statements to standardize paths
# Usage: 823-update-import-paths.sh [old_import] [new_import] [optional-path]

set -e

# Check for required tools
command -v rg >/dev/null 2>&1 || { echo "Error: ripgrep not found. Install: cargo install ripgrep"; exit 2; }

if [ $# -lt 2 ]; then
  echo "Usage: $0 [old_import] [new_import] [optional-path]"
  echo ""
  echo "Examples:"
  echo "  $0 'from src.core' 'from src.backend.core'"
  echo "  $0 'import src.core' 'import src.backend.core' src/"
  exit 2
fi

OLD_IMPORT="$1"
NEW_IMPORT="$2"
SEARCH_PATH="${3:-.}"

echo "Import Path Update"
echo "Old: $OLD_IMPORT"
echo "New: $NEW_IMPORT"

# Find files with the old import (respects .gitignore automatically)
FILES_FOUND=$(rg --type py --files-with-matches "$OLD_IMPORT" "$SEARCH_PATH" 2>/dev/null || echo "")

if [ -z "$FILES_FOUND" ]; then
  echo "No files with old import found"
  exit 1
fi

echo "Files affected:"
TOTAL_UPDATES=0
FILE_COUNT=0
while IFS= read -r file; do
  count=$(rg --count "$OLD_IMPORT" "$file" 2>/dev/null | cut -d: -f2)
  if [ "$count" -gt 0 ]; then
    echo "$file: $count update(s)"
    TOTAL_UPDATES=$((TOTAL_UPDATES + count))
    FILE_COUNT=$((FILE_COUNT + 1))
  fi
done <<< "$FILES_FOUND" | sort
echo "Total: $FILE_COUNT files, $TOTAL_UPDATES imports"
echo ""
echo "To apply changes:"
echo "WARNING: This script only shows preview. Use with caution!"
echo ""
echo "Recommended: Use 'sd' tool (install: cargo install sd) for safe string replacement:"
echo "  rg --type py --files-with-matches '$OLD_IMPORT' '$SEARCH_PATH' | xargs sd '$OLD_IMPORT' '$NEW_IMPORT'"
echo ""
echo "Alternative (requires escaping special regex chars in OLD_IMPORT):"
echo "  # First escape special characters in OLD_IMPORT for sed"
echo "  ESCAPED_OLD=\$(echo '$OLD_IMPORT' | sed 's/[[\.*^$()+?{|]/\\\\&/g')"
echo "  ESCAPED_NEW=\$(echo '$NEW_IMPORT' | sed 's/[[\.*^$()+?{|]/\\\\&/g')"
echo "  rg --type py --files-with-matches '$OLD_IMPORT' '$SEARCH_PATH' | xargs sed -i \"s|\$ESCAPED_OLD|\$ESCAPED_NEW|g\""
echo ""
echo "NOTE: Import paths contain dots (.) which are special regex characters. Use 'sd' for reliable replacement."

exit 0
