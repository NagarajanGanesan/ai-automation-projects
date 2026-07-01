"""FastAPI application factory.

Building the app inside a factory keeps import side effects out of module scope,
which is friendlier to testing and to ASGI servers.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.api.routes import router as api_router
from app.config import get_settings
from app.core.exceptions import register_exception_handlers


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version=__version__,
        description=(
            "Generate positive, negative, boundary, and equivalence test data, "
            "API request payloads, and database seed data from a user story, an "
            "API specification, and validation rules — powered by Claude with a "
            "deterministic rule-based fallback."
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

    return app


app = create_app()
