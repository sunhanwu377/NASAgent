# Config Init TOML Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a first-run `nasagent config init` flow that creates `~/.config/nasagent/config.toml`, guides LLM setup, loads that TOML file, and shows effective config as TOML.

**Architecture:** Keep configuration file concerns in `nasagent.config.settings` so CLI commands and runtime code share the same source of truth. Keep the CLI command thin: prompt users, call settings helpers, and print TOML. Use Python 3.11 `tomllib` for reads and a small focused TOML renderer for the limited settings shape to avoid adding dependencies.

**Tech Stack:** Python 3.11, Typer, Pydantic Settings, pytest, ruff, mypy, `tomllib`.

## Global Constraints

- Default config path is `~/.config/nasagent/config.toml`.
- `nasagent config init` creates the config file only when missing.
- Existing config files are not overwritten.
- `config init` prompts for LLM provider, model, base URL, and API key.
- API key prompt is optional and hidden while typed.
- `nasagent config show` outputs TOML, not JSON.
- `config show` redacts `llm.api_key` as `********`.
- Environment variables using `NASAGENT_` and `__` override TOML file values.
- Optional unset values are omitted from generated TOML and `config show` output.
- Do not add UGREEN profile setup, automatic merging, or `--force` overwrite.
- Do not add runtime dependencies for TOML writing.

---

## File Structure

- Modify `src/nasagent/config/settings.py`: own config path resolution, TOML loading, settings construction with file defaults, TOML-safe dict conversion, and TOML rendering.
- Modify `src/nasagent/cli/commands/config.py`: use the settings helpers for `show`; implement `init` prompts and no-overwrite behavior.
- Modify `tests/unit/config/test_settings.py`: unit-test TOML loading, environment precedence, TOML rendering, and redaction data conversion.
- Modify `tests/integration/test_cli.py`: integration-test `config init` and `config show` CLI behavior.
- Modify `docs/configuration.md`: document `config.toml`, init/show behavior, and environment precedence.

---

### Task 1: Settings TOML Loading And Rendering

**Files:**
- Modify: `src/nasagent/config/settings.py`
- Modify: `tests/unit/config/test_settings.py`

**Interfaces:**
- Consumes: existing `NasAgentSettings`, `LlmSettings`, `SafetySettings`, `ObservabilitySettings` classes.
- Produces: `DEFAULT_CONFIG_PATH: Path`, `default_config_path() -> Path`, `load_config_file(path: Path | None = None) -> dict[str, object]`, `load_settings(path: Path | None = None) -> NasAgentSettings`, `settings_to_toml_data(settings: NasAgentSettings, *, redact: bool = False) -> dict[str, object]`, `render_toml(data: dict[str, object]) -> str`.

- [ ] **Step 1: Write failing settings tests**

Append these tests to `tests/unit/config/test_settings.py`:

```python
from pathlib import Path

from nasagent.config.settings import (
    LlmSettings,
    NasAgentSettings,
    load_config_file,
    load_settings,
    render_toml,
    settings_to_toml_data,
)


def test_load_config_file_reads_toml(tmp_path: Path) -> None:
    config_path = tmp_path / "config.toml"
    config_path.write_text(
        '[llm]\nmodel = "gpt-4o-mini"\n\n[observability]\nrun_log_dir = "/tmp/nasagent"\n',
        encoding="utf-8",
    )

    data = load_config_file(config_path)

    assert data == {
        "llm": {"model": "gpt-4o-mini"},
        "observability": {"run_log_dir": "/tmp/nasagent"},
    }


def test_load_config_file_returns_empty_dict_when_missing(tmp_path: Path) -> None:
    assert load_config_file(tmp_path / "missing.toml") == {}


def test_load_settings_uses_config_file_values(tmp_path: Path) -> None:
    config_path = tmp_path / "config.toml"
    config_path.write_text(
        '[llm]\nprovider = "openai"\nmodel = "gpt-4o-mini"\napi_key = "file-key"\n',
        encoding="utf-8",
    )

    settings = load_settings(config_path)

    assert settings.llm.provider == "openai"
    assert settings.llm.model == "gpt-4o-mini"
    assert settings.llm.api_key == "file-key"


def test_environment_overrides_config_file_values(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    config_path = tmp_path / "config.toml"
    config_path.write_text('[llm]\nmodel = "file-model"\n', encoding="utf-8")
    monkeypatch.setenv("NASAGENT_LLM__MODEL", "env-model")

    settings = load_settings(config_path)

    assert settings.llm.model == "env-model"


def test_settings_to_toml_data_omits_unset_optional_values() -> None:
    settings = NasAgentSettings(llm=LlmSettings(api_key=None, base_url=None))

    data = settings_to_toml_data(settings)

    assert data["llm"] == {"provider": "openai", "model": "gpt-4.1-mini"}


def test_settings_to_toml_data_redacts_api_key() -> None:
    settings = NasAgentSettings(llm=LlmSettings(api_key="secret-api-key"))

    data = settings_to_toml_data(settings, redact=True)

    assert data["llm"]["api_key"] == "********"


def test_render_toml_outputs_sections_and_arrays() -> None:
    output = render_toml(
        {
            "llm": {"provider": "openai", "model": "gpt-4.1-mini"},
            "safety": {"require_confirmation_for": ("delete_file", "upload_file")},
        }
    )

    assert "[llm]" in output
    assert 'provider = "openai"' in output
    assert "[safety]" in output
    assert 'require_confirmation_for = ["delete_file", "upload_file"]' in output
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/config/test_settings.py -v`

