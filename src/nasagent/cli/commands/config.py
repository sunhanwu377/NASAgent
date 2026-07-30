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


def _prompt_str(label: str, current: str) -> str:
    """Prompt for a string value. Empty input keeps the original."""
    value = typer.prompt(f"  {label} [{current}]", default="", show_default=False)
    return value.strip() if value.strip() else current


def _prompt_llm(current: LlmSettings) -> LlmSettings:
    typer.echo()
    typer.echo("── LLM Configuration ──")
    typer.echo(f"  provider : {current.provider}")
    typer.echo(f"  model    : {current.model}")
    if current.base_url:
        typer.echo(f"  base_url : {current.base_url}")
    else:
        typer.echo("  base_url : (not set)")
    api_key = None
    try:
        api_key = CredentialStore().get("llm.api_key")
    except Exception:
        pass
    if api_key:
        masked = api_key if len(api_key) <= 10 else f"{api_key[:4]}***{api_key[-4:]}"
        typer.echo(f"  api_key  : {masked}")
    else:
        typer.echo("  api_key  : (not set)")
    typer.echo("  (press Enter to keep current value)")

    if not typer.confirm("Modify LLM settings?", default=False):
        return current

    provider = _prompt_str("provider", current.provider)
    model = _prompt_str("model", current.model)
    base_url_raw = _prompt_str("base_url", current.base_url or "")
    base_url = base_url_raw if base_url_raw else None
    new_api_key = typer.prompt(
        "  api_key (leave blank to keep existing)", default="", hide_input=True, show_default=False,
    )

    if new_api_key:
        CredentialStore().set("llm.api_key", new_api_key)

    return LlmSettings(
        provider=provider,
        model=model,
        base_url=base_url,
    )


def _prompt_safety(current: SafetySettings) -> SafetySettings:
    typer.echo()
    typer.echo("── Safety Configuration ──")
    typer.echo(f"  default_mode              : {current.default_mode}")
    typer.echo(f"  allow_auto_write          : {current.allow_auto_write}")
    typer.echo(f"  allow_destructive         : {current.allow_destructive}")
    if current.require_confirmation_for:
        cfm_display = ", ".join(current.require_confirmation_for)
    else:
        cfm_display = "(none)"
    typer.echo(f"  require_confirmation_for  : {cfm_display}")
    typer.echo("  (press Enter to keep current value)")

    if not typer.confirm("Modify Safety settings?", default=False):
        return current

    default_mode = _prompt_str("default_mode", current.default_mode)
    allow_auto_write = typer.confirm("  allow_auto_write", default=current.allow_auto_write)
    allow_destructive = typer.confirm("  allow_destructive", default=current.allow_destructive)
    cfm_raw = typer.prompt(
        "  require_confirmation_for [comma-separated, blank for none]",
        default="", show_default=False,
    )
    if cfm_raw.strip():
        require_confirmation_for = tuple(
            t.strip() for t in cfm_raw.split(",") if t.strip()
        )
    else:
        require_confirmation_for = current.require_confirmation_for

    return SafetySettings(
        default_mode=default_mode,
        allow_auto_write=allow_auto_write,
        allow_destructive=allow_destructive,
        require_confirmation_for=require_confirmation_for,
    )


def _prompt_observability(current: ObservabilitySettings) -> ObservabilitySettings:
    typer.echo()
    typer.echo("── Observability Configuration ──")
    typer.echo(f"  run_log_dir      : {current.run_log_dir}")
    typer.echo(f"  memory_dir       : {current.memory_dir}")
    typer.echo(f"  redact_sensitive : {current.redact_sensitive}")
    typer.echo("  (press Enter to keep current value)")

    if not typer.confirm("Modify Observability settings?", default=False):
        return current

    run_log_dir = _prompt_str("run_log_dir", current.run_log_dir)
    memory_dir = _prompt_str("memory_dir", current.memory_dir)
    redact_sensitive = typer.confirm("  redact_sensitive", default=current.redact_sensitive)

    return ObservabilitySettings(
        run_log_dir=run_log_dir,
        memory_dir=memory_dir,
        redact_sensitive=redact_sensitive,
    )


@app.command("init")
def init() -> None:
    config_path = default_config_path()

    if config_path.exists():
        typer.echo(f"Config exists: {config_path}")
        try:
            settings = load_settings()
        except tomllib.TOMLDecodeError as exc:
            typer.echo(f"Invalid TOML: {exc}")
            if typer.confirm("Re-initialize config from scratch?", default=False):
                config_path.unlink()
                # recurse to fresh init
                return init()
            raise typer.Exit(1) from exc

        new_llm = _prompt_llm(settings.llm)
        new_safety = _prompt_safety(settings.safety)
        new_observability = _prompt_observability(settings.observability)

        updated = NasAgentSettings(
            llm=new_llm,
            safety=new_safety,
            observability=new_observability,
            apps=settings.apps,
            plugins=settings.plugins,
        )

        config_path.write_text(render_toml(settings_to_toml_data(updated)), encoding="utf-8")
        typer.echo(f"\nConfig saved: {config_path}")
        return

    # Fresh init
    default_llm = LlmSettings()
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
    )
    if api_key:
        CredentialStore().set("llm.api_key", api_key)

    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(render_toml(settings_to_toml_data(settings)), encoding="utf-8")
    typer.echo(f"Created config: {config_path}")
