from inspect import signature
from pathlib import Path

import pytest
from rich.console import Console
from typer.testing import CliRunner

from nasagent.agent.planning.schemas import Plan, PlanStep
from nasagent.agent.state.models import AgentState, StepResult
from nasagent.cli.app import app
from nasagent.cli.commands import chat as chat_command
from nasagent.cli.commands import config as config_command
from nasagent.cli.commands import run as run_command
from nasagent.cli.rendering.panels import banner_panel, task_result_panel
from nasagent.cli.rendering.renderer import CliRenderer
from nasagent.config import settings as settings_module
from nasagent.config.secrets import CredentialStore
from nasagent.config.settings import LlmSettings, NasAgentSettings
from nasagent.llm.base import LlmProvider
from nasagent.platform import plugins as platform_plugins
from nasagent.platform.plugins import PluginManifest
from nasagent.safety.risk import RiskLevel
from nasagent.tools.base import ToolDefinition
from nasagent.tools.schemas import ToolCallResult


async def _fake_plugin_tool() -> dict[str, str]:
    return {"status": "ok"}


def _fake_entry_points():  # type: ignore[no-untyped-def]
    def register(plugin_context):  # type: ignore[no-untyped-def]
        plugin_context.manifest = PluginManifest(name="third-party", version="1.2.3")
        plugin_context.platform.tools.register(
            ToolDefinition("example.ping", "Ping example plugin", RiskLevel.READ, _fake_plugin_tool)
        )

    class FakeEntryPoint:
        name = "third-party"

        def load(self):  # type: ignore[no-untyped-def]
            return register

    return [FakeEntryPoint()]


def _broken_entry_points():  # type: ignore[no-untyped-def]
    class BrokenEntryPoint:
        name = "broken"

        def load(self):  # type: ignore[no-untyped-def]
            raise RuntimeError("boom")

    return [BrokenEntryPoint()]


@pytest.fixture
def cli_runner() -> CliRunner:
    return CliRunner()


class FakeOnlineProvider(LlmProvider):
    async def complete(self, messages):  # type: ignore[no-untyped-def]
        return Plan(
            goal="check storage",
            steps=[
                PlanStep(
                    id="s1",
                    description="Get storage",
                    risk="read",
                    expected_tools=["get_storage_status"],
                )
            ],
        ).model_dump_json()

    async def stream_complete(self, messages):  # type: ignore[no-untyped-def]
        yield await self.complete(messages)


def test_tools_list_command() -> None:
    runner = CliRunner()

    result = runner.invoke(app, ["tools", "list"])

    assert result.exit_code == 0
    assert "get_storage_status" in result.output


def test_tools_list_command_includes_platform_plugin_tools() -> None:
    runner = CliRunner()

    result = runner.invoke(app, ["tools", "list"])

    assert result.exit_code == 0
    assert "docker.containers.list" in result.output
    assert "alist.fs.list" in result.output
    assert "vaultwarden.users.list" in result.output


def test_chat_tools_slash_uses_platform_registry() -> None:
    runner = CliRunner()

    result = runner.invoke(app, ["chat", "--profile", "simulator"], input="/tools\nexit\n")

    assert result.exit_code == 0
    assert "Agent-callable tools:" in result.output
    assert "docker.containers.list" in result.output
    assert "alist.fs.list" in result.output


def test_apps_list_command_smoke(cli_runner) -> None:  # type: ignore[no-untyped-def]
    result = cli_runner.invoke(app, ["apps", "list"])

    assert result.exit_code == 0
    assert "Configured apps" in result.output


