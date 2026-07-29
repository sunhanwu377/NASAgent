from nasagent.platform.commands import CommandDefinition, CommandResult
from nasagent.platform.context import PlatformContext


def register_builtin_commands(context: PlatformContext) -> None:
    context.commands.register(
        CommandDefinition("help", "Show help", "/help", lambda args: _help(context, args))
    )
    context.commands.register(
        CommandDefinition(
            "apps", "List configured apps", "/apps", lambda args: _apps(context, args)
        )
    )
    context.commands.register(
        CommandDefinition(
            "plugins", "List plugins", "/plugins", lambda args: _plugins(context, args)
        )
    )
    context.commands.register(
        CommandDefinition("tools", "List tools", "/tools", lambda args: _tools(context, args))
    )
    context.commands.register(
        CommandDefinition(
            "containers",
            "List containers",
            "/containers",
            lambda args: _containers(context, args),
        )
    )


def _help(context: PlatformContext, args: tuple[str, ...]) -> CommandResult:
    commands = ", ".join(command.usage for command in context.commands.list())
    return CommandResult(f"Commands: {commands}")


def _apps(context: PlatformContext, args: tuple[str, ...]) -> CommandResult:
    apps = context.apps.list()
    if not apps:
        return CommandResult("Configured apps: none")
    lines = ["Configured apps:"]
    for endpoint in apps:
        credential = endpoint.credential_key or "none"
        lines.append(
            f"- {endpoint.name} ({endpoint.app_type}) {endpoint.base_url} credential={credential}"
        )
    return CommandResult("\n".join(lines))


def _plugins(context: PlatformContext, args: tuple[str, ...]) -> CommandResult:
    lines = ["Plugins:"]
    if context.plugin_manifests:
        for manifest in context.plugin_manifests.values():
            name = str(getattr(manifest, "name", "unknown"))
            version = str(getattr(manifest, "version", "unknown"))
            lines.append(f"- {name} {version} loaded")
    else:
        lines.append("- none loaded")
    if context.plugin_errors:
        lines.append("Plugin load errors:")
        for error in context.plugin_errors:
            plugin = str(getattr(error, "plugin", "unknown"))
            message = str(getattr(error, "message", "unknown error"))
            lines.append(f"- {plugin}: {message}")
    return CommandResult("\n".join(lines))


def _tools(context: PlatformContext, args: tuple[str, ...]) -> CommandResult:
    tools = context.tools.list()
    if not tools:
        return CommandResult("Agent-callable tools: none")
    lines = ["Agent-callable tools:"]
    for tool in tools:
        lines.append(f"- {tool.name} ({tool.risk_level.value}) {tool.description}")
    return CommandResult("\n".join(lines))


def _containers(context: PlatformContext, args: tuple[str, ...]) -> CommandResult:
    return CommandResult("Docker containers require Docker integration configuration")
