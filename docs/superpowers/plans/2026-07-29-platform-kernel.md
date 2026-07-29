# NASAgent Platform Kernel Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first-phase NASAgent platform kernel: registries, plugins, commands, LAN discovery, credential persistence, Docker/app tool skeletons, and public-facing documentation.

**Architecture:** Add a small platform layer that owns shared registries and context. Built-in capabilities and third-party plugins use the same registration APIs; CLI, chat slash commands, and agent tools resolve capabilities from those registries before using the existing `StepRunner` and `SafetyPolicy`.

**Tech Stack:** Python 3.11, Typer, Rich, Pydantic v2, httpx, Docker SDK, pytest, pytest-asyncio, pytest-httpx, ruff, mypy.

## Global Constraints

- Keep existing simulator behavior working.
- Do not replace `StepRunner` or `SafetyPolicy`; route new agent-callable tools through existing tool execution.
- Secrets must be stored in `~/.local/share/nasagent/secrets.toml` with `0600` permissions.
- Config remains in `~/.config/nasagent/config.toml` for non-sensitive settings.
- Discovery must avoid aggressive whole-network scanning by default.
- Lucky API tools must not fake unverified endpoints.
- Docker Compose tools must use explicit subprocess arguments without shell interpolation and require confirmation.
- README and permanent docs must be updated with architecture and data flow.

---

## File Structure

Create or modify these files across the plan:

- Create `src/nasagent/platform/context.py`: `PlatformContext` container for settings, credentials, tools, commands, apps, and plugin state.
- Create `src/nasagent/platform/apps.py`: app endpoint models and app registry.
- Create `src/nasagent/platform/commands.py`: reusable command definitions and command registry.
- Create `src/nasagent/platform/plugins.py`: plugin manifest, plugin context, plugin manager, entry point loading.
- Create `src/nasagent/plugins/builtin.py`: built-in plugin registration entry point.
- Modify `src/nasagent/tools/registry.py`: keep existing API, add namespace/list filtering only if needed by plugins.
- Modify `src/nasagent/agent/graph/nodes.py`: make `default_tool_registry()` load built-in plugin tools.
- Modify `src/nasagent/config/secrets.py`: add `CredentialStore` while preserving `SecretValue` and `load_env_secret`.
- Modify `src/nasagent/config/settings.py`: add app/plugin config models and TOML rendering support.
- Create `src/nasagent/discovery/models.py`: discovery result and probe data models.
- Create `src/nasagent/discovery/protocols.py`: constrained protocol/generic probe orchestration interfaces.
- Create `src/nasagent/discovery/vendors/base.py`: vendor probe protocol and registry.
- Create `src/nasagent/discovery/vendors/ugreen.py`: UGREEN probe.
- Create `src/nasagent/discovery/vendors/synology.py`: Synology probe.
- Create `src/nasagent/discovery/vendors/fnos.py`: FNOS placeholder probe with explicit conservative matching.
- Create `src/nasagent/discovery/vendors/zspace.py`: Zspace placeholder probe with explicit conservative matching.
- Create `src/nasagent/discovery/vendors/generic.py`: generic NAS admin fallback probe.
- Modify `src/nasagent/cli/commands/config.py`: discovery-assisted init and secrets handling.
- Modify `src/nasagent/cli/commands/chat.py`: slash command dispatch before normal chat/task handling.
- Create `src/nasagent/cli/commands/apps.py`: `nasagent apps list`.
- Create `src/nasagent/cli/commands/plugins.py`: `nasagent plugins list`.
- Create `src/nasagent/cli/commands/containers.py`: `nasagent containers list`.
- Modify `src/nasagent/cli/app.py`: register new Typer command modules.
- Create `src/nasagent/integrations/docker/client.py`: Docker SDK and Compose execution wrappers.
- Create `src/nasagent/integrations/docker/tools.py`: Docker `ToolDefinition` registrations.
- Create `src/nasagent/integrations/alist/client.py`: minimal AList client.
- Create `src/nasagent/integrations/alist/tools.py`: minimal AList tools.
- Create `src/nasagent/integrations/lucky/client.py`: endpoint/token management only until API is verified.
- Create `src/nasagent/integrations/vaultwarden/client.py`: minimal Vaultwarden admin client skeleton.
- Create unit/integration tests under `tests/unit/platform`, `tests/unit/discovery`, `tests/unit/integrations`, and existing `tests/integration`.
- Modify `docs/architecture.md`, `docs/agent-flow.md`, `docs/tools.md`, `docs/cli.md`, `docs/configuration.md`.
- Create `docs/discovery.md` and `docs/plugins.md`.
- Rewrite `README.md`.

---

### Task 1: Platform Registries And Context

**Files:**
- Create: `src/nasagent/platform/__init__.py`
- Create: `src/nasagent/platform/apps.py`
- Create: `src/nasagent/platform/commands.py`
- Create: `src/nasagent/platform/context.py`
- Test: `tests/unit/platform/test_apps.py`
- Test: `tests/unit/platform/test_commands.py`
- Test: `tests/unit/platform/test_context.py`

**Interfaces:**
- Consumes: `ToolRegistry` from `nasagent.tools.registry`, `NasAgentSettings` from `nasagent.config.settings`.
- Produces: `AppEndpoint`, `AppRegistry`, `CommandDefinition`, `CommandRegistry`, `CommandResult`, `PlatformContext`.

- [ ] **Step 1: Write failing app registry tests**

```python
# tests/unit/platform/test_apps.py
import pytest

from nasagent.platform.apps import AppEndpoint, AppRegistry


def test_app_registry_registers_and_lists_endpoint() -> None:
    registry = AppRegistry()
    endpoint = AppEndpoint(
        name="home",
        app_type="alist",
        base_url="http://nas.local:5244",
        credential_key="alist.home.token",
    )

    registry.register(endpoint)

    assert registry.get("home") == endpoint
    assert registry.list(app_type="alist") == [endpoint]


def test_app_registry_rejects_duplicate_name() -> None:
    registry = AppRegistry()
    endpoint = AppEndpoint(name="home", app_type="alist", base_url="http://example.test")
    registry.register(endpoint)

    with pytest.raises(ValueError, match="App endpoint already registered: home"):
        registry.register(endpoint)
```

- [ ] **Step 2: Write failing command registry tests**

```python
# tests/unit/platform/test_commands.py
import pytest

from nasagent.platform.commands import CommandDefinition, CommandRegistry, CommandResult


def _handler(args: tuple[str, ...]) -> CommandResult:
    return CommandResult(message="handled " + " ".join(args))


def test_command_registry_resolves_name_and_alias() -> None:
    registry = CommandRegistry()
    command = CommandDefinition(
        name="apps",
        description="List apps",
        usage="/apps",
        handler=_handler,
        aliases=("app",),
        plugin="builtin",
    )

    registry.register(command)

    assert registry.get("apps") == command
    assert registry.get("app") == command
    assert registry.dispatch("/apps list").message == "handled list"


def test_command_registry_rejects_duplicate_name() -> None:
    registry = CommandRegistry()
    command = CommandDefinition("apps", "List apps", "/apps", _handler)
    registry.register(command)

    with pytest.raises(ValueError, match="Command already registered: apps"):
        registry.register(command)
```

- [ ] **Step 3: Write failing context test**

```python
# tests/unit/platform/test_context.py
from nasagent.config.settings import NasAgentSettings
from nasagent.platform.context import create_platform_context


def test_create_platform_context_has_empty_registries() -> None:
    context = create_platform_context(settings=NasAgentSettings())

    assert context.settings.llm.provider == "openai"
    assert context.apps.list() == []
    assert context.commands.list() == []
    assert context.tools.list() == []
```

- [ ] **Step 4: Run tests and verify they fail**

Run: `uv run pytest tests/unit/platform -v`

Expected: FAIL because `nasagent.platform` modules do not exist.

