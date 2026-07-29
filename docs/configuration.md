# Configuration

Default configuration belongs under `~/.config/nasagent/`. Runtime logs belong under `~/.nasagent/runs/`.

Secrets must not be committed. Phase 1 can use environment variables and local TOML files. System keyring support can be added without changing adapter interfaces.

Environment variables use the `NASAGENT_` prefix and `__` for nested fields, for example `NASAGENT_LLM__API_KEY` or `NASAGENT_OBSERVABILITY__RUN_LOG_DIR`.

Profiles select the NAS adapter. The built-in `simulator` profile is the supported phase 1 CLI path; UGREEN profiles should wait for verified API details before real operations are added.

Important settings:

- `safety.allow_auto_write`: lets non-confirmation-required write tools run without approval.
- `safety.allow_destructive`: permits destructive tools to request approval; it does not execute them automatically.
- `safety.require_confirmation_for`: tool names that always require approval.
- `observability.run_log_dir`: directory for sanitized run JSON files, defaulting to `~/.nasagent/runs`.
- `observability.redact_sensitive`: keeps credentials, tokens, API keys, and similar values out of persisted state.
