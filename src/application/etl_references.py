"""Pure canonical ETL reference construction and locator verification."""

from __future__ import annotations

import hashlib
import json
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from src.domain.citation import EvidenceSpan

_ASSET_LOCATOR_VERSION = "asset-manifest-v1"


def display_line_range(start_line: int, end_line: int) -> str:
    if start_line < 0 or end_line < 0 or end_line < start_line:
        return "L?"
    return f"L{start_line + 1}-{end_line}"


def format_line_range(start_line: int | None, end_line: int | None) -> str | None:
    if (
        start_line is None
        or end_line is None
        or start_line < 0
        or end_line < start_line
    ):
        return None
    return display_line_range(start_line, end_line)


def coerce_range(value: Any) -> list[int | None] | None:
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        return None
    coerced: list[int | None] = []
    for item in value:
        if item is None:
            coerced.append(None)
        elif type(item) is int:
            coerced.append(item)
        else:
            return None
    return coerced


def asset_ref_from_span(span: EvidenceSpan) -> dict[str, Any]:
    """Build a self-verifying reference to the complete indexed span.

    ``quote``, its SHA-256 and the char/byte locator all describe the same
    evidence. Presentation layers may bound a serialized response, but an
    AssetRef must never silently replace the exact quote with a prefix while
    retaining the full-span hash and ranges.
    """
    quote = span.text
    ref: dict[str, Any] = {
        "source_type": "span",
        "doc_id": span.doc_id,
        "span_id": span.span_id,
        "block_id": span.block_id,
        "page": span.page,
        "source_revision_id": span.source_revision_id,
        "locator_version": span.locator_version,
        "locator_source_sha256": span.locator_source_sha256,
        "quote": quote,
        "quote_sha256": span.text_sha256,
        "excerpt": span.text[:200],
        "quote_chars": len(quote),
        "quote_truncated": False,
        "craap": span.craap.model_dump(exclude_none=True),
    }
    if span.asset_id:
        ref["asset_id"] = span.asset_id
    if span.line_start is not None and span.line_end is not None:
        ref["line_range"] = [span.line_start, span.line_end]
    if span.char_start is not None and span.char_end is not None:
        ref["char_range"] = [span.char_start, span.char_end]
    if span.byte_start is not None and span.byte_end is not None:
        ref["byte_range"] = [span.byte_start, span.byte_end]
    if span.bbox:
        ref["bbox"] = span.bbox
    return ref


def _asset_locator_payload(
    manifest: Any,
    asset_type: str,
    asset: Any,
) -> dict[str, Any]:
    return {
        "doc_id": manifest.doc_id,
        "source_pdf_sha256": getattr(manifest, "source_pdf_sha256", ""),
        "asset_type": asset_type,
        "asset_id": asset.id,
        "page": getattr(asset, "page", None),
        "line_start": getattr(asset, "line_start", None),
        "line_end": getattr(asset, "line_end", None),
        "source_block_id": getattr(asset, "source_block_id", ""),
        "source_order": getattr(asset, "source_order", 0),
        "section_id": getattr(asset, "section_id", ""),
        "section_title": getattr(asset, "section_title", ""),
    }


def _asset_locator_sha256(manifest: Any, asset_type: str, asset: Any) -> str:
    payload = _asset_locator_payload(manifest, asset_type, asset)
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()


def _asset_ref_from_manifest_asset(
    manifest: Any,
    asset_type: str,
    asset: Any,
) -> dict[str, Any]:
    ref: dict[str, Any] = {
        "source_type": asset_type,
        "doc_id": manifest.doc_id,
        "asset_id": asset.id,
        "page": getattr(asset, "page", None),
        "source_revision_id": getattr(manifest, "source_pdf_sha256", ""),
        "locator_version": _ASSET_LOCATOR_VERSION,
        "locator_source_sha256": _asset_locator_sha256(manifest, asset_type, asset),
        "label": getattr(asset, "caption", "") or asset.id,
        "excerpt": getattr(asset, "preview", "")
        or getattr(asset, "caption", "")
        or asset.id,
    }
    source_block_id = getattr(asset, "source_block_id", "")
    if source_block_id:
        ref["block_id"] = source_block_id
    line_start = getattr(asset, "line_start", None)
    line_end = getattr(asset, "line_end", None)
    if line_start is not None and line_end is not None:
        ref["line_range"] = [line_start, line_end]
    return ref


