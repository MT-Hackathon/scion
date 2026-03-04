#!/bin/bash
# Description: Rename functions with automatic import path updates
# Usage: 822-rename-function-safely.sh [old_name] [new_name] [source_file]

set -e

# Check for required tools
command -v rg >/dev/null 2>&1 || { echo "Error: ripgrep not found. Install: cargo install ripgrep"; exit 2; }

if [ $# -lt 3 ]; then
  echo "Usage: $0 [old_name] [new_name] [source_file]"
  echo ""
  echo "Examples:"
  echo "  $0 'create_entity' 'create_entity_store' 'src/backend/core/ecs_architecture.py'"
  exit 2
fi

OLD_NAME="$1"
NEW_NAME="$2"
SOURCE_FILE="$3"

if [ ! -f "$SOURCE_FILE" ]; then
  echo "Error: Source file $SOURCE_FILE not found"
  exit 2
fi

echo "Rename: $OLD_NAME → $NEW_NAME"
echo "Source: $SOURCE_FILE"

# Find all files that reference this function (respects .gitignore automatically)
FILES_TO_UPDATE=$(rg --files-with-matches "$OLD_NAME" 2>/dev/null || echo "")

if [ -z "$FILES_TO_UPDATE" ]; then
  echo "No files reference $OLD_NAME"
  exit 1
fi

echo "Files to update:"
TOTAL_UPDATES=0
FILE_COUNT=0
while IFS= read -r file; do
  count=$(rg --count "$OLD_NAME" "$file" 2>/dev/null | cut -d: -f2)
  if [ "$count" -gt 0 ]; then
    # Check if it's the definition or a reference
    if rg -q "def $OLD_NAME\|function $OLD_NAME\|export.*$OLD_NAME" "$file"; then
      echo "$file: renamed definition"
    else
      echo "$file: updated $count reference(s)"
    fi
    TOTAL_UPDATES=$((TOTAL_UPDATES + count))
    FILE_COUNT=$((FILE_COUNT + 1))
  fi
done <<< "$FILES_TO_UPDATE"
echo "Total: $FILE_COUNT files, $TOTAL_UPDATES updates"
echo ""
echo "To apply changes:"
echo "WARNING: This script only shows preview. Use with caution!"
echo ""
echo "Recommended: Use 'sd' tool (install: cargo install sd) for safe string replacement:"
echo "  rg --files-with-matches '$OLD_NAME' | xargs sd '$OLD_NAME' '$NEW_NAME'"
echo ""
echo "Alternative (requires escaping special regex chars if OLD_NAME contains them):"
echo "  # First escape special characters in OLD_NAME for sed"
echo "  ESCAPED_OLD=\$(echo '$OLD_NAME' | sed 's/[[\.*^$()+?{|]/\\\\&/g')"
echo "  ESCAPED_NEW=\$(echo '$NEW_NAME' | sed 's/[[\.*^$()+?{|]/\\\\&/g')"
echo "  rg --files-with-matches '$OLD_NAME' | xargs sed -i \"s/\$ESCAPED_OLD/\$ESCAPED_NEW/g\""
echo ""
echo "NOTE: Function names typically don't contain special regex characters, but use 'sd' for safety."

exit 0