Expected: FAIL because `load_config_file`, `load_settings`, `settings_to_toml_data`, and `render_toml` do not exist.

- [ ] **Step 3: Implement settings helpers**

Replace `src/nasagent/config/settings.py` with:

```python
from pathlib import Path
import tomllib
from typing import Any

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


DEFAULT_CONFIG_PATH = Path("~/.config/nasagent/config.toml")


class LlmSettings(BaseModel):
    provider: str = "openai"
    model: str = "gpt-4.1-mini"
    api_key: str | None = None
    base_url: str | None = None


class SafetySettings(BaseModel):
    default_mode: str = "confirm_destructive"
    allow_auto_write: bool = False
    allow_destructive: bool = False
    require_confirmation_for: tuple[str, ...] = ("delete_file", "upload_file")


class ObservabilitySettings(BaseModel):
    run_log_dir: str = "~/.nasagent/runs"
    redact_sensitive: bool = True

    def expanded_run_log_dir(self) -> Path:
        return Path(self.run_log_dir).expanduser()


class NasAgentSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="NASAGENT_", env_nested_delimiter="__")

    llm: LlmSettings = Field(default_factory=LlmSettings)
    safety: SafetySettings = Field(default_factory=SafetySettings)
    observability: ObservabilitySettings = Field(default_factory=ObservabilitySettings)


def default_config_path() -> Path:
    return DEFAULT_CONFIG_PATH.expanduser()


def load_config_file(path: Path | None = None) -> dict[str, object]:
    config_path = path or default_config_path()
    if not config_path.exists():
        return {}
    with config_path.open("rb") as config_file:
        return tomllib.load(config_file)


def load_settings(path: Path | None = None) -> NasAgentSettings:
    return NasAgentSettings(**load_config_file(path))


def settings_to_toml_data(settings: NasAgentSettings, *, redact: bool = False) -> dict[str, object]:
    data = settings.model_dump(mode="python")
    if redact and data["llm"].get("api_key"):
        data["llm"]["api_key"] = "********"
    return _drop_none(data)


def render_toml(data: dict[str, object]) -> str:
    lines: list[str] = []
    for section_name, section_values in data.items():
        if not isinstance(section_values, dict):
            continue
        if lines:
            lines.append("")
        lines.append(f"[{section_name}]")
        for key, value in section_values.items():
            lines.append(f"{key} = {_format_toml_value(value)}")
    return "\n".join(lines) + "\n"


def _drop_none(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _drop_none(item) for key, item in value.items() if item is not None}
    if isinstance(value, tuple):
        return tuple(_drop_none(item) for item in value)
    if isinstance(value, list):
        return [_drop_none(item) for item in value]
    return value


def _format_toml_value(value: object) -> str:
    if isinstance(value, str):
        return _format_toml_string(value)
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int | float):
        return str(value)
    if isinstance(value, tuple | list):
        return "[" + ", ".join(_format_toml_value(item) for item in value) + "]"
    raise TypeError(f"Unsupported TOML value: {value!r}")


def _format_toml_string(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'
```

- [ ] **Step 4: Run unit tests**

Run: `uv run pytest tests/unit/config/test_settings.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

Only commit if the user explicitly requested commits. If committing is requested, run:

```bash
git add src/nasagent/config/settings.py tests/unit/config/test_settings.py
git commit -m "feat: load settings from toml config"
```

---

### Task 2: Config CLI Init And Show

**Files:**
- Modify: `src/nasagent/cli/commands/config.py`
- Modify: `src/nasagent/cli/commands/run.py`
- Modify: `tests/integration/test_cli.py`

**Interfaces:**
- Consumes: `default_config_path() -> Path`, `load_settings(path: Path | None = None) -> NasAgentSettings`, `settings_to_toml_data(settings: NasAgentSettings, *, redact: bool = False) -> dict[str, object]`, `render_toml(data: dict[str, object]) -> str` from Task 1.
- Produces: `nasagent config init` creates TOML via prompts; `nasagent config show` prints TOML; runtime execution uses `load_settings()` so config files affect normal runs.

- [ ] **Step 1: Write failing CLI tests**

Append these tests to `tests/integration/test_cli.py`:

```python
from pathlib import Path

