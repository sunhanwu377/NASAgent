from collections.abc import Sequence
from typing import Any

from nasagent.safety.policy import RiskLevel
from nasagent.tools.base import ToolDefinition


async def _not_configured(*args: Any, **kwargs: Any) -> dict[str, str]:
    return {"status": "Vaultwarden endpoint and admin token are required"}


def vaultwarden_tool_definitions() -> Sequence[ToolDefinition]:
    return (
        ToolDefinition(
            "vaultwarden.users.list",
            "List Vaultwarden users",
            RiskLevel.READ,
            _not_configured,
        ),
    )
