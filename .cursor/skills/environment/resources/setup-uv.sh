#!/usr/bin/env bash
# Install uv if not present
if command -v uv &> /dev/null; then
    echo "uv already installed: $(uv --version)"
    exit 0
fi
curl -LsSf https://astral.sh/uv/install.sh | sh
echo "Restart your terminal or run: source ~/.bashrc"
