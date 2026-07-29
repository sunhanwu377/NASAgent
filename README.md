# NASAgent

NASAgent is a Python CLI AI agent for operating NAS devices safely.

Phase 1 provides an extensible package-first framework with OpenAI planning, ReAct-style step execution, simulator-backed NAS tools, UGREEN adapter boundaries, Rich CLI output, safety policy, local configuration and credential models, tests, documentation, and GitHub/Gitea CI definitions.

## Quick Start

```bash
uv sync --all-extras --dev
uv run nasagent tools list
uv run nasagent apps list
uv run nasagent plugins list
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

NASAgent includes an internal platform context that wires together registries for tools, slash-style commands, and NAS app endpoints. The plugin manager loads the built-in NAS plugin into the existing tool registry path, registers shared slash commands, and can record entry-point plugin load failures without stopping the platform.

Configuration is loaded into `NasAgentSettings`, which includes LLM, safety, observability, app endpoint, and plugin setting models. Long-lived app credentials belong in the local credential store at `~/.local/share/nasagent/secrets.toml`, while `config.toml` stores references such as `credential_key`.

`nasagent config init` writes non-sensitive settings to `~/.config/nasagent/config.toml`. If an LLM API key is entered, it is stored as `llm.api_key` in `~/.local/share/nasagent/secrets.toml`; the secrets file is created with mode `0600` and the key is not written into config TOML. `nasagent config show` keeps existing redaction behavior for sensitive values loaded into settings.

The discovery scanner has a conservative foundation for NAS service detection. mDNS and SSDP discovery functions are safe no-op placeholders today, and `DiscoveryScanner.scan_hosts([...])` probes only the explicit hosts passed to it using the registered vendor and generic probe targets. It does not perform broad LAN or subnet scanning in this task.

The CLI exposes shared platform commands through `nasagent apps list`, `nasagent plugins list`, and `nasagent containers list`. The chat REPL also dispatches slash commands such as `/help`, `/apps`, `/plugins`, `/tools`, and `/containers` before falling back to conversational or simulator task handling.

The built-in plugin registers Docker, AList, and Vaultwarden tool definitions through the same tool registry and safety policy path as NAS tools. Docker container, image, network, volume, and Compose tools are present for planning and confirmation handling; Compose command helpers build explicit `docker compose` subprocess argument lists without invoking a shell. AList and Vaultwarden tools are minimal namespaced placeholders until configured endpoint-backed handlers are wired in. Lucky currently has an endpoint/token client skeleton but no built-in tools.

Later tasks are expected to connect this foundation to app endpoint discovery, credential-backed app clients, and higher-level integrations.

## Documentation

- `docs/architecture.md`
- `docs/agent-flow.md`
- `docs/adapters.md`
- `docs/tools.md`
- `docs/cli.md`
- `docs/configuration.md`
- `docs/development.md`
- `docs/packaging.md`
