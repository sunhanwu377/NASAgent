from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles


def create_app() -> FastAPI:
    app = FastAPI(title="NASAgent", version="0.1.0")

    static_dir = Path(__file__).parent / "static"
    templates_dir = Path(__file__).parent / "templates"

    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    # Routes
    from nasagent.web.routes import chat as chat_routes
    from nasagent.web.routes import config as config_routes
    from nasagent.web.routes import config_api as config_api_routes
    from nasagent.web.routes import health as health_routes

    app.include_router(chat_routes.router)
    app.include_router(config_routes.router, prefix="/settings")
    app.include_router(config_api_routes.api_router, prefix="/settings")
    app.include_router(health_routes.router)

    from nasagent.web.templates import configure_templates
    configure_templates(app, str(templates_dir))

    return app


def main():
    import uvicorn
    uvicorn.run("nasagent.web.server:create_app", host="0.0.0.0", port=8000, factory=True)


if __name__ == "__main__":
    main()
