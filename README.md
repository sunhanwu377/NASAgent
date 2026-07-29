# NASAgent

NASAgent is a Python CLI AI agent for operating NAS devices safely.

Phase 1 focuses on an extensible architecture, simulator-backed NAS tools, OpenAI planning, ReAct-style execution, and UGREEN NAS integration boundaries.

## Development

```bash
uv sync --all-extras --dev
uv run pytest
uv run ruff check .
uv run mypy src
```