from nasagent.config import settings as settings_module


def test_config_init_creates_toml_file(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    config_path = tmp_path / "config.toml"
    monkeypatch.setattr(settings_module, "DEFAULT_CONFIG_PATH", config_path)
    runner = CliRunner()

    result = runner.invoke(
        app,
        ["config", "init"],
        input="openai\ngpt-4o-mini\nhttps://openai-compatible.example/v1\nsecret-api-key\n",
    )

    assert result.exit_code == 0
    assert config_path.exists()
    content = config_path.read_text(encoding="utf-8")
    assert "[llm]" in content
    assert 'provider = "openai"' in content
    assert 'model = "gpt-4o-mini"' in content
    assert 'base_url = "https://openai-compatible.example/v1"' in content
    assert 'api_key = "secret-api-key"' in content
    assert "[safety]" in content
    assert "[observability]" in content
    assert str(config_path) in result.output


def test_config_init_does_not_overwrite_existing_file(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    config_path = tmp_path / "config.toml"
    config_path.write_text('[llm]\nmodel = "existing"\n', encoding="utf-8")
    monkeypatch.setattr(settings_module, "DEFAULT_CONFIG_PATH", config_path)
    runner = CliRunner()

    result = runner.invoke(app, ["config", "init"])

    assert result.exit_code == 0
    assert config_path.read_text(encoding="utf-8") == '[llm]\nmodel = "existing"\n'
    assert "already exists" in result.output


def test_config_show_outputs_toml_and_redacts_api_key(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    config_path = tmp_path / "config.toml"
    config_path.write_text(
        '[llm]\nmodel = "file-model"\napi_key = "secret-api-key"\n',
        encoding="utf-8",
    )
    monkeypatch.setattr(settings_module, "DEFAULT_CONFIG_PATH", config_path)
    runner = CliRunner()

    result = runner.invoke(app, ["config", "show"])

    assert result.exit_code == 0
    assert "[llm]" in result.output
    assert 'model = "file-model"' in result.output
    assert 'api_key = "********"' in result.output
    assert "secret-api-key" not in result.output
    assert "{" not in result.output
```

Modify existing `test_config_show_redacts_api_key` in `tests/integration/test_cli.py` from JSON assertions to TOML assertions:

```python
def test_config_show_redacts_api_key(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("NASAGENT_LLM__API_KEY", "secret-api-key")
    runner = CliRunner()

    result = runner.invoke(app, ["config", "show"])

    assert result.exit_code == 0
    assert "secret-api-key" not in result.output
    assert 'api_key = "********"' in result.output
```

- [ ] **Step 2: Run CLI tests to verify they fail**

Run: `uv run pytest tests/integration/test_cli.py -v`

Expected: FAIL because `config init` still prints a stub message, `config show` still prints JSON, and `run.py` still constructs `NasAgentSettings()` directly.

- [ ] **Step 3: Implement CLI commands and runtime settings loading**

Replace `src/nasagent/cli/commands/config.py` with:

```python
import typer

from nasagent.config.settings import (
    LlmSettings,
    NasAgentSettings,
    default_config_path,
    load_settings,
    render_toml,
    settings_to_toml_data,
)

app = typer.Typer(no_args_is_help=True)


@app.command("show")
def show() -> None:
    settings = load_settings()
    typer.echo(render_toml(settings_to_toml_data(settings, redact=True)))


@app.command("init")
def init() -> None:
    config_path = default_config_path()
    if config_path.exists():
        typer.echo(f"Config already exists: {config_path}")
        typer.echo("Run `nasagent config show` to view the effective configuration.")
        return

    default_settings = NasAgentSettings()
    provider = typer.prompt("LLM provider", default=default_settings.llm.provider)
    model = typer.prompt("LLM model", default=default_settings.llm.model)
    base_url = typer.prompt("LLM base URL (optional)", default="")
    api_key = typer.prompt("LLM API key (optional)", default="", hide_input=True)

    settings = NasAgentSettings(
        llm=LlmSettings(
            provider=provider,
            model=model,
            base_url=base_url or None,
            api_key=api_key or None,
        ),
        safety=default_settings.safety,
        observability=default_settings.observability,
    )

    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(render_toml(settings_to_toml_data(settings)), encoding="utf-8")
    typer.echo(f"Created config: {config_path}")
```

In `src/nasagent/cli/commands/run.py`, change imports and default settings construction:

```python
from nasagent.config.settings import LlmSettings, NasAgentSettings, load_settings
```

Change this line in `execute_simulator_task`:

```python
active_settings = settings or NasAgentSettings()
```

to:

```python
active_settings = settings or load_settings()
```

- [ ] **Step 4: Run CLI tests**

Run: `uv run pytest tests/integration/test_cli.py -v`

Expected: PASS.

- [ ] **Step 5: Run config and run related tests**

Run: `uv run pytest tests/unit/config/test_settings.py tests/integration/test_cli.py -v`

Expected: PASS.

- [ ] **Step 6: Commit**

Only commit if the user explicitly requested commits. If committing is requested, run:

```bash
git add src/nasagent/cli/commands/config.py src/nasagent/cli/commands/run.py tests/integration/test_cli.py
git commit -m "feat: add config init toml workflow"
```

---

### Task 3: Documentation And Full Verification

**Files:**
- Modify: `docs/configuration.md`
- Verify: `README.md`, `docs/cli.md`

**Interfaces:**
- Consumes: completed Task 1 and Task 2 behavior.
- Produces: user-facing documentation for `config.toml`, `config init`, `config show`, and precedence rules.

- [ ] **Step 1: Update configuration docs**

Replace `docs/configuration.md` with:

```markdown
# Configuration

Default configuration belongs at `~/.config/nasagent/config.toml`. Runtime logs belong under `~/.nasagent/runs/` by default.

Create the first config file with:

```bash
uv run nasagent config init
```

The init command creates `~/.config/nasagent/config.toml` when it does not already exist and guides you through LLM configuration. Existing config files are not overwritten.

Show the effective configuration with:

```bash
uv run nasagent config show
```

`config show` prints TOML and redacts `llm.api_key`.

Example config:

```toml
[llm]
provider = "openai"
model = "gpt-4.1-mini"
base_url = "https://api.openai.com/v1"
api_key = "your-api-key"

[safety]
default_mode = "confirm_destructive"
allow_auto_write = false
allow_destructive = false
require_confirmation_for = ["delete_file", "upload_file"]

[observability]
run_log_dir = "~/.nasagent/runs"
redact_sensitive = true
```

Secrets must not be committed. Local TOML files are for user-specific configuration. System keyring support can be added without changing adapter interfaces.

Environment variables use the `NASAGENT_` prefix and `__` for nested fields, for example `NASAGENT_LLM__API_KEY` or `NASAGENT_OBSERVABILITY__RUN_LOG_DIR`. Environment variables override values from `config.toml`.

Profiles select the NAS adapter. The built-in `simulator` profile is the supported phase 1 CLI path; UGREEN profiles should wait for verified API details before real operations are added.

Important settings:

- `safety.allow_auto_write`: lets non-confirmation-required write tools run without approval.
- `safety.allow_destructive`: permits destructive tools to request approval; it does not execute them automatically.
- `safety.require_confirmation_for`: tool names that always require approval.
- `observability.run_log_dir`: directory for sanitized run JSON files, defaulting to `~/.nasagent/runs`.
- `observability.redact_sensitive`: keeps credentials, tokens, API keys, and similar values out of persisted state.
```

- [ ] **Step 2: Run documentation-related checks**

Run: `uv run ruff format --check .`

Expected: PASS.

Run: `uv run ruff check .`

Expected: PASS.

- [ ] **Step 3: Run type checks**

Run: `uv run mypy src`

Expected: PASS.

- [ ] **Step 4: Run full tests**

Run: `uv run pytest`

Expected: PASS.

- [ ] **Step 5: Smoke-test CLI commands**

Use a temporary home directory so the smoke test does not modify the real user config:

```bash
tmp_home="$(mktemp -d)"
HOME="$tmp_home" uv run nasagent config init <<'EOF'
openai
gpt-4.1-mini


EOF
HOME="$tmp_home" uv run nasagent config show
```

Expected: the first command prints `Created config: .../.config/nasagent/config.toml`; the second command prints TOML sections `[llm]`, `[safety]`, and `[observability]`.

- [ ] **Step 6: Commit**

Only commit if the user explicitly requested commits. If committing is requested, run:

```bash
git add docs/configuration.md
git commit -m "docs: document toml configuration workflow"
```

---

## Self-Review

- Spec coverage: Task 1 covers config loading, environment precedence, TOML data conversion, optional omission, and redaction data. Task 2 covers `config init`, no-overwrite behavior, `config show` TOML output, and runtime use of file config. Task 3 covers docs and full verification.
- Placeholder scan: no `TBD`, `TODO`, vague edge handling, or references to undefined helpers remain.
- Type consistency: helper signatures match across Task 1 and Task 2; CLI tests patch `settings_module.DEFAULT_CONFIG_PATH`, which `default_config_path()` reads dynamically.
