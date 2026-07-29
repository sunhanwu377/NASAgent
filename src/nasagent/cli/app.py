import typer

from nasagent.cli.commands import config, profiles, tools
from nasagent.cli.commands.chat import chat
from nasagent.cli.commands.run import run_task

app = typer.Typer(no_args_is_help=True)
app.command("chat")(chat)
app.command("run")(run_task)
app.add_typer(config.app, name="config")
app.add_typer(profiles.app, name="profiles")
app.add_typer(tools.app, name="tools")


if __name__ == "__main__":
    app()