- [ ] **Step 5: Implement app registry**

```python
# src/nasagent/platform/apps.py
from dataclasses import dataclass


@dataclass(frozen=True)
class AppEndpoint:
    name: str
    app_type: str
    base_url: str
    credential_key: str | None = None
    frontend_url: str | None = None
    notes: str | None = None


class AppRegistry:
    def __init__(self) -> None:
        self._apps: dict[str, AppEndpoint] = {}

    def register(self, endpoint: AppEndpoint) -> None:
        if endpoint.name in self._apps:
            raise ValueError(f"App endpoint already registered: {endpoint.name}")
        self._apps[endpoint.name] = endpoint

    def get(self, name: str) -> AppEndpoint | None:
        return self._apps.get(name)

    def list(self, *, app_type: str | None = None) -> list[AppEndpoint]:
        endpoints = list(self._apps.values())
        if app_type is not None:
            return [endpoint for endpoint in endpoints if endpoint.app_type == app_type]
        return endpoints
```

- [ ] **Step 6: Implement command registry**

```python
# src/nasagent/platform/commands.py
from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True)
class CommandResult:
    message: str
    exit_code: int = 0


CommandHandler = Callable[[tuple[str, ...]], CommandResult]


@dataclass(frozen=True)
class CommandDefinition:
    name: str
    description: str
    usage: str
    handler: CommandHandler
    aliases: tuple[str, ...] = ()
    plugin: str | None = None


class CommandRegistry:
    def __init__(self) -> None:
        self._commands: dict[str, CommandDefinition] = {}
        self._aliases: dict[str, str] = {}

    def register(self, command: CommandDefinition) -> None:
        if command.name in self._commands:
            raise ValueError(f"Command already registered: {command.name}")
        self._commands[command.name] = command
        for alias in command.aliases:
            if alias in self._aliases or alias in self._commands:
                raise ValueError(f"Command alias already registered: {alias}")
            self._aliases[alias] = command.name

    def get(self, name: str) -> CommandDefinition | None:
        normalized = name.removeprefix("/")
        command_name = self._aliases.get(normalized, normalized)
        return self._commands.get(command_name)

    def list(self) -> list[CommandDefinition]:
        return list(self._commands.values())

    def dispatch(self, raw: str) -> CommandResult:
        parts = raw.strip().split()
        if not parts:
            return CommandResult(message="No command provided", exit_code=1)
        command = self.get(parts[0])
        if command is None:
            return CommandResult(message=f"Unknown command: {parts[0]}", exit_code=1)
        return command.handler(tuple(parts[1:]))
```

- [ ] **Step 7: Implement platform context**

```python
# src/nasagent/platform/context.py
from dataclasses import dataclass

from nasagent.config.settings import NasAgentSettings
from nasagent.platform.apps import AppRegistry
from nasagent.platform.commands import CommandRegistry
from nasagent.tools.registry import ToolRegistry


@dataclass
class PlatformContext:
    settings: NasAgentSettings
    tools: ToolRegistry
    commands: CommandRegistry
    apps: AppRegistry


def create_platform_context(*, settings: NasAgentSettings) -> PlatformContext:
    return PlatformContext(
        settings=settings,
        tools=ToolRegistry(),
        commands=CommandRegistry(),
        apps=AppRegistry(),
    )
```

```python
# src/nasagent/platform/__init__.py
from nasagent.platform.apps import AppEndpoint, AppRegistry
from nasagent.platform.commands import CommandDefinition, CommandRegistry, CommandResult
from nasagent.platform.context import PlatformContext, create_platform_context

__all__ = [
    "AppEndpoint",
    "AppRegistry",
    "CommandDefinition",
    "CommandRegistry",
    "CommandResult",
    "PlatformContext",
    "create_platform_context",
]
```

- [ ] **Step 8: Run task tests**

Run: `uv run pytest tests/unit/platform -v`

Expected: PASS.

- [ ] **Step 9: Run quality checks for touched code**

Run: `uv run ruff check src/nasagent/platform tests/unit/platform`

Expected: PASS.

- [ ] **Step 10: Commit**

```bash
git add src/nasagent/platform tests/unit/platform
git commit -m "feat: add platform registries"
```

---

### Task 2: Credential Store And Config Models

**Files:**
- Modify: `src/nasagent/config/secrets.py`
- Modify: `src/nasagent/config/settings.py`
- Test: `tests/unit/config/test_secrets.py`
- Test: `tests/unit/config/test_settings.py`

**Interfaces:**
- Consumes: existing `SecretValue`, `load_env_secret`, `settings_to_toml_data`.
- Produces: `CredentialStore`, `CredentialFilePermissionError`, `default_secrets_path()`, `AppEndpointSettings`, `PluginSettings`.

- [ ] **Step 1: Add failing credential store tests**

Append to `tests/unit/config/test_secrets.py`:

```python
import os

import pytest

from nasagent.config.secrets import CredentialFilePermissionError, CredentialStore


def test_credential_store_writes_file_with_0600(tmp_path) -> None:
    path = tmp_path / "secrets.toml"
    store = CredentialStore(path)

    store.set("alist.home.token", "secret-token")

    assert store.get("alist.home.token") == "secret-token"
    assert oct(path.stat().st_mode & 0o777) == "0o600"


def test_credential_store_redacted_summary_hides_values(tmp_path) -> None:
    path = tmp_path / "secrets.toml"
    store = CredentialStore(path)
    store.set("alist.home.token", "secret-token")

    summary = store.redacted_summary()

    assert summary == {"alist.home.token": "********"}
    assert "secret-token" not in repr(summary)


def test_credential_store_refuses_unsafe_permissions(tmp_path) -> None:
    path = tmp_path / "secrets.toml"
    path.write_text('[secrets]\n"alist.home.token" = "secret-token"\n')
    os.chmod(path, 0o644)

    store = CredentialStore(path)

    with pytest.raises(CredentialFilePermissionError, match="must be 0600"):
        store.get("alist.home.token")
```

- [ ] **Step 2: Add failing settings tests**

Append to `tests/unit/config/test_settings.py`:

```python
from nasagent.config.settings import AppEndpointSettings, NasAgentSettings, settings_to_toml_data


def test_settings_include_app_endpoints_and_plugins() -> None:
    settings = NasAgentSettings(
        apps={
            "alist.home": AppEndpointSettings(
                app_type="alist",
                base_url="http://nas.local:5244",
                credential_key="alist.home.token",
            )
        },
        plugins={"builtin": True},
    )

    data = settings_to_toml_data(settings)

    assert data["apps"]["alist.home"]["app_type"] == "alist"
    assert data["apps"]["alist.home"]["base_url"] == "http://nas.local:5244"
    assert data["plugins"]["builtin"] is True
```

- [ ] **Step 3: Run tests and verify they fail**

Run: `uv run pytest tests/unit/config/test_secrets.py tests/unit/config/test_settings.py -v`

Expected: FAIL because new classes and settings fields do not exist.

- [ ] **Step 4: Implement credential store**

Add to `src/nasagent/config/secrets.py` while preserving existing exports:

```python
import tomllib
from pathlib import Path
from typing import Any


class CredentialFilePermissionError(RuntimeError):
    pass


def default_secrets_path() -> Path:
    return Path.home() / ".local" / "share" / "nasagent" / "secrets.toml"


class CredentialStore:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or default_secrets_path()

    def get(self, key: str) -> str | None:
        data = self._read()
        value = data.get(key)
        if value is None:
            return None
        return str(value)

    def set(self, key: str, value: str) -> None:
        data = self._read(allow_missing=True)
        data[key] = value
        self._write(data)

    def redacted_summary(self) -> dict[str, str]:
        return {key: "********" for key in self._read(allow_missing=True)}

    def _read(self, *, allow_missing: bool = False) -> dict[str, Any]:
        if not self.path.exists():
            if allow_missing:
                return {}
            return {}
        mode = self.path.stat().st_mode & 0o777
        if mode != 0o600:
            raise CredentialFilePermissionError(f"Secrets file {self.path} must be 0600")
        with self.path.open("rb") as handle:
            parsed = tomllib.load(handle)
        secrets = parsed.get("secrets", {})
        if not isinstance(secrets, dict):
            return {}
        return dict(secrets)

    def _write(self, data: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        lines = ["[secrets]"]
        for key in sorted(data):
            escaped_key = key.replace('"', '\\"')
            escaped_value = str(data[key]).replace('"', '\\"')
            lines.append(f'"{escaped_key}" = "{escaped_value}"')
        self.path.write_text("\n".join(lines) + "\n")
        os.chmod(self.path, 0o600)
```

