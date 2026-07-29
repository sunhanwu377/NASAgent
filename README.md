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

## Platform Foundation

NASAgent includes an internal platform context that wires together registries for tools, slash-style commands, and NAS app endpoints. The current foundation keeps these registries available to the agent runtime without claiming built-in command packs, app discovery, or plugin loading yet.

Later tasks are expected to connect this foundation to plugin registration, app endpoint discovery, and higher-level integrations.

## Documentation

- `docs/architecture.md`
- `docs/agent-flow.md`
- `docs/adapters.md`
- `docs/tools.md`
- `docs/cli.md`
- `docs/configuration.md`
- `docs/development.md`
- `docs/packaging.md`
