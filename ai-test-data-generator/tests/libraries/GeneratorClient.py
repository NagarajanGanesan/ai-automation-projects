"""Robot Framework keyword library for the AI Test Data Generator.

Wraps the FastAPI app in Starlette's ``TestClient`` so the Robot suites run
fully offline — no live server, no API key (the app falls back to the
deterministic rule-based engine). Each public method is exposed as a keyword.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any, Dict

from fastapi.testclient import TestClient

from app.main import create_app

# tests/libraries/GeneratorClient.py -> project root is two levels up.
_SAMPLE_REQUEST = (
    Path(__file__).resolve().parents[2] / "sample_data" / "sample_request.json"
)


class GeneratorClient:
    """Keywords for driving the generator API in tests."""

    ROBOT_LIBRARY_SCOPE = "GLOBAL"

    def __init__(self) -> None:
        self._client = TestClient(create_app())

    # -- HTTP calls -------------------------------------------------------
    def get_health(self):
        return self._client.get("/api/health")

    def post_generate(self, body: Dict[str, Any]):
        return self._client.post("/api/generate", json=body)

    def get_result(self, generation_id: str):
        return self._client.get(f"/api/result/{generation_id}")

    # -- response helpers -------------------------------------------------
    def status_code(self, response) -> int:
        return int(response.status_code)

    def json_body(self, response) -> Any:
        return response.json()

    # -- request fixtures -------------------------------------------------
    def load_sample_request(self) -> Dict[str, Any]:
        return json.loads(_SAMPLE_REQUEST.read_text(encoding="utf-8"))

    def with_empty_fields(self, body: Dict[str, Any]) -> Dict[str, Any]:
        clone = copy.deepcopy(body)
        clone["api_spec"]["fields"] = []
        return clone
