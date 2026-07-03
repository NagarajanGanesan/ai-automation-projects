"""HTTP API routes.

Endpoints
---------
* ``POST /upload``           — upload and parse a Robot Framework artifact.
* ``GET  /projects``         — auto-discover Robot output.xml files on disk.
* ``POST /projects/analyze`` — parse + analyze a discovered output.xml.
* ``POST /analyze``          — generate the AI failure analysis.
* ``GET  /summary``          — statistics + executive summary for a result.
* ``GET  /recommendations``  — recommendations + risk areas for a result.
* ``GET  /health``           — liveness / capability probe.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, Query, UploadFile

from app import __version__
from app.api.dependencies import get_agent, get_analysis_service
from app.config import Settings, get_settings
from app.models.schemas import (
    AnalyzeProjectRequest,
    AnalyzeRequest,
    AnalyzeResponse,
    HealthResponse,
    ProjectAnalysisResponse,
    ProjectsResponse,
    RecommendationsResponse,
    SummaryResponse,
    UploadResponse,
)
from app.services.ai_agent import AIAnalysisAgent
from app.services.analysis_service import AnalysisService

router = APIRouter()


@router.get("/health", response_model=HealthResponse, tags=["meta"])
async def health(
    settings: Settings = Depends(get_settings),
    agent: AIAnalysisAgent = Depends(get_agent),
) -> HealthResponse:
    """Report service health and whether a real AI provider is active."""
    return HealthResponse(
        version=__version__,
        ai_enabled=type(agent).__name__ == "ClaudeAnalysisAgent",
    )


@router.post("/upload", response_model=UploadResponse, tags=["analysis"])
async def upload(
    file: UploadFile = File(..., description="Robot Framework output.xml"),
    service: AnalysisService = Depends(get_analysis_service),
) -> UploadResponse:
    """Upload a Robot Framework artifact and return the parsed structure."""
    content = await file.read()
    stored = service.ingest(filename=file.filename or "upload.xml", content=content)
    return UploadResponse(
        result_id=stored.result_id,
        filename=stored.filename,
        parsed=stored.parsed,
    )


@router.get("/projects", response_model=ProjectsResponse, tags=["discovery"])
async def projects(
    service: AnalysisService = Depends(get_analysis_service),
) -> ProjectsResponse:
    """Auto-discover Robot Framework ``output.xml`` files on disk.

    Scans the configured ``PROJECT_ROOTS`` (the sibling ``tests/`` suites by
    default) and lists each result so any project can be analyzed without a
    manual upload.
    """
    found = service.discover_projects()
    roots = {p.root for p in found}
    return ProjectsResponse(root_count=len(roots), count=len(found), projects=found)


@router.post(
    "/projects/analyze",
    response_model=ProjectAnalysisResponse,
    tags=["discovery"],
)
async def analyze_project(
    request: AnalyzeProjectRequest,
    service: AnalysisService = Depends(get_analysis_service),
) -> ProjectAnalysisResponse:
    """Parse and AI-analyze a discovered ``output.xml`` in one call."""
    stored = service.ingest_path(request.path)
    analysis = service.analyze(stored.result_id)
    return ProjectAnalysisResponse(
        result_id=stored.result_id,
        project=stored.filename,
        path=stored.filename,
        parsed=stored.parsed,
        analysis=analysis,
    )


@router.post("/analyze", response_model=AnalyzeResponse, tags=["analysis"])
async def analyze(
    request: AnalyzeRequest,
    service: AnalysisService = Depends(get_analysis_service),
) -> AnalyzeResponse:
    """Run the AI analysis for a previously uploaded result."""
    analysis = service.analyze(request.result_id)
    return AnalyzeResponse(result_id=request.result_id, analysis=analysis)


@router.get("/summary", response_model=SummaryResponse, tags=["analysis"])
async def summary(
    result_id: str = Query(..., description="Result id returned by /upload"),
    service: AnalysisService = Depends(get_analysis_service),
) -> SummaryResponse:
    """Return statistics and, if available, the executive summary."""
    stored = service.get_result(result_id)
    analysis = stored.analysis
    return SummaryResponse(
        result_id=result_id,
        statistics=stored.parsed,
        executive_summary=analysis.executive_summary if analysis else None,
        overall_risk=analysis.overall_risk if analysis else None,
    )


@router.get(
    "/recommendations",
    response_model=RecommendationsResponse,
    tags=["analysis"],
)
async def recommendations(
    result_id: str = Query(..., description="Result id returned by /upload"),
    service: AnalysisService = Depends(get_analysis_service),
) -> RecommendationsResponse:
    """Return recommendations and risk areas, running analysis on demand."""
    stored = service.get_result(result_id)
    analysis = stored.analysis or service.analyze(result_id)
    return RecommendationsResponse(
        result_id=result_id,
        recommendations=analysis.recommendations,
        risk_areas=analysis.risk_areas,
    )
