import asyncio
import tomllib

import typer

from nasagent.config.secrets import CredentialStore
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
from nasagent.discovery.scanner import DiscoveryScanner

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
    scan_lan = typer.confirm("Scan local network for NAS services?", default=False)
    if scan_lan:
        typer.echo(
            "LAN discovery is enabled. "
            "Protocol scanners and vendor probes will run with safe limits."
        )
        services = asyncio.run(DiscoveryScanner().scan_hosts([]))
        if services:
            typer.echo("Discovered NAS services:")
            for service in services:
                url = (
                    service.login_url
                    or service.admin_url
                    or f"{service.scheme}://{service.host}:{service.port}/"
                )
                typer.echo(f"- {service.service_type}: {url}")
        else:
            typer.echo(
                "No NAS services discovered. You can add app endpoints manually in config.toml."
            )

    settings = NasAgentSettings(
        llm=LlmSettings(
            provider=provider,
            model=model,
            base_url=base_url or None,
        ),
        safety=default_safety,
        observability=default_observability,
    )
    if api_key:
        CredentialStore().set("llm.api_key", api_key)

    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(render_toml(settings_to_toml_data(settings)), encoding="utf-8")
    typer.echo(f"Created config: {config_path}")
