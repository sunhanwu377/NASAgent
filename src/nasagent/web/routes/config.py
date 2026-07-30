from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from nasagent.config.settings import KNOWN_APP_TYPES, load_settings
from nasagent.web.templates import get_templates

router = APIRouter(tags=["config"])


@router.get("", response_class=HTMLResponse)
async def settings_page(request: Request):
    return get_templates().TemplateResponse(request, "settings.html", {"request": request})


@router.get("/llm", response_class=HTMLResponse)
async def settings_llm(request: Request):
    settings = load_settings()
    return get_templates().TemplateResponse(request, "settings_llm.html", {
        "request": request,
        "settings": settings,
    })


@router.get("/safety", response_class=HTMLResponse)
async def settings_safety(request: Request):
    settings = load_settings()
    return get_templates().TemplateResponse(request, "settings_safety.html", {
        "request": request,
        "settings": settings,
    })


@router.get("/apps", response_class=HTMLResponse)
async def settings_apps(request: Request):
    settings = load_settings()
    return get_templates().TemplateResponse(request, "settings_apps.html", {
        "request": request,
        "apps": settings.apps,
        "app_types": KNOWN_APP_TYPES,
    })
