import typer

app = typer.Typer(no_args_is_help=True)


@app.command("list")
def list_profiles() -> None:
    typer.echo("simulator")


@app.command("add")
def add_profile(name: str) -> None:
    typer.echo(f"Profile creation requested: {name}")
