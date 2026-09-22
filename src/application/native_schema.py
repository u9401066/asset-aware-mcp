"""Complete native schemas, selected by operation or read in hash-pinned pages."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from src.domain.native_assets import NativeDocumentRequest
from src.domain.native_operations import operation_fields

INLINE_SCHEMA_MAX_CHARS = 6000


def compact_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """Omit prose annotations/null defaults while preserving validation keywords."""
    result: dict[str, Any] = {}
    for key, value in schema.items():
        if key in {"title", "description"} or (key == "default" and value is None):
            continue
        if key in {"properties", "$defs", "patternProperties", "dependentSchemas"}:
            result[key] = {name: compact_schema(node) for name, node in value.items()}
        elif key in {"anyOf", "oneOf", "allOf", "prefixItems"}:
            result[key] = [compact_schema(node) for node in value]
        elif key in {
            "items",
            "additionalProperties",
            "not",
            "if",
            "then",
            "else",
        } and isinstance(value, dict):
            result[key] = compact_schema(value)
        else:
            result[key] = value
    return result


def _non_null(schema: dict[str, Any]) -> dict[str, Any]:
    result = dict(schema)
    if "anyOf" in result:
        branches = [item for item in result.pop("anyOf") if item != {"type": "null"}]
        result.update(branches[0] if len(branches) == 1 else {"anyOf": branches})
    if result.get("type") == "array":
        result["minItems"] = max(1, result.get("minItems", 0))
    return result


def _references(node: Any) -> set[str]:
    if isinstance(node, list):
        return set().union(*(_references(item) for item in node))
    if not isinstance(node, dict):
        return set()
    references = set().union(*(_references(value) for value in node.values()))
    if isinstance(node.get("$ref"), str) and node["$ref"].startswith("#/$defs/"):
        references.add(node["$ref"].removeprefix("#/$defs/"))
    return references


def request_schema(for_op: str | None = None) -> dict[str, Any]:
    schema = compact_schema(NativeDocumentRequest.model_json_schema())
    if for_op is None:
        return schema
    fields = operation_fields(for_op)
    properties = {
        k: v
        for k, v in schema["properties"].items()
        if k in fields.required | fields.optional | {"op"}
    }
    properties["op"] = {"type": "string", "const": for_op}
    for name in fields.required:
        properties[name] = _non_null(properties[name])
    selected: dict[str, Any] = {
        "type": "object",
        "additionalProperties": False,
        "properties": properties,
        "required": ["op", *sorted(fields.required)],
    }
    if for_op in {
        "schema",
        "read_derivations",
        "verify_derivation",
        "read_ods",
        "read_ods_cell",
        "read_ods_dependencies",
    }:
        hash_field = (
            "schema_sha256"
            if for_op == "schema"
            else "ods_text_sha256"
            if for_op in {"read_ods", "read_ods_cell", "read_ods_dependencies"}
            else "derivations_sha256"
        )
        offset_field = "offset" if for_op == "verify_derivation" else "text_offset"
        selected["allOf"] = [
            {
                "if": {
                    "properties": {offset_field: {"minimum": 1}},
                    "required": [offset_field],
                },
                "then": {
                    "required": [hash_field],
                    "properties": {hash_field: _non_null(properties[hash_field])},
                },
            }
        ]
    _attach_definitions(selected, schema.get("$defs", {}))
    return selected


def _attach_definitions(schema: dict[str, Any], definitions: dict[str, Any]) -> None:
    selected: dict[str, Any] = {}
    pending = _references(schema)
    while pending:
        name = pending.pop()
        if name in selected:
            continue
        selected[name] = definitions[name]
        pending.update(_references(selected[name]) - selected.keys())
    if selected:
        schema["$defs"] = selected


def schema_text(schema: dict[str, Any]) -> tuple[str, str]:
    text = json.dumps(schema, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return text, hashlib.sha256(text.encode("utf-8")).hexdigest()


def schema_discovery(for_op: str | None) -> dict[str, Any]:
    schema = request_schema(for_op)
    text, digest = schema_text(schema)
    request: dict[str, Any] = {
        "op": "schema",
        "schema_sha256": digest,
        "text_offset": 0,
        "text_limit": 2000,
    }
    if for_op is not None:
        request["for_op"] = for_op
    inline = (
        len(json.dumps({"schema": schema}, ensure_ascii=False, indent=2))
        <= INLINE_SCHEMA_MAX_CHARS
    )
    return {
        "for_op": for_op,
        "schema_sha256": digest,
        "schema_chars": len(text),
        "schema_delivery": "inline" if inline else "paged",
        "schema_request": request,
        **({"schema": schema} if inline else {}),
    }


def read_schema(request: NativeDocumentRequest) -> dict[str, Any]:
    text, digest = schema_text(request_schema(request.for_op))
    if request.schema_sha256 is not None and request.schema_sha256 != digest:
        raise ValueError(
            "Native schema changed or scope differs; restart schema discovery"
        )
    start = min(request.text_offset, len(text))
    end = min(start + request.text_limit, len(text))
    # Escaped patterns/control characters can use six JSON characters per char.
    # Bound the encoded excerpt too, leaving room for the response envelope.
    while len(json.dumps(text[start:end], ensure_ascii=False)) > 8000:
        end = start + (end - start) // 2
    return {
        "success": True,
        "schema_version": "native-schema-page-v1",
        "for_op": request.for_op,
        "schema_sha256": digest,
        "text_excerpt": text[start:end],
        "text_length": len(text),
        "excerpt_char_range": [start, end],
        "next_text_offset": end if end < len(text) else None,
        "representation_complete": start == 0 and end == len(text),
        "serialization": "canonical-json; UTF-8 SHA-256",
    }
