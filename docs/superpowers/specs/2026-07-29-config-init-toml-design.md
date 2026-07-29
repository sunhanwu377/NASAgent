# Config Init TOML Design

## Goal

Improve the first-run configuration experience so users can run `nasagent config init` to create a local TOML configuration file and configure the LLM provider without manually discovering environment variable names.

## Current State

`nasagent config init` only prints a message. `NasAgentSettings` currently reads defaults and `NASAGENT_` environment variables. `nasagent config show` prints JSON and redacts `llm.api_key`.

## User Experience

`nasagent config init` creates `~/.config/nasagent/config.toml` when it does not exist. It prompts for LLM settings:

- `llm.provider`, default `openai`
- `llm.model`, default `gpt-4.1-mini`
- `llm.base_url`, optional
- `llm.api_key`, optional and hidden while typed

The generated file also includes safe defaults for `safety` and `observability`.

If `~/.config/nasagent/config.toml` already exists, `config init` does not overwrite it. It prints the existing path and suggests `nasagent config show`.

`nasagent config show` displays the effective configuration as TOML, not JSON. The output mirrors the config file structure and continues to redact `llm.api_key` as `********`.

## Configuration Loading

The settings layer reads `~/.config/nasagent/config.toml` when present. Environment variables keep precedence over file values, using the existing `NASAGENT_` prefix and `__` nested delimiter. This keeps current environment-based workflows working while adding file-based defaults.

## TOML Shape

```toml
[llm]
provider = "openai"
model = "gpt-4.1-mini"
api_key = "********"
base_url = "https://api.openai.com/v1"

[safety]
default_mode = "confirm_destructive"
allow_auto_write = false
allow_destructive = false
require_confirmation_for = ["delete_file", "upload_file"]

[observability]
run_log_dir = "~/.nasagent/runs"
redact_sensitive = true
```

Optional unset values are omitted from generated TOML and `config show` output to keep the file concise.

## Components

- `nasagent.config.settings`: add helpers for resolving the default config path, loading TOML, merging file values into `NasAgentSettings`, and rendering settings as TOML-safe dictionaries.
- `nasagent.cli.commands.config`: implement `init` prompts, no-overwrite behavior, TOML file writing, and TOML output for `show`.
- `docs/configuration.md`: document `config.toml`, `config init`, `config show`, and environment variable precedence.

## Error Handling

If the config directory does not exist, `config init` creates it. If the config file exists, `config init` exits successfully without changing it. Invalid TOML should surface as a clear CLI error when loading or showing config.

## Tests

Add coverage for:

- first-time `config init` creates `config.toml`
- existing config is not overwritten
- prompted LLM values are written
- `config show` outputs TOML and redacts `llm.api_key`
- settings read values from `config.toml`
- environment variables override TOML values

## Out Of Scope

This change does not add UGREEN profile setup, automatic merge of existing config files, or a `--force` overwrite flag. Those can be added later if the CLI needs a broader setup wizard.
