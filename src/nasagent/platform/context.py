from dataclasses import dataclass

from nasagent.config.settings import NasAgentSettings
from nasagent.platform.apps import AppEndpoint, AppRegistry
from nasagent.platform.commands import CommandRegistry
from nasagent.tools.registry import ToolRegistry


@dataclass
class PlatformContext:
    settings: NasAgentSettings
    tools: ToolRegistry
    commands: CommandRegistry
    apps: AppRegistry


def create_platform_context(*, settings: NasAgentSettings) -> PlatformContext:
    apps = AppRegistry()
    for name, endpoint in settings.apps.items():
        apps.register(
            AppEndpoint(
                name=name,
                app_type=endpoint.app_type,
                base_url=endpoint.base_url,
                credential_key=endpoint.credential_key,
                frontend_url=endpoint.frontend_url,
                notes=endpoint.notes,
            )
        )
    return PlatformContext(
        settings=settings,
        tools=ToolRegistry(),
        commands=CommandRegistry(),
        apps=apps,
    )
