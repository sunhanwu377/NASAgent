# NASAgent

> AI-assisted NAS automation from the command line, built for safe operations, extensible plugins, and local-first control.

## Why NASAgent

NASAgent helps homelab and NAS users inspect storage, operate files, manage apps, and automate deployment workflows through a safety-aware CLI agent.

## Features

- Safety-aware ReAct-style execution.
- Simulator-backed development mode.
- Extensible tool and command registries.
- Python plugin entry points.
- LAN discovery foundation with vendor probe support.
- Local secrets file with redacted output.
- Docker and NAS app integration foundations.

## Status

NASAgent is early-stage. Simulator tools are usable today. Docker, AList, Lucky, Vaultwarden, Cloudflare, and sun-panel support are being added incrementally and are not all production-ready.

## Quick Start

```bash
uv sync --all-extras --dev
uv run nasagent tools list
uv run nasagent run "check storage" --profile simulator
```

## CLI Examples

```bash
uv run nasagent config init
uv run nasagent tools list
uv run nasagent apps list
uv run nasagent plugins list
uv run nasagent containers list
```

## Chat Examples

```bash
uv run nasagent chat
/help
/apps
/plugins
/containers
```

## Integrations

| Integration | Status | Notes |
| --- | --- | --- |
| Simulator NAS | Available | Safe local development and tests |
| UGREEN NAS | Boundary | Awaiting verified API details |
| Docker | Foundation | SDK tools and guarded Compose operations |
| AList | Minimal | Auth and filesystem tool foundation |
| Lucky | Planned | API must be verified before write tools |
| Vaultwarden | Minimal | Targets Vaultwarden, not official Bitwarden cloud APIs |
| Cloudflare | Plugin target | Intended as third-party plugin example |
| sun-panel | Planned | Future app publishing flow |

## Safety

Tools are classified as `read`, `write`, `destructive`, or `system`. Higher-risk operations require confirmation and continue through NASAgent's safety policy.

## Configuration And Secrets

Non-sensitive config lives in `~/.config/nasagent/config.toml`. Tokens and API keys live in `~/.local/share/nasagent/secrets.toml` with `0600` permissions and are redacted by default.

## Documentation

- `docs/architecture.md`
- `docs/agent-flow.md`
- `docs/tools.md`
- `docs/cli.md`
- `docs/configuration.md`
- `docs/discovery.md`
- `docs/plugins.md`
- `docs/development.md`
- `docs/packaging.md`

## Development

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run mypy src
```
