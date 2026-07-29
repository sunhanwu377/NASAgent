import tomllib

import typer

from nasagent.config.settings import (
    LlmSettings,
    NasAgentSettings,
    ObservabilitySettings,
    SafetySettings,
    default_config_path,
    load_settings,
    render_toml,
    settings_to_toml_data,
)

app = typer.Typer(no_args_is_help=True)


@app.command("show")
def show() -> None:
    try:
        settings = load_settings()
    except tomllib.TOMLDecodeError as exc:
        typer.echo(f"Invalid TOML config at {default_config_path()}: {exc}")
        raise typer.Exit(1) from exc
    typer.echo(render_toml(settings_to_toml_data(settings, redact=True)))


@app.command("init")
def init() -> None:
    config_path = default_config_path()
    if config_path.exists():
        typer.echo(f"Config already exists: {config_path}")
        typer.echo("Run `nasagent config show` to view the effective configuration.")
        return

    default_llm = LlmSettings()
    default_safety = SafetySettings()
    default_observability = ObservabilitySettings()
    provider = typer.prompt("LLM provider", default=default_llm.provider)
    model = typer.prompt("LLM model", default=default_llm.model)
    base_url = typer.prompt("LLM base URL (optional)", default="")
    api_key = typer.prompt("LLM API key (optional)", default="", hide_input=True)

    settings = NasAgentSettings(
        llm=LlmSettings(
            provider=provider,
            model=model,
            base_url=base_url or None,
            api_key=api_key or None,
        ),
        safety=default_safety,
        observability=default_observability,
    )

    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(render_toml(settings_to_toml_data(settings)), encoding="utf-8")
    typer.echo(f"Created config: {config_path}")
