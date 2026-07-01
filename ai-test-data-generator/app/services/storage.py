"""Generation result storage.

A small abstraction over persistence so the API layer never depends on a
concrete store. The default in-memory implementation suffices for a
single-process deployment and for tests; a Redis or database store can be
added later by implementing :class:`ResultStore` without touching callers.
"""

from __future__ import annotations

import threading
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict

from app.core.exceptions import ResultNotFoundError
from app.models.schemas import GeneratedTestData


@dataclass
class StoredGeneration:
    """A generated artifact set plus its id."""

    generation_id: str
    generated: GeneratedTestData


class ResultStore(ABC):
    """Abstract persistence interface for generation results."""

    @abstractmethod
    def create(self, generated: GeneratedTestData) -> StoredGeneration:
        ...

    @abstractmethod
    def get(self, generation_id: str) -> StoredGeneration:
        ...


class InMemoryResultStore(ResultStore):
    """Thread-safe, process-local result store."""

    def __init__(self) -> None:
        self._items: Dict[str, StoredGeneration] = {}
        self._lock = threading.Lock()

    def create(self, generated: GeneratedTestData) -> StoredGeneration:
        generation_id = uuid.uuid4().hex
        stored = StoredGeneration(generation_id=generation_id, generated=generated)
        with self._lock:
            self._items[generation_id] = stored
        return stored

    def get(self, generation_id: str) -> StoredGeneration:
        with self._lock:
            stored = self._items.get(generation_id)
        if stored is None:
            raise ResultNotFoundError(
                f"No generation found for id '{generation_id}'."
            )
        return stored
