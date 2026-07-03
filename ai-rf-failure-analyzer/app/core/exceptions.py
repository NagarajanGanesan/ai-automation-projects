"""Domain exceptions and their FastAPI handlers.

Defining a small exception hierarchy keeps error handling explicit and lets
the API layer translate domain failures into appropriate HTTP responses
without leaking implementation details.
"""

from __future__ import annotations

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse


class AnalyzerError(Exception):
    """Base class for all application-specific errors."""

    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    code: str = "analyzer_error"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class ParseError(AnalyzerError):
    """Raised when a Robot Framework artifact cannot be parsed."""

    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    code = "parse_error"


class ValidationError(AnalyzerError):
    """Raised when an uploaded file fails validation."""

    status_code = status.HTTP_400_BAD_REQUEST
    code = "validation_error"


class ResultNotFoundError(AnalyzerError):
    """Raised when a referenced result id does not exist."""

    status_code = status.HTTP_404_NOT_FOUND
    code = "result_not_found"


class AnalysisNotFoundError(AnalyzerError):
    """Raised when analysis is requested before it has been produced."""

    status_code = status.HTTP_409_CONFLICT
    code = "analysis_not_found"


class AIServiceError(AnalyzerError):
    """Raised when the AI provider fails to produce an analysis."""

    status_code = status.HTTP_502_BAD_GATEWAY
    code = "ai_service_error"


def register_exception_handlers(app: FastAPI) -> None:
    """Attach a single handler for the :class:`AnalyzerError` hierarchy."""

    @app.exception_handler(AnalyzerError)
    async def _handle_analyzer_error(  # pragma: no cover - thin wrapper
        _request: Request, exc: AnalyzerError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": exc.code, "message": exc.message}},
        )
