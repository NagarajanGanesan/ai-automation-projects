"""FastAPI dependency providers.

Collaborators are built once and cached for the process lifetime. The
``GenerationService`` is assembled from its dependencies here, which is the
only composition-root in the application. Tests can override any of these
providers via ``app.dependency_overrides``.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Optional

from fastapi import Depends

from app.config import Settings, get_settings
from app.services.generation_service import GenerationService
from app.services.generator_agent import TestDataGenerator, build_generator
from app.services.storage import InMemoryResultStore, ResultStore

# Process-local singleton for the generator. It is built lazily from settings;
# the settings object is not hashable, so we cache the instance directly rather
# than via ``lru_cache`` keyed on ``Settings``.
_GENERATOR: Optional[TestDataGenerator] = None


@lru_cache(maxsize=1)
def get_store() -> ResultStore:
    return InMemoryResultStore()


def get_generator(settings: Settings = Depends(get_settings)) -> TestDataGenerator:
    global _GENERATOR
    if _GENERATOR is None:
        _GENERATOR = build_generator(settings)
    return _GENERATOR


def get_generation_service(
    settings: Settings = Depends(get_settings),
    generator: TestDataGenerator = Depends(get_generator),
    store: ResultStore = Depends(get_store),
) -> GenerationService:
    return GenerationService(
        generator=generator,
        store=store,
        default_count=settings.default_record_count,
        max_count=settings.max_record_count,
    )
