from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from nasagent.web.templates import get_templates

router = APIRouter(tags=["config"])


@router.get("", response_class=HTMLResponse)
async def settings_page(request: Request):
    return get_templates().TemplateResponse("settings.html", {"request": request})
