"""Deterministic, offline test-data engine.

This is the heart of the product's "always functional" guarantee: it generates
all six artifact categories purely from the structured ``FieldSpec`` constraints,
with no network access. It is fully deterministic, which keeps the unit tests
reproducible and gives users a reliable baseline even without an API key.

The Claude engine (see :mod:`app.services.generator_agent`) produces richer,
story-aware data; this engine produces correct, exhaustive, mechanical data.
"""

from __future__ import annotations

from typing import Any, Dict, List

from app.models.schemas import (
    APISpecification,
    ApiRequestPayload,
    BoundaryValue,
    CaseKind,
    EquivalencePartition,
    FieldSpec,
    FieldType,
    GeneratedTestData,
    GenerationRequest,
    TestRecord,
)
from app.utils import values
from app.utils.sql import build_seed_data

_JSON_HEADERS = {"Content-Type": "application/json", "Accept": "application/json"}


def generate(request: GenerationRequest, count: int) -> GeneratedTestData:
    """Generate the full artifact set for ``request`` (``count`` positives)."""
    spec = request.api_spec
    fields = spec.fields

    positive = _positive_records(spec, count)
    negative = _negative_records(spec)
    boundary = _boundary_values(fields)
    partitions = _equivalence_partitions(fields)
    payloads = _api_payloads(spec, positive, negative)

    table = request.table_name or _table_from_path(spec.path)
    seed = build_seed_data(table, [r.data for r in positive])

    notes = _notes(request)

    return GeneratedTestData(
        positive=positive,
        negative=negative,
        boundary_values=boundary,
        equivalence_partitions=partitions,
        api_payloads=payloads,
        seed_data=seed,
        notes=notes,
        model="rule-based",
        generated_by_ai=False,
    )


# -- positive --------------------------------------------------------------
def _positive_records(spec: APISpecification, count: int) -> List[TestRecord]:
    records: List[TestRecord] = []
    for i in range(count):
        data = {f.name: values.valid_value(f, i) for f in spec.fields}
        records.append(
            TestRecord(
                name=f"positive_{i + 1}",
                description="All fields valid and within constraints.",
                kind=CaseKind.POSITIVE,
                data=data,
                expected_valid=True,
                expected_status=spec.success_status,
            )
        )
    return records


# -- negative --------------------------------------------------------------
def _negative_records(spec: APISpecification) -> List[TestRecord]:
    """One record per distinct constraint violation, baseline otherwise valid."""
    baseline = {f.name: values.valid_value(f, 0) for f in spec.fields}
    records: List[TestRecord] = []

    def add(field: str, reason: str, mutate) -> None:
        data = dict(baseline)
        mutate(data)
        records.append(
            TestRecord(
                name=f"negative_{field}_{len(records) + 1}",
                description=f"Violates: {reason}",
                kind=CaseKind.NEGATIVE,
                data=data,
                expected_valid=False,
                expected_status=spec.error_status,
                violated_field=field,
                violation_reason=reason,
            )
        )

    for field in spec.fields:
        if field.required:
            add(field.name, "required field missing", lambda d, n=field.name: d.pop(n, None))

        if field.enum:
            bad = values.non_enum_value(field)
            add(field.name, "value not in allowed enum", lambda d, n=field.name, v=bad: d.__setitem__(n, v))

        below = values.below_min(field)
        if below is not None:
            add(field.name, f"below minimum ({field.minimum})", lambda d, n=field.name, v=below: d.__setitem__(n, v))
        above = values.above_max(field)
        if above is not None:
            add(field.name, f"above maximum ({field.maximum})", lambda d, n=field.name, v=above: d.__setitem__(n, v))

        short = values.too_short(field)
        if short is not None:
            add(field.name, f"shorter than min_length ({field.min_length})", lambda d, n=field.name, v=short: d.__setitem__(n, v))
        long_ = values.too_long(field)
        if long_ is not None:
            add(field.name, f"longer than max_length ({field.max_length})", lambda d, n=field.name, v=long_: d.__setitem__(n, v))

        if not field.enum:  # enum mismatch already covers wrong values
            mistype = values.invalid_type_value(field)
            if mistype is not None:
                add(field.name, f"wrong type for {field.type.value}", lambda d, n=field.name, v=mistype: d.__setitem__(n, v))

    return records


