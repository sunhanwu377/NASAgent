from collections.abc import Sequence
from typing import Any

from nasagent.safety.policy import RiskLevel
from nasagent.tools.base import ToolDefinition


async def _not_configured(*args: Any, **kwargs: Any) -> dict[str, str]:
    return {"status": "AList endpoint and token are required"}


def alist_tool_definitions() -> Sequence[ToolDefinition]:
    return (
        ToolDefinition(
            "alist.auth.login",
            "Log in to AList",
            RiskLevel.WRITE,
            _not_configured,
        ),
        ToolDefinition(
            "alist.fs.list",
            "List AList files",
            RiskLevel.READ,
            _not_configured,
        ),
        ToolDefinition(
            "alist.fs.get",
            "Get AList file metadata",
            RiskLevel.READ,
            _not_configured,
        ),
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
