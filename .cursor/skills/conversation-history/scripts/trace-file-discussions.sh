#!/bin/bash
# Description: Find all conversations mentioning specific files
# Usage: trace-file-discussions.sh FILE_PATTERN [PROJECT_PATH]
#
# This script is a wrapper that calls the Python implementation.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_SCRIPT="$SCRIPT_DIR/trace-file-discussions.py"

# Guard: Validate Python script exists
if [[ ! -f "$PYTHON_SCRIPT" ]]; then
    echo "Error: Python script not found: $PYTHON_SCRIPT" >&2
    exit 1
fi

# Guard: Validate Python is available
if ! command -v python3 &> /dev/null; then
    echo "Error: python3 is not available" >&2
    exit 1
fi

# Guard: Validate arguments
if [[ $# -lt 1 ]]; then
    echo "Error: FILE_PATTERN is required" >&2
    echo "Usage: $0 FILE_PATTERN [PROJECT_PATH]" >&2
    exit 2
fi

python3 "$PYTHON_SCRIPT" "$@"

