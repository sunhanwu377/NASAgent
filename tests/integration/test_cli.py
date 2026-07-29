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
