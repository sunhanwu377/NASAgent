import typer
from rich.console import Console

from nasagent.agent.graph.nodes import default_tool_registry
from nasagent.cli.rendering.tables import tools_table

app = typer.Typer(no_args_is_help=True)


@app.command("list")
def list_tools() -> None:
    console = Console()
    console.print(tools_table(default_tool_registry()))
