"""Pydantic data models.

This module defines three layers of models:

* **Domain models** that describe parsed Robot Framework results
  (``KeywordFailure``, ``TestCaseResult``, ``SuiteStatistics``, ``ParsedResult``).
* **AI models** that describe the structured analysis produced by the agent
  (``RootCause``, ``FlakyPattern``, ``RiskArea``, ``Recommendation``,
  ``AIAnalysis``).
* **API models** used directly in request/response bodies.

Keeping them in one well-organised module gives every layer a single source
of truth for shapes and validation.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------
class TestStatus(str, Enum):
    """Robot Framework test outcome."""

    PASS = "PASS"
    FAIL = "FAIL"
    SKIP = "SKIP"
    NOT_RUN = "NOT RUN"


class Severity(str, Enum):
    """Qualitative severity used by AI insights."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# ---------------------------------------------------------------------------
# Domain models (parsed from output.xml)
# ---------------------------------------------------------------------------
class KeywordFailure(BaseModel):
    """A keyword whose execution failed within a test case."""

    name: str
    library: Optional[str] = None
    error_message: Optional[str] = None
    test_name: str
    suite_name: str


class TestCaseResult(BaseModel):
    """The outcome of a single Robot Framework test case."""

    name: str
    suite: str
    status: TestStatus
    message: Optional[str] = None
    duration_seconds: float = 0.0
    tags: List[str] = Field(default_factory=list)
    failing_keyword: Optional[str] = None


class SuiteStatistics(BaseModel):
    """Aggregate counts for a suite (or the whole run)."""

    name: str
    total: int = 0
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    duration_seconds: float = 0.0

    @property
    def pass_rate(self) -> float:
        executed = self.passed + self.failed
        return round(self.passed / executed, 4) if executed else 0.0


class ParsedResult(BaseModel):
    """Structured view of a parsed Robot Framework execution."""

    generated_at: Optional[datetime] = None
    generator: Optional[str] = None
    total_tests: int = 0
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    total_duration_seconds: float = 0.0
    suite_statistics: List[SuiteStatistics] = Field(default_factory=list)
    failed_tests: List[TestCaseResult] = Field(default_factory=list)
    all_tests: List[TestCaseResult] = Field(default_factory=list)
    keyword_failures: List[KeywordFailure] = Field(default_factory=list)

    @property
    def pass_rate(self) -> float:
        executed = self.passed + self.failed
        return round(self.passed / executed, 4) if executed else 0.0


# ---------------------------------------------------------------------------
# AI analysis models
# ---------------------------------------------------------------------------
class RootCause(BaseModel):
    """A probable root cause for one or more failures."""

    title: str
    explanation: str
    affected_tests: List[str] = Field(default_factory=list)
    confidence: Severity = Severity.MEDIUM


class FlakyPattern(BaseModel):
    """A detected pattern suggesting test flakiness."""

    description: str
    evidence: str
    affected_tests: List[str] = Field(default_factory=list)


class RiskArea(BaseModel):
    """An area of the test suite or product carrying elevated risk."""

    area: str
    reason: str
    severity: Severity = Severity.MEDIUM


class Recommendation(BaseModel):
    """An actionable automation-improvement suggestion."""

    title: str
    detail: str
    priority: Severity = Severity.MEDIUM


class AIAnalysis(BaseModel):
    """The full structured output produced by the AI agent."""

    executive_summary: str
    overall_risk: Severity = Severity.MEDIUM
    root_causes: List[RootCause] = Field(default_factory=list)
    flaky_patterns: List[FlakyPattern] = Field(default_factory=list)
    risk_areas: List[RiskArea] = Field(default_factory=list)
    recommendations: List[Recommendation] = Field(default_factory=list)
    model: Optional[str] = None
    generated_by_ai: bool = True


# ---------------------------------------------------------------------------
# API models
# ---------------------------------------------------------------------------
class UploadResponse(BaseModel):
    """Returned by ``POST /upload``."""

    result_id: str
    filename: str
    parsed: ParsedResult


class AnalyzeRequest(BaseModel):
    """Body for ``POST /analyze``."""

    result_id: str


class AnalyzeResponse(BaseModel):
    """Returned by ``POST /analyze``."""

    result_id: str
    analysis: AIAnalysis


class SummaryResponse(BaseModel):
    """Returned by ``GET /summary``."""

    result_id: str
    statistics: ParsedResult
    executive_summary: Optional[str] = None
    overall_risk: Optional[Severity] = None


class RecommendationsResponse(BaseModel):
    """Returned by ``GET /recommendations``."""

    result_id: str
    recommendations: List[Recommendation]
    risk_areas: List[RiskArea]


class HealthResponse(BaseModel):
    """Returned by ``GET /health``."""

    status: str = "ok"
    version: str
    ai_enabled: bool


# ---------------------------------------------------------------------------
# Project auto-discovery models
# ---------------------------------------------------------------------------
class DiscoveredProject(BaseModel):
    """A Robot Framework ``output.xml`` found by scanning the project roots."""

    project: str = Field(..., description="Friendly project name (folder path).")
    path: str = Field(..., description="Absolute path to the output.xml.")
    relative_path: str = Field(..., description="Path relative to its scan root.")
    root: str = Field(..., description="The scan root the file was found under.")
    size_bytes: int = 0
    modified_at: Optional[datetime] = None


class ProjectsResponse(BaseModel):
    """Returned by ``GET /projects``."""

    root_count: int
    count: int
    projects: List[DiscoveredProject] = Field(default_factory=list)


class AnalyzeProjectRequest(BaseModel):
    """Body for ``POST /projects/analyze`` — analyze a discovered output.xml."""

    path: str = Field(..., description="Path of a discovered project output.xml.")


class ProjectAnalysisResponse(BaseModel):
    """Returned by ``POST /projects/analyze``."""

    result_id: str
    project: str
    path: str
    parsed: ParsedResult
    analysis: AIAnalysis
