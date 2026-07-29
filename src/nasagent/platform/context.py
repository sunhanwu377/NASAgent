from dataclasses import dataclass

from nasagent.config.settings import NasAgentSettings
from nasagent.platform.apps import AppRegistry
from nasagent.platform.commands import CommandRegistry
from nasagent.tools.registry import ToolRegistry


@dataclass
class PlatformContext:
    settings: NasAgentSettings
    tools: ToolRegistry
    commands: CommandRegistry
    apps: AppRegistry


def create_platform_context(*, settings: NasAgentSettings) -> PlatformContext:
    return PlatformContext(
        settings=settings,
        tools=ToolRegistry(),
        commands=CommandRegistry(),
        apps=AppRegistry(),
    )