# -- boundary values -------------------------------------------------------
def _boundary_values(fields: List[FieldSpec]) -> List[BoundaryValue]:
    out: List[BoundaryValue] = []
    for f in fields:
        checks = [
            ("below_min", values.below_min(f), False, f"Just below minimum {f.minimum}."),
            ("at_min", values.at_min(f), True, f"Exactly at minimum {f.minimum}."),
            ("at_max", values.at_max(f), True, f"Exactly at maximum {f.maximum}."),
            ("above_max", values.above_max(f), False, f"Just above maximum {f.maximum}."),
            ("below_min_length", values.too_short(f), False, f"One char below min_length {f.min_length}."),
            ("at_min_length", values.at_min_length(f), True, f"Exactly min_length {f.min_length}."),
            ("at_max_length", values.at_max_length(f), True, f"Exactly max_length {f.max_length}."),
            ("above_max_length", values.too_long(f), False, f"One char above max_length {f.max_length}."),
        ]
        for boundary, value, valid, desc in checks:
            if value is not None:
                out.append(
                    BoundaryValue(
                        field=f.name,
                        boundary=boundary,
                        value=value,
                        expected_valid=valid,
                        description=desc,
                    )
                )
    return out


# -- equivalence partitions ------------------------------------------------
def _equivalence_partitions(fields: List[FieldSpec]) -> List[EquivalencePartition]:
    out: List[EquivalencePartition] = []

    def add(field: str, partition: str, valid: bool, value: Any, desc: str) -> None:
        out.append(
            EquivalencePartition(
                field=field,
                partition=partition,
                partition_class="valid" if valid else "invalid",
                representative_value=value,
                expected_valid=valid,
                description=desc,
            )
        )

    for f in fields:
        # The always-valid representative class.
        add(f.name, "valid", True, values.valid_value(f, 0), "A representative valid value.")

        if f.required:
            add(f.name, "missing", False, None, "Required field omitted.")

        if f.minimum is not None:
            add(f.name, "below_min", False, values.below_min(f), "Numbers below the minimum.")
        if f.maximum is not None:
            add(f.name, "above_max", False, values.above_max(f), "Numbers above the maximum.")
        if f.enum:
            add(f.name, "not_in_enum", False, values.non_enum_value(f), "Values outside the enum.")
        if f.min_length is not None and f.min_length > 0:
            add(f.name, "too_short", False, values.too_short(f), "Strings shorter than min_length.")
        if f.max_length is not None:
            add(f.name, "too_long", False, values.too_long(f), "Strings longer than max_length.")
        if f.type is FieldType.EMAIL:
            add(f.name, "malformed_email", False, values.invalid_type_value(f), "Strings that are not emails.")

    return out


# -- API payloads ----------------------------------------------------------
def _api_payloads(
    spec: APISpecification, positive: List[TestRecord], negative: List[TestRecord]
) -> List[ApiRequestPayload]:
    payloads: List[ApiRequestPayload] = []
    for rec in positive:
        payloads.append(
            ApiRequestPayload(
                name=rec.name,
                kind=CaseKind.POSITIVE,
                method=spec.method.upper(),
                path=spec.path,
                headers=dict(_JSON_HEADERS),
                body=rec.data,
                expected_status=spec.success_status,
            )
        )
    for rec in negative:
        payloads.append(
            ApiRequestPayload(
                name=rec.name,
                kind=CaseKind.NEGATIVE,
                method=spec.method.upper(),
                path=spec.path,
                headers=dict(_JSON_HEADERS),
                body=rec.data,
                expected_status=spec.error_status,
            )
        )
    return payloads


# -- helpers ---------------------------------------------------------------
def _table_from_path(path: str) -> str:
    segments = [s for s in (path or "").split("/") if s and not s.startswith("{")]
    return segments[-1] if segments else "test_table"


def _notes(request: GenerationRequest) -> str:
    parts = [
        "Generated by the deterministic rule-based engine "
        "(set ANTHROPIC_API_KEY for story-aware Claude generation)."
    ]
    if request.validation_rules:
        parts.append(
            f"{len(request.validation_rules)} cross-field/textual validation rule(s) "
            "are recorded but not auto-violated by the offline engine; the Claude "
            "engine crafts data for these."
        )
    return " ".join(parts)