def test_apps_list_command_reads_configured_apps(cli_runner, tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    config_path = tmp_path / "config.toml"
    config_path.write_text(
        "[apps.home]\n"
        'app_type = "alist"\n'
        'base_url = "http://nas.local:5244"\n'
        'credential_key = "alist.home.token"\n',
        encoding="utf-8",
    )
    monkeypatch.setattr(settings_module, "DEFAULT_CONFIG_PATH", config_path)

    result = cli_runner.invoke(app, ["apps", "list"])

    assert result.exit_code == 0
    assert "home" in result.output
    assert "alist" in result.output
    assert "http://nas.local:5244" in result.output
    assert "alist.home.token" in result.output


def test_plugins_list_command_smoke(cli_runner) -> None:  # type: ignore[no-untyped-def]
    result = cli_runner.invoke(app, ["plugins", "list"])

    assert result.exit_code == 0
    assert "builtin" in result.output


def test_plugins_list_command_loads_entry_points(cli_runner, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(platform_plugins, "entry_points_select", _fake_entry_points)

    result = cli_runner.invoke(app, ["plugins", "list"])

    assert result.exit_code == 0
    assert "third-party" in result.output
    assert "1.2.3" in result.output


def test_chat_plugins_slash_reports_entry_point_errors(cli_runner, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(platform_plugins, "entry_points_select", _broken_entry_points)

    result = cli_runner.invoke(app, ["chat", "--profile", "simulator"], input="/plugins\nexit\n")

    assert result.exit_code == 0
    assert "broken" in result.output
    assert "boom" in result.output


def test_rich_banner_panel_includes_profile_provider_and_streaming_state() -> None:
    console = Console(record=True, color_system=None, width=100)

    console.print(banner_panel("simulator", "openai", True))

    output = console.export_text()
    assert "NASAgent" in output
    assert "openai · simulator · streaming on" in output


def test_rich_task_result_panel_lists_tools_from_agent_state() -> None:
    state = AgentState(
        goal="check storage",
        final_summary="Executed tools: get_storage_status",
        step_results=[
            StepResult(
                step_id="s1",
                success=True,
                tool_results=[ToolCallResult(tool_name="get_storage_status", result={})],
            )
        ],
    )
    console = Console(record=True, color_system=None, width=100)

    console.print(task_result_panel(state))

    output = console.export_text()
    assert "Task Complete" in output
    assert "Goal" in output
    assert "check storage" in output
    assert "Tools" in output
    assert "get_storage_status" in output


def test_task_result_panel_public_api_accepts_only_agent_state() -> None:
    assert list(signature(task_result_panel).parameters) == ["state"]


def test_cli_renderer_prints_reusable_terminal_lines() -> None:
    console = Console(record=True, color_system=None, width=100)
    renderer = CliRenderer(console)

    renderer.prompt()
    renderer.agent_start()
    renderer.agent_chunk("hello")
    renderer.agent_end()
    renderer.status("working")
    renderer.success("done")
    renderer.tool("get_storage_status", completed=True)

    output = console.export_text()
    assert "you      >" in output
    assert "agent    >" in output
    assert "hello" in output
    assert "system   ." in output
    assert "working" in output
    assert "done" in output
    assert "tool     ." in output
    assert "get_storage_status completed" in output


def test_cli_renderer_prints_stable_error_label() -> None:
    console = Console(record=True, color_system=None, width=100)
    renderer = CliRenderer(console)

    renderer.error("broken")

    output = console.export_text()
    assert "error    ! broken" in output


def test_cli_renderer_renders_markdown_agent_messages() -> None:
    console = Console(record=True, color_system=None, width=100)
    renderer = CliRenderer(console)

    renderer.agent_message("## Title\n\n- **fast**\n- `safe`")

    output = console.export_text()
    assert "agent    >" in output
    assert "Title" in output
    assert "fast" in output
    assert "safe" in output
    assert "## Title" not in output


def test_cli_renderer_detects_numbered_markdown() -> None:
    console = Console(record=True, color_system=None, width=100)
    renderer = CliRenderer(console)

    renderer.agent_message("1. First\n2. Second")

    output = console.export_text()
    assert "agent    >" in output
    assert "First" in output
    assert "1. First" not in output


def test_cli_renderer_spinner_leaves_stable_transcript_line() -> None:
    console = Console(record=True, color_system=None, width=100)
    renderer = CliRenderer(console)

    with renderer.spinner("system", "planning"):
        pass

    output = console.export_text()
    assert "system   . planning" in output


def test_run_command_with_simulator(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(settings_module, "DEFAULT_CONFIG_PATH", tmp_path / "missing.toml")
    runner = CliRunner()

    result = runner.invoke(app, ["run", "check storage", "--profile", "simulator"])

    assert result.exit_code == 0
    assert "system   . planning task" in result.output
    assert "system   . plan ready" in result.output
    assert "tool     . get_storage_status completed" in result.output
    assert "Task Complete" in result.output
    assert "Executed tools: get_storage_status" in result.output


def test_run_command_reports_malformed_toml(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    config_path = tmp_path / "config.toml"
    config_path.write_text('[llm\nmodel = "broken"\n', encoding="utf-8")
    monkeypatch.setattr(settings_module, "DEFAULT_CONFIG_PATH", config_path)
    runner = CliRunner()

    result = runner.invoke(app, ["run", "check storage", "--profile", "simulator"])

    assert result.exit_code != 0
    assert "Config Error" in result.output
    assert "Invalid TOML config" in result.output
    assert config_path.name in result.output
    assert "Traceback" not in result.output


def test_chat_command_runs_until_exit(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(settings_module, "DEFAULT_CONFIG_PATH", tmp_path / "missing.toml")
    runner = CliRunner()

    result = runner.invoke(app, ["chat", "--profile", "simulator"], input="check storage\nexit\n")

    assert result.exit_code == 0
    assert "NASAgent" in result.output
    assert "you      >" in result.output
    assert "system   . planning and running task" in result.output
    assert "system   . plan ready" in result.output
    assert "tool     . get_storage_status completed" in result.output
    assert "Task Complete" in result.output
    assert "Executed tools: get_storage_status" in result.output
    assert "Goodbye" in result.output


def test_chat_apps_slash_lists_configured_apps(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    config_path = tmp_path / "config.toml"
    config_path.write_text(
        "[apps.home]\n"
        'app_type = "alist"\n'
        'base_url = "http://nas.local:5244"\n'
        'credential_key = "alist.home.token"\n',
        encoding="utf-8",
    )
    monkeypatch.setattr(settings_module, "DEFAULT_CONFIG_PATH", config_path)
    runner = CliRunner()

    result = runner.invoke(app, ["chat", "--profile", "simulator"], input="/apps\nexit\n")

    assert result.exit_code == 0
    assert "Configured apps:" in result.output
    assert "home" in result.output
    assert "alist" in result.output
    assert "http://nas.local:5244" in result.output
    assert "alist.home.token" in result.output


def test_chat_command_runs_chinese_storage_task_offline(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(settings_module, "DEFAULT_CONFIG_PATH", tmp_path / "missing.toml")
    runner = CliRunner()

    result = runner.invoke(app, ["chat", "--profile", "simulator"], input="查看存储状态\nexit\n")

    assert result.exit_code == 0
    assert "tool     . get_storage_status completed" in result.output
    assert "Task Complete" in result.output
    assert "Executed tools: get_storage_status" in result.output


def test_chat_command_routes_conversation_to_llm_without_tools(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    config_path = tmp_path / "config.toml"
    config_path.write_text('[llm]\napi_key = "test-key"\n', encoding="utf-8")
    monkeypatch.setattr(settings_module, "DEFAULT_CONFIG_PATH", config_path)

    class FakeChatProvider:
        def __init__(self, settings) -> None:  # type: ignore[no-untyped-def]
            self.settings = settings

        async def complete(self, messages):  # type: ignore[no-untyped-def]
            return "RAID is a storage technology."

        async def stream_complete(self, messages):  # type: ignore[no-untyped-def]
            yield "RAID is "
            yield "a storage technology."

    monkeypatch.setattr(chat_command, "OpenAiProvider", FakeChatProvider)
    runner = CliRunner()

    result = runner.invoke(app, ["chat", "--profile", "simulator"], input="explain RAID\nexit\n")

    assert result.exit_code == 0
    assert "system   . waiting for LLM" in result.output
    assert "agent    >" in result.output
    assert "RAID is a storage technology." in result.output
    assert "Executed tools" not in result.output


def test_chat_command_preserves_plain_text_streaming_output(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    config_path = tmp_path / "config.toml"
    config_path.write_text('[llm]\napi_key = "test-key"\n', encoding="utf-8")
    monkeypatch.setattr(settings_module, "DEFAULT_CONFIG_PATH", config_path)

    class FakeChatProvider:
        def __init__(self, settings) -> None:  # type: ignore[no-untyped-def]
            self.settings = settings

        async def complete(self, messages):  # type: ignore[no-untyped-def]
            return "complete should not be called"

        async def stream_complete(self, messages):  # type: ignore[no-untyped-def]
            yield "plain "
            yield "stream"

    monkeypatch.setattr(chat_command, "OpenAiProvider", FakeChatProvider)
    runner = CliRunner()

    result = runner.invoke(app, ["chat", "--profile", "simulator"], input="explain RAID\nexit\n")

    assert result.exit_code == 0
    assert "system   . waiting for LLM" in result.output
    assert "agent    > plain stream" in result.output
    assert "Executed tools" not in result.output


def test_chat_command_renders_markdown_conversation_response(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    config_path = tmp_path / "config.toml"
    config_path.write_text('[llm]\napi_key = "test-key"\n', encoding="utf-8")
    monkeypatch.setattr(settings_module, "DEFAULT_CONFIG_PATH", config_path)

    class FakeChatProvider:
        def __init__(self, settings) -> None:  # type: ignore[no-untyped-def]
            self.settings = settings

        async def complete(self, messages):  # type: ignore[no-untyped-def]
            return "## RAID\n\n- **Redundancy**\n- `storage`"

        async def stream_complete(self, messages):  # type: ignore[no-untyped-def]
            yield "## RAID\n\n"
            yield "- **Redundancy**\n- `storage`"

    monkeypatch.setattr(chat_command, "OpenAiProvider", FakeChatProvider)
    runner = CliRunner()

    result = runner.invoke(app, ["chat", "--profile", "simulator"], input="explain RAID\nexit\n")

    assert result.exit_code == 0
    assert "agent    >" in result.output
    assert "RAID" in result.output
    assert "Redundancy" in result.output
    assert "storage" in result.output
    assert "## RAID" not in result.output
    assert "Executed tools" not in result.output


def test_chat_command_detects_markdown_split_across_initial_chunks(
    tmp_path: Path, monkeypatch
) -> None:  # type: ignore[no-untyped-def]
    config_path = tmp_path / "config.toml"
    config_path.write_text('[llm]\napi_key = "test-key"\n', encoding="utf-8")
    monkeypatch.setattr(settings_module, "DEFAULT_CONFIG_PATH", config_path)

    class FakeChatProvider:
        def __init__(self, settings) -> None:  # type: ignore[no-untyped-def]
            self.settings = settings

        async def complete(self, messages):  # type: ignore[no-untyped-def]
            return "complete should not be called"

        async def stream_complete(self, messages):  # type: ignore[no-untyped-def]
            yield "1"
            yield ". First\n"
            yield "2. Second"

    monkeypatch.setattr(chat_command, "OpenAiProvider", FakeChatProvider)
    runner = CliRunner()

    result = runner.invoke(app, ["chat", "--profile", "simulator"], input="explain RAID\nexit\n")

    assert result.exit_code == 0
    assert "agent    >" in result.output
    assert "First" in result.output
    assert "Second" in result.output
    assert "1. First" not in result.output


def test_chat_command_treats_list_raid_levels_as_conversation(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    config_path = tmp_path / "config.toml"
    config_path.write_text('[llm]\napi_key = "test-key"\n', encoding="utf-8")
    monkeypatch.setattr(settings_module, "DEFAULT_CONFIG_PATH", config_path)

    class FakeChatProvider:
        def __init__(self, settings) -> None:  # type: ignore[no-untyped-def]
            self.settings = settings

        async def complete(self, messages):  # type: ignore[no-untyped-def]
            return "fake LLM RAID levels response"

        async def stream_complete(self, messages):  # type: ignore[no-untyped-def]
            raise AssertionError("stream_complete should not be called")

    monkeypatch.setattr(chat_command, "OpenAiProvider", FakeChatProvider)
    runner = CliRunner()

    result = runner.invoke(
        app,
        ["chat", "--profile", "simulator", "--no-stream"],
        input="list RAID levels\nexit\n",
    )

    assert result.exit_code == 0
    assert "system   . waiting for LLM" in result.output
    assert "agent    > fake LLM RAID levels response" in result.output
    assert "Executed tools" not in result.output


def test_chat_command_can_disable_streaming_for_conversation(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    config_path = tmp_path / "config.toml"
    config_path.write_text('[llm]\napi_key = "test-key"\n', encoding="utf-8")
    monkeypatch.setattr(settings_module, "DEFAULT_CONFIG_PATH", config_path)

    class FakeChatProvider:
        def __init__(self, settings) -> None:  # type: ignore[no-untyped-def]
            self.settings = settings

        async def complete(self, messages):  # type: ignore[no-untyped-def]
            return "complete response"

        async def stream_complete(self, messages):  # type: ignore[no-untyped-def]
            raise AssertionError("stream_complete should not be called")

    monkeypatch.setattr(chat_command, "OpenAiProvider", FakeChatProvider)
    runner = CliRunner()

    result = runner.invoke(
        app,
        ["chat", "--profile", "simulator", "--no-stream"],
        input="explain RAID\nexit\n",
    )

    assert result.exit_code == 0
    assert "system   . waiting for LLM" in result.output
    assert "agent    > complete response" in result.output
    assert "complete response" in result.output
    assert "Executed tools" not in result.output


def test_chat_command_reports_malformed_toml(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    config_path = tmp_path / "config.toml"
    config_path.write_text('[llm\nmodel = "broken"\n', encoding="utf-8")
    monkeypatch.setattr(settings_module, "DEFAULT_CONFIG_PATH", config_path)
    runner = CliRunner()

    result = runner.invoke(app, ["chat", "--profile", "simulator"], input="check storage\n")

    assert result.exit_code != 0
    assert "Config Error" in result.output
    assert "Invalid TOML config" in result.output
    assert config_path.name in result.output
    assert "Traceback" not in result.output


def test_chat_command_reports_malformed_toml_before_local_greeting(
    tmp_path: Path, monkeypatch
) -> None:  # type: ignore[no-untyped-def]
    config_path = tmp_path / "config.toml"
    config_path.write_text('[llm\nmodel = "broken"\n', encoding="utf-8")
    monkeypatch.setattr(settings_module, "DEFAULT_CONFIG_PATH", config_path)
    runner = CliRunner()

    result = runner.invoke(app, ["chat", "--profile", "simulator"], input="hello\n")

    assert result.exit_code != 0
    assert "Config Error" in result.output
    assert "Invalid TOML config" in result.output
    assert config_path.name in result.output
    assert "Traceback" not in result.output


def test_run_command_with_device_task_does_not_report_storage_plan(
    tmp_path: Path, monkeypatch
) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(settings_module, "DEFAULT_CONFIG_PATH", tmp_path / "missing.toml")
    runner = CliRunner()

    result = runner.invoke(app, ["run", "show device status", "--profile", "simulator"])

    assert result.exit_code == 0
    assert "show device status" in result.output
    assert "Executed tools: get_storage_status" not in result.output


def test_execute_simulator_task_uses_injected_online_provider_factory(tmp_path) -> None:  # type: ignore[no-untyped-def]
    captured_settings: list[LlmSettings] = []

    def provider_factory(llm_settings: LlmSettings) -> LlmProvider:
        captured_settings.append(llm_settings)
        return FakeOnlineProvider()

    settings = NasAgentSettings(
        llm=LlmSettings(api_key="test-key", base_url="https://openai-compatible.example/v1"),
        observability={"run_log_dir": str(tmp_path)},
    )

    state = run_command.execute_simulator_task(
        "check storage",
        settings=settings,
        online=True,
        provider_factory=provider_factory,
    )

    assert state.step_results[0].tool_results[0].tool_name == "get_storage_status"
    assert captured_settings == [settings.llm]


def test_execute_simulator_task_uses_credential_store_api_key_for_provider_selection(
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "config.toml"
    config_path.write_text('[llm]\nbase_url = "https://openai-compatible.example/v1"\n')
    store = CredentialStore(tmp_path / "secrets.toml")
    store.set("llm.api_key", "stored-api-key")
    settings = settings_module.load_settings(config_path, credential_store=store)
    captured_settings: list[LlmSettings] = []

    def provider_factory(llm_settings: LlmSettings) -> LlmProvider:
        captured_settings.append(llm_settings)
        return FakeOnlineProvider()

    state = run_command.execute_simulator_task(
        "check storage",
        settings=settings,
        provider_factory=provider_factory,
    )

    assert state.step_results[0].tool_results[0].tool_name == "get_storage_status"
    assert captured_settings[0].api_key == "stored-api-key"


def test_execute_simulator_task_offline_stays_deterministic(tmp_path) -> None:  # type: ignore[no-untyped-def]
    settings = NasAgentSettings(observability={"run_log_dir": str(tmp_path)})

    state = run_command.execute_simulator_task(
        "show device status", settings=settings, online=False
    )

    assert state.step_results[0].tool_results[0].tool_name == "get_device_status"


def test_config_show_redacts_api_key(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(settings_module, "DEFAULT_CONFIG_PATH", tmp_path / "missing.toml")
    monkeypatch.setenv("NASAGENT_LLM__API_KEY", "secret-api-key")
    runner = CliRunner()

    result = runner.invoke(app, ["config", "show"])

    assert result.exit_code == 0
    assert "secret-api-key" not in result.output
    assert 'api_key = "********"' in result.output


def test_config_show_redacts_credential_store_api_key(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    config_path = tmp_path / "config.toml"
    secrets_path = tmp_path / "secrets.toml"
    config_path.write_text('[llm]\nmodel = "file-model"\n', encoding="utf-8")
    CredentialStore(secrets_path).set("llm.api_key", "stored-api-key")
    monkeypatch.setattr(settings_module, "DEFAULT_CONFIG_PATH", config_path)
    monkeypatch.setattr(
        settings_module,
        "CredentialStore",
        lambda: CredentialStore(secrets_path),
    )
    runner = CliRunner()

    result = runner.invoke(app, ["config", "show"])

    assert result.exit_code == 0
    assert "stored-api-key" not in result.output
    assert 'api_key = "********"' in result.output
    assert "stored-api-key" not in config_path.read_text(encoding="utf-8")


def test_config_init_creates_toml_file(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    config_path = tmp_path / "config.toml"
    secrets_path = tmp_path / "secrets.toml"
    monkeypatch.setattr(settings_module, "DEFAULT_CONFIG_PATH", config_path)
    monkeypatch.setattr(
        config_command,
        "CredentialStore",
        lambda: CredentialStore(secrets_path),
    )
    runner = CliRunner()

    result = runner.invoke(
        app,
        ["config", "init"],
        input="openai\ngpt-4o-mini\nhttps://openai-compatible.example/v1\nsecret-api-key\nn\n",
    )

    assert result.exit_code == 0
    assert config_path.exists()
    content = config_path.read_text(encoding="utf-8")
    assert "[llm]" in content
    assert 'provider = "openai"' in content
    assert 'model = "gpt-4o-mini"' in content
    assert 'base_url = "https://openai-compatible.example/v1"' in content
    assert "secret-api-key" not in content
    assert "api_key" not in content
    assert secrets_path.exists()
    assert oct(secrets_path.stat().st_mode & 0o777) == "0o600"
    assert '"llm.api_key" = "secret-api-key"' in secrets_path.read_text(encoding="utf-8")
    assert "[safety]" in content
    assert "[observability]" in content
    assert str(config_path) in result.output


def test_config_init_uses_safe_defaults_when_environment_is_set(
    tmp_path: Path, monkeypatch
) -> None:  # type: ignore[no-untyped-def]
    config_path = tmp_path / "config.toml"
    monkeypatch.setattr(settings_module, "DEFAULT_CONFIG_PATH", config_path)
    monkeypatch.setenv("NASAGENT_LLM__PROVIDER", "env-provider")
    monkeypatch.setenv("NASAGENT_LLM__MODEL", "env-model")
    monkeypatch.setenv("NASAGENT_LLM__BASE_URL", "https://env.example/v1")
    monkeypatch.setenv("NASAGENT_LLM__API_KEY", "env-api-key")
    monkeypatch.setenv("NASAGENT_SAFETY__ALLOW_AUTO_WRITE", "true")
    monkeypatch.setenv("NASAGENT_SAFETY__ALLOW_DESTRUCTIVE", "true")
    monkeypatch.setenv("NASAGENT_OBSERVABILITY__RUN_LOG_DIR", "/tmp/env-runs")
    runner = CliRunner()

    result = runner.invoke(app, ["config", "init"], input="\n\n\n\nn\n")

    assert result.exit_code == 0
    content = config_path.read_text(encoding="utf-8")
    assert 'provider = "openai"' in content
    assert 'model = "gpt-4.1-mini"' in content
    assert "env-provider" not in content
    assert "env-model" not in content
    assert "https://env.example/v1" not in content
    assert "env-api-key" not in content
    assert "allow_auto_write = false" in content
    assert "allow_destructive = false" in content
    assert 'run_log_dir = "~/.nasagent/runs"' in content


def test_config_init_omits_blank_optional_values(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    config_path = tmp_path / "config.toml"
    monkeypatch.setattr(settings_module, "DEFAULT_CONFIG_PATH", config_path)
    runner = CliRunner()

    result = runner.invoke(app, ["config", "init"], input="\n\n\n\nn\n")

    assert result.exit_code == 0
    content = config_path.read_text(encoding="utf-8")
    assert "base_url" not in content
    assert "api_key" not in content


def test_config_init_can_skip_lan_discovery(cli_runner, tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(settings_module, "DEFAULT_CONFIG_PATH", tmp_path / "config.toml")

    result = cli_runner.invoke(
        app,
        ["config", "init"],
        input="openai\ngpt-4o-mini\nhttps://api.openai.com/v1\n\nn\n",
    )

    assert result.exit_code == 0
    assert "Scan local network" in result.output


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


def test_config_show_reports_malformed_toml(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    config_path = tmp_path / "config.toml"
    config_path.write_text('[llm\nmodel = "broken"\n', encoding="utf-8")
    monkeypatch.setattr(settings_module, "DEFAULT_CONFIG_PATH", config_path)
    runner = CliRunner()

    result = runner.invoke(app, ["config", "show"])

    assert result.exit_code != 0
    assert "Invalid TOML config" in result.output
    assert str(config_path) in result.output
    assert "Traceback" not in result.output
