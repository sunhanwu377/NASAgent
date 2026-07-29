import tomllib
from pathlib import Path

from rich.console import Group
from rich.panel import Panel
from rich.text import Text

from nasagent.agent.state.models import AgentState


def banner_panel(profile: str, provider: str | None, streaming: bool) -> Panel:
    provider_label = provider or "offline"
    streaming_label = "streaming on" if streaming else "streaming off"
    return Panel(
        Text("NASAgent", style="bold cyan")
        + Text(f"  {provider_label} · {profile} · {streaming_label}", style="dim"),
        border_style="cyan",
        padding=(0, 1),
    )


def task_result_panel(state: AgentState) -> Panel:
    tool_names = [
        tool_result.tool_name
        for step_result in state.step_results
        for tool_result in step_result.tool_results
    ]
    tools = ", ".join(tool_names) if tool_names else "none"
    return Panel(
        Group(
            Text("Goal   ", style="bold cyan") + Text(state.goal),
            Text("Tools  ", style="bold magenta") + Text(tools),
            Text(""),
            Text(state.final_summary),
        ),
        title="Task Complete",
        border_style="green",
        padding=(0, 1),
    )


def config_error_panel(path: Path, error: tomllib.TOMLDecodeError) -> Panel:
    return Panel(
        Group(
            Text("Invalid TOML config", style="bold red"),
            Text(f"File: {path}"),
            Text(f"Error: {error}"),
            Text("Hint: run `nasagent config show`"),
        ),
        title="Config Error",
        border_style="red",
        padding=(0, 1),
    )
