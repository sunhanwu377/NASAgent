# Configuration

Default configuration belongs at `~/.config/nasagent/config.toml`. Local persisted secrets belong at `~/.local/share/nasagent/secrets.toml`. Runtime logs belong under `~/.nasagent/runs/` by default.

- Non-sensitive config path: `~/.config/nasagent/config.toml`
- Sensitive secrets path: `~/.local/share/nasagent/secrets.toml`
- Secrets file mode: `0600`
- Display output is redacted by default.

Create the first config file with:

```bash
uv run nasagent config init
```

The init command creates `~/.config/nasagent/config.toml` when it does not already exist and guides you through LLM configuration. Existing config files are not overwritten. Non-sensitive LLM settings are written to config TOML. If you enter an LLM API key, `config init` stores it through `CredentialStore` as `llm.api_key` in `~/.local/share/nasagent/secrets.toml`; it is not written to `config.toml`.

`config init` also asks whether to scan the local network for NAS services. The default is no scan. When enabled, the current implementation runs conservative discovery plumbing with safe limits: mDNS and SSDP discovery functions are placeholders that return no services today, and vendor probes only run for explicit hosts supplied to `DiscoveryScanner.scan_hosts(hosts)`. `config init` does not perform broad subnet or aggressive LAN scanning. If no service is discovered, add app endpoints manually in `config.toml`.

Show the effective configuration with:

```bash
uv run nasagent config show
```

`config show` prints TOML and redacts `llm.api_key` if it is present in loaded settings.

Example config:

```toml
[llm]
provider = "openai"
model = "gpt-4.1-mini"
base_url = "https://api.openai.com/v1"

[safety]
default_mode = "confirm_destructive"
allow_auto_write = false
allow_destructive = false
require_confirmation_for = ["delete_file", "upload_file"]

[observability]
run_log_dir = "~/.nasagent/runs"
redact_sensitive = true

[apps."alist.home"]
app_type = "alist"
base_url = "http://nas.local:5244"
credential_key = "alist.home.token"

[plugins.builtin]
enabled = true
```

Secrets must not be committed and should not be placed in `config.toml`. Store secret values in `~/.local/share/nasagent/secrets.toml`, which `CredentialStore` creates and reads only with `0600` permissions. `config init` stores an entered LLM API key as `llm.api_key`. Store non-secret references in config, for example an app endpoint `credential_key` that points to a credential-store entry. System keyring support can be added later without changing adapter interfaces.

Environment variables use the `NASAGENT_` prefix and `__` for nested fields, for example `NASAGENT_LLM__API_KEY` or `NASAGENT_OBSERVABILITY__RUN_LOG_DIR`. Environment variables override values from `config.toml`.

Profiles select the NAS adapter. The built-in `simulator` profile is the supported phase 1 CLI path; UGREEN profiles should wait for verified API details before real operations are added.

Important settings:

- `safety.allow_auto_write`: lets non-confirmation-required write tools run without approval.
- `safety.allow_destructive`: permits destructive tools to request approval; it does not execute them automatically.
- `safety.require_confirmation_for`: tool names that always require approval.
- `observability.run_log_dir`: directory for sanitized run JSON files, defaulting to `~/.nasagent/runs`.
- `observability.redact_sensitive`: keeps credentials, tokens, API keys, and similar values out of persisted state.
- `apps.<name>.app_type`: app adapter category for a configured NAS app endpoint.
- `apps.<name>.base_url`: base URL for that app endpoint.
- `apps.<name>.credential_key`: optional credential-store key containing the endpoint secret.
- `plugins.<name>.enabled`: records whether a named plugin is enabled in configuration; plugin loading is not implemented yet.
