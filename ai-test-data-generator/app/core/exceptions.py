"""Domain exceptions and their FastAPI handlers.

A small exception hierarchy keeps error handling explicit and lets the API
layer translate domain failures into appropriate HTTP responses without
leaking implementation details.
"""

from __future__ import annotations

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse


class GeneratorError(Exception):
    """Base class for all application-specific errors."""

    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    code: str = "generator_error"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class ValidationError(GeneratorError):
    """Raised when an incoming generation request is invalid."""

    status_code = status.HTTP_400_BAD_REQUEST
    code = "validation_error"


class ResultNotFoundError(GeneratorError):
    """Raised when a referenced generation id does not exist."""

    status_code = status.HTTP_404_NOT_FOUND
    code = "result_not_found"


class AIServiceError(GeneratorError):
    """Raised when the AI provider fails to produce output."""

    status_code = status.HTTP_502_BAD_GATEWAY
    code = "ai_service_error"


def register_exception_handlers(app: FastAPI) -> None:
    """Attach a single handler for the :class:`GeneratorError` hierarchy."""

    @app.exception_handler(GeneratorError)
    async def _handle_generator_error(  # pragma: no cover - thin wrapper
        _request: Request, exc: GeneratorError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": exc.code, "message": exc.message}},
        )
