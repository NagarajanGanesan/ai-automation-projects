"""Application configuration.

Settings are loaded from environment variables (and an optional ``.env``
file) using Pydantic. Keeping configuration in a single, validated object
makes the rest of the codebase free of ``os.getenv`` calls and easy to test.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Project base directory: the analyzer package root (parent of ``app/``).
# Relative ``project_roots`` are resolved against this so discovery works the
# same regardless of the process' current working directory.
_BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """Strongly-typed application settings.

    All values can be overridden via environment variables. See
    ``.env.example`` for the full list.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- Service metadata -------------------------------------------------
    app_name: str = "AI Robot Framework Failure Analyzer"
    environment: str = Field(default="development")
    debug: bool = Field(default=False)

    # --- Anthropic / Claude ----------------------------------------------
    anthropic_api_key: str = Field(default="", description="Anthropic API key.")
    # Default to the latest, most capable model. Override per environment.
    claude_model: str = Field(default="claude-opus-4-8")
    claude_max_tokens: int = Field(default=8000, ge=256, le=128000)
    # Reasoning effort: low | medium | high | xhigh | max
    claude_effort: str = Field(default="high")
    # Request timeout (seconds) for the Anthropic client.
    claude_timeout_seconds: float = Field(default=120.0, gt=0)

    # --- Upload constraints ----------------------------------------------
    max_upload_bytes: int = Field(default=50 * 1024 * 1024)  # 50 MB
    allowed_upload_extensions: List[str] = Field(
        default_factory=lambda: [".xml", ".html"]
    )

    # --- CORS -------------------------------------------------------------
    cors_allow_origins: List[str] = Field(default_factory=lambda: ["*"])

    # --- Robot project auto-discovery ------------------------------------
    # Directories scanned (recursively) for Robot Framework ``output.xml``
    # files. Each match is exposed as a discoverable "project". Relative paths
    # resolve against the analyzer package root, so the defaults find the
    # sibling ``tests/`` projects out of the box; absolute paths point the
    # analyzer at ANY other repo. Override with the ``PROJECT_ROOTS`` env var.
    project_roots: List[str] = Field(
        default_factory=lambda: ["../tests", "sample_data"]
    )
    # Filename glob that identifies a machine-readable Robot result.
    output_glob: str = Field(default="output*.xml")
    # Directory names pruned during the scan (never descended into).
    scan_exclude_dirs: List[str] = Field(
        default_factory=lambda: [
            ".venv",
            "venv",
            "node_modules",
            ".git",
            "__pycache__",
            ".pytest_cache",
            "dryrun",  # robot --dryrun artifacts carry no real execution results
        ]
    )

    @property
    def ai_enabled(self) -> bool:
        """Whether a real Claude agent can be constructed."""
        return bool(self.anthropic_api_key.strip())

    @property
    def resolved_project_roots(self) -> List[Path]:
        """``project_roots`` as absolute paths, de-duplicated, existing only.

        Relative entries resolve against the analyzer package root so behaviour
        is independent of the current working directory.
        """
        resolved: List[Path] = []
        seen = set()
        for root in self.project_roots:
            path = Path(root)
            if not path.is_absolute():
                path = _BASE_DIR / path
            path = path.resolve()
            if path.is_dir() and path not in seen:
                seen.add(path)
                resolved.append(path)
        return resolved


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached :class:`Settings` instance.

    The cache guarantees a single settings object per process, which is the
    behaviour FastAPI dependency injection expects.
    """
    return Settings()
