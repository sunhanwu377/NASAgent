import re
import tomllib
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from rich.console import Console
from rich.markdown import Markdown
from rich.status import Status
from rich.text import Text

from nasagent.agent.state.models import AgentState
from nasagent.cli.rendering.panels import (
    banner_panel,
    config_error_panel,
    task_result_panel,
)


class CliRenderer:
    def __init__(self, console: Console | None = None) -> None:
        self.console = console or Console()

    def banner(self, *, profile: str, provider: str | None, streaming: bool) -> None:
        self.console.print(banner_panel(profile, provider, streaming))
        self.console.print("Type exit or quit to leave.", style="dim")

    def prompt(self) -> None:
        self.console.print(_label("you", ">", "bold cyan"), end="")

    def agent_start(self) -> None:
        self.console.print(_label("agent", ">", "bold green"), end="")

    def agent_chunk(self, chunk: str) -> None:
        self.console.print(chunk, end="")

    def agent_end(self) -> None:
        self.console.print()

    def agent_message(self, message: str) -> None:
        self.agent_start()
        if looks_like_markdown(message):
            self.console.print()
            self.console.print(Markdown(message))
            return
        self.agent_chunk(message)
        self.agent_end()

    def status(self, message: str) -> None:
        self.console.print(_line("system", ".", message, "cyan"))

    def success(self, message: str) -> None:
        self.console.print(_line("system", ".", message, "green"))

    def error(self, message: str) -> None:
        self.console.print(_line("error", "!", message, "red"))

    def tool(self, name: str, *, completed: bool = False) -> None:
        suffix = " completed" if completed else ""
        self.console.print(_line("tool", ".", f"{name}{suffix}", "magenta"))

    def task_result(self, state: AgentState) -> None:
        self.console.print(task_result_panel(state))

    def config_error(self, path: Path, error: tomllib.TOMLDecodeError) -> None:
        self.console.print(config_error_panel(path, error))

    @contextmanager
    def spinner(self, label: str, message: str) -> Iterator[None]:
        self.console.print(_line(label, ".", message, "cyan"))
        status = Status(_line(label, ".", message, "cyan"), console=self.console, spinner="dots")
        status.start()
        try:
            yield
        finally:
            status.stop()


def _label(name: str, separator: str, style: str) -> Text:
    return Text(f"{name:<8} ", style=style) + Text(f"{separator} ", style="dim")


def _line(name: str, separator: str, message: str, style: str) -> Text:
    return _label(name, separator, style) + Text(message, style="dim")


def looks_like_markdown(message: str) -> bool:
    stripped = message.strip()
    if not stripped:
        return False
    markdown_prefixes = ("# ", "## ", "### ", "- ", "* ", "> ", "```", "| ")
    if stripped.startswith(markdown_prefixes):
        return True
    if re.match(r"^\d+\.\s", stripped):
        return True
    return any(token in stripped for token in ("**", "__", "`", "\n- ", "\n1. "))
