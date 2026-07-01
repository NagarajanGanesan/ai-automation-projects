"""Test-data generation agents.

The :class:`TestDataGenerator` interface lets the rest of the system depend on
an abstraction rather than on Anthropic specifically (Dependency Inversion).
Two implementations are provided:

* :class:`ClaudeTestDataGenerator` — calls the Anthropic Claude API to produce
  story-aware, semantically rich test data.
* :class:`RuleBasedTestDataGenerator` — a deterministic, offline fallback that
  derives correct, exhaustive data from the field constraints. It keeps the
  product fully functional and testable without a network or API key.

Why the Claude path does not use structured outputs (``output_config.format``):
the generated payloads (``data``, ``body``, seed ``rows``) are intentionally
free-form objects, and JSON-schema structured outputs require
``additionalProperties: false`` on every object — they cannot express arbitrary
key/value records. So the Claude path constrains shape via a strict prompt and
parses the returned JSON, validating it against the same Pydantic models.
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from typing import List, Optional

from pydantic import BaseModel, Field

from app.config import Settings
from app.core.exceptions import AIServiceError
from app.models.schemas import (
    ApiRequestPayload,
    BoundaryValue,
    DatabaseSeedData,
    EquivalencePartition,
    GeneratedTestData,
    GenerationRequest,
    TestRecord,
)
from app.services import rule_based
from app.utils.sql import build_seed_data

_SYSTEM_PROMPT = (
    "You are a senior SDET (software test engineer) who designs high-quality "
    "test data. Given a user story, an API specification, and validation rules, "
    "produce comprehensive, realistic test data. Apply standard black-box "
    "techniques: positive cases (all constraints satisfied), negative cases "
    "(each violating exactly one rule), boundary-value analysis, and "
    "equivalence partitioning. Honour every field constraint and cross-field "
    "validation rule. Values must be realistic for the domain implied by the "
    "user story. Respond with a SINGLE JSON object only — no prose, no markdown "
    "fences — matching exactly the schema described in the prompt."
)


class _LLMGenerated(BaseModel):
    """The shape the model must return (server metadata is added afterwards).

    Field payloads (``data``/``body``/``rows``) are free-form objects, so this
    is validated after parsing rather than enforced via structured outputs.
    """

    positive: List[TestRecord] = Field(default_factory=list)
    negative: List[TestRecord] = Field(default_factory=list)
    boundary_values: List[BoundaryValue] = Field(default_factory=list)
    equivalence_partitions: List[EquivalencePartition] = Field(default_factory=list)
    api_payloads: List[ApiRequestPayload] = Field(default_factory=list)
    seed_data: DatabaseSeedData
    notes: Optional[str] = None


class TestDataGenerator(ABC):
    """Abstract test-data generator."""

    @abstractmethod
    def generate(self, request: GenerationRequest, count: int) -> GeneratedTestData:
        """Produce the full set of test-data artifacts for ``request``."""
        raise NotImplementedError


# ---------------------------------------------------------------------------
# Claude implementation
# ---------------------------------------------------------------------------
class ClaudeTestDataGenerator(TestDataGenerator):
    """Anthropic Claude-backed generator."""

    def __init__(self, settings: Settings) -> None:
        # Imported lazily so the package works without the SDK installed when
        # only the rule-based generator is needed.
        import anthropic

        self._settings = settings
        self._client = anthropic.Anthropic(
            api_key=settings.anthropic_api_key,
            timeout=settings.claude_timeout_seconds,
        )

    def generate(self, request: GenerationRequest, count: int) -> GeneratedTestData:
        import anthropic

        prompt = self._build_user_prompt(request, count)
        try:
            response = self._client.messages.create(
                model=self._settings.claude_model,
                max_tokens=self._settings.claude_max_tokens,
                system=_SYSTEM_PROMPT,
                thinking={"type": "adaptive"},
                output_config={"effort": self._settings.claude_effort},
                messages=[{"role": "user", "content": prompt}],
            )
        except anthropic.APIError as exc:  # pragma: no cover - network path
            raise AIServiceError(f"Claude request failed: {exc}") from exc

        if response.stop_reason == "refusal":  # pragma: no cover - rare
            raise AIServiceError("The model declined to generate this data.")

        text = next(
            (block.text for block in response.content if block.type == "text"),
            None,
        )
        if not text:  # pragma: no cover - defensive
            raise AIServiceError("Empty response from the model.")

        try:
            draft = _LLMGenerated.model_validate_json(_strip_json_fences(text))
        except ValueError as exc:  # pragma: no cover - defensive
            raise AIServiceError(f"Could not parse model output: {exc}") from exc

        # Rebuild the seed SQL ourselves so the INSERT statements are always
        # syntactically correct regardless of what the model emitted.
        seed = build_seed_data(draft.seed_data.table, draft.seed_data.rows)

        return GeneratedTestData(
            positive=draft.positive,
            negative=draft.negative,
            boundary_values=draft.boundary_values,
            equivalence_partitions=draft.equivalence_partitions,
            api_payloads=draft.api_payloads,
            seed_data=seed,
            notes=draft.notes,
            model=getattr(response, "model", self._settings.claude_model),
            generated_by_ai=True,
        )

    @staticmethod
    def _build_user_prompt(request: GenerationRequest, count: int) -> str:
        spec = request.api_spec
        payload = {
            "user_story": request.user_story,
            "api_spec": spec.model_dump(),
            "validation_rules": [r.model_dump() for r in request.validation_rules],
            "positive_record_count": count,
            "seed_table": request.table_name or _table_hint(spec.path),
        }
        schema_hint = {
            "positive": [
                {
                    "name": "str",
                    "description": "str",
                    "kind": "positive",
                    "data": {"<field>": "<value>"},
                    "expected_valid": True,
                    "expected_status": spec.success_status,
                }
            ],
            "negative": [
                {
                    "name": "str",
                    "description": "str",
                    "kind": "negative",
                    "data": {"<field>": "<value>"},
                    "expected_valid": False,
                    "expected_status": spec.error_status,
                    "violated_field": "str",
                    "violation_reason": "str",
                }
            ],
            "boundary_values": [
                {
                    "field": "str",
                    "boundary": "at_min|below_min|at_max|above_max|...",
                    "value": "<value>",
                    "expected_valid": True,
                    "description": "str",
                }
            ],
            "equivalence_partitions": [
                {
                    "field": "str",
                    "partition": "str",
                    "partition_class": "valid|invalid",
                    "representative_value": "<value>",
                    "expected_valid": True,
                    "description": "str",
                }
            ],
            "api_payloads": [
                {
                    "name": "str",
                    "kind": "positive|negative",
                    "method": spec.method.upper(),
                    "path": spec.path,
                    "headers": {"Content-Type": "application/json"},
                    "body": {"<field>": "<value>"},
                    "expected_status": spec.success_status,
                }
            ],
            "seed_data": {
                "table": "str",
                "columns": ["str"],
                "rows": [{"<column>": "<value>"}],
                "sql": ["INSERT ... (regenerated server-side; may be omitted)"],
            },
            "notes": "optional str",
        }
        return (
            "Generate test data for the following. Respond with ONE JSON object "
            "whose keys and shapes match the schema example exactly.\n\n"
            "INPUT:\n"
            + json.dumps(payload, indent=2, default=str)
            + "\n\nOUTPUT JSON SCHEMA (shape, not literal values):\n"
            + json.dumps(schema_hint, indent=2)
        )


# ---------------------------------------------------------------------------
# Offline / deterministic implementation
# ---------------------------------------------------------------------------
class RuleBasedTestDataGenerator(TestDataGenerator):
    """Deterministic generator used when no AI provider is configured."""

    def generate(self, request: GenerationRequest, count: int) -> GeneratedTestData:
        return rule_based.generate(request, count)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _strip_json_fences(text: str) -> str:
    """Remove ```json ... ``` fences a model may wrap the JSON in."""
    stripped = text.strip()
    if stripped.startswith("```"):
        first_newline = stripped.find("\n")
        if first_newline != -1:
            stripped = stripped[first_newline + 1 :]
        if stripped.endswith("```"):
            stripped = stripped[:-3]
    return stripped.strip()


def _table_hint(path: str) -> str:
    segments = [s for s in (path or "").split("/") if s and not s.startswith("{")]
    return segments[-1] if segments else "test_table"


def build_generator(settings: Settings) -> TestDataGenerator:
    """Factory selecting the best available generator for the configuration."""
    if settings.ai_enabled:
        try:
            return ClaudeTestDataGenerator(settings)
        except Exception:  # pragma: no cover - SDK import/init failure
            return RuleBasedTestDataGenerator()
    return RuleBasedTestDataGenerator()
