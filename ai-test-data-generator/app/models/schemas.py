"""Pydantic data models.

Three layers of models:

* **Input models** describing the generation request — a user story, an API
  specification (``FieldSpec`` list), and validation rules.
* **Output models** describing the generated artifacts — positive/negative test
  records, boundary values, equivalence partitions, API request payloads, and
  database seed data.
* **API models** used directly in request/response bodies.

Keeping them in one well-organised module gives every layer a single source of
truth for shapes and validation.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------
class FieldType(str, Enum):
    """The supported logical types for an API field.

    These drive deterministic value generation and the boundary / equivalence
    analysis in the rule-based engine.
    """

    STRING = "string"
    INTEGER = "integer"
    NUMBER = "number"
    BOOLEAN = "boolean"
    EMAIL = "email"
    DATE = "date"
    DATETIME = "datetime"
    UUID = "uuid"
    ENUM = "enum"


class CaseKind(str, Enum):
    """Classification of a generated test record."""

    POSITIVE = "positive"
    NEGATIVE = "negative"
    BOUNDARY = "boundary"


# ---------------------------------------------------------------------------
# Input models
# ---------------------------------------------------------------------------
class FieldSpec(BaseModel):
    """Specification of a single API field, including its constraints.

    Constraints double as the field-level validation rules the generator uses
    to derive valid values, invalid values, boundaries, and partitions.
    """

    name: str = Field(..., description="Field name as it appears in the payload.")
    type: FieldType = FieldType.STRING
    required: bool = True
    description: Optional[str] = None

    # Numeric constraints (integer / number).
    minimum: Optional[float] = None
    maximum: Optional[float] = None

    # String constraints.
    min_length: Optional[int] = Field(default=None, ge=0)
    max_length: Optional[int] = Field(default=None, ge=0)
    pattern: Optional[str] = Field(default=None, description="Regex the value must match.")

    # Enumerations / allowed values.
    enum: Optional[List[Any]] = None

    # An optional concrete example to anchor positive generation.
    example: Optional[Any] = None


class APISpecification(BaseModel):
    """A minimal, generator-friendly description of an API endpoint."""

    method: str = Field(default="POST", description="HTTP method, e.g. POST.")
    path: str = Field(default="/", description="Endpoint path, e.g. /api/v1/users.")
    description: Optional[str] = None
    fields: List[FieldSpec] = Field(default_factory=list)
    headers: Dict[str, str] = Field(
        default_factory=dict,
        description=(
            "Default request headers applied to every generated payload — e.g. "
            "gateway auth headers. For secrets, reference an environment variable "
            "with %{ENV_VAR} (Robot Framework resolves it at runtime) instead of "
            "hard-coding the value."
        ),
    )
    success_status: int = Field(default=201, description="Expected status for valid input.")
    error_status: int = Field(default=400, description="Expected status for invalid input.")


class ValidationRule(BaseModel):
    """A human-readable validation rule.

    Field-level constraints live on :class:`FieldSpec`; this captures
    additional or cross-field rules (e.g. "end_date must be after start_date").
    The rule-based engine treats these as documentation/expected-errors, while
    the Claude engine reasons over them to craft richer cases.
    """

    rule: str = Field(..., description="Plain-language rule.")
    fields: List[str] = Field(default_factory=list)
    error_message: Optional[str] = None


class GenerationRequest(BaseModel):
    """Body for ``POST /api/generate``."""

    user_story: str = Field(..., description="The user story / acceptance context.")
    api_spec: APISpecification
    validation_rules: List[ValidationRule] = Field(default_factory=list)
    table_name: Optional[str] = Field(
        default=None, description="Target table for seed data; derived from path if omitted."
    )
    count: Optional[int] = Field(
        default=None, ge=1, description="Number of positive records (defaults from settings)."
    )


# ---------------------------------------------------------------------------
# Output models
# ---------------------------------------------------------------------------
class TestRecord(BaseModel):
    """A single positive or negative test record."""

    name: str
    description: str
    kind: CaseKind
    data: Dict[str, Any] = Field(default_factory=dict)
    expected_valid: bool
    expected_status: int
    violated_field: Optional[str] = None
    violation_reason: Optional[str] = None


class BoundaryValue(BaseModel):
    """A boundary value for one field."""

    field: str
    boundary: str = Field(..., description="e.g. 'at_min', 'below_min', 'above_max'.")
    value: Any = None
    expected_valid: bool
    description: str


class EquivalencePartition(BaseModel):
    """One equivalence class for a field, with a representative value."""

    field: str
    partition: str = Field(..., description="Partition name, e.g. 'in_range'.")
    partition_class: str = Field(..., description="'valid' or 'invalid'.")
    representative_value: Any = None
    expected_valid: bool
    description: str


class ApiRequestPayload(BaseModel):
    """A concrete, ready-to-send API request."""

    name: str
    kind: CaseKind
    method: str
    path: str
    headers: Dict[str, str] = Field(default_factory=dict)
    body: Dict[str, Any] = Field(default_factory=dict)
    expected_status: int


class DatabaseSeedData(BaseModel):
    """Database seed rows plus generated INSERT statements."""

    table: str
    columns: List[str] = Field(default_factory=list)
    rows: List[Dict[str, Any]] = Field(default_factory=list)
    sql: List[str] = Field(default_factory=list)


class ExportArtifacts(BaseModel):
    """Ready-to-use test files for several automation stacks.

    Generated deterministically server-side from the API payloads, so they are
    always syntactically correct regardless of which engine produced the data.
    Each field is a complete, runnable file for one framework.
    """

    robot_framework: str = Field(..., description="A runnable Robot Framework suite (.robot).")
    pytest: str = Field(..., description="A runnable pytest module (requests-based).")
    playwright: str = Field(..., description="A runnable Playwright (@playwright/test) spec.")
    python: str = Field(..., description="A standalone Python script (no test framework).")


class GeneratedTestData(BaseModel):
    """The full set of generated artifacts."""

    positive: List[TestRecord] = Field(default_factory=list)
    negative: List[TestRecord] = Field(default_factory=list)
    boundary_values: List[BoundaryValue] = Field(default_factory=list)
    equivalence_partitions: List[EquivalencePartition] = Field(default_factory=list)
    api_payloads: List[ApiRequestPayload] = Field(default_factory=list)
    seed_data: DatabaseSeedData
    exports: Optional[ExportArtifacts] = None
    notes: Optional[str] = None
    model: Optional[str] = None
    generated_by_ai: bool = True


# ---------------------------------------------------------------------------
# API models
# ---------------------------------------------------------------------------
class GenerateResponse(BaseModel):
    """Returned by ``POST /api/generate``."""

    generation_id: str
    generated: GeneratedTestData


class HealthResponse(BaseModel):
    """Returned by ``GET /api/health``."""

    status: str = "ok"
    version: str
    ai_enabled: bool
