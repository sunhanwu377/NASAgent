from nasagent.config.settings import SafetySettings
from nasagent.safety.policy import SafetyPolicy
from nasagent.safety.risk import RiskLevel
from nasagent.tools.base import ToolDefinition


async def noop() -> None:
    return None


def test_read_tool_is_allowed_without_confirmation() -> None:
    tool = ToolDefinition(
        name="status",
        description="status",
        risk_level=RiskLevel.READ,
        handler=noop,
    )
    decision = SafetyPolicy(SafetySettings()).evaluate(tool)

    assert decision.allowed is True
    assert decision.requires_confirmation is False


def test_destructive_tool_is_blocked_by_default() -> None:
    tool = ToolDefinition(
        name="delete_file",
        description="delete",
        risk_level=RiskLevel.DESTRUCTIVE,
        handler=noop,
    )
    decision = SafetyPolicy(SafetySettings()).evaluate(tool)

    assert decision.allowed is False
    assert decision.requires_confirmation is True
