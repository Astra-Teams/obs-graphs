# Use the official Ollama image as the base
FROM ollama/ollama

# Argument to specify the models to be pulled during the build (comma-separated)
ARG BUILT_IN_OLLAMA_MODELS="tinyllama:1.1b"
ENV BUILT_IN_OLLAMA_MODELS=${BUILT_IN_OLLAMA_MODELS}

# Set the host to 0.0.0.0 to allow connections from other containers
ENV OLLAMA_HOST=0.0.0.0

# Install curl, which is used for healthcheck polling.
USER root
RUN apt-get update && \
  apt-get install -y --no-install-recommends curl && \
  rm -rf /var/lib/apt/lists/*

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Add a healthcheck to ensure the Ollama server is responsive
HEALTHCHECK --interval=10s --timeout=5s --start-period=300s --retries=30 \
  CMD curl -fsS http://127.0.0.1:11434 >/dev/null || exit 1

ENTRYPOINT ["/entrypoint.sh"]