def _strict_json_equal(actual: Any, expected: Any) -> bool:
    """Compare locator values without Python's bool/int coercion."""
    if type(actual) is not type(expected):
        return False
    if isinstance(expected, list):
        return len(actual) == len(expected) and all(
            _strict_json_equal(actual_item, expected_item)
            for actual_item, expected_item in zip(actual, expected, strict=True)
        )
    if isinstance(expected, dict):
        return actual.keys() == expected.keys() and all(
            _strict_json_equal(actual[key], expected[key]) for key in expected
        )
    return bool(actual == expected)


def verify_span_reference(
    ref: dict[str, Any],
    span: EvidenceSpan | None,
) -> dict[str, Any]:
    """Verify a span AssetRef and return structured status."""
    if ref.get("source_type") != "span":
        return {
            "valid": False,
            "status": "unsupported",
            "issues": ["Only span-level AssetRef objects can be verified"],
        }

    doc_id = str(ref.get("doc_id") or "")
    span_id = str(ref.get("span_id") or "")
    if not doc_id or not span_id:
        return {
            "valid": False,
            "status": "invalid",
            "issues": ["Citation ref must include doc_id and span_id"],
        }

    if span is None:
        return {
            "valid": False,
            "status": "missing",
            "doc_id": doc_id,
            "span_id": span_id,
            "issues": [f"Citation span not found: {span_id}"],
        }

    issues: list[str] = []

    def _is_missing(value: Any) -> bool:
        return value is None or value == ""

    def require_equal(field: str, expected: Any) -> None:
        if field not in ref or _is_missing(ref.get(field)):
            issues.append(f"{field} missing")
        elif not _strict_json_equal(ref.get(field), expected):
            issues.append(f"{field} mismatch")

    def require_range(field: str, expected: list[int | None]) -> None:
        if field not in ref:
            issues.append(f"{field} missing")
        elif coerce_range(ref.get(field)) != expected:
            issues.append(f"{field} mismatch")

    require_equal("source_revision_id", span.source_revision_id)
    require_equal("locator_version", span.locator_version)
    if span.locator_source_sha256:
        require_equal("locator_source_sha256", span.locator_source_sha256)
    else:
        issues.append("indexed span missing locator_source_sha256")
    if span.block_id:
        require_equal("block_id", span.block_id)
    if span.page is not None:
        require_equal("page", span.page)
    if span.line_start is not None and span.line_end is not None:
        require_range("line_range", [span.line_start, span.line_end])
    if span.char_start is not None and span.char_end is not None:
        require_range("char_range", [span.char_start, span.char_end])
    if span.byte_start is not None and span.byte_end is not None:
        require_range("byte_range", [span.byte_start, span.byte_end])
    if span.bbox:
        require_equal("bbox", span.bbox)

    if "quote" not in ref:
        issues.append("quote missing")
    elif ref.get("quote") != span.text:
        issues.append("quote mismatch")
    require_equal("quote_sha256", span.text_sha256)
    if "quote_chars" not in ref:
        issues.append("quote_chars missing")
    elif (
        not isinstance(ref.get("quote_chars"), int)
        or isinstance(ref.get("quote_chars"), bool)
        or ref.get("quote_chars") != len(span.text)
    ):
        issues.append("quote_chars mismatch")
    if "quote_truncated" not in ref:
        issues.append("quote_truncated missing")
    elif ref.get("quote_truncated") is not False:
        issues.append("quote_truncated mismatch")

    return {
        "valid": not issues,
        "status": "verified" if not issues else "mismatch",
        "doc_id": doc_id,
        "span_id": span_id,
        "page": span.page,
        "line_range": [span.line_start, span.line_end],
        "line_display": format_line_range(span.line_start, span.line_end),
        "char_range": [span.char_start, span.char_end],
        "byte_range": [span.byte_start, span.byte_end],
        "text_sha256": span.text_sha256,
        "source_revision_id": span.source_revision_id,
        "locator_version": span.locator_version,
        "locator_source_sha256": span.locator_source_sha256,
        "issues": issues,
    }


