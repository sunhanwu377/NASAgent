import typer
from rich.console import Console

from nasagent.cli.rendering.tables import tools_table
from nasagent.config.settings import load_settings
from nasagent.platform.context import create_platform_context
from nasagent.platform.plugins import load_platform_plugins

app = typer.Typer(no_args_is_help=True)


@app.command("list")
def list_tools() -> None:
    context = create_platform_context(settings=load_settings())
    load_platform_plugins(context)
    console = Console()
    console.print(tools_table(context.tools))
