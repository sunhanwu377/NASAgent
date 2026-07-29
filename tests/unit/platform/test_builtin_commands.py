from nasagent.config.settings import NasAgentSettings
from nasagent.platform.apps import AppEndpoint
from nasagent.platform.context import create_platform_context
from nasagent.plugins.commands import register_builtin_commands


def test_apps_command_lists_redacted_endpoint() -> None:
    context = create_platform_context(settings=NasAgentSettings())
    context.apps.register(
        AppEndpoint(
            name="home",
            app_type="alist",
            base_url="http://nas.local:5244",
            credential_key="alist.home.token",
        )
    )
    register_builtin_commands(context)

    result = context.commands.dispatch("/apps")

    assert "home" in result.message
    assert "alist" in result.message
    assert "alist.home.token" in result.message


def test_help_command_lists_registered_commands() -> None:
    context = create_platform_context(settings=NasAgentSettings())
    register_builtin_commands(context)

    result = context.commands.dispatch("/help")
    assert "/apps" in result.message
    assert "/plugins" in result.message
