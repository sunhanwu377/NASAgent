import typer

from nasagent.config.settings import NasAgentSettings

app = typer.Typer(no_args_is_help=True)


@app.command("show")
def show() -> None:
    settings = NasAgentSettings()
    data = settings.model_dump()
    if settings.llm.api_key:
        data["llm"]["api_key"] = "********"
    typer.echo(NasAgentSettings.model_validate(data).model_dump_json(indent=2))


@app.command("init")
def init() -> None:
    typer.echo("Default config can be created under ~/.config/nasagent/.")
