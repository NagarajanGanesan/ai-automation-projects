"""FastAPI dependency providers.

Collaborators are built once and cached for the process lifetime. The
``AnalysisService`` is assembled from its dependencies here, which is the only
composition-root in the application. Tests can override any of these
providers via ``app.dependency_overrides``.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Optional

from fastapi import Depends

from app.config import Settings, get_settings
from app.parsers.robot_parser import RobotOutputParser
from app.services.ai_agent import AIAnalysisAgent, build_agent
from app.services.analysis_service import AnalysisService
from app.services.discovery import FileSystemProjectScanner, ProjectScanner
from app.services.storage import InMemoryResultStore, ResultStore

# Process-local singleton for the agent. It is built lazily from settings; the
# settings object itself is not hashable, so we cache the instance directly
# rather than via ``lru_cache`` keyed on ``Settings``.
_AGENT: Optional[AIAnalysisAgent] = None


@lru_cache(maxsize=1)
def get_store() -> ResultStore:
    return InMemoryResultStore()


@lru_cache(maxsize=1)
def get_parser() -> RobotOutputParser:
    return RobotOutputParser()


def get_scanner(settings: Settings = Depends(get_settings)) -> ProjectScanner:
    return FileSystemProjectScanner(
        settings.resolved_project_roots,
        output_glob=settings.output_glob,
        exclude_dirs=settings.scan_exclude_dirs,
    )


def get_agent(settings: Settings = Depends(get_settings)) -> AIAnalysisAgent:
    global _AGENT
    if _AGENT is None:
        _AGENT = build_agent(settings)
    return _AGENT


def get_analysis_service(
    settings: Settings = Depends(get_settings),
    parser: RobotOutputParser = Depends(get_parser),
    store: ResultStore = Depends(get_store),
    agent: AIAnalysisAgent = Depends(get_agent),
    scanner: ProjectScanner = Depends(get_scanner),
) -> AnalysisService:
    return AnalysisService(
        parser=parser,
        store=store,
        agent=agent,
        scanner=scanner,
        max_upload_bytes=settings.max_upload_bytes,
        allowed_extensions=settings.allowed_upload_extensions,
    )