- [ ] **Step 5: Implement settings models**

Add to `src/nasagent/config/settings.py`:

```python
class AppEndpointSettings(BaseModel):
    app_type: str
    base_url: str
    credential_key: str | None = None
    frontend_url: str | None = None
    notes: str | None = None


class NasAgentSettings(BaseSettings):
    llm: LlmSettings = Field(default_factory=LlmSettings)
    safety: SafetySettings = Field(default_factory=SafetySettings)
    observability: ObservabilitySettings = Field(default_factory=ObservabilitySettings)
    apps: dict[str, AppEndpointSettings] = Field(default_factory=dict)
    plugins: dict[str, bool] = Field(default_factory=dict)
```

Update `settings_to_toml_data()` to include `apps` and `plugins` when non-empty:

```python
if settings.apps:
    data["apps"] = {
        name: endpoint.model_dump(exclude_none=True) for name, endpoint in settings.apps.items()
    }
if settings.plugins:
    data["plugins"] = settings.plugins
```

- [ ] **Step 6: Run task tests**

Run: `uv run pytest tests/unit/config/test_secrets.py tests/unit/config/test_settings.py -v`

Expected: PASS.

- [ ] **Step 7: Run quality checks**

Run: `uv run ruff check src/nasagent/config tests/unit/config`

Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add src/nasagent/config tests/unit/config
git commit -m "feat: add credential persistence"
```

---

### Task 3: Plugin Manager And Built-In Plugin Path

**Files:**
- Create: `src/nasagent/platform/plugins.py`
- Create: `src/nasagent/plugins/__init__.py`
- Create: `src/nasagent/plugins/builtin.py`
- Modify: `src/nasagent/agent/graph/nodes.py`
- Test: `tests/unit/platform/test_plugins.py`
- Test: `tests/integration/test_agent_graph.py`

**Interfaces:**
- Consumes: `PlatformContext`, `ToolDefinition`, existing storage/device/file tool registration functions from `nasagent.agent.graph.nodes` or existing tool modules.
- Produces: `PluginManifest`, `PluginContext`, `PluginLoadError`, `PluginManager`, `load_builtin_plugins(context)`.

- [ ] **Step 1: Write failing plugin tests**

```python
# tests/unit/platform/test_plugins.py
from nasagent.config.settings import NasAgentSettings
from nasagent.platform.context import create_platform_context
from nasagent.platform.plugins import PluginManager


def test_plugin_manager_loads_builtin_plugin_tools() -> None:
    context = create_platform_context(settings=NasAgentSettings())
    manager = PluginManager(context)

    manager.load_builtin()

    tool_names = {tool.name for tool in context.tools.list()}
    assert "storage.status" in tool_names
    assert "device.status" in tool_names
    assert manager.manifests["builtin"].name == "builtin"


def test_plugin_manager_records_failed_entry_point() -> None:
    context = create_platform_context(settings=NasAgentSettings())
    manager = PluginManager(context)

    class BrokenEntryPoint:
        name = "broken"

        def load(self):
            raise RuntimeError("boom")

    manager.load_entry_points(entry_points=[BrokenEntryPoint()])

    assert manager.errors[0].plugin == "broken"
    assert "boom" in manager.errors[0].message
```

- [ ] **Step 2: Run tests and verify they fail**

Run: `uv run pytest tests/unit/platform/test_plugins.py -v`

Expected: FAIL because `nasagent.platform.plugins` does not exist.

- [ ] **Step 3: Implement plugin models and manager**

```python
# src/nasagent/platform/plugins.py
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from importlib.metadata import entry_points

from nasagent.platform.context import PlatformContext


PluginRegister = Callable[["PluginContext"], None]


@dataclass(frozen=True)
class PluginManifest:
    name: str
    version: str
    description: str = ""
    author: str | None = None
    permissions: tuple[str, ...] = ()


@dataclass(frozen=True)
class PluginLoadError:
    plugin: str
    message: str


@dataclass
class PluginContext:
    platform: PlatformContext
    manifest: PluginManifest | None = None


class PluginManager:
    def __init__(self, context: PlatformContext) -> None:
        self.context = context
        self.manifests: dict[str, PluginManifest] = {}
        self.errors: list[PluginLoadError] = []

    def register_manifest(self, manifest: PluginManifest) -> None:
        self.manifests[manifest.name] = manifest

    def load_builtin(self) -> None:
        from nasagent.plugins.builtin import register

        plugin_context = PluginContext(platform=self.context)
        register(plugin_context)
        if plugin_context.manifest is not None:
            self.register_manifest(plugin_context.manifest)

    def load_entry_points(self, *, entry_points: Iterable[object] | None = None) -> None:
        discovered = entry_points
        if discovered is None:
            discovered = entry_points_select()
        for entry_point in discovered:
            name = str(getattr(entry_point, "name", "unknown"))
            try:
                register = entry_point.load()
                plugin_context = PluginContext(platform=self.context)
                register(plugin_context)
                if plugin_context.manifest is not None:
                    self.register_manifest(plugin_context.manifest)
            except Exception as exc:
                self.errors.append(PluginLoadError(plugin=name, message=str(exc)))


def entry_points_select() -> Iterable[object]:
    return entry_points(group="nasagent.plugins")
```

- [ ] **Step 4: Implement built-in plugin registration**

```python
# src/nasagent/plugins/__init__.py
```

```python
# src/nasagent/plugins/builtin.py
from nasagent.agent.graph.nodes import register_builtin_nas_tools
from nasagent.platform.plugins import PluginContext, PluginManifest


def register(plugin: PluginContext) -> None:
    plugin.manifest = PluginManifest(
        name="builtin",
        version="0.1.0",
        description="NASAgent built-in tools and commands",
        permissions=("nas",),
    )
    register_builtin_nas_tools(plugin.platform.tools)
```

- [ ] **Step 5: Split `default_tool_registry()` registration helper**

Modify `src/nasagent/agent/graph/nodes.py` so existing behavior remains:

```python
def register_builtin_nas_tools(registry: ToolRegistry) -> None:
    registry.register(device_status_tool())
    registry.register(storage_status_tool())
    registry.register(list_files_tool())
    registry.register(search_files_tool())
    registry.register(upload_file_tool())
    registry.register(download_file_tool())
    registry.register(delete_file_tool())


def default_tool_registry() -> ToolRegistry:
    registry = ToolRegistry()
    register_builtin_nas_tools(registry)
    return registry
```

- [ ] **Step 6: Run plugin and existing graph tests**

Run: `uv run pytest tests/unit/platform/test_plugins.py tests/integration/test_agent_graph.py -v`

Expected: PASS.

- [ ] **Step 7: Run quality checks**

Run: `uv run ruff check src/nasagent/platform src/nasagent/plugins src/nasagent/agent/graph tests/unit/platform`

Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add src/nasagent/platform src/nasagent/plugins src/nasagent/agent/graph tests/unit/platform tests/integration/test_agent_graph.py
git commit -m "feat: add plugin manager"
```

---

### Task 4: Shared Commands, CLI Subcommands, And Chat Slash Dispatch

