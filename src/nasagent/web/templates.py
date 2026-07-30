from fastapi import FastAPI
from fastapi.templating import Jinja2Templates


templates: Jinja2Templates | None = None


def configure_templates(app: FastAPI, templates_dir: str) -> None:
    global templates
    templates = Jinja2Templates(directory=templates_dir)


def get_templates() -> Jinja2Templates:
    if templates is None:
        raise RuntimeError("Templates not configured")
    return templates
