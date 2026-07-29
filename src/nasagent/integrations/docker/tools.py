from collections.abc import Sequence
from typing import Any

from nasagent.safety.policy import RiskLevel
from nasagent.tools.base import ToolDefinition


async def _not_configured(*args: Any, **kwargs: Any) -> dict[str, str]:
    return {"status": "Docker integration requires a Docker daemon"}


def docker_tool_definitions() -> Sequence[ToolDefinition]:
    return (
        ToolDefinition(
            "docker.containers.list",
            "List Docker containers",
            RiskLevel.READ,
            _not_configured,
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
            "docker.networks.list",
            "List Docker networks",
            RiskLevel.READ,
            _not_configured,
        ),
        ToolDefinition(
            "docker.volumes.list",
            "List Docker volumes",
            RiskLevel.READ,
            _not_configured,
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