**Files:**
- Create: `src/nasagent/plugins/commands.py`
- Create: `src/nasagent/cli/commands/apps.py`
- Create: `src/nasagent/cli/commands/plugins.py`
- Create: `src/nasagent/cli/commands/containers.py`
- Modify: `src/nasagent/plugins/builtin.py`
- Modify: `src/nasagent/cli/commands/chat.py`
- Modify: `src/nasagent/cli/app.py`
- Test: `tests/unit/platform/test_builtin_commands.py`
- Test: `tests/integration/test_cli.py`

**Interfaces:**
- Consumes: `CommandRegistry`, `PluginManager`, `create_platform_context`, `CliRenderer`.
- Produces: built-in command handlers for `help`, `apps`, `plugins`, `tools`, `containers`; CLI wrappers; chat slash dispatch.

- [ ] **Step 1: Write failing built-in command tests**

```python
# tests/unit/platform/test_builtin_commands.py
from nasagent.config.settings import NasAgentSettings
from nasagent.platform.apps import AppEndpoint
from nasagent.platform.context import create_platform_context
from nasagent.plugins.commands import register_builtin_commands


def test_apps_command_lists_redacted_endpoint() -> None:
    context = create_platform_context(settings=NasAgentSettings())
    context.apps.register(
        AppEndpoint(
            name="home",
            app_type="alist",
            base_url="http://nas.local:5244",
            credential_key="alist.home.token",
        )
    )
    register_builtin_commands(context)

    result = context.commands.dispatch("/apps")

    assert "home" in result.message
    assert "alist" in result.message
    assert "alist.home.token" in result.message


def test_help_command_lists_registered_commands() -> None:
    context = create_platform_context(settings=NasAgentSettings())
    register_builtin_commands(context)

    result = context.commands.dispatch("/help")
    assert "/apps" in result.message
    assert "/plugins" in result.message
```

- [ ] **Step 2: Add CLI smoke tests**

Append to `tests/integration/test_cli.py` using the existing runner fixture pattern:

```python
def test_apps_list_command_smoke(cli_runner) -> None:
    result = cli_runner.invoke(app, ["apps", "list"])

    assert result.exit_code == 0
    assert "Configured apps" in result.output


def test_plugins_list_command_smoke(cli_runner) -> None:
    result = cli_runner.invoke(app, ["plugins", "list"])

    assert result.exit_code == 0
    assert "builtin" in result.output
```

- [ ] **Step 3: Run tests and verify they fail**

Run: `uv run pytest tests/unit/platform/test_builtin_commands.py tests/integration/test_cli.py -v`

Expected: FAIL because command modules are missing.

- [ ] **Step 4: Implement built-in command handlers**

```python
# src/nasagent/plugins/commands.py
from nasagent.platform.commands import CommandDefinition, CommandResult
from nasagent.platform.context import PlatformContext


def register_builtin_commands(context: PlatformContext) -> None:
    context.commands.register(CommandDefinition("help", "Show help", "/help", _help))
    context.commands.register(CommandDefinition("apps", "List configured apps", "/apps", _apps))
    context.commands.register(CommandDefinition("plugins", "List plugins", "/plugins", _plugins))
    context.commands.register(CommandDefinition("tools", "List tools", "/tools", _tools))
    context.commands.register(
        CommandDefinition("containers", "List containers", "/containers", _containers)
    )


def _help(args: tuple[str, ...]) -> CommandResult:
    return CommandResult("Commands: /help, /apps, /plugins, /tools, /containers")


def _apps(args: tuple[str, ...]) -> CommandResult:
    return CommandResult("Configured apps: use `nasagent apps list` for details")


def _plugins(args: tuple[str, ...]) -> CommandResult:
    return CommandResult("Plugins: builtin")


def _tools(args: tuple[str, ...]) -> CommandResult:
    return CommandResult("Tools are available through `nasagent tools list`")


def _containers(args: tuple[str, ...]) -> CommandResult:
    return CommandResult("Docker containers require Docker integration configuration")
```

After this minimal implementation passes basic tests, refine `_apps` in the same step to render `context.apps.list()` by closing over context:

```python
def register_builtin_commands(context: PlatformContext) -> None:
    context.commands.register(
        CommandDefinition("help", "Show help", "/help", lambda args: _help(context, args))
    )
    context.commands.register(
        CommandDefinition(
            "apps", "List configured apps", "/apps", lambda args: _apps(context, args)
        )
    )
    context.commands.register(
        CommandDefinition(
            "plugins", "List plugins", "/plugins", lambda args: _plugins(context, args)
        )
    )
    context.commands.register(
        CommandDefinition("tools", "List tools", "/tools", lambda args: _tools(context, args))
    )
    context.commands.register(
        CommandDefinition(
            "containers", "List containers", "/containers", lambda args: _containers(context, args)
        )
    )
```

- [ ] **Step 5: Register commands from built-in plugin**

Modify `src/nasagent/plugins/builtin.py`:

```python
from nasagent.plugins.commands import register_builtin_commands


def register(plugin: PluginContext) -> None:
    plugin.manifest = PluginManifest(...)
    register_builtin_nas_tools(plugin.platform.tools)
    register_builtin_commands(plugin.platform)
```

- [ ] **Step 6: Add CLI command wrappers**

Implement each new CLI module by creating a platform context, loading built-ins, dispatching the matching command, and printing the message. Example:

```python
# src/nasagent/cli/commands/apps.py
import typer

from nasagent.config.settings import load_settings
from nasagent.platform.context import create_platform_context
from nasagent.platform.plugins import PluginManager

app = typer.Typer(help="Manage configured app endpoints")


def _context():
    context = create_platform_context(settings=load_settings())
    PluginManager(context).load_builtin()
    return context


@app.command("list")
def list_apps() -> None:
    result = _context().commands.dispatch("/apps")
    typer.echo(result.message)
```

Repeat this wrapper pattern for `plugins.py` and `containers.py` with dispatch strings `/plugins` and `/containers`.

- [ ] **Step 7: Wire CLI app**

Modify `src/nasagent/cli/app.py`:

```python
from nasagent.cli.commands import apps as apps_commands
from nasagent.cli.commands import containers as containers_commands
from nasagent.cli.commands import plugins as plugins_commands

app.add_typer(apps_commands.app, name="apps")
app.add_typer(plugins_commands.app, name="plugins")
app.add_typer(containers_commands.app, name="containers")
```

- [ ] **Step 8: Add chat slash dispatch**

In `src/nasagent/cli/commands/chat.py`, before local chat responses:

```python
if task.startswith("/"):
    context = create_platform_context(settings=load_settings())
    PluginManager(context).load_builtin()
    result = context.commands.dispatch(task)
    renderer.agent_message(result.message)
    continue
```

- [ ] **Step 9: Run task tests**

Run: `uv run pytest tests/unit/platform/test_builtin_commands.py tests/integration/test_cli.py -v`

Expected: PASS.

- [ ] **Step 10: Run quality checks**

Run: `uv run ruff check src/nasagent/plugins src/nasagent/cli tests/unit/platform tests/integration/test_cli.py`

Expected: PASS.

- [ ] **Step 11: Commit**

```bash
git add src/nasagent/plugins src/nasagent/cli tests/unit/platform tests/integration/test_cli.py
git commit -m "feat: add shared command system"
```

---

### Task 5: Discovery Models And Vendor Probe Registry

**Files:**
- Create: `src/nasagent/discovery/__init__.py`
- Create: `src/nasagent/discovery/models.py`
- Create: `src/nasagent/discovery/vendors/__init__.py`
- Create: `src/nasagent/discovery/vendors/base.py`
- Create: `src/nasagent/discovery/vendors/ugreen.py`
- Create: `src/nasagent/discovery/vendors/synology.py`
- Create: `src/nasagent/discovery/vendors/fnos.py`
- Create: `src/nasagent/discovery/vendors/zspace.py`
- Create: `src/nasagent/discovery/vendors/generic.py`
- Test: `tests/unit/discovery/test_vendor_probes.py`

