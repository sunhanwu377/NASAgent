from pydantic import BaseModel

from nasagent.config.settings import SafetySettings
from nasagent.safety.risk import RiskLevel
from nasagent.tools.base import ToolDefinition


class SafetyDecision(BaseModel):
    allowed: bool
    requires_confirmation: bool
    reason: str
    approval_allowed: bool = False


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
            requires_confirmation = (
                not self._settings.allow_auto_write
                or tool.requires_confirmation
                or tool.name in self._settings.require_confirmation_for
            )
            return SafetyDecision(
                allowed=not requires_confirmation,
                requires_confirmation=requires_confirmation,
                reason="write operation requires policy evaluation",
                approval_allowed=True,
            )
        if tool.risk_level == RiskLevel.DESTRUCTIVE:
            return SafetyDecision(
                allowed=False,
                requires_confirmation=True,
                reason="destructive operation disabled by safety settings",
                approval_allowed=self._settings.allow_destructive,
            )
        return SafetyDecision(allowed=False, requires_confirmation=True, reason="system operation")
