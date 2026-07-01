"""Application service orchestrating validation, generation, and storage.

This is the single place that wires the collaborators together. Each
collaborator is injected, so the service has one responsibility — coordinate
the workflow — and is trivially unit-testable with fakes.
"""

from __future__ import annotations

from app.core.exceptions import ValidationError
from app.models.schemas import GenerationRequest
from app.services.generator_agent import TestDataGenerator
from app.services.storage import ResultStore, StoredGeneration
from app.utils.exporters import build_exports


class GenerationService:
    """Coordinates validate → generate → store."""

    def __init__(
        self,
        generator: TestDataGenerator,
        store: ResultStore,
        *,
        default_count: int,
        max_count: int,
    ) -> None:
        self._generator = generator
        self._store = store
        self._default_count = default_count
        self._max_count = max_count

    def generate(self, request: GenerationRequest) -> StoredGeneration:
        """Validate the request, generate the data, and persist the result."""
        self._validate(request)
        count = self._resolve_count(request.count)
        generated = self._generator.generate(request, count)
        # Apply spec-level default headers (e.g. gateway auth) to every payload,
        # so the merge happens once regardless of which engine produced the data.
        self._apply_spec_headers(generated, request)
        # Build the Robot Framework / pytest / Playwright / Python exports uniformly
        # server-side, so both the Claude and rule-based engines emit runnable files.
        generated.exports = build_exports(
            generated.api_payloads,
            request.api_spec.method,
            request.api_spec.path,
        )
        return self._store.create(generated)

    def get(self, generation_id: str) -> StoredGeneration:
        return self._store.get(generation_id)

    # -- internals --------------------------------------------------------
    @staticmethod
    def _apply_spec_headers(generated, request: GenerationRequest) -> None:
        """Merge ``api_spec.headers`` into each payload (payload values win)."""
        spec_headers = request.api_spec.headers
        if not spec_headers:
            return
        for payload in generated.api_payloads:
            payload.headers = {**spec_headers, **payload.headers}

    def _validate(self, request: GenerationRequest) -> None:
        if not request.user_story.strip():
            raise ValidationError("user_story must not be empty.")
        if not request.api_spec.fields:
            raise ValidationError(
                "api_spec.fields must contain at least one field to generate data for."
            )
        names = [f.name for f in request.api_spec.fields]
        if len(names) != len(set(names)):
            raise ValidationError("api_spec.fields contains duplicate field names.")

    def _resolve_count(self, requested: int | None) -> int:
        count = requested if requested is not None else self._default_count
        return max(1, min(count, self._max_count))
