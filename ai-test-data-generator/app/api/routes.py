"""HTTP API routes.

Endpoints
---------
* ``POST /generate``        — generate the full test-data set for a request.
* ``GET  /result/{id}``     — fetch a previously generated result.
* ``GET  /health``          — liveness / capability probe.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Path

from app import __version__
from app.api.dependencies import get_generation_service, get_generator
from app.models.schemas import (
    GenerateResponse,
    GenerationRequest,
    HealthResponse,
)
from app.services.generation_service import GenerationService
from app.services.generator_agent import TestDataGenerator

router = APIRouter()


@router.get("/health", response_model=HealthResponse, tags=["meta"])
async def health(
    generator: TestDataGenerator = Depends(get_generator),
) -> HealthResponse:
    """Report service health and whether a real AI provider is active."""
    return HealthResponse(
        version=__version__,
        ai_enabled=type(generator).__name__ == "ClaudeTestDataGenerator",
    )


@router.post("/generate", response_model=GenerateResponse, tags=["generation"])
async def generate(
    request: GenerationRequest,
    service: GenerationService = Depends(get_generation_service),
) -> GenerateResponse:
    """Generate positive/negative/boundary/equivalence data, payloads, and seeds."""
    stored = service.generate(request)
    return GenerateResponse(
        generation_id=stored.generation_id,
        generated=stored.generated,
    )


@router.get("/result/{generation_id}", response_model=GenerateResponse, tags=["generation"])
async def get_result(
    generation_id: str = Path(..., description="Id returned by /generate"),
    service: GenerationService = Depends(get_generation_service),
) -> GenerateResponse:
    """Fetch a previously generated result by id."""
    stored = service.get(generation_id)
    return GenerateResponse(
        generation_id=stored.generation_id,
        generated=stored.generated,
    )
