from typer.testing import CliRunner

from nasagent.cli.app import app


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


def test_run_command_with_device_task_does_not_report_storage_plan() -> None:
    runner = CliRunner()

    result = runner.invoke(app, ["run", "show device status", "--profile", "simulator"])

    assert result.exit_code == 0
    assert "show device status" in result.output
    assert "Executed tools: get_storage_status" not in result.output


def test_config_show_redacts_api_key(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("NASAGENT_LLM__API_KEY", "secret-api-key")
    runner = CliRunner()

    result = runner.invoke(app, ["config", "show"])

    assert result.exit_code == 0
    assert "secret-api-key" not in result.output
    assert '"api_key": "********"' in result.output
