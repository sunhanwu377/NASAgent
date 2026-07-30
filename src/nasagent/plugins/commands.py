from nasagent.config.settings import KNOWN_APP_TYPES, persist_app_config
from nasagent.platform.commands import CommandDefinition, CommandResult
from nasagent.platform.context import PlatformContext


def register_builtin_commands(context: PlatformContext) -> None:
    context.commands.register(
        CommandDefinition("help", "Show help", "/help", lambda args: _help(context, args))
    )
    context.commands.register(
        CommandDefinition(
            "apps",
            "List supported apps and manage configuration",
            "/apps [type|configure ...]",
            lambda args: _apps(context, args),
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
    if args and args[0] == "configure":
        return _apps_configure(context, args[1:])
    if args:
        return _apps_detail(context, args[0])
    return _apps_overview(context)


def _apps_overview(context: PlatformContext) -> CommandResult:
    configured = {endpoint.app_type: endpoint for endpoint in context.apps.list()}

    lines = ["Supported apps:"]
    for app_type, meta in KNOWN_APP_TYPES.items():
        if app_type in configured:
            endpoint = configured[app_type]
            status = f"  configured ✓"
            detail = f"    name={endpoint.name}  base_url={endpoint.base_url}"
            if endpoint.credential_key:
                detail += f"  credential={endpoint.credential_key}"
        else:
            status = "  not configured ✗"
            detail = f"    hint: /apps configure {app_type} <name> <base_url> [credential_key]"
        lines.append(f"  {app_type}: {meta['description']}")
        lines.append(status)
        lines.append(detail)
        lines.append("")

    return CommandResult("\n".join(lines).rstrip())


def _apps_detail(context: PlatformContext, app_type: str) -> CommandResult:
    meta = KNOWN_APP_TYPES.get(app_type)
    if meta is None:
        known = ", ".join(KNOWN_APP_TYPES.keys())
        return CommandResult(
            f"Unknown app type: {app_type}\nSupported types: {known}", exit_code=1
        )

    endpoints = context.apps.list(app_type=app_type)
    lines = [f"{app_type}: {meta['description']}", f"Default port: {meta['default_port']}", ""]

    if endpoints:
        lines.append("Configured endpoints:")
        for endpoint in endpoints:
            credential = endpoint.credential_key or "none"
            lines.append(
                f"  - {endpoint.name}  base_url={endpoint.base_url}  credential={credential}"
            )
    else:
        lines.append("No endpoints configured.")
        lines.append("")
        lines.append("To configure, run:")
        lines.append(
            f"  /apps configure {app_type} <name> <base_url> [credential_key]"
        )
        lines.append("")
        lines.append("Example:")
        lines.append(
            f"  /apps configure {app_type} home http://nas.local:{meta['default_port']}"
        )

    return CommandResult("\n".join(lines))


def _apps_configure(context: PlatformContext, args: tuple[str, ...]) -> CommandResult:
    if len(args) < 3:
        return CommandResult(
            "Usage: /apps configure <app_type> <name> <base_url> [credential_key]\n"
            "Example: /apps configure alist home http://nas.local:5244",
            exit_code=1,
        )

    app_type, name, base_url = args[0], args[1], args[2]
    credential_key = args[3] if len(args) > 3 else None

    if app_type not in KNOWN_APP_TYPES:
        known = ", ".join(KNOWN_APP_TYPES.keys())
        return CommandResult(
            f"Unknown app type: {app_type}\nSupported types: {known}", exit_code=1
        )

    if context.apps.get(name):
        return CommandResult(
            f"App endpoint '{name}' is already configured.\n"
            f"Edit ~/.config/nasagent/config.toml to update.",
            exit_code=1,
        )

    try:
        config_path = persist_app_config(
            name=name,
            app_type=app_type,
            base_url=base_url,
            credential_key=credential_key,
        )
    except Exception as exc:
        return CommandResult(f"Failed to persist config: {exc}", exit_code=1)

    return CommandResult(
        f"App configured and saved to {config_path}\n"
        f"  {name}: {app_type} → {base_url}\n"
        f"Restart nasagent to activate the endpoint."
    )


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


from nasagent.memory.manager import MemoryManager


def register_memory_commands(context: PlatformContext, memory_manager: MemoryManager) -> None:
    context.commands.register(
        CommandDefinition(
            "session", "Manage chat sessions",
            "/session new|switch|list|delete <name>",
            lambda args: _session(memory_manager, args),
            aliases=("sessions",),
        )
    )
    context.commands.register(
        CommandDefinition(
            "remember", "Add persistent memory",
            "/remember <content>",
            lambda args: _remember(memory_manager, args),
        )
    )
    context.commands.register(
        CommandDefinition(
            "forget", "Delete persistent memory by ID",
            "/forget <id>",
            lambda args: _forget(memory_manager, args),
        )
    )
    context.commands.register(
        CommandDefinition(
            "memories", "List all persistent memories",
            "/memories",
            lambda args: _memories(memory_manager, args),
        )
    )
    context.commands.register(
        CommandDefinition(
            "pref", "Manage user preferences",
            "/pref set|get|list|delete <key> [value]",
            lambda args: _pref(memory_manager, args),
            aliases=("prefs", "preference"),
        )
    )


def _session(mgr: MemoryManager, args: tuple[str, ...]) -> CommandResult:
    if not args:
        return CommandResult("Usage: /session new|switch|list|delete <name>", exit_code=1)
    action = args[0]
    if action == "new":
        if len(args) < 2:
            return CommandResult("Usage: /session new <name>", exit_code=1)
        meta = mgr.session_store.create(args[1])
        mgr.ensure_session(args[1])
        return CommandResult(f"Session created: {meta.name} ({meta.session_id})")
    elif action == "switch":
        if len(args) < 2:
            return CommandResult("Usage: /session switch <name>", exit_code=1)
        try:
            target = next(s for s in mgr.session_store.list_all() if s.name == args[1])
        except StopIteration:
            return CommandResult(f"Session not found: {args[1]}", exit_code=1)
        meta = mgr.ensure_session(args[1])
        return CommandResult(f"Switched to session: {meta.name} ({meta.session_id})")
    elif action == "list":
        sessions = mgr.session_store.list_all()
        if not sessions:
            return CommandResult("No sessions.")
        current = mgr.session_store.get_current()
        lines = ["Sessions:"]
        for s in sessions:
            marker = " *" if current and s.session_id == current.session_id else ""
            lines.append(f"  {s.name} ({s.session_id}){marker}")
        return CommandResult("\n".join(lines))
    elif action == "delete":
        if len(args) < 2:
            return CommandResult("Usage: /session delete <name>", exit_code=1)
        try:
            target = next(s for s in mgr.session_store.list_all() if s.name == args[1])
        except StopIteration:
            return CommandResult(f"Session not found: {args[1]}", exit_code=1)
        mgr.session_store.delete(target.session_id)
        return CommandResult(f"Session deleted: {target.name}")
    else:
        return CommandResult(f"Unknown action: {action}", exit_code=1)


def _remember(mgr: MemoryManager, args: tuple[str, ...]) -> CommandResult:
    if not args:
        return CommandResult("Usage: /remember <content>", exit_code=1)
    entry = mgr.persistent_memory.remember(" ".join(args))
    return CommandResult(f"Memory saved: {entry.id}")


def _forget(mgr: MemoryManager, args: tuple[str, ...]) -> CommandResult:
    if not args:
        return CommandResult("Usage: /forget <id>", exit_code=1)
    mgr.persistent_memory.forget(args[0])
    return CommandResult(f"Memory removed: {args[0]}")


def _memories(mgr: MemoryManager, args: tuple[str, ...]) -> CommandResult:
    entries = mgr.persistent_memory.list_all()
    if not entries:
        return CommandResult("No persistent memories.")
    lines = ["Persistent memories:"]
    for e in entries:
        lines.append(f"  {e.id}: {e.content}")
    return CommandResult("\n".join(lines))


def _pref(mgr: MemoryManager, args: tuple[str, ...]) -> CommandResult:
    if not args:
        return CommandResult("Usage: /pref set|get|list|delete <key> [value]", exit_code=1)
    action = args[0]
    if action == "set":
        if len(args) < 3:
            return CommandResult("Usage: /pref set <key> <value>", exit_code=1)
        mgr.persistent_memory.set_preference(args[1], args[2])
        return CommandResult(f"Preference set: {args[1]} = {args[2]}")
    elif action == "get":
        if len(args) < 2:
            return CommandResult("Usage: /pref get <key>", exit_code=1)
        value = mgr.persistent_memory.get_preference(args[1])
        return CommandResult(f"{args[1]} = {value}" if value is not None else f"{args[1]} (not set)")
    elif action == "list":
        prefs = mgr.persistent_memory.get_all_preferences()
        if not prefs:
            return CommandResult("No preferences set.")
        lines = ["Preferences:"]
        for k, v in prefs.items():
            lines.append(f"  {k}: {v}")
        return CommandResult("\n".join(lines))
    elif action == "delete":
        if len(args) < 2:
            return CommandResult("Usage: /pref delete <key>", exit_code=1)
        mgr.persistent_memory.delete_preference(args[1])
        return CommandResult(f"Preference deleted: {args[1]}")
    else:
        return CommandResult(f"Unknown action: {action}", exit_code=1)
