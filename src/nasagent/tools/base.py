from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from nasagent.nas.base import NasAdapter
from nasagent.safety.risk import RiskLevel


@dataclass(frozen=True)
class ToolContext:
    adapter: NasAdapter


ToolHandler = Callable[..., Awaitable[Any]]


@dataclass(frozen=True)
class ToolDefinition:
    name: str
    description: str
    risk_level: RiskLevel
    handler: ToolHandler
    requires_confirmation: bool = False
    supports_dry_run: bool = False
    adapter_capability: str | None = None
