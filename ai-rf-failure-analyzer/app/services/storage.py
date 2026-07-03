"""Result storage.

A small abstraction over persistence so the API layer never depends on a
concrete store. The default in-memory implementation is sufficient for a
single-process deployment and for tests; swapping in Redis or a database
later only requires a new :class:`ResultStore` implementation.
"""

from __future__ import annotations

import threading
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Optional

from app.core.exceptions import ResultNotFoundError
from app.models.schemas import AIAnalysis, ParsedResult


@dataclass
class StoredResult:
    """A parsed run plus its (optional) AI analysis."""

    result_id: str
    filename: str
    parsed: ParsedResult
    analysis: Optional[AIAnalysis] = field(default=None)


class ResultStore(ABC):
    """Abstract persistence interface for parsed results."""

    @abstractmethod
    def create(self, filename: str, parsed: ParsedResult) -> StoredResult:
        ...

    @abstractmethod
    def get(self, result_id: str) -> StoredResult:
        ...

    @abstractmethod
    def attach_analysis(self, result_id: str, analysis: AIAnalysis) -> StoredResult:
        ...


class InMemoryResultStore(ResultStore):
    """Thread-safe, process-local result store."""

    def __init__(self) -> None:
        self._items: Dict[str, StoredResult] = {}
        self._lock = threading.Lock()

    def create(self, filename: str, parsed: ParsedResult) -> StoredResult:
        result_id = uuid.uuid4().hex
        stored = StoredResult(result_id=result_id, filename=filename, parsed=parsed)
        with self._lock:
            self._items[result_id] = stored
        return stored

    def get(self, result_id: str) -> StoredResult:
        with self._lock:
            stored = self._items.get(result_id)
        if stored is None:
            raise ResultNotFoundError(f"No result found for id '{result_id}'.")
        return stored

    def attach_analysis(self, result_id: str, analysis: AIAnalysis) -> StoredResult:
        with self._lock:
            stored = self._items.get(result_id)
            if stored is None:
                raise ResultNotFoundError(f"No result found for id '{result_id}'.")
            stored.analysis = analysis
        return stored
