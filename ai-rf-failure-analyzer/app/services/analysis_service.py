"""Application service orchestrating parsing, storage, and AI analysis.

This is the single place that wires the collaborators together. Each
collaborator is injected, so the service has one responsibility — coordinate
the workflow — and is trivially unit-testable with fakes.
"""

from __future__ import annotations

from typing import List

from app.core.exceptions import AnalysisNotFoundError, ValidationError
from app.models.schemas import AIAnalysis, DiscoveredProject, ParsedResult
from app.parsers.base import ResultParser
from app.services.ai_agent import AIAnalysisAgent
from app.services.discovery import ProjectScanner
from app.services.storage import ResultStore, StoredResult
from app.utils.statistics import build_metrics


class AnalysisService:
    """Coordinates upload → parse → store → analyse."""

    def __init__(
        self,
        parser: ResultParser,
        store: ResultStore,
        agent: AIAnalysisAgent,
        scanner: ProjectScanner,
        *,
        max_upload_bytes: int,
        allowed_extensions: list,
    ) -> None:
        self._parser = parser
        self._store = store
        self._agent = agent
        self._scanner = scanner
        self._max_upload_bytes = max_upload_bytes
        self._allowed_extensions = {e.lower() for e in allowed_extensions}

    # -- upload / parse ---------------------------------------------------
    def ingest(self, filename: str, content: bytes) -> StoredResult:
        """Validate, parse, and persist an uploaded artifact."""
        self._validate_upload(filename, content)
        parsed: ParsedResult = self._parser.parse(content)
        return self._store.create(filename=filename, parsed=parsed)

    # -- discovery --------------------------------------------------------
    def discover_projects(self) -> List[DiscoveredProject]:
        """List every Robot ``output.xml`` found under the configured roots."""
        return self._scanner.discover()

    def ingest_path(self, path: str) -> StoredResult:
        """Validate, read, parse, and persist a discovered ``output.xml``.

        The path is resolved through the scanner, which rejects anything
        outside the configured roots — so this never reads arbitrary files.
        """
        resolved = self._scanner.resolve_allowed(path)
        content = resolved.read_bytes()
        self._validate_upload(resolved.name, content)
        parsed: ParsedResult = self._parser.parse(content)
        return self._store.create(filename=str(resolved), parsed=parsed)

    def _validate_upload(self, filename: str, content: bytes) -> None:
        if not content:
            raise ValidationError("Uploaded file is empty.")
        if len(content) > self._max_upload_bytes:
            raise ValidationError(
                f"File exceeds the maximum size of {self._max_upload_bytes} bytes."
            )
        suffix = _suffix(filename)
        if suffix not in self._allowed_extensions:
            raise ValidationError(
                f"Unsupported file type '{suffix}'. Allowed: "
                f"{sorted(self._allowed_extensions)}."
            )

    # -- analysis ---------------------------------------------------------
    def analyze(self, result_id: str) -> AIAnalysis:
        """Run (or re-run) the AI analysis for a stored result."""
        stored = self._store.get(result_id)
        metrics = build_metrics(stored.parsed)
        analysis = self._agent.analyze(stored.parsed, metrics)
        self._store.attach_analysis(result_id, analysis)
        return analysis

    def get_analysis(self, result_id: str) -> AIAnalysis:
        """Return an existing analysis, raising if it has not been produced."""
        stored = self._store.get(result_id)
        if stored.analysis is None:
            raise AnalysisNotFoundError(
                "Analysis has not been generated yet. Call POST /analyze first."
            )
        return stored.analysis

    def get_result(self, result_id: str) -> StoredResult:
        return self._store.get(result_id)


def _suffix(filename: str) -> str:
    name = (filename or "").strip().lower()
    dot = name.rfind(".")
    return name[dot:] if dot != -1 else ""