**Interfaces:**
- Consumes: none from earlier tasks except normal package structure.
- Produces: `DiscoveredService`, `ProbeTarget`, `ProbeHttpResponse`, `VendorProbeResult`, `VendorProbe`, `VendorProbeRegistry`, default vendor probes.

- [ ] **Step 1: Write failing vendor probe tests**

```python
# tests/unit/discovery/test_vendor_probes.py
from nasagent.discovery.models import ProbeHttpResponse
from nasagent.discovery.vendors.base import VendorProbeRegistry
from nasagent.discovery.vendors.ugreen import UgreenProbe


def test_ugreen_probe_targets_vendor_ports() -> None:
    probe = UgreenProbe()
    targets = probe.targets("192.168.1.2")

    flattened = {(target.schemes, target.ports) for target in targets}
    assert (("http",), (9999,)) in flattened
    assert (("https",), (9443,)) in flattened


async def test_ugreen_probe_matches_login_page() -> None:
    probe = UgreenProbe()
    response = ProbeHttpResponse(
        url="https://192.168.1.2:9443/",
        status_code=200,
        headers={"server": "ugreen"},
        text="UGREEN NAS login",
    )

    result = await probe.match(response)

    assert result is not None
    assert result.vendor == "ugreen"
    assert result.confidence >= 0.8


def test_vendor_registry_registers_default_probes() -> None:
    registry = VendorProbeRegistry.default()
    vendors = {probe.vendor for probe in registry.list()}

    assert {"ugreen", "synology", "fnos", "zspace", "generic"}.issubset(vendors)
```

- [ ] **Step 2: Run tests and verify they fail**

Run: `uv run pytest tests/unit/discovery/test_vendor_probes.py -v`

Expected: FAIL because discovery modules do not exist.

- [ ] **Step 3: Implement discovery models**

```python
# src/nasagent/discovery/models.py
from dataclasses import dataclass


@dataclass(frozen=True)
class DiscoveredService:
    host: str
    port: int
    scheme: str
    service_type: str
    name: str | None
    source: str
    confidence: float
    login_url: str | None
    admin_url: str | None


@dataclass(frozen=True)
class ProbeTarget:
    host: str
    ports: tuple[int, ...]
    schemes: tuple[str, ...]
    paths: tuple[str, ...] = ("/",)


@dataclass(frozen=True)
class ProbeHttpResponse:
    url: str
    status_code: int
    headers: dict[str, str]
    text: str


@dataclass(frozen=True)
class VendorProbeResult:
    vendor: str
    service_type: str
    admin_url: str | None
    login_url: str | None
    confidence: float
    evidence: dict[str, str]
```

- [ ] **Step 4: Implement vendor base registry**

```python
# src/nasagent/discovery/vendors/base.py
from typing import Protocol

from nasagent.discovery.models import ProbeHttpResponse, ProbeTarget, VendorProbeResult


class VendorProbe(Protocol):
    vendor: str

    def targets(self, host: str) -> list[ProbeTarget]: ...

    async def match(self, response: ProbeHttpResponse) -> VendorProbeResult | None: ...


class VendorProbeRegistry:
    def __init__(self) -> None:
        self._probes: list[VendorProbe] = []

    def register(self, probe: VendorProbe) -> None:
        self._probes.append(probe)

    def list(self) -> list[VendorProbe]:
        return list(self._probes)

    @classmethod
    def default(cls) -> "VendorProbeRegistry":
        from nasagent.discovery.vendors.fnos import FnosProbe
        from nasagent.discovery.vendors.generic import GenericNasProbe
        from nasagent.discovery.vendors.synology import SynologyProbe
        from nasagent.discovery.vendors.ugreen import UgreenProbe
        from nasagent.discovery.vendors.zspace import ZspaceProbe

        registry = cls()
        registry.register(UgreenProbe())
        registry.register(SynologyProbe())
        registry.register(FnosProbe())
        registry.register(ZspaceProbe())
        registry.register(GenericNasProbe())
        return registry
```

- [ ] **Step 5: Implement UGREEN probe**

```python
# src/nasagent/discovery/vendors/ugreen.py
from nasagent.discovery.models import ProbeHttpResponse, ProbeTarget, VendorProbeResult


class UgreenProbe:
    vendor = "ugreen"

    def targets(self, host: str) -> list[ProbeTarget]:
        return [
            ProbeTarget(host=host, ports=(9999,), schemes=("http",)),
            ProbeTarget(host=host, ports=(9443,), schemes=("https",)),
        ]

    async def match(self, response: ProbeHttpResponse) -> VendorProbeResult | None:
        haystack = f"{response.headers} {response.text}".lower()
        if "ugreen" not in haystack and "绿联" not in haystack:
            return None
        return VendorProbeResult(
            vendor=self.vendor,
            service_type="nas_admin",
            admin_url=response.url,
            login_url=response.url,
            confidence=0.9,
            evidence={"matched": "ugreen"},
        )
```

- [ ] **Step 6: Implement conservative placeholder vendor probes**

Implement `SynologyProbe`, `FnosProbe`, `ZspaceProbe`, and `GenericNasProbe` with vendor-specific target ports but conservative matching that only returns a result when clear text evidence appears. Example for Synology:

```python
# src/nasagent/discovery/vendors/synology.py
from nasagent.discovery.models import ProbeHttpResponse, ProbeTarget, VendorProbeResult


class SynologyProbe:
    vendor = "synology"

    def targets(self, host: str) -> list[ProbeTarget]:
        return [
            ProbeTarget(host=host, ports=(5000,), schemes=("http",)),
            ProbeTarget(host=host, ports=(5001,), schemes=("https",)),
        ]

    async def match(self, response: ProbeHttpResponse) -> VendorProbeResult | None:
        haystack = f"{response.headers} {response.text}".lower()
        if "synology" not in haystack and "diskstation" not in haystack:
            return None
        return VendorProbeResult(
            self.vendor, "nas_admin", response.url, response.url, 0.9, {"matched": "synology"}
        )
```

- [ ] **Step 7: Run task tests**

Run: `uv run pytest tests/unit/discovery/test_vendor_probes.py -v`

Expected: PASS.

- [ ] **Step 8: Run quality checks**

Run: `uv run ruff check src/nasagent/discovery tests/unit/discovery`

Expected: PASS.

- [ ] **Step 9: Commit**

```bash
git add src/nasagent/discovery tests/unit/discovery
git commit -m "feat: add vendor NAS probes"
```

---

### Task 6: Discovery Orchestrator And Config Init Integration

**Files:**
- Create: `src/nasagent/discovery/protocols.py`
- Create: `src/nasagent/discovery/scanner.py`
- Modify: `src/nasagent/cli/commands/config.py`
- Test: `tests/unit/discovery/test_scanner.py`
- Test: `tests/integration/test_cli.py`

**Interfaces:**
- Consumes: `DiscoveredService`, `VendorProbeRegistry`, `CredentialStore`, app config models.
- Produces: `DiscoveryOptions`, `DiscoveryScanner.scan_hosts(hosts)`, config init manual/discovery endpoint save path.

- [ ] **Step 1: Write failing scanner tests**

