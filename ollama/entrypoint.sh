#!/bin/bash
set -eux

# Start ollama serve in the background
ollama serve &
pid=$!

# Wait for the server to be ready
t=0
until curl -sSf --max-time 2 http://127.0.0.1:11434 > /dev/null; do
  if [ "$t" -ge 300 ]; then echo "Timeout waiting for ollama server"; exit 1; fi
  echo "Waiting for ollama server to start..."
  sleep 1
  t=$((t+1))
done

# Pull models if they don't exist
if [ -n "${BUILT_IN_OLLAMA_MODELS}" ]; then
  echo "Models to ensure: ${BUILT_IN_OLLAMA_MODELS}"
  echo "${BUILT_IN_OLLAMA_MODELS}" | tr ',' '
' | while IFS= read -r model; do
    model=$(echo "$model" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
    if [ -n "$model" ]; then
      # Check if model exists
      if ! ollama list | grep -q "^${model}"; then
        echo "Pulling model: $model"
        if ! ollama pull "$model"; then
          echo "ERROR: Failed to pull model: $model" >&2
          exit 1
        fi
      else
        echo "Model already exists: $model"
      fi
    fi
  done
fi

# Wait for the background process to exit
wait $pid
