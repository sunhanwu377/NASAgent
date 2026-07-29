# NASAgent

NASAgent is a Python CLI AI agent for operating NAS devices safely.

Phase 1 provides an extensible package-first framework with OpenAI planning, ReAct-style step execution, simulator-backed NAS tools, UGREEN adapter boundaries, Rich CLI output, safety policy, tests, documentation, and GitHub/Gitea CI definitions.

## Quick Start

```bash
uv sync --all-extras --dev
uv run nasagent tools list
uv run nasagent run "check storage" --profile simulator
```

## Development

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run mypy src
```

## Documentation

- `docs/architecture.md`
- `docs/agent-flow.md`
- `docs/adapters.md`
- `docs/tools.md`
- `docs/cli.md`
- `docs/configuration.md`
- `docs/development.md`
- `docs/packaging.md`
