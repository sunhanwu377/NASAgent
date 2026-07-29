from pydantic import BaseModel

from nasagent.config.settings import SafetySettings
from nasagent.safety.risk import RiskLevel
from nasagent.tools.base import ToolDefinition


class SafetyDecision(BaseModel):
    allowed: bool
    requires_confirmation: bool
    reason: str


class SafetyPolicy:
    def __init__(self, settings: SafetySettings) -> None:
        self._settings = settings

    def evaluate(self, tool: ToolDefinition) -> SafetyDecision:
        if tool.risk_level == RiskLevel.READ:
            return SafetyDecision(
                allowed=True,
                requires_confirmation=False,
                reason="read operation",
            )
        if tool.risk_level == RiskLevel.WRITE:
            requires_confirmation = tool.name in self._settings.require_confirmation_for
            return SafetyDecision(
                allowed=self._settings.allow_auto_write or requires_confirmation,
                requires_confirmation=requires_confirmation,
                reason="write operation requires policy evaluation",
            )
        if tool.risk_level == RiskLevel.DESTRUCTIVE:
            return SafetyDecision(
                allowed=self._settings.allow_destructive,
                requires_confirmation=True,
                reason="destructive operation",
            )
        return SafetyDecision(allowed=False, requires_confirmation=True, reason="system operation")