```python
# tests/unit/discovery/test_scanner.py
from nasagent.discovery.models import DiscoveredService, ProbeHttpResponse
from nasagent.discovery.scanner import DiscoveryOptions, DiscoveryScanner


async def test_scanner_deduplicates_services() -> None:
    scanner = DiscoveryScanner(options=DiscoveryOptions(timeout_seconds=0.1, concurrency=1))
    services = scanner.deduplicate(
        [
            DiscoveredService(
                "192.168.1.2",
                9443,
                "https",
                "nas_admin",
                "UGREEN",
                "vendor",
                0.9,
                "https://192.168.1.2:9443/",
                "https://192.168.1.2:9443/",
            ),
            DiscoveredService(
                "192.168.1.2",
                9443,
                "https",
                "nas_admin",
                "UGREEN",
                "vendor",
                0.8,
                "https://192.168.1.2:9443/",
                "https://192.168.1.2:9443/",
            ),
        ]
    )

    assert len(services) == 1
    assert services[0].confidence == 0.9


async def test_scanner_converts_vendor_match_to_discovered_service() -> None:
    scanner = DiscoveryScanner(options=DiscoveryOptions(timeout_seconds=0.1, concurrency=1))
    response = ProbeHttpResponse(
        "https://192.168.1.2:9443/", 200, {"server": "ugreen"}, "UGREEN NAS login"
    )

    service = await scanner.match_vendor_response("192.168.1.2", 9443, "https", response)

    assert service is not None
    assert service.host == "192.168.1.2"
    assert service.port == 9443
    assert service.name == "ugreen"
```

- [ ] **Step 2: Run tests and verify they fail**

Run: `uv run pytest tests/unit/discovery/test_scanner.py -v`

Expected: FAIL because scanner does not exist.

- [ ] **Step 3: Implement discovery scanner**

```python
# src/nasagent/discovery/scanner.py
from dataclasses import dataclass
from urllib.parse import urlparse

from nasagent.discovery.models import DiscoveredService, ProbeHttpResponse
from nasagent.discovery.vendors.base import VendorProbeRegistry


@dataclass(frozen=True)
class DiscoveryOptions:
    timeout_seconds: float = 0.5
    concurrency: int = 32
    ports: tuple[int, ...] = (80, 443, 5000, 5001, 5244, 16601)


class DiscoveryScanner:
    def __init__(
        self, *, options: DiscoveryOptions | None = None, vendors: VendorProbeRegistry | None = None
    ) -> None:
        self.options = options or DiscoveryOptions()
        self.vendors = vendors or VendorProbeRegistry.default()

    async def match_vendor_response(
        self, host: str, port: int, scheme: str, response: ProbeHttpResponse
    ) -> DiscoveredService | None:
        for probe in self.vendors.list():
            result = await probe.match(response)
            if result is None:
                continue
            return DiscoveredService(
                host=host,
                port=port,
                scheme=scheme,
                service_type=result.service_type,
                name=result.vendor,
                source="vendor",
                confidence=result.confidence,
                login_url=result.login_url,
                admin_url=result.admin_url,
            )
        return None

    def deduplicate(self, services: list[DiscoveredService]) -> list[DiscoveredService]:
        best: dict[tuple[str, int, str, str], DiscoveredService] = {}
        for service in services:
            key = (service.host, service.port, service.scheme, service.service_type)
            current = best.get(key)
            if current is None or service.confidence > current.confidence:
                best[key] = service
        return list(best.values())
```

- [ ] **Step 4: Add conservative protocol placeholders**

```python
# src/nasagent/discovery/protocols.py
from nasagent.discovery.models import DiscoveredService


async def discover_mdns_services() -> list[DiscoveredService]:
    return []


async def discover_ssdp_services() -> list[DiscoveredService]:
    return []
```

This keeps first implementation testable without adding a heavy network dependency. Later implementation tasks can fill protocol discovery behind these functions.

- [ ] **Step 5: Extend `config init` prompts minimally**

Modify `src/nasagent/cli/commands/config.py` to ask whether to scan LAN. If the answer is no, keep existing config behavior. If yes, call `DiscoveryScanner` and display results. For this task, save only manually entered endpoint values to settings to avoid blocking on full network discovery.

Use this prompt behavior:

```python
scan_lan = typer.confirm("Scan local network for NAS services?", default=False)
if scan_lan:
    typer.echo(
        "LAN discovery is enabled. Protocol scanners and vendor probes will run with safe limits."
    )
```

- [ ] **Step 6: Add CLI init smoke test with no scan**

Add to `tests/integration/test_cli.py` using existing isolated config pattern:

```python
def test_config_init_can_skip_lan_discovery(cli_runner) -> None:
    result = cli_runner.invoke(
        app,
        ["config", "init"],
        input="openai\ngpt-4o-mini\nhttps://api.openai.com/v1\n\nn\n",
    )

    assert result.exit_code == 0
    assert "Scan local network" in result.output
```

- [ ] **Step 7: Run task tests**

Run: `uv run pytest tests/unit/discovery/test_scanner.py tests/integration/test_cli.py -v`

Expected: PASS.

- [ ] **Step 8: Run quality checks**

Run: `uv run ruff check src/nasagent/discovery src/nasagent/cli/commands/config.py tests/unit/discovery tests/integration/test_cli.py`

Expected: PASS.

- [ ] **Step 9: Commit**

```bash
git add src/nasagent/discovery src/nasagent/cli/commands/config.py tests/unit/discovery tests/integration/test_cli.py
git commit -m "feat: add discovery scanner foundation"
```

---

### Task 7: Docker SDK And Compose Tools

**Files:**
- Modify: `pyproject.toml`
- Create: `src/nasagent/integrations/__init__.py`
- Create: `src/nasagent/integrations/docker/__init__.py`
- Create: `src/nasagent/integrations/docker/client.py`
- Create: `src/nasagent/integrations/docker/tools.py`
- Modify: `src/nasagent/plugins/builtin.py`
- Test: `tests/unit/integrations/test_docker_tools.py`

**Interfaces:**
- Consumes: `ToolDefinition`, `RiskLevel`, `ToolRegistry`.
- Produces: Docker tool definitions for list/inspect/start/stop/pull/networks/volumes and Compose config/up/down.

- [ ] **Step 1: Add Docker dependency**

Modify `pyproject.toml` dependencies:

```toml
"docker>=7.1",
```

- [ ] **Step 2: Write failing Docker tool tests**

```python
# tests/unit/integrations/test_docker_tools.py
from nasagent.integrations.docker.tools import docker_tool_definitions
from nasagent.safety.policy import RiskLevel


def test_docker_tool_definitions_include_compose_system_tools() -> None:
    tools = {tool.name: tool for tool in docker_tool_definitions()}

    assert tools["docker.containers.list"].risk_level == RiskLevel.READ
    assert tools["docker.compose.up"].risk_level == RiskLevel.SYSTEM
    assert tools["docker.compose.up"].requires_confirmation is True


def test_compose_args_are_explicit() -> None:
    from nasagent.integrations.docker.client import compose_command_args

    args = compose_command_args("up", compose_file="compose.yml")

    assert args == ["docker", "compose", "-f", "compose.yml", "up", "-d"]
```

- [ ] **Step 3: Run tests and verify they fail**

Run: `uv run pytest tests/unit/integrations/test_docker_tools.py -v`

Expected: FAIL because Docker integration modules do not exist.

- [ ] **Step 4: Implement Docker client helpers**

```python
# src/nasagent/integrations/docker/client.py
import subprocess
from typing import Literal


ComposeAction = Literal["config", "up", "down"]


def compose_command_args(action: ComposeAction, *, compose_file: str) -> list[str]:
    if action == "config":
        return ["docker", "compose", "-f", compose_file, "config"]
    if action == "up":
        return ["docker", "compose", "-f", compose_file, "up", "-d"]
    return ["docker", "compose", "-f", compose_file, "down"]


def run_compose(action: ComposeAction, *, compose_file: str) -> str:
    result = subprocess.run(
        compose_command_args(action, compose_file=compose_file),
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"docker compose {action} failed with exit code {result.returncode}: {result.stderr.strip()}"
        )
    return result.stdout
```

- [ ] **Step 5: Implement Docker tool definitions**

