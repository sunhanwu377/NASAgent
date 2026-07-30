from fastapi import APIRouter, Form
from fastapi.responses import HTMLResponse

from nasagent.config.secrets import CredentialStore
from nasagent.config.settings import (
    default_config_path,
    load_config_file,
    load_settings,
    persist_app_config,
    render_toml,
    settings_to_toml_data,
)

api_router = APIRouter(prefix="/api/config", tags=["config_api"])


@api_router.get("/show")
async def config_show():
    settings = load_settings()
    return settings_to_toml_data(settings, redact=True)


@api_router.post("/llm")
async def config_llm(
    provider: str = Form("openai"),
    model: str = Form("gpt-4.1-mini"),
    api_key: str = Form(""),
    base_url: str = Form(""),
):
    config_data = load_config_file()
    llm = config_data.setdefault("llm", {})
    llm["provider"] = provider
    llm["model"] = model
    if base_url:
        llm["base_url"] = base_url
    elif "base_url" in llm:
        del llm["base_url"]

    target = default_config_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(render_toml(config_data), encoding="utf-8")

    if api_key:
        CredentialStore().set("llm.api_key", api_key)

    return HTMLResponse(
        "<script>alert('LLM settings saved'); window.location='/settings'</script>"
    )


@api_router.post("/safety")
async def config_safety(
    default_mode: str = Form("confirm_destructive"),
    allow_auto_write: bool = Form(False),
    allow_destructive: bool = Form(False),
    require_confirmation_for: str = Form(""),
):
    config_data = load_config_file()
    safety = config_data.setdefault("safety", {})
    safety["default_mode"] = default_mode
    safety["allow_auto_write"] = allow_auto_write
    safety["allow_destructive"] = allow_destructive
    if require_confirmation_for:
        safety["require_confirmation_for"] = [
            t.strip() for t in require_confirmation_for.split(",") if t.strip()
        ]
    elif "require_confirmation_for" in safety:
        del safety["require_confirmation_for"]

    target = default_config_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(render_toml(config_data), encoding="utf-8")
    return HTMLResponse(
        "<script>alert('Safety settings saved'); window.location='/settings'</script>"
    )


@api_router.post("/app/add")
async def config_app_add(
    name: str = Form(...),
    app_type: str = Form(...),
    base_url: str = Form(...),
    credential_key: str = Form(""),
):
    persist_app_config(name, app_type, base_url, credential_key=credential_key or None)
    return HTMLResponse(
        f"<script>alert('App {name} added'); window.location='/settings'</script>"
    )


@api_router.get("/")
async def config_current():
    settings = load_settings()
    return settings_to_toml_data(settings, redact=True)
