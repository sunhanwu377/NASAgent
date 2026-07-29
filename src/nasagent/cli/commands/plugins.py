import typer

from nasagent.config.settings import load_settings
from nasagent.platform.context import PlatformContext, create_platform_context
from nasagent.platform.plugins import load_platform_plugins

app = typer.Typer(help="Manage plugins")


def _context() -> PlatformContext:
    context = create_platform_context(settings=load_settings())
    load_platform_plugins(context)
    return context


@app.command("list")
def list_plugins() -> None:
    result = _context().commands.dispatch("/plugins")
    typer.echo(result.message)
