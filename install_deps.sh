#!/bin/bash
# Script to install dependencies with optional git authentication

set -e

# Use GITHUB_OLLAMA_DEEP_RESEARCHER_TOKEN for private git dependencies
if [ -n "$GITHUB_OLLAMA_DEEP_RESEARCHER_TOKEN" ]; then
    git config --global url."https://${GITHUB_OLLAMA_DEEP_RESEARCHER_TOKEN}@github.com/".insteadOf "https://github.com/"
fi

# Install dependencies
if [ "$1" = "--no-dev" ]; then
    uv sync --no-dev
else
    uv sync
fi

# Clean up git config
if [ -n "$GITHUB_OLLAMA_DEEP_RESEARCHER_TOKEN" ]; then
    git config --global --unset url."https://${GITHUB_OLLAMA_DEEP_RESEARCHER_TOKEN}@github.com/".insteadOf || true
fi