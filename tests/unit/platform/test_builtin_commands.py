from nasagent.config.settings import KNOWN_APP_TYPES, NasAgentSettings
from nasagent.platform.apps import AppEndpoint
from nasagent.platform.context import create_platform_context
from nasagent.plugins.commands import register_builtin_commands


def test_apps_overview_shows_supported_types() -> None:
    context = create_platform_context(settings=NasAgentSettings())
    register_builtin_commands(context)

    result = context.commands.dispatch("/apps")

    assert "Supported apps:" in result.message
    for app_type in KNOWN_APP_TYPES:
        assert app_type in result.message
        assert "not configured" in result.message


def test_apps_overview_shows_configured_endpoint() -> None:
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

    assert "Supported apps:" in result.message
    assert "alist" in result.message
    assert "configured ✓" in result.message
    assert "home" in result.message
    assert "http://nas.local:5244" in result.message
    assert "alist.home.token" in result.message


def test_apps_detail_configured() -> None:
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

    result = context.commands.dispatch("/apps alist")

    assert "alist" in result.message
    assert "Configured endpoints:" in result.message
    assert "home" in result.message
    assert "http://nas.local:5244" in result.message


def test_apps_detail_unconfigured() -> None:
    context = create_platform_context(settings=NasAgentSettings())
    register_builtin_commands(context)

    result = context.commands.dispatch("/apps vaultwarden")

    assert "vaultwarden" in result.message
    assert "No endpoints configured" in result.message
    assert "/apps configure" in result.message


def test_apps_detail_unknown_type() -> None:
    context = create_platform_context(settings=NasAgentSettings())
    register_builtin_commands(context)

    result = context.commands.dispatch("/apps unknown")

    assert result.exit_code == 1
    assert "Unknown app type" in result.message


def test_apps_configure_persists() -> None:
    context = create_platform_context(settings=NasAgentSettings())
    register_builtin_commands(context)

    result = context.commands.dispatch("/apps configure alist mynas http://nas.local:5244 mytoken")

    assert result.exit_code == 0
    assert "App configured" in result.message


def test_apps_configure_rejects_duplicate(tmp_path) -> None:
    context = create_platform_context(settings=NasAgentSettings())
    context.apps.register(
        AppEndpoint(name="home", app_type="alist", base_url="http://nas.local:5244")
    )
    register_builtin_commands(context)

    result = context.commands.dispatch("/apps configure alist home http://nas.local:5244")

    assert result.exit_code == 1
    assert "already configured" in result.message


def test_apps_configure_insufficient_args() -> None:
    context = create_platform_context(settings=NasAgentSettings())
    register_builtin_commands(context)

    result = context.commands.dispatch("/apps configure alist")

    assert result.exit_code == 1
    assert "Usage:" in result.message


def test_help_command_lists_registered_commands() -> None:
    context = create_platform_context(settings=NasAgentSettings())
    register_builtin_commands(context)

    result = context.commands.dispatch("/help")
    assert "/apps" in result.message
    assert "/plugins" in result.message
