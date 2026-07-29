import pytest

from nasagent.config.settings import SafetySettings
from nasagent.integrations.docker.tools import docker_tool_definitions
from nasagent.safety.policy import RiskLevel, SafetyPolicy


def test_docker_tool_definitions_include_compose_system_tools() -> None:
    tools = {tool.name: tool for tool in docker_tool_definitions()}

    assert tools["docker.containers.list"].risk_level == RiskLevel.READ
    assert tools["docker.compose.up"].risk_level == RiskLevel.SYSTEM
    assert tools["docker.compose.up"].requires_confirmation is True


def test_compose_args_are_explicit() -> None:
    from nasagent.integrations.docker.client import compose_command_args

    args = compose_command_args("up", compose_file="compose.yml")

    assert args == ["docker", "compose", "-f", "compose.yml", "up", "-d"]


@pytest.mark.parametrize("compose_file", ["/tmp/compose.yml", "../compose.yml"])
def test_compose_args_reject_disallowed_paths(compose_file: str) -> None:
    from nasagent.integrations.docker.client import compose_command_args

    with pytest.raises(ValueError, match="compose file path"):
        compose_command_args("up", compose_file=compose_file)


def test_docker_compose_tools_require_safety_confirmation() -> None:
    tools = {tool.name: tool for tool in docker_tool_definitions()}
    decision = SafetyPolicy(SafetySettings()).evaluate(tools["docker.compose.down"])

    assert decision.allowed is False
    assert decision.requires_confirmation is True
    assert decision.reason == "system operation"