def verify_asset_reference(
    ref: dict[str, Any],
    manifest: Any,
) -> dict[str, Any]:
    source_type = ref.get("source_type")
    if ref.get("canonical_asset_ref") is False:
        return {
            "valid": False,
            "status": "unsupported",
            "issues": ["Non-canonical AssetRef previews cannot be health-checked"],
        }
    if source_type not in {"table", "figure"}:
        return {
            "valid": False,
            "status": "unsupported",
            "issues": ["Only span/table/figure AssetRef objects can be health-checked"],
        }
    doc_id = ref.get("doc_id")
    asset_id = ref.get("asset_id")
    if (
        type(doc_id) is not str
        or not doc_id
        or type(asset_id) is not str
        or not asset_id
    ):
        return {
            "valid": False,
            "status": "invalid",
            "issues": ["Asset ref must include doc_id and asset_id"],
        }
    if manifest is None:
        return {
            "valid": False,
            "status": "missing",
            "doc_id": doc_id,
            "asset_id": asset_id,
            "issues": [f"Document manifest not found: {doc_id}"],
        }
    asset = (
        manifest.assets.find_table(asset_id)
        if source_type == "table"
        else manifest.assets.find_figure(asset_id)
    )
    if asset is None:
        return {
            "valid": False,
            "status": "missing",
            "doc_id": doc_id,
            "asset_id": asset_id,
            "issues": [f"{source_type} asset not found: {asset_id}"],
        }
    issues: list[str] = []

    def require_equal(field: str, expected: Any) -> None:
        if field not in ref:
            issues.append(f"{field} missing")
        elif not _strict_json_equal(ref.get(field), expected):
            issues.append(f"{field} mismatch")

    require_equal("doc_id", getattr(manifest, "doc_id", ""))
    require_equal("asset_id", getattr(asset, "id", ""))
    require_equal("source_revision_id", getattr(manifest, "source_pdf_sha256", ""))
    require_equal("locator_version", _ASSET_LOCATOR_VERSION)
    expected_locator = _asset_locator_sha256(manifest, source_type, asset)
    require_equal("locator_source_sha256", expected_locator)
    require_equal("page", getattr(asset, "page", None))

    expected_block_id = getattr(asset, "source_block_id", "")
    if expected_block_id:
        require_equal("block_id", expected_block_id)
    elif "block_id" in ref and not _strict_json_equal(
        ref.get("block_id"), expected_block_id
    ):
        issues.append("block_id mismatch")

    expected_line_range = [
        getattr(asset, "line_start", None),
        getattr(asset, "line_end", None),
    ]
    if all(value is not None for value in expected_line_range):
        if "line_range" not in ref:
            issues.append("line_range missing")
        elif coerce_range(ref.get("line_range")) != expected_line_range:
            issues.append("line_range mismatch")
    elif (
        "line_range" in ref
        and coerce_range(ref.get("line_range")) != expected_line_range
    ):
        issues.append("line_range mismatch")
    return {
        "valid": not issues,
        "status": "verified" if not issues else "mismatch",
        "doc_id": doc_id,
        "asset_id": asset_id,
        "source_type": source_type,
        "page": getattr(asset, "page", None),
        "line_range": [
            getattr(asset, "line_start", None),
            getattr(asset, "line_end", None),
        ],
        "source_revision_id": getattr(manifest, "source_pdf_sha256", ""),
        "locator_version": _ASSET_LOCATOR_VERSION,
        "locator_source_sha256": expected_locator,
        "issues": issues,
    }
