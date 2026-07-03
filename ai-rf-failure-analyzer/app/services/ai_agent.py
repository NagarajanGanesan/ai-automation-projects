"""AI analysis agent.

The :class:`AIAnalysisAgent` interface lets the rest of the system depend on
an abstraction rather than on Anthropic specifically (Dependency Inversion).
Two implementations are provided:

* :class:`ClaudeAnalysisAgent` — calls the Anthropic Claude API and returns a
  schema-validated structured analysis.
* :class:`RuleBasedAnalysisAgent` — a deterministic, offline fallback used
  when no API key is configured and in tests. It keeps the product fully
  functional without network access.

The agent is intentionally grounded: it is given pre-computed metrics and the
concrete failures, and is instructed to reason only from that evidence.
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from typing import Any, Dict, List

from pydantic import BaseModel, Field

from app.config import Settings
from app.core.exceptions import AIServiceError
from app.models.schemas import (
    AIAnalysis,
    FlakyPattern,
    Recommendation,
    RiskArea,
    RootCause,
    Severity,
)
from app.models.schemas import ParsedResult

_SYSTEM_PROMPT = (
    "You are a senior QA automation analyst specialising in Robot Framework. "
    "You are given structured metrics and the concrete failures from a single "
    "test execution. Analyse only the evidence provided — do not invent tests, "
    "errors, or stack traces that are not present. Identify probable root "
    "causes, detect patterns that suggest flaky tests (timeouts, waits, "
    "intermittent network/element errors), call out the riskiest areas, and "
    "give concrete, prioritised automation improvements. Write an executive "
    "summary a QA lead could paste into a status report."
)


class _LLMAnalysis(BaseModel):
    """Schema the model is constrained to fill (excludes server metadata)."""

    executive_summary: str = Field(description="2-4 sentence summary for a QA lead.")
    overall_risk: Severity
    root_causes: List[RootCause]
    flaky_patterns: List[FlakyPattern]
    risk_areas: List[RiskArea]
    recommendations: List[Recommendation]


class AIAnalysisAgent(ABC):
    """Abstract analysis agent."""

    @abstractmethod
    def analyze(self, result: ParsedResult, metrics: Dict[str, Any]) -> AIAnalysis:
        """Produce a structured failure analysis for a parsed run."""
        raise NotImplementedError


# ---------------------------------------------------------------------------
# Claude implementation
# ---------------------------------------------------------------------------
class ClaudeAnalysisAgent(AIAnalysisAgent):
    """Anthropic Claude-backed analysis agent."""

    def __init__(self, settings: Settings) -> None:
        # Imported lazily so the package can be installed/used without the
        # SDK present (e.g. when only the rule-based agent is needed).
        import anthropic

        self._settings = settings
        self._client = anthropic.Anthropic(
            api_key=settings.anthropic_api_key,
            timeout=settings.claude_timeout_seconds,
        )

    def analyze(self, result: ParsedResult, metrics: Dict[str, Any]) -> AIAnalysis:
        import anthropic

        prompt = self._build_user_prompt(result, metrics)
        schema = _sanitize_schema(_LLMAnalysis.model_json_schema())
        try:
            response = self._client.messages.create(
                model=self._settings.claude_model,
                max_tokens=self._settings.claude_max_tokens,
                system=_SYSTEM_PROMPT,
                thinking={"type": "adaptive"},
                output_config={
                    "effort": self._settings.claude_effort,
                    "format": {"type": "json_schema", "schema": schema},
                },
                messages=[{"role": "user", "content": prompt}],
            )
        except anthropic.APIError as exc:  # pragma: no cover - network path
            raise AIServiceError(f"Claude request failed: {exc}") from exc

        if response.stop_reason == "refusal":  # pragma: no cover - rare
            raise AIServiceError("The model declined to analyse this input.")

        text = next(
            (block.text for block in response.content if block.type == "text"),
            None,
        )
        if not text:  # pragma: no cover - defensive
            raise AIServiceError("Empty response from the model.")

        try:
            draft = _LLMAnalysis.model_validate_json(text)
        except ValueError as exc:  # pragma: no cover - defensive
            raise AIServiceError(f"Could not parse model output: {exc}") from exc

        return AIAnalysis(
            **draft.model_dump(),
            model=getattr(response, "model", self._settings.claude_model),
            generated_by_ai=True,
        )

    @staticmethod
    def _build_user_prompt(result: ParsedResult, metrics: Dict[str, Any]) -> str:
        payload = {
            "metrics": metrics,
            "failed_tests": [
                {
                    "name": t.name,
                    "suite": t.suite,
                    "message": t.message,
                    "failing_keyword": t.failing_keyword,
                    "duration_seconds": t.duration_seconds,
                    "tags": t.tags,
                }
                for t in result.failed_tests
            ],
            "keyword_failures": [
                {
                    "keyword": k.name,
                    "library": k.library,
                    "error": k.error_message,
                    "test": k.test_name,
                    "suite": k.suite_name,
                }
                for k in result.keyword_failures
            ],
        }
        return (
            "Analyse the following Robot Framework execution. Respond strictly "
            "in the required JSON schema.\n\n"
            + json.dumps(payload, indent=2, default=str)
        )


# ---------------------------------------------------------------------------
# Offline / deterministic implementation
# ---------------------------------------------------------------------------
class RuleBasedAnalysisAgent(AIAnalysisAgent):
    """Heuristic analysis used when no AI provider is configured.

    It produces a genuinely useful, grounded analysis from the metrics so the
    application is fully functional offline and unit tests are deterministic.
    """

    _FLAKY_HINTS = (
        "timeout",
        "timed out",
        "element not",
        "not visible",
        "stale element",
        "connection",
        "no such element",
        "retry",
        "intermittent",
    )

    def analyze(self, result: ParsedResult, metrics: Dict[str, Any]) -> AIAnalysis:
        root_causes = self._root_causes(result)
        flaky = self._flaky_patterns(result)
        risk_areas = self._risk_areas(result, metrics)
        recommendations = self._recommendations(result, metrics, flaky)
        overall_risk = self._overall_risk(result)

        summary = (
            f"{result.failed} of {result.total_tests} tests failed "
            f"({round(result.pass_rate * 100, 1)}% pass rate) across "
            f"{len(result.suite_statistics)} suite(s). "
        )
        if flaky:
            summary += f"{len(flaky)} pattern(s) suggest possible flakiness. "
        if root_causes:
            summary += f"Top likely cause: {root_causes[0].title}."
        else:
            summary += "No failures detected — the run is healthy."

        return AIAnalysis(
            executive_summary=summary.strip(),
            overall_risk=overall_risk,
            root_causes=root_causes,
            flaky_patterns=flaky,
            risk_areas=risk_areas,
            recommendations=recommendations,
            model="rule-based",
            generated_by_ai=False,
        )

    # -- heuristics -------------------------------------------------------
    def _root_causes(self, result: ParsedResult) -> List[RootCause]:
        causes: List[RootCause] = []
        grouped: Dict[str, List[str]] = {}
        for kw in result.keyword_failures:
            key = (kw.error_message or kw.name or "Unknown error").strip()
            grouped.setdefault(key[:120], []).append(kw.test_name)
        for message, tests in sorted(
            grouped.items(), key=lambda kv: len(kv[1]), reverse=True
        ):
            causes.append(
                RootCause(
                    title=message,
                    explanation=(
                        "This error recurs across the listed tests, indicating a "
                        "shared root cause rather than isolated test issues."
                        if len(tests) > 1
                        else "Isolated failure tied to a single test."
                    ),
                    affected_tests=sorted(set(tests)),
                    confidence=Severity.HIGH if len(tests) > 1 else Severity.MEDIUM,
                )
            )
        return causes[:5]

    def _flaky_patterns(self, result: ParsedResult) -> List[FlakyPattern]:
        patterns: List[FlakyPattern] = []
        for kw in result.keyword_failures:
            haystack = f"{kw.name} {kw.error_message or ''}".lower()
            hit = next((h for h in self._FLAKY_HINTS if h in haystack), None)
            if hit:
                patterns.append(
                    FlakyPattern(
                        description=f"Possible flakiness near '{kw.name}'.",
                        evidence=f"Failure text contains '{hit}': "
                        f"{(kw.error_message or '').strip()[:160]}",
                        affected_tests=[kw.test_name],
                    )
                )
        return patterns

    def _risk_areas(
        self, result: ParsedResult, metrics: Dict[str, Any]
    ) -> List[RiskArea]:
        areas: List[RiskArea] = []
        for stat in result.suite_statistics:
            if stat.failed:
                rate = stat.failed / max(stat.total, 1)
                areas.append(
                    RiskArea(
                        area=stat.name,
                        reason=f"{stat.failed}/{stat.total} tests failing "
                        f"({round(rate * 100, 1)}%).",
                        severity=Severity.CRITICAL if rate >= 0.5 else Severity.HIGH,
                    )
                )
        for entry in metrics.get("keyword_failure_counts", [])[:3]:
            if entry["failures"] > 1:
                areas.append(
                    RiskArea(
                        area=f"{entry['library']}.{entry['keyword']}",
                        reason=f"Keyword failed {entry['failures']} times.",
                        severity=Severity.MEDIUM,
                    )
                )
        return areas

    def _recommendations(
        self,
        result: ParsedResult,
        metrics: Dict[str, Any],
        flaky: List[FlakyPattern],
    ) -> List[Recommendation]:
        recs: List[Recommendation] = []
        if flaky:
            recs.append(
                Recommendation(
                    title="Stabilise flaky-prone keywords",
                    detail="Replace fixed sleeps with explicit waits, add retries "
                    "with backoff, and assert on stable locators to remove the "
                    "timing/element errors detected above.",
                    priority=Severity.HIGH,
                )
            )
        if result.failed:
            recs.append(
                Recommendation(
                    title="Quarantine and triage failing suites",
                    detail="Tag the failing suites and run them in isolation to "
                    "confirm whether failures are deterministic before the next "
                    "release gate.",
                    priority=Severity.HIGH,
                )
            )
        slowest = metrics.get("slowest_tests", [])
        if slowest and slowest[0]["duration_seconds"] > 0:
            recs.append(
                Recommendation(
                    title="Profile the slowest tests",
                    detail=f"'{slowest[0]['name']}' took "
                    f"{slowest[0]['duration_seconds']}s. Investigate setup cost "
                    "and consider parallelisation to shorten the feedback loop.",
                    priority=Severity.MEDIUM,
                )
            )
        if not recs:
            recs.append(
                Recommendation(
                    title="Maintain current quality",
                    detail="No failures detected. Keep monitoring durations and "
                    "expand coverage for under-tested areas.",
                    priority=Severity.LOW,
                )
            )
        return recs

    @staticmethod
    def _overall_risk(result: ParsedResult) -> Severity:
        if result.total_tests == 0:
            return Severity.LOW
        rate = result.pass_rate
        if rate >= 0.95:
            return Severity.LOW
        if rate >= 0.85:
            return Severity.MEDIUM
        if rate >= 0.6:
            return Severity.HIGH
        return Severity.CRITICAL


# ---------------------------------------------------------------------------
# Schema sanitisation for structured outputs
# ---------------------------------------------------------------------------
def _sanitize_schema(schema: Dict[str, Any]) -> Dict[str, Any]:
    """Make a Pydantic JSON schema compatible with structured outputs.

    Structured outputs require every object to set ``additionalProperties:
    false`` and to list all of its properties as ``required``. This walks the
    schema (including ``$defs``) and applies those rules in place.
    """

    def _walk(node: Any) -> None:
        if isinstance(node, dict):
            if node.get("type") == "object" and "properties" in node:
                node["additionalProperties"] = False
                node["required"] = list(node["properties"].keys())
            for value in node.values():
                _walk(value)
        elif isinstance(node, list):
            for item in node:
                _walk(item)

    _walk(schema)
    return schema


def build_agent(settings: Settings) -> AIAnalysisAgent:
    """Factory selecting the best available agent for the configuration."""
    if settings.ai_enabled:
        try:
            return ClaudeAnalysisAgent(settings)
        except Exception:  # pragma: no cover - SDK import/init failure
            # Fall back to the offline agent rather than breaking startup.
            return RuleBasedAnalysisAgent()
    return RuleBasedAnalysisAgent()
