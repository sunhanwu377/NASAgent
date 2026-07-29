from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True)
class CommandResult:
    message: str
    exit_code: int = 0


CommandHandler = Callable[[tuple[str, ...]], CommandResult]


@dataclass(frozen=True)
class CommandDefinition:
    name: str
    description: str
    usage: str
    handler: CommandHandler
    aliases: tuple[str, ...] = ()
    plugin: str | None = None


class CommandRegistry:
    def __init__(self) -> None:
        self._commands: dict[str, CommandDefinition] = {}
        self._aliases: dict[str, str] = {}

    def register(self, command: CommandDefinition) -> None:
        if command.name in self._commands or command.name in self._aliases:
            raise ValueError(f"Command already registered: {command.name}")
        for alias in command.aliases:
            if alias in self._aliases or alias in self._commands:
                raise ValueError(f"Command alias already registered: {alias}")

        self._commands[command.name] = command
        for alias in command.aliases:
            self._aliases[alias] = command.name

    def get(self, name: str) -> CommandDefinition | None:
        normalized = name.removeprefix("/")
        command_name = self._aliases.get(normalized, normalized)
        return self._commands.get(command_name)

    def list(self) -> list[CommandDefinition]:
        return list(self._commands.values())

    def dispatch(self, raw: str) -> CommandResult:
        parts = raw.strip().split()
        if not parts:
            return CommandResult(message="No command provided", exit_code=1)
        command = self.get(parts[0])
        if command is None:
            return CommandResult(message=f"Unknown command: {parts[0]}", exit_code=1)
        return command.handler(tuple(parts[1:]))
