import typer

from nasagent.config.settings import load_settings
from nasagent.platform.context import PlatformContext, create_platform_context
from nasagent.platform.plugins import PluginManager

app = typer.Typer(help="Manage plugins")


def _context() -> PlatformContext:
    context = create_platform_context(settings=load_settings())
    PluginManager(context).load_builtin()
    return context


@app.command("list")
def list_plugins() -> None:
    result = _context().commands.dispatch("/plugins")
    typer.echo(result.message)
