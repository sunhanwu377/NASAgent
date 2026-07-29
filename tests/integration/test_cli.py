from typer.testing import CliRunner

from nasagent.agent.planning.schemas import Plan, PlanStep
from nasagent.cli.app import app
from nasagent.cli.commands import run as run_command
from nasagent.config.settings import LlmSettings, NasAgentSettings
from nasagent.llm.base import LlmProvider


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


def test_tools_list_command() -> None:
    runner = CliRunner()

    result = runner.invoke(app, ["tools", "list"])

    assert result.exit_code == 0
    assert "get_storage_status" in result.output


def test_run_command_with_simulator() -> None:
    runner = CliRunner()

    result = runner.invoke(app, ["run", "check storage", "--profile", "simulator"])

    assert result.exit_code == 0
    assert "Executed tools: get_storage_status" in result.output


def test_chat_command_runs_until_exit() -> None:
    runner = CliRunner()

    result = runner.invoke(app, ["chat", "--profile", "simulator"], input="check storage\nexit\n")

    assert result.exit_code == 0
    assert "NASAgent chat" in result.output
    assert "Executed tools: get_storage_status" in result.output
    assert "Goodbye" in result.output


def test_run_command_with_device_task_does_not_report_storage_plan() -> None:
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


def test_execute_simulator_task_offline_stays_deterministic(tmp_path) -> None:  # type: ignore[no-untyped-def]
    settings = NasAgentSettings(observability={"run_log_dir": str(tmp_path)})

    state = run_command.execute_simulator_task(
        "show device status", settings=settings, online=False
    )

    assert state.step_results[0].tool_results[0].tool_name == "get_device_status"


def test_config_show_redacts_api_key(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("NASAGENT_LLM__API_KEY", "secret-api-key")
    runner = CliRunner()

    result = runner.invoke(app, ["config", "show"])

    assert result.exit_code == 0
    assert "secret-api-key" not in result.output
    assert '"api_key": "********"' in result.output
