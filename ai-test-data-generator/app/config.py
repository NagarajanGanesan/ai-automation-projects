"""Application configuration.

Settings are loaded from environment variables (and an optional ``.env`` file)
using Pydantic. Keeping configuration in a single, validated object keeps the
rest of the codebase free of ``os.getenv`` calls and easy to test.
"""

from __future__ import annotations

from functools import lru_cache
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


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
    app_name: str = "AI Test Data Generator"
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

    # --- Generation defaults ---------------------------------------------
    # How many positive records to generate by default (overridable per request).
    default_record_count: int = Field(default=3, ge=1, le=100)
    # Hard cap so a single request can never ask for an unbounded amount of data.
    max_record_count: int = Field(default=50, ge=1, le=1000)

    # --- CORS -------------------------------------------------------------
    cors_allow_origins: List[str] = Field(default_factory=lambda: ["*"])

    @property
    def ai_enabled(self) -> bool:
        """Whether a real Claude agent can be constructed."""
        return bool(self.anthropic_api_key.strip())


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached :class:`Settings` instance (one per process)."""
    return Settings()
