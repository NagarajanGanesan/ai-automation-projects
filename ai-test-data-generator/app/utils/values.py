"""Deterministic value generation for the rule-based engine.

Every function here is a pure, deterministic helper: given a field spec (and an
index for variation), it returns a concrete value. Determinism is deliberate —
it makes the offline engine fully testable and reproducible, and avoids any
``random`` so the same spec always yields the same data.

Functions that return ``Optional`` return ``None`` when the operation does not
apply to the field (e.g. there is no "below minimum" value for a field without
a numeric minimum), which callers use to skip inapplicable cases.
"""

from __future__ import annotations

from typing import Any, Optional

from app.models.schemas import FieldSpec, FieldType

# A token guaranteed not to be a member of any realistic enum.
NOT_IN_ENUM = "__not_a_valid_option__"


def _string_of_length(seed: str, length: int) -> str:
    """Return a string of exactly ``length`` chars derived from ``seed``."""
    if length <= 0:
        return ""
    base = (seed or "x").replace(" ", "_")
    if len(base) >= length:
        return base[:length]
    return base + "x" * (length - len(base))


def _default_string_length(field: FieldSpec) -> int:
    """Pick a valid length honouring min/max length constraints."""
    lo = field.min_length if field.min_length is not None else 1
    hi = field.max_length if field.max_length is not None else max(lo, 8)
    # Prefer a comfortable mid value clamped into [lo, hi].
    target = max(lo, min(hi, 8))
    return max(target, lo)


def valid_value(field: FieldSpec, index: int = 0) -> Any:
    """Return a valid value for ``field``, varied by ``index``."""
    if field.example is not None and index == 0:
        return field.example
    if field.enum:
        return field.enum[index % len(field.enum)]

    ftype = field.type
    if ftype is FieldType.BOOLEAN:
        return index % 2 == 0
    if ftype in (FieldType.INTEGER, FieldType.NUMBER):
        lo = field.minimum if field.minimum is not None else 1
        hi = field.maximum if field.maximum is not None else lo + 1000
        value = lo + index
        if value > hi:
            value = hi
        return int(value) if ftype is FieldType.INTEGER else float(value)
    if ftype is FieldType.EMAIL:
        return f"user{index}@example.com"
    if ftype is FieldType.DATE:
        return f"2024-01-{(index % 28) + 1:02d}"
    if ftype is FieldType.DATETIME:
        return f"2024-01-{(index % 28) + 1:02d}T10:00:00Z"
    if ftype is FieldType.UUID:
        return f"{index:08d}-0000-4000-8000-000000000000"

    # STRING (and any unhandled type) — honour length constraints.
    seed = f"{field.name}{index}" if index else field.name
    return _string_of_length(seed, _default_string_length(field))


# -- numeric boundaries ----------------------------------------------------
def _num(field: FieldSpec, value: float) -> Any:
    return int(value) if field.type is FieldType.INTEGER else value


def at_min(field: FieldSpec) -> Optional[Any]:
    return _num(field, field.minimum) if field.minimum is not None else None


def below_min(field: FieldSpec) -> Optional[Any]:
    return _num(field, field.minimum - 1) if field.minimum is not None else None


def at_max(field: FieldSpec) -> Optional[Any]:
    return _num(field, field.maximum) if field.maximum is not None else None


def above_max(field: FieldSpec) -> Optional[Any]:
    return _num(field, field.maximum + 1) if field.maximum is not None else None


# -- string-length boundaries ---------------------------------------------
def at_min_length(field: FieldSpec) -> Optional[str]:
    if field.min_length is None:
        return None
    return _string_of_length(field.name, field.min_length)


def too_short(field: FieldSpec) -> Optional[str]:
    if field.min_length is None or field.min_length <= 0:
        return None
    return _string_of_length(field.name, field.min_length - 1)


def at_max_length(field: FieldSpec) -> Optional[str]:
    if field.max_length is None:
        return None
    return _string_of_length(field.name, field.max_length)


def too_long(field: FieldSpec) -> Optional[str]:
    if field.max_length is None:
        return None
    return _string_of_length(field.name, field.max_length + 1)


# -- invalid representatives ----------------------------------------------
def invalid_type_value(field: FieldSpec) -> Any:
    """Return a value of the wrong type/format for ``field``."""
    mapping = {
        FieldType.INTEGER: "not-a-number",
        FieldType.NUMBER: "not-a-number",
        FieldType.BOOLEAN: "not-a-boolean",
        FieldType.EMAIL: "not-an-email",
        FieldType.DATE: "31/13/2024",
        FieldType.DATETIME: "not-a-datetime",
        FieldType.UUID: "not-a-uuid",
        FieldType.STRING: 1234567,  # a number where a string is expected
    }
    return mapping.get(field.type, None)


def non_enum_value(field: FieldSpec) -> Optional[Any]:
    """Return a value guaranteed to be outside ``field.enum``."""
    if not field.enum:
        return None
    return NOT_IN_ENUM
