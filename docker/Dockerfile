FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates curl && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:0.5.18 /uv /usr/local/bin/uv

WORKDIR /app

ENV UV_PROJECT_ENVIRONMENT=/usr/local

COPY pyproject.toml uv.lock ./
RUN uv sync --extra web --frozen --no-dev

COPY src/ ./src/

ENV NASAGENT_OBSERVABILITY__RUN_LOG_DIR=/data/runs
ENV NASAGENT_OBSERVABILITY__MEMORY_DIR=/data/memory

VOLUME ["/root/.config/nasagent", "/root/.local/share/nasagent", "/data"]

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

ENTRYPOINT ["nasagent-web"]
