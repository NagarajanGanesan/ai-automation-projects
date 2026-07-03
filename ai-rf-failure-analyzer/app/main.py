"""FastAPI application factory.

Building the app inside a factory keeps import side effects out of module
scope, which is friendlier to testing and to ASGI servers. The frontend is
served as static files from the same origin to avoid CORS in the common
single-container deployment.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app import __version__
from app.api.routes import router as api_router
from app.config import get_settings
from app.core.exceptions import register_exception_handlers

_FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version=__version__,
        description=(
            "Analyse Robot Framework execution results and generate "
            "intelligent failure insights using Claude."
        ),
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allow_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_exception_handlers(app)
    app.include_router(api_router, prefix="/api")

    if _FRONTEND_DIR.is_dir():
        app.mount(
            "/static",
            StaticFiles(directory=str(_FRONTEND_DIR)),
            name="static",
        )

        @app.get("/", include_in_schema=False)
        async def index() -> FileResponse:  # pragma: no cover - static serving
            return FileResponse(str(_FRONTEND_DIR / "index.html"))

    return app


app = create_app()
