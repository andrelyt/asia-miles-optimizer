"""Standard-library validation for the keywords used by repository schemas.

This is not a general JSON Schema implementation. Unsupported schema keywords
fail closed so a future contract cannot be silently ignored.
"""
from datetime import date, datetime
import json
import math
from pathlib import Path
import re

SCHEMA_DIR = Path(__file__).resolve().parents[1] / "schemas"
KEYWORDS = {
    "$schema", "$id", "title", "description", "type", "enum", "properties",
    "required", "additionalProperties", "items", "minItems", "uniqueItems",
    "minLength", "pattern", "minimum", "maximum", "format",
}


class ValidationError(ValueError):
    """Input violates the repository schema or a documented semantic invariant."""


def parse_date(value):
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        raise ValidationError("date must use YYYY-MM-DD")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValidationError("invalid date: " + value) from exc


def _matches(value, kind):
    if kind == "object":
        return isinstance(value, dict)
    if kind == "array":
        return isinstance(value, list)
    if kind == "string":
        return isinstance(value, str)
    if kind == "null":
        return value is None
    if kind == "boolean":
        return isinstance(value, bool)
    if kind == "integer":
        return (isinstance(value, int) and not isinstance(value, bool)) or (
            isinstance(value, float) and math.isfinite(value) and int(value) == value)
    raise ValidationError("unsupported schema type: " + str(kind))


def _validate(value, schema, path):
    unknown = set(schema) - KEYWORDS
    if unknown:
        raise ValidationError("unsupported schema keywords: " + ", ".join(sorted(unknown)))
    types = schema.get("type")
    if types is not None:
        types = types if isinstance(types, list) else [types]
        if not any(_matches(value, kind) for kind in types):
            raise ValidationError(path + ": expected " + "/".join(types))
    if "enum" in schema and value not in schema["enum"]:
        raise ValidationError(path + ": value outside enum")
    if isinstance(value, dict):
        for key in schema.get("required", []):
            if key not in value:
                raise ValidationError(path + ": missing " + key)
        properties = schema.get("properties", {})
        for key, child in value.items():
            if key in properties:
                _validate(child, properties[key], path + "." + key)
            elif schema.get("additionalProperties") is False:
                raise ValidationError(path + ": unexpected " + key)
    if isinstance(value, list):
        if len(value) < schema.get("minItems", 0):
            raise ValidationError(path + ": too few items")
        if schema.get("uniqueItems") and len({json.dumps(x, sort_keys=True) for x in value}) != len(value):
            raise ValidationError(path + ": duplicate items")
        if "items" in schema:
            for index, child in enumerate(value):
                _validate(child, schema["items"], f"{path}[{index}]")
    if isinstance(value, str):
        if len(value) < schema.get("minLength", 0):
            raise ValidationError(path + ": string too short")
        if "pattern" in schema and not re.search(schema["pattern"], value):
            raise ValidationError(path + ": pattern mismatch")
        if schema.get("format") == "date":
            parse_date(value)
        elif schema.get("format") == "date-time":
            if not re.fullmatch(r"\d{4}-\d{2}-\d{2}[Tt]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:[Zz]|[+-]\d{2}:\d{2})", value):
                raise ValidationError(path + ": expected timezone-aware RFC3339 date-time")
            try:
                datetime.fromisoformat(value.upper().replace("Z", "+00:00"))
            except ValueError as exc:
                raise ValidationError(path + ": invalid date-time") from exc
        elif "format" in schema:
            raise ValidationError("unsupported schema format: " + schema["format"])
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if isinstance(value, float) and not math.isfinite(value):
            raise ValidationError(path + ": non-finite number")
        if "minimum" in schema and value < schema["minimum"]:
            raise ValidationError(path + ": below minimum")
        if "maximum" in schema and value > schema["maximum"]:
            raise ValidationError(path + ": above maximum")


def validate(value, schema_name):
    schema = json.loads((SCHEMA_DIR / schema_name).read_text(encoding="utf-8"))
    _validate(value, schema, "$")
