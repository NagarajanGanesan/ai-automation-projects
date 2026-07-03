"""Parser abstraction.

The :class:`ResultParser` interface decouples the rest of the application
from any concrete parsing implementation (Dependency Inversion Principle).
New formats — JUnit XML, Allure, a future Robot schema — can be supported by
adding a new implementation without touching the services that consume
parsed results.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.models.schemas import ParsedResult


class ResultParser(ABC):
    """Abstract base for test-result parsers."""

    @abstractmethod
    def parse(self, content: bytes) -> ParsedResult:
        """Parse raw artifact ``content`` into a :class:`ParsedResult`.

        Implementations must raise :class:`app.core.exceptions.ParseError`
        when the content is malformed or unsupported.
        """
        raise NotImplementedError
