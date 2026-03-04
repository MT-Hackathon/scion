#!/bin/bash
# Description: Process log files, extract error patterns, and create error summaries
# Usage: 842-aggregate-logs.sh [log-file] [optional-level]

set -e

# Check for required tools
command -v rg >/dev/null 2>&1 || { echo "Error: ripgrep not found. Install: cargo install ripgrep"; exit 2; }

if [ $# -lt 1 ]; then
  echo "Usage: $0 [log-file] [optional-level]"
  echo ""
  echo "Examples:"
  echo "  $0 universal_api.log"
  echo "  $0 universal_api.log ERROR"
  exit 2
fi

LOG_FILE="$1"
LEVEL="${2:-}"

if [ ! -f "$LOG_FILE" ]; then
  echo "Error: Log file $LOG_FILE not found"
  exit 2
fi

echo "Log Analysis"

# Count total entries
TOTAL_LINES=$(wc -l < "$LOG_FILE")
echo "Total entries: $TOTAL_LINES"

# Count by level using ripgrep
# Handle ripgrep output format: "filepath:count" or empty if no matches
count_level() {
  local pattern="$1"
  local result
  result=$(rg --count "$pattern" "$LOG_FILE" 2>/dev/null || echo "")
  if [ -z "$result" ]; then
    echo 0
  else
    # Extract count from "filepath:count" format
    echo "$result" | cut -d: -f2 | head -1
  fi
}

INFO_COUNT=$(count_level '\[INFO\]|\[INFO ')
WARNING_COUNT=$(count_level '\[WARNING\]|\[WARNING ')
ERROR_COUNT=$(count_level '\[ERROR\]|\[ERROR ')
DEBUG_COUNT=$(count_level '\[DEBUG\]|\[DEBUG ')

echo "Levels: INFO ($INFO_COUNT), WARNING ($WARNING_COUNT), ERROR ($ERROR_COUNT), DEBUG ($DEBUG_COUNT)"

# If level specified, filter; otherwise default to ERROR
if [ -n "$LEVEL" ]; then
  FILTER_PATTERN="\[$LEVEL\]"
else
  FILTER_PATTERN="\[ERROR\]"
fi

echo "Top Patterns:"
# Extract error messages and count occurrences
PATTERN_COUNT=$(rg --count "$FILTER_PATTERN" "$LOG_FILE" 2>/dev/null | cut -d: -f2 | head -1 || echo 0)
if [ "$PATTERN_COUNT" -eq 0 ]; then
  echo "  No $FILTER_PATTERN entries found"
else
  rg "$FILTER_PATTERN" "$LOG_FILE" 2>/dev/null | \
    sed 's/^.*\] //' | \
    sort | uniq -c | sort -rn | head -10 | \
    while read -r count message; do
      echo "$count: $(echo "$message" | cut -c1-80)"
    done
fi

exit 0
