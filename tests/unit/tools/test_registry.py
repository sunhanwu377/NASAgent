import pytest

from nasagent.safety.risk import RiskLevel
from nasagent.tools.base import ToolDefinition
from nasagent.tools.registry import ToolRegistry


async def noop() -> None:
    return None


def test_tool_registry_registers_and_resolves_tool() -> None:
    registry = ToolRegistry()
    tool = ToolDefinition(
        name="status",
        description="status",
        risk_level=RiskLevel.READ,
        handler=noop,
    )

    registry.register(tool)

    assert registry.get("status") == tool


def test_tool_registry_rejects_duplicate_name() -> None:
    registry = ToolRegistry()
    tool = ToolDefinition(
        name="status",
        description="status",
        risk_level=RiskLevel.READ,
        handler=noop,
    )
    registry.register(tool)


    with pytest.raises(ValueError, match="Tool already registered: status"):
        registry.register(tool)
