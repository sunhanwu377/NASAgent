import pytest

from nasagent.platform.commands import CommandDefinition, CommandRegistry, CommandResult


def _handler(args: tuple[str, ...]) -> CommandResult:
    return CommandResult(message="handled " + " ".join(args))


def test_command_registry_resolves_name_and_alias() -> None:
    registry = CommandRegistry()
    command = CommandDefinition(
        name="apps",
        description="List apps",
        usage="/apps",
        handler=_handler,
        aliases=("app",),
        plugin="builtin",
    )

    registry.register(command)

    assert registry.get("apps") == command
    assert registry.get("app") == command
    assert registry.dispatch("/apps list").message == "handled list"


def test_command_registry_rejects_duplicate_name() -> None:
    registry = CommandRegistry()
    command = CommandDefinition("apps", "List apps", "/apps", _handler)
    registry.register(command)

    with pytest.raises(ValueError, match="Command already registered: apps"):
        registry.register(command)


def test_command_registry_rejects_alias_conflict_without_partial_registration() -> None:
    registry = CommandRegistry()
    apps = CommandDefinition("apps", "List apps", "/apps", _handler, aliases=("app",))
    files = CommandDefinition("files", "List files", "/files", _handler, aliases=("app",))
    registry.register(apps)

    with pytest.raises(ValueError, match="Command alias already registered: app"):
        registry.register(files)

    assert registry.get("files") is None
    assert registry.list() == [apps]


def test_command_registry_rejects_name_collision_with_existing_alias() -> None:
    registry = CommandRegistry()
    apps = CommandDefinition("apps", "List apps", "/apps", _handler, aliases=("app",))
    app = CommandDefinition("app", "Open app", "/app", _handler)
    registry.register(apps)

    with pytest.raises(ValueError, match="Command already registered: app"):
        registry.register(app)

    assert registry.get("app") == apps
    assert registry.list() == [apps]
