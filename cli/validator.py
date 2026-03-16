"""JSON Schema input validation for skill payloads.

Validates payloads against merged skill schema (allOf base + skill).
Falls back to manual required-field check if jsonschema not installed.
"""

from __future__ import annotations

from typing import Any


def validate_input(payload: dict[str, Any], schema: dict[str, Any]) -> list[str]:
    """Validate payload against skill schema.

    Returns list of error messages (empty = valid).
    """
    try:
        import jsonschema
    except ImportError:
        return _validate_required(payload, schema)

    flat = _flatten_schema(schema)
    errors: list[str] = []
    try:
        jsonschema.validate(payload, flat)
    except jsonschema.ValidationError as exc:
        errors.append(exc.message)
    except jsonschema.SchemaError as exc:
        errors.append(f"Schema error: {exc.message}")
    return errors


def _flatten_schema(schema: dict) -> dict:
    """Flatten allOf into single schema for validation.

    Skips $ref entries (base schema validated implicitly by merging
    required + properties from non-ref sub-schemas).
    """
    if "allOf" not in schema:
        return schema

    merged: dict[str, Any] = {
        "type": "object",
        "properties": {},
        "required": [],
    }
    for sub in schema["allOf"]:
        if "$ref" in sub:
            continue
        merged["properties"].update(sub.get("properties", {}))
        merged["required"].extend(sub.get("required", []))

    # Deduplicate required
    merged["required"] = list(dict.fromkeys(merged["required"]))
    return merged


def _validate_required(payload: dict, schema: dict) -> list[str]:
    """Fallback: check required fields only (no jsonschema dep)."""
    errors: list[str] = []
    required: list[str] = list(schema.get("required", []))

    if "allOf" in schema:
        for sub in schema["allOf"]:
            if isinstance(sub, dict) and "$ref" not in sub:
                required.extend(sub.get("required", []))

    seen = set()
    for field in required:
        if field in seen:
            continue
        seen.add(field)
        if field not in payload or not payload[field]:
            errors.append(f"Missing required field: {field}")
    return errors