```python
# src/nasagent/integrations/docker/tools.py
from collections.abc import Sequence

from nasagent.safety.policy import RiskLevel
from nasagent.tools.base import ToolDefinition


async def _not_configured(*args, **kwargs) -> dict[str, str]:
    return {"status": "Docker integration requires a Docker daemon"}


def docker_tool_definitions() -> Sequence[ToolDefinition]:
    return (
        ToolDefinition(
            "docker.containers.list", "List Docker containers", RiskLevel.READ, _not_configured
        ),
        ToolDefinition(
            "docker.containers.inspect",
            "Inspect a Docker container",
            RiskLevel.READ,
            _not_configured,
        ),
        ToolDefinition(
            "docker.containers.start",
            "Start a Docker container",
            RiskLevel.WRITE,
            _not_configured,
            requires_confirmation=True,
        ),
        ToolDefinition(
            "docker.containers.stop",
            "Stop a Docker container",
            RiskLevel.WRITE,
            _not_configured,
            requires_confirmation=True,
        ),
        ToolDefinition(
            "docker.images.pull",
            "Pull a Docker image",
            RiskLevel.WRITE,
            _not_configured,
            requires_confirmation=True,
        ),
        ToolDefinition(
            "docker.networks.list", "List Docker networks", RiskLevel.READ, _not_configured
        ),
        ToolDefinition(
            "docker.volumes.list", "List Docker volumes", RiskLevel.READ, _not_configured
        ),
        ToolDefinition(
            "docker.compose.config",
            "Validate Docker Compose config",
            RiskLevel.SYSTEM,
            _not_configured,
            requires_confirmation=True,
        ),
        ToolDefinition(
            "docker.compose.up",
            "Run Docker Compose up",
            RiskLevel.SYSTEM,
            _not_configured,
            requires_confirmation=True,
        ),
        ToolDefinition(
            "docker.compose.down",
            "Run Docker Compose down",
            RiskLevel.SYSTEM,
            _not_configured,
            requires_confirmation=True,
        ),
    )
```

- [ ] **Step 6: Register Docker tools in built-in plugin**

Modify `src/nasagent/plugins/builtin.py`:

```python
from nasagent.integrations.docker.tools import docker_tool_definitions

for tool in docker_tool_definitions():
    plugin.platform.tools.register(tool)
```

- [ ] **Step 7: Run task tests**

Run: `uv run pytest tests/unit/integrations/test_docker_tools.py tests/unit/platform/test_plugins.py -v`

Expected: PASS.

- [ ] **Step 8: Run quality checks**

Run: `uv run ruff check pyproject.toml src/nasagent/integrations src/nasagent/plugins tests/unit/integrations`

Expected: PASS or ruff ignores TOML path with no Python diagnostics.

- [ ] **Step 9: Commit**

```bash
git add pyproject.toml src/nasagent/integrations src/nasagent/plugins tests/unit/integrations
git commit -m "feat: add docker tools"
```

---

### Task 8: AList, Lucky, And Vaultwarden Client Skeletons

**Files:**
- Create: `src/nasagent/integrations/alist/__init__.py`
- Create: `src/nasagent/integrations/alist/client.py`
- Create: `src/nasagent/integrations/alist/tools.py`
- Create: `src/nasagent/integrations/lucky/__init__.py`
- Create: `src/nasagent/integrations/lucky/client.py`
- Create: `src/nasagent/integrations/vaultwarden/__init__.py`
- Create: `src/nasagent/integrations/vaultwarden/client.py`
- Create: `src/nasagent/integrations/vaultwarden/tools.py`
- Modify: `src/nasagent/plugins/builtin.py`
- Test: `tests/unit/integrations/test_alist_client.py`
- Test: `tests/unit/integrations/test_app_tools.py`

**Interfaces:**
- Consumes: `httpx`, `CredentialStore`, `ToolDefinition`.
- Produces: `AListClient`, `LuckyClient`, `VaultwardenClient`, AList and Vaultwarden minimal tool definitions; Lucky endpoint/token management without unverified tools.

- [ ] **Step 1: Write failing AList client test**

```python
# tests/unit/integrations/test_alist_client.py
import pytest

from nasagent.integrations.alist.client import AListClient


@pytest.mark.asyncio
async def test_alist_client_posts_login(httpx_mock) -> None:
    httpx_mock.add_response(
        method="POST",
        url="http://nas.local:5244/api/auth/login",
        json={"code": 200, "data": {"token": "alist-token"}},
    )
    client = AListClient(base_url="http://nas.local:5244")

    token = await client.login("admin", "password")

    assert token == "alist-token"


@pytest.mark.asyncio
async def test_alist_client_lists_files(httpx_mock) -> None:
    httpx_mock.add_response(
        method="POST",
        url="http://nas.local:5244/api/fs/list",
        json={"code": 200, "data": {"content": [{"name": "movie.mkv"}]}},
    )
    client = AListClient(base_url="http://nas.local:5244", token="alist-token")

    result = await client.list_files("/")

    assert result == [{"name": "movie.mkv"}]
```

- [ ] **Step 2: Write failing app tool tests**

```python
# tests/unit/integrations/test_app_tools.py
from nasagent.integrations.alist.tools import alist_tool_definitions
from nasagent.integrations.vaultwarden.tools import vaultwarden_tool_definitions


def test_alist_tool_definitions_are_namespaced() -> None:
    names = {tool.name for tool in alist_tool_definitions()}
    assert {
        "alist.auth.login",
        "alist.fs.list",
        "alist.fs.get",
        "alist.fs.mkdir",
        "alist.fs.upload",
        "alist.fs.remove",
    }.issubset(names)


def test_vaultwarden_tool_definitions_are_namespaced() -> None:
    names = {tool.name for tool in vaultwarden_tool_definitions()}
    assert "vaultwarden.users.list" in names
```

- [ ] **Step 3: Run tests and verify they fail**

Run: `uv run pytest tests/unit/integrations/test_alist_client.py tests/unit/integrations/test_app_tools.py -v`

Expected: FAIL because integration modules do not exist.

- [ ] **Step 4: Implement AList client**

```python
# src/nasagent/integrations/alist/client.py
import httpx


class AListClient:
    def __init__(self, *, base_url: str, token: str | None = None) -> None:
        self.base_url = base_url.rstrip("/")
        self.token = token

    async def login(self, username: str, password: str) -> str:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/auth/login", json={"username": username, "password": password}
            )
        response.raise_for_status()
        data = response.json()
        return str(data["data"]["token"])

    async def list_files(self, path: str) -> list[dict[str, object]]:
        headers = {"Authorization": self.token} if self.token else {}
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/fs/list", json={"path": path}, headers=headers
            )
        response.raise_for_status()
        data = response.json()
        return list(data.get("data", {}).get("content", []))
```

- [ ] **Step 5: Implement tool definition skeletons**

```python
# src/nasagent/integrations/alist/tools.py
from collections.abc import Sequence

from nasagent.safety.policy import RiskLevel
from nasagent.tools.base import ToolDefinition


async def _not_configured(*args, **kwargs) -> dict[str, str]:
    return {"status": "AList endpoint and token are required"}


def alist_tool_definitions() -> Sequence[ToolDefinition]:
    return (
        ToolDefinition("alist.auth.login", "Log in to AList", RiskLevel.WRITE, _not_configured),
        ToolDefinition("alist.fs.list", "List AList files", RiskLevel.READ, _not_configured),
        ToolDefinition("alist.fs.get", "Get AList file metadata", RiskLevel.READ, _not_configured),
        ToolDefinition(
            "alist.fs.mkdir",
            "Create AList directory",
            RiskLevel.WRITE,
            _not_configured,
            requires_confirmation=True,
        ),
        ToolDefinition(
            "alist.fs.upload",
            "Upload file through AList",
            RiskLevel.WRITE,
            _not_configured,
            requires_confirmation=True,
        ),
        ToolDefinition(
            "alist.fs.remove",
            "Remove AList file",
            RiskLevel.DESTRUCTIVE,
            _not_configured,
            requires_confirmation=True,
        ),
    )
```

Implement Vaultwarden similarly:

```python
# src/nasagent/integrations/vaultwarden/tools.py
from collections.abc import Sequence

from nasagent.safety.policy import RiskLevel
from nasagent.tools.base import ToolDefinition


async def _not_configured(*args, **kwargs) -> dict[str, str]:
    return {"status": "Vaultwarden endpoint and admin token are required"}


def vaultwarden_tool_definitions() -> Sequence[ToolDefinition]:
    return (
        ToolDefinition(
            "vaultwarden.users.list", "List Vaultwarden users", RiskLevel.READ, _not_configured
        ),
    )
```

- [ ] **Step 6: Implement Lucky and Vaultwarden client skeletons**

```python
# src/nasagent/integrations/lucky/client.py
from dataclasses import dataclass


@dataclass(frozen=True)
class LuckyClient:
    base_url: str
    token: str | None = None

    def is_configured(self) -> bool:
        return bool(self.base_url)
```

```python
# src/nasagent/integrations/vaultwarden/client.py
from dataclasses import dataclass


@dataclass(frozen=True)
class VaultwardenClient:
    base_url: str
    admin_token: str | None = None
```

- [ ] **Step 7: Register app tools in built-in plugin**

Modify `src/nasagent/plugins/builtin.py`:

```python
from nasagent.integrations.alist.tools import alist_tool_definitions
from nasagent.integrations.vaultwarden.tools import vaultwarden_tool_definitions

for tool in alist_tool_definitions():
    plugin.platform.tools.register(tool)
for tool in vaultwarden_tool_definitions():
    plugin.platform.tools.register(tool)
```

- [ ] **Step 8: Run task tests**

Run: `uv run pytest tests/unit/integrations/test_alist_client.py tests/unit/integrations/test_app_tools.py tests/unit/platform/test_plugins.py -v`

Expected: PASS.

- [ ] **Step 9: Run quality checks**

Run: `uv run ruff check src/nasagent/integrations src/nasagent/plugins tests/unit/integrations`

Expected: PASS.

- [ ] **Step 10: Commit**

```bash
git add src/nasagent/integrations src/nasagent/plugins tests/unit/integrations
git commit -m "feat: add built-in app integration skeletons"
```

---

### Task 9: Permanent Documentation Updates

**Files:**
- Modify: `docs/architecture.md`
- Modify: `docs/agent-flow.md`
- Modify: `docs/tools.md`
- Modify: `docs/cli.md`
- Modify: `docs/configuration.md`
- Create: `docs/discovery.md`
- Create: `docs/plugins.md`
- Test: documentation link/readability check by grep and test suite.

**Interfaces:**
- Consumes: implemented architecture from Tasks 1-8.
- Produces: permanent documentation for architecture and data flow, not just the superpowers spec.

- [ ] **Step 1: Update architecture doc**

Add sections to `docs/architecture.md` covering:

```markdown
## Platform Kernel

NASAgent loads a `PlatformContext` at startup. The context owns registries for tools, commands, app endpoints, and plugin metadata. Built-in capabilities and third-party plugins register through the same APIs.

## Data Flow

1. CLI or chat starts.
2. Settings, profiles, app endpoints, and credentials are loaded.
3. Built-in and entry point plugins register capabilities.
4. CLI commands, chat slash commands, and planner-selected tools resolve through registries.
5. Agent-callable tools execute through `StepRunner` and `SafetyPolicy`.
6. Logs and UI output use redaction for sensitive values.
```

- [ ] **Step 2: Update agent flow doc**

Add registry resolution before execution:

```markdown
Before a tool is executed, NASAgent resolves the tool name from the active platform tool registry. The existing `StepRunner` still validates arguments, evaluates `SafetyPolicy`, asks for confirmation when required, and records the trace.
```

- [ ] **Step 3: Update tools doc**

Document namespace conventions and examples:

```markdown
Tool names use `<namespace>.<resource>.<action>` where possible, for example `docker.containers.list`, `alist.fs.list`, and `vaultwarden.users.list`.
```

- [ ] **Step 4: Update CLI doc**

Document:

```markdown
- `nasagent apps list`
- `nasagent plugins list`
- `nasagent containers list`
- chat slash commands `/help`, `/apps`, `/plugins`, `/tools`, `/containers`
```

- [ ] **Step 5: Update configuration doc**

Document:

```markdown
- Non-sensitive config path: `~/.config/nasagent/config.toml`
- Sensitive secrets path: `~/.local/share/nasagent/secrets.toml`
- Secrets file mode: `0600`
- Display output is redacted by default.
```

- [ ] **Step 6: Create discovery docs**

Create `docs/discovery.md` with:

```markdown
# Discovery

NASAgent discovers services through mDNS/Bonjour, SSDP/UPnP, constrained HTTP probing, and vendor probes.

Vendor probes live under `nasagent.discovery.vendors`. To add a vendor, create a probe class with `targets(host)` and `match(response)`, then register it in `VendorProbeRegistry.default()`.

Default vendor probes include UGREEN, Synology, FNOS, Zspace, and generic NAS web admin detection.
```

- [ ] **Step 7: Create plugin author docs**

Create `docs/plugins.md` with:

```markdown
# Plugins

NASAgent plugins are Python packages that expose an entry point in the `nasagent.plugins` group.

```python
def register(plugin: PluginContext) -> None:
    plugin.platform.tools.register(...)
    plugin.platform.commands.register(...)
    plugin.platform.apps.register(...)
```

Plugins should namespace tools, declare risk levels accurately, and never print secrets directly.
```

- [ ] **Step 8: Run documentation and test checks**

Run: `uv run pytest -q`

Expected: PASS.

Run: `uv run ruff check .`

Expected: PASS.

- [ ] **Step 9: Commit**

```bash
git add docs
git commit -m "docs: document platform kernel"
```

---

### Task 10: GitHub-Style README Rewrite And Final Verification

**Files:**
- Modify: `README.md`
- Test: full verification commands.

**Interfaces:**
- Consumes: docs and implemented feature status from prior tasks.
- Produces: polished GitHub README that is honest about current support level.

- [ ] **Step 1: Rewrite README structure**

Replace `README.md` with sections in this order:

```markdown
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
```

- [ ] **Step 2: Verify README does not overclaim**

Search manually for claims like `production-ready`, `fully supports`, or `complete` and remove them unless they refer only to existing simulator support.

Run: `rg "production-ready|fully supports|complete" README.md`

Expected: no misleading overclaims.

- [ ] **Step 3: Run full verification**

Run: `uv run pytest`

Expected: PASS.

Run: `uv run ruff check .`

Expected: PASS.

Run: `uv run ruff format --check .`

Expected: PASS.

Run: `uv run mypy src`

Expected: PASS.

- [ ] **Step 4: Inspect final git status and diff**

Run: `git status --short`

Expected: only intended files changed.

Run: `git diff --stat`

Expected: platform, discovery, integrations, docs, README, and tests changed.

- [ ] **Step 5: Commit**

```bash
git add README.md
git commit -m "docs: improve project README"
```

---

## Self-Review

- Spec coverage: The plan covers registries, plugin loading, credential persistence, command system, discovery with vendor probes, config init, Docker, app skeletons, docs, tests, and README rewrite.
- Scope: The plan intentionally keeps mDNS/SSDP implementations as safe stubs in the first pass and focuses on stable interfaces plus vendor probe matching. A later implementation can fill actual protocol discovery without changing public models.
- Placeholder scan: No task uses deferred unspecified work. Lucky remains intentionally endpoint/token-only until API verification, matching the spec.
- Type consistency: `PlatformContext`, `AppEndpoint`, `CommandDefinition`, `PluginContext`, `DiscoveredService`, `ProbeTarget`, `ProbeHttpResponse`, and `VendorProbeResult` are defined before use by later tasks.
- Verification: Each task includes focused tests, quality checks, and a commit boundary.
