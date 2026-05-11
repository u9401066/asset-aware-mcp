"""
Document Tools - ETL + 文件管理 MCP 工具

包含：
- parse_pdf_structure: Marker 結構化解析
- search_source_location: 來源位置搜尋
- ingest_documents: PDF 文件攝入
- list_documents: 列出所有文件
- delete_document: 刪除已攝入的 PDF 文件及本地 artifacts
- convert_pdf_to_docx: 將 PDF 內容層重建為 DOCX
- convert_pdf_to_pptx: 將 PDF Markdown 重建為可編輯 PPTX
- inspect_document_manifest: 查看文件 Manifest
- fetch_document_asset: 擷取文件資產
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import TYPE_CHECKING, Any

from mcp.types import ImageContent, TextContent

from src.application.document_service import normalize_page_ranges
from src.application.output_paths import (
    resolve_document_output_path,
)
from src.presentation.dependencies import (
    asset_service,
    document_service,
    get_marker_extractor,
    job_service,
    layout_visualizer,
    pdf_extractor,
    repository,
    segmentation_service,
)
from src.presentation.mcp_app import mcp
from src.presentation.mcp_context import (
    create_subrange_progress_callback,
    log_message,
    report_progress,
)
from src.presentation.tools.citation_support import (
    asset_ref_from_span,
    coerce_range,
    display_line_range,
    format_line_range,
    load_citation_status,
    load_or_build_evidence_spans,
)
from src.presentation.tools.conversion_job_support import (
    conversion_result_payload,
    create_conversion_job_response,
)

if TYPE_CHECKING:
    from mcp.server.fastmcp import Context
else:
    Context = Any

_FOAM_INDEX_START = "<!-- asset-aware:evidence-index:start -->"
_FOAM_INDEX_END = "<!-- asset-aware:evidence-index:end -->"
_FOAM_ASSET_INDEX_START = "<!-- asset-aware:asset-index:start -->"
_FOAM_ASSET_INDEX_END = "<!-- asset-aware:asset-index:end -->"
_ASSET_LOCATOR_VERSION = "asset-manifest-v1"


def _normalize_op(op: str) -> str:
    return op.strip().lower().replace("-", "_")


def _unsupported_document_op(kind: str, op: str, allowed: set[str]) -> str:
    allowed_ops = ", ".join(sorted(allowed))
    return f"Unsupported {kind} op `{op}`. Supported operations: {allowed_ops}."


def _missing_document_param(name: str) -> str:
    return f"Missing required parameter: {name} is required."


def _filter_evidence_spans(
    spans: list[Any],
    *,
    query: str = "",
    span_id: str = "",
    span_kinds: list[str] | None = None,
) -> list[Any]:
    filtered = spans
    if span_id:
        filtered = [span for span in filtered if span.span_id == span_id]
    if query:
        query_lower = query.lower()
        filtered = [span for span in filtered if query_lower in span.text.lower()]
    if span_kinds:
        allowed_kinds = {kind.lower() for kind in span_kinds}
        filtered = [
            span for span in filtered if span.span_kind.lower() in allowed_kinds
        ]
    return filtered


def _foam_anchor_id(span_id: str) -> str:
    """Return a Foam-safe block anchor id derived from a stable span id."""
    cleaned = re.sub(r"[^A-Za-z0-9-]+", "-", span_id.replace("_", "-")).strip("-")
    cleaned = cleaned.lower() or "span"
    if not cleaned.startswith("spn-"):
        cleaned = f"spn-{cleaned}"
    return cleaned


def _claim_anchor_id(span_id: str) -> str:
    """Return a Foam-safe claim candidate anchor derived from a span id."""
    cleaned = _foam_anchor_id(span_id)
    if cleaned.startswith("spn-"):
        cleaned = "clm-" + cleaned[4:]
    elif not cleaned.startswith("clm-"):
        cleaned = f"clm-{cleaned}"
    return cleaned


def _claim_draft_from_span_text(text: str, limit: int = 320) -> str:
    """Build a non-inventive claim draft from the exact evidence quote."""
    compact = re.sub(r"\s+", " ", text).strip()
    if len(compact) <= limit:
        return compact
    return compact[: limit - 1].rstrip() + "…"


def _foam_scalar(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    return json.dumps(str(value), ensure_ascii=False)


def _foam_frontmatter_lines(frontmatter: dict[str, Any]) -> list[str]:
    lines = ["---"]
    for key, value in frontmatter.items():
        if value is None or value == "":
            continue
        if isinstance(value, list):
            rendered = ", ".join(_foam_scalar(item) for item in value)
            lines.append(f"{key}: [{rendered}]")
        else:
            lines.append(f"{key}: {_foam_scalar(value)}")
    lines.append("---")
    return lines


def _foam_quote_lines(text: str) -> list[str]:
    lines = text.splitlines() or [""]
    return [f"> {line}" if line else ">" for line in lines]


def _foam_slug(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9-]+", "-", value.strip().lower()).strip("-")
    return slug or "evidence"


def _foam_asset_anchor_id(asset_type: str, asset_id: str) -> str:
    prefix = "fig" if asset_type == "figure" else "tab"
    cleaned = re.sub(r"[^A-Za-z0-9-]+", "-", asset_id.replace("_", "-")).strip("-")
    cleaned = cleaned.lower() or prefix
    if not cleaned.startswith(f"{prefix}-"):
        cleaned = f"{prefix}-{cleaned}"
    return cleaned


def _resolve_foam_write_paths(
    *,
    wiki_root: str,
    output_path: str,
    index_path: str,
    doc_id: str,
    citation_key: str,
) -> tuple[Path, Path, Path]:
    if not wiki_root:
        raise ValueError("wiki_root is required for Foam file writes")
    root = Path(wiki_root).expanduser().resolve()
    default_name = _foam_slug(citation_key or doc_id)
    target = (
        Path(output_path).expanduser()
        if output_path
        else Path("evidence") / (f"{default_name}-evidence.md")
    )
    index = Path(index_path).expanduser() if index_path else Path("Evidence Index.md")
    if not target.is_absolute():
        target = root / target
    if not index.is_absolute():
        index = root / index
    target = target.resolve()
    index = index.resolve()
    for candidate in (target, index):
        if candidate != root and root not in candidate.parents:
            raise ValueError(f"Foam output path escapes wiki_root: {candidate}")
    return root, target, index


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


def _foam_entry_metadata(
    entry: dict[str, Any],
    *,
    citation_key: str = "",
) -> dict[str, Any]:
    anchor_id = _foam_anchor_id(str(entry.get("span_id") or ""))
    source_ref = citation_key.strip() or str(entry.get("doc_id") or "")
    verification = entry.get("verification") or {}
    frontmatter = {
        "title": f"Evidence {entry.get('span_id')}",
        "type": "evidence",
        "tags": ["asset-aware", "evidence"],
        "source_doc_id": entry.get("doc_id"),
        "source_revision_id": entry.get("source_revision_id"),
        "span_id": entry.get("span_id"),
        "block_id": entry.get("block_id"),
        "asset_id": entry.get("asset_id"),
        "page": entry.get("page"),
        "line_start": (entry.get("line_range") or [None, None])[0],
        "line_end": (entry.get("line_range") or [None, None])[1],
        "char_start": (entry.get("char_range") or [None, None])[0],
        "char_end": (entry.get("char_range") or [None, None])[1],
        "byte_start": (entry.get("byte_range") or [None, None])[0],
        "byte_end": (entry.get("byte_range") or [None, None])[1],
        "text_sha256": entry.get("text_sha256"),
        "locator_source_sha256": entry.get("locator_source_sha256"),
        "verified": bool(verification.get("valid")),
    }
    return {
        "anchor_id": anchor_id,
        "block_anchor": f"^{anchor_id}",
        "wikilink": f"[[{source_ref}#^{anchor_id}]]" if source_ref else "",
        "embed": f"![[{source_ref}#^{anchor_id}]]" if source_ref else "",
        "frontmatter": frontmatter,
    }


def _verify_span_ref_payload(ref: dict[str, Any]) -> dict[str, Any]:
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

    spans = load_or_build_evidence_spans(repository, doc_id)
    span = next((item for item in spans if item.span_id == span_id), None)
    if span is None:
        return {
            "valid": False,
            "status": "missing",
            "doc_id": doc_id,
            "span_id": span_id,
            "issues": [f"Citation span not found: {span_id}"],
        }

    issues: list[str] = []
    if ref.get("source_revision_id") != span.source_revision_id:
        issues.append("source_revision_id mismatch")
    if ref.get("locator_version") != span.locator_version:
        issues.append("locator_version mismatch")
    if (
        "locator_source_sha256" in ref
        and ref.get("locator_source_sha256") != span.locator_source_sha256
    ):
        issues.append("locator_source_sha256 mismatch")
    if "block_id" in ref and ref.get("block_id") != span.block_id:
        issues.append("block_id mismatch")
    if "page" in ref and ref.get("page") != span.page:
        issues.append("page mismatch")
    if "line_range" in ref and coerce_range(ref.get("line_range")) != [
        span.line_start,
        span.line_end,
    ]:
        issues.append("line_range mismatch")
    if "char_range" in ref and coerce_range(ref.get("char_range")) != [
        span.char_start,
        span.char_end,
    ]:
        issues.append("char_range mismatch")
    if "byte_range" in ref and coerce_range(ref.get("byte_range")) != [
        span.byte_start,
        span.byte_end,
    ]:
        issues.append("byte_range mismatch")
    if "bbox" in ref and ref.get("bbox") != span.bbox:
        issues.append("bbox mismatch")

    quote = str(ref.get("quote") or "")
    quote_sha256 = str(ref.get("quote_sha256") or "")
    if quote and quote not in span.text:
        issues.append("quote is not contained in indexed span text")
    if quote_sha256:
        expected = hashlib.sha256((quote or span.text).encode("utf-8")).hexdigest()
        if quote_sha256 != expected and quote_sha256 != span.text_sha256:
            issues.append("quote_sha256 mismatch")

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


def _citation_bundle_entry(
    span: Any,
    *,
    include_verification: bool,
    citation_key: str = "",
) -> dict[str, Any]:
    ref = asset_ref_from_span(span)
    entry: dict[str, Any] = {
        "doc_id": span.doc_id,
        "span_id": span.span_id,
        "span_kind": span.span_kind,
        "source_type": span.source_type,
        "block_id": span.block_id,
        "asset_id": span.asset_id,
        "page": span.page,
        "line_range": [span.line_start, span.line_end],
        "line_display": format_line_range(span.line_start, span.line_end),
        "char_range": [span.char_start, span.char_end],
        "byte_range": [span.byte_start, span.byte_end],
        "bbox": span.bbox,
        "source_revision_id": span.source_revision_id,
        "locator_version": span.locator_version,
        "locator_source_sha256": span.locator_source_sha256,
        "text_sha256": span.text_sha256,
        "normalized_text_sha256": span.normalized_text_sha256,
        "quote": span.text,
        "context_before": span.context_before,
        "context_after": span.context_after,
        "section_hierarchy": span.section_hierarchy,
        "extraction_backend": span.extraction_backend,
        "craap": span.craap.model_dump(exclude_none=True),
        "asset_ref": ref,
    }
    if include_verification:
        entry["verification"] = _verify_span_ref_payload(ref)
    entry["foam"] = _foam_entry_metadata(entry, citation_key=citation_key)
    return entry


def _format_citation_bundle(payload: dict[str, Any]) -> str:
    if not payload.get("success"):
        return str(payload.get("error") or "Citation bundle failed")

    lines = [
        f"# Citation Bundle: {payload['doc_id']}",
        "",
        f"**Bundle version:** `{payload['bundle_version']}`",
        f"**Returned:** {payload['returned']}/{payload['matched_count']} spans",
    ]
    if payload.get("query"):
        lines.append(f"**Query:** `{payload['query']}`")
    lines.append("")

    for index, entry in enumerate(payload["entries"], 1):
        verification = entry.get("verification") or {}
        status = verification.get("status", "not_verified")
        issues = verification.get("issues") or []
        quote = entry["quote"][:500] + ("..." if len(entry["quote"]) > 500 else "")
        lines.extend(
            [
                f"## Evidence {index}: `{entry['span_id']}`",
                f"- **Kind:** {entry['span_kind']}",
                f"- **Block:** `{entry['block_id']}`",
                f"- **Page:** {entry['page'] or '?'}",
                f"- **Lines:** {entry['line_display'] or '?'}",
                f"- **Chars:** {entry['char_range'][0]}-{entry['char_range'][1]}",
                f"- **SHA256:** `{entry['text_sha256']}`",
                f"- **Verification:** {status}",
            ]
        )
        if issues:
            lines.append(f"- **Issues:** {', '.join(issues)}")
        lines.extend(
            [
                "",
                f"> {quote}",
                "",
                "AssetRef:",
                "```json",
                json.dumps(entry["asset_ref"], ensure_ascii=False, indent=2),
                "```",
                "",
            ]
        )

    return "\n".join(lines)


def _format_foam_evidence_pack(payload: dict[str, Any]) -> str:
    if not payload.get("success"):
        return str(payload.get("error") or "Citation bundle failed")

    frontmatter = {
        "title": f"Evidence pack: {payload['doc_id']}",
        "type": "evidence_pack",
        "tags": ["asset-aware", "evidence", "foam"],
        "source_doc_id": payload["doc_id"],
        "bundle_version": payload["bundle_version"],
        "query": payload.get("query") or "",
        "matched_count": payload.get("matched_count", 0),
        "returned": payload.get("returned", 0),
    }
    lines = _foam_frontmatter_lines(frontmatter)
    lines.extend(
        [
            "",
            f"# Evidence Pack: {payload['doc_id']}",
            "",
        ]
    )
    if payload.get("query"):
        lines.extend([f"`query`: {payload['query']}", ""])

    for index, entry in enumerate(payload["entries"], 1):
        foam = entry.get("foam") or {}
        verification = entry.get("verification") or {}
        status = verification.get("status", "not_verified")
        issues = verification.get("issues") or []
        lines.extend(
            [
                f"## Evidence {index}: `{entry['span_id']}`",
                "",
                f"- `foam_anchor`: `{foam.get('block_anchor', '')}`",
                f"- `wikilink`: `{foam.get('wikilink', '')}`",
                f"- `embed`: `{foam.get('embed', '')}`",
                f"- `verification`: `{status}`",
                f"- `source_revision_id`: `{entry['source_revision_id']}`",
                f"- `locator_source_sha256`: `{entry['locator_source_sha256']}`",
                f"- `text_sha256`: `{entry['text_sha256']}`",
                f"- `page`: {entry['page'] or '?'}",
                f"- `lines`: {entry['line_display'] or '?'}",
                "",
            ]
        )
        if issues:
            lines.extend([f"- `issues`: {', '.join(issues)}", ""])
        lines.extend(_foam_quote_lines(str(entry.get("quote") or "")))
        lines.extend(
            [
                "",
                str(foam.get("block_anchor") or ""),
                "",
                "```json",
                json.dumps(entry["asset_ref"], ensure_ascii=False, indent=2),
                "```",
                "",
            ]
        )

    return "\n".join(lines).rstrip() + "\n"


def _claim_promotion_entry(span: Any, *, citation_key: str = "") -> dict[str, Any]:
    evidence = _citation_bundle_entry(
        span,
        include_verification=True,
        citation_key=citation_key,
    )
    verification = evidence.get("verification") or {}
    claim_anchor = _claim_anchor_id(span.span_id)
    source_ref = _foam_slug(citation_key or span.doc_id)
    return {
        "doc_id": span.doc_id,
        "claim_id": claim_anchor,
        "span_id": span.span_id,
        "block_id": span.block_id,
        "page": span.page,
        "line_display": format_line_range(span.line_start, span.line_end),
        "claim_text": _claim_draft_from_span_text(span.text),
        "claim_text_source": "exact_evidence_quote",
        "requires_verification": True,
        "verified": bool(verification.get("valid")),
        "promotion_status": "ready" if verification.get("valid") else "blocked",
        "verification": verification,
        "asset_ref": evidence["asset_ref"],
        "evidence": evidence,
        "foam": {
            "block_anchor": f"^{claim_anchor}",
            "wikilink": f"[[{source_ref}#^{claim_anchor}]]",
            "evidence_wikilink": (evidence.get("foam") or {}).get("wikilink", ""),
        },
    }


def _claim_promotion_payload(
    *,
    doc_id: str,
    query: str,
    span_id: str,
    span_kinds: list[str] | None,
    limit: int,
    citation_key: str,
) -> dict[str, Any]:
    spans = load_or_build_evidence_spans(repository, doc_id)
    if not spans:
        status = load_citation_status(repository, doc_id) or {}
        reason = str(status.get("reason") or "").strip()
        error = (
            f"No citation-ready evidence spans found for doc_id: {doc_id}. {reason}"
            if reason
            else (
                f"Citation index not found for doc_id: {doc_id}. "
                "Run ingest_documents again or ensure blocks.json/full markdown exist."
            )
        )
        return {
            "success": False,
            "doc_id": doc_id,
            "workflow_version": "claim-promotion-v1",
            "error": error,
        }

    filtered = _filter_evidence_spans(
        spans,
        query=query,
        span_id=span_id,
        span_kinds=span_kinds,
    )
    if not filtered:
        target = span_id or query
        return {
            "success": False,
            "doc_id": doc_id,
            "workflow_version": "claim-promotion-v1",
            "error": f"No evidence spans found for `{target}` in doc_id: {doc_id}",
        }

    bounded_limit = max(1, min(limit, 25))
    entries = [
        _claim_promotion_entry(span, citation_key=citation_key)
        for span in filtered[:bounded_limit]
    ]
    return {
        "success": True,
        "workflow_version": "claim-promotion-v1",
        "doc_id": doc_id,
        "query": query,
        "span_id": span_id,
        "span_kinds": span_kinds or [],
        "citation_key": citation_key,
        "matched_count": len(filtered),
        "returned": len(entries),
        "verification_required": True,
        "entries": entries,
    }


def _format_claim_promotion_markdown(payload: dict[str, Any]) -> str:
    if not payload.get("success"):
        return str(payload.get("error") or "Claim promotion failed")

    lines = [
        f"# Claim Promotion Candidates: {payload['doc_id']}",
        "",
        f"**Workflow version:** `{payload['workflow_version']}`",
        f"**Returned:** {payload['returned']}/{payload['matched_count']} candidates",
        "**Rule:** Promotion is blocked unless verification is valid.",
        "",
    ]
    if payload.get("query"):
        lines.extend([f"**Query:** `{payload['query']}`", ""])

    for index, entry in enumerate(payload["entries"], 1):
        verification = entry.get("verification") or {}
        issues = verification.get("issues") or []
        lines.extend(
            [
                f"## Candidate {index}: `{entry['claim_id']}`",
                f"- **Status:** {entry['promotion_status']}",
                f"- **Verified:** {entry['verified']}",
                f"- **Span:** `{entry['span_id']}`",
                f"- **Block:** `{entry['block_id']}`",
                f"- **Page:** {entry['page'] or '?'}",
                f"- **Lines:** {entry['line_display'] or '?'}",
                f"- **Evidence link:** {(entry.get('foam') or {}).get('evidence_wikilink', '')}",
            ]
        )
        if issues:
            lines.append(f"- **Issues:** {', '.join(issues)}")
        lines.extend(["", f"> {entry['claim_text']}", ""])

    return "\n".join(lines)


def _format_foam_claim_promotion_pack(payload: dict[str, Any]) -> str:
    if not payload.get("success"):
        return str(payload.get("error") or "Claim promotion failed")

    frontmatter = {
        "title": f"Claim promotion candidates: {payload['doc_id']}",
        "type": "claim_promotion_pack",
        "tags": ["asset-aware", "evidence", "claims", "foam"],
        "source_doc_id": payload["doc_id"],
        "workflow_version": payload["workflow_version"],
        "query": payload.get("query") or "",
        "matched_count": payload.get("matched_count", 0),
        "returned": payload.get("returned", 0),
        "verification_required": True,
    }
    lines = _foam_frontmatter_lines(frontmatter)
    lines.extend(
        [
            "",
            f"# Claim Promotion Candidates: {payload['doc_id']}",
            "",
            "> Promotion is blocked unless verification is valid.",
            "",
        ]
    )

    for index, entry in enumerate(payload["entries"], 1):
        foam = entry.get("foam") or {}
        verification = entry.get("verification") or {}
        issues = verification.get("issues") or []
        lines.extend(
            [
                f"## Claim Candidate {index}: `{entry['claim_id']}`",
                "",
                f"- `foam_anchor`: `{foam.get('block_anchor', '')}`",
                f"- `wikilink`: `{foam.get('wikilink', '')}`",
                f"- `evidence`: `{foam.get('evidence_wikilink', '')}`",
                f"- `promotion_status`: `{entry['promotion_status']}`",
                f"- `verified`: `{str(entry['verified']).lower()}`",
                f"- `span_id`: `{entry['span_id']}`",
                f"- `page`: {entry['page'] or '?'}",
                f"- `lines`: {entry['line_display'] or '?'}",
                "",
                "### Claim Draft",
                "",
                f"> {entry['claim_text']}",
                "",
            ]
        )
        if issues:
            lines.extend([f"- `issues`: {', '.join(issues)}", ""])
        verification_payload = {
            "verification": verification,
            "evidence": entry.get("evidence") or {},
        }
        lines.extend(
            [
                str(foam.get("block_anchor") or ""),
                "",
                "### AssetRef",
                "",
                "```json",
                json.dumps(entry["asset_ref"], ensure_ascii=False, indent=2),
                "```",
                "",
                "### Verification Payload",
                "",
                "```json",
                json.dumps(verification_payload, ensure_ascii=False, indent=2),
                "```",
                "",
            ]
        )

    return "\n".join(lines).rstrip() + "\n"


def _write_foam_claim_promotion_pack(
    payload: dict[str, Any],
    *,
    wiki_root: str,
    output_path: str,
    index_path: str,
    citation_key: str,
    update_index: bool,
    overwrite: bool,
) -> dict[str, Any]:
    blocked = [
        entry
        for entry in payload.get("entries", [])
        if not (entry.get("verification") or {}).get("valid")
    ]
    if blocked:
        return {
            "success": False,
            "doc_id": payload.get("doc_id"),
            "error": "Claim promotion write blocked: every candidate must verify first.",
            "blocked_count": len(blocked),
            "blocked_claim_ids": [entry.get("claim_id") for entry in blocked],
        }

    if not output_path:
        default_name = _foam_slug(citation_key or str(payload.get("doc_id") or "doc"))
        output_path = str(Path("evidence") / f"{default_name}-claims.md")
    root, target, index = _resolve_foam_write_paths(
        wiki_root=wiki_root,
        output_path=output_path,
        index_path=index_path,
        doc_id=str(payload.get("doc_id") or ""),
        citation_key=citation_key,
    )
    markdown = _format_foam_claim_promotion_pack(payload)
    _write_foam_text(target, markdown, overwrite=overwrite)
    index_written = False
    if update_index:
        _update_foam_index(index, payload, target)
        index_written = True
    return {
        "success": True,
        "operation": "foam_claim_promotion_write",
        "wiki_root": str(root),
        "output_path": str(target),
        "index_path": str(index) if index_written else "",
        "index_updated": index_written,
        "doc_id": payload.get("doc_id"),
        "returned": payload.get("returned", 0),
        "matched_count": payload.get("matched_count", 0),
        "wikilinks": [
            (entry.get("foam") or {}).get("wikilink", "")
            for entry in payload.get("entries", [])
        ],
    }


def _format_foam_asset_note(
    manifest: Any,
    asset_type: str,
    asset: Any,
    *,
    citation_key: str = "",
) -> tuple[str, dict[str, Any]]:
    anchor_id = _foam_asset_anchor_id(asset_type, asset.id)
    source_ref = f"{_foam_slug(citation_key or manifest.doc_id)}-{_foam_slug(asset.id)}"
    asset_ref = _asset_ref_from_manifest_asset(manifest, asset_type, asset)
    frontmatter = {
        "title": f"{asset_type.title()} {asset.id}",
        "type": f"{asset_type}_evidence",
        "tags": ["asset-aware", "evidence", asset_type],
        "source_doc_id": manifest.doc_id,
        "source_revision_id": getattr(manifest, "source_pdf_sha256", ""),
        "asset_id": asset.id,
        "page": getattr(asset, "page", None),
        "line_start": getattr(asset, "line_start", None),
        "line_end": getattr(asset, "line_end", None),
        "source_block_id": getattr(asset, "source_block_id", ""),
        "source_order": getattr(asset, "source_order", 0),
        "section_id": getattr(asset, "section_id", ""),
        "section_title": getattr(asset, "section_title", ""),
        "locator_source_sha256": asset_ref["locator_source_sha256"],
    }
    lines = _foam_frontmatter_lines(frontmatter)
    lines.extend(
        [
            "",
            f"# {asset_type.title()} Evidence: {asset.id}",
            "",
            f"- `foam_anchor`: `^{anchor_id}`",
            f"- `wikilink`: `[[{source_ref}#^{anchor_id}]]`",
            f"- `source_doc_id`: `{manifest.doc_id}`",
            f"- `asset_id`: `{asset.id}`",
            f"- `page`: {getattr(asset, 'page', None) or '?'}",
        ]
    )
    line_display = format_line_range(
        getattr(asset, "line_start", None),
        getattr(asset, "line_end", None),
    )
    if line_display:
        lines.append(f"- `lines`: {line_display}")
    section_title = getattr(asset, "section_title", "")
    if section_title:
        lines.append(f"- `section`: {section_title}")
    caption = getattr(asset, "caption", "")
    if caption:
        lines.extend(["", f"> {caption}"])
    if asset_type == "table":
        table_markdown = getattr(asset, "markdown", "")
        if table_markdown:
            lines.extend(["", "## Table", "", table_markdown])
        else:
            lines.extend(["", "## Preview", "", getattr(asset, "preview", "")])
    else:
        figure_path = getattr(asset, "path", "")
        lines.extend(
            [
                "",
                "## Figure",
                "",
                f"- `image_path`: `{figure_path}`",
                f"- `size`: {getattr(asset, 'width', 0)}x{getattr(asset, 'height', 0)}",
                f"- `format`: {getattr(asset, 'ext', '')}",
            ]
        )
    lines.extend(
        [
            "",
            f"^{anchor_id}",
            "",
            "```json",
            json.dumps(asset_ref, ensure_ascii=False, indent=2),
            "```",
            "",
        ]
    )
    note = "\n".join(lines).rstrip() + "\n"
    meta = {
        "asset_type": asset_type,
        "asset_id": asset.id,
        "anchor": f"^{anchor_id}",
        "wikilink": f"[[{source_ref}#^{anchor_id}]]",
        "asset_ref": asset_ref,
    }
    return note, meta


def _write_foam_text(path: Path, text: str, *, overwrite: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.read_text(encoding="utf-8") != text and not overwrite:
        raise FileExistsError(
            f"Foam evidence file already exists: {path}. Pass overwrite=true to replace it."
        )
    path.write_text(text, encoding="utf-8")


def _foam_index_block(payload: dict[str, Any], note_path: Path) -> str:
    note_stem = note_path.stem
    lines = [
        _FOAM_INDEX_START,
        "## Asset-Aware Evidence Index",
        "",
    ]
    for entry in payload.get("entries", []):
        foam = entry.get("foam") or {}
        anchor = foam.get("block_anchor") or ""
        verification = entry.get("verification") or {}
        status = verification.get("status", "not_verified")
        line_display = entry.get("line_display") or "?"
        lines.append(
            "- "
            f"[[{note_stem}#{anchor}]] "
            f"`{entry.get('span_id', '')}` "
            f"p.{entry.get('page') or '?'} {line_display} "
            f"`{status}`"
        )
    lines.extend(["", _FOAM_INDEX_END, ""])
    return "\n".join(lines)


def _update_foam_index(
    index_path: Path, payload: dict[str, Any], note_path: Path
) -> None:
    block = _foam_index_block(payload, note_path)
    if index_path.exists():
        text = index_path.read_text(encoding="utf-8")
    else:
        text = "# Evidence Index\n\n"
    if _FOAM_INDEX_START in text and _FOAM_INDEX_END in text:
        pattern = re.compile(
            re.escape(_FOAM_INDEX_START) + r".*?" + re.escape(_FOAM_INDEX_END) + r"\n?",
            re.DOTALL,
        )
        text = pattern.sub(block, text)
    else:
        text = text.rstrip() + "\n\n" + block
    index_path.parent.mkdir(parents=True, exist_ok=True)
    index_path.write_text(text, encoding="utf-8")


def _foam_asset_index_block(asset_notes: list[dict[str, Any]]) -> str:
    lines = [
        _FOAM_ASSET_INDEX_START,
        "## Asset-Aware Table/Figure Index",
        "",
    ]
    for item in asset_notes:
        lines.append(
            "- "
            f"{item['wikilink']} "
            f"`{item['asset_type']}` "
            f"`{item['asset_id']}` "
            f"p.{item.get('page') or '?'}"
        )
    lines.extend(["", _FOAM_ASSET_INDEX_END, ""])
    return "\n".join(lines)


def _update_foam_asset_index(
    index_path: Path, asset_notes: list[dict[str, Any]]
) -> None:
    block = _foam_asset_index_block(asset_notes)
    if index_path.exists():
        text = index_path.read_text(encoding="utf-8")
    else:
        text = "# Evidence Index\n\n"
    if _FOAM_ASSET_INDEX_START in text and _FOAM_ASSET_INDEX_END in text:
        pattern = re.compile(
            re.escape(_FOAM_ASSET_INDEX_START)
            + r".*?"
            + re.escape(_FOAM_ASSET_INDEX_END)
            + r"\n?",
            re.DOTALL,
        )
        text = pattern.sub(block, text)
    else:
        text = text.rstrip() + "\n\n" + block
    index_path.parent.mkdir(parents=True, exist_ok=True)
    index_path.write_text(text, encoding="utf-8")


def _write_foam_evidence_pack(
    payload: dict[str, Any],
    *,
    wiki_root: str,
    output_path: str,
    index_path: str,
    citation_key: str,
    update_index: bool,
    overwrite: bool,
) -> dict[str, Any]:
    root, target, index = _resolve_foam_write_paths(
        wiki_root=wiki_root,
        output_path=output_path,
        index_path=index_path,
        doc_id=str(payload.get("doc_id") or ""),
        citation_key=citation_key,
    )
    markdown = _format_foam_evidence_pack(payload)
    _write_foam_text(target, markdown, overwrite=overwrite)
    index_written = False
    if update_index:
        _update_foam_index(index, payload, target)
        index_written = True
    return {
        "success": True,
        "operation": "foam_write",
        "wiki_root": str(root),
        "output_path": str(target),
        "index_path": str(index) if index_written else "",
        "index_updated": index_written,
        "doc_id": payload.get("doc_id"),
        "returned": payload.get("returned", 0),
        "matched_count": payload.get("matched_count", 0),
        "wikilinks": [
            (entry.get("foam") or {}).get("wikilink", "")
            for entry in payload.get("entries", [])
        ],
    }


def _selected_manifest_assets(
    manifest: Any,
    asset_type: str | None,
    asset_id: str,
) -> list[tuple[str, Any]]:
    requested = (asset_type or "all").lower()
    selected: list[tuple[str, Any]] = []
    if requested in {"all", "table", "tables"}:
        for table in manifest.assets.tables:
            if asset_id in {"", "all", table.id}:
                selected.append(("table", table))
    if requested in {"all", "figure", "figures"}:
        for figure in manifest.assets.figures:
            if asset_id in {"", "all", figure.id}:
                selected.append(("figure", figure))
    return selected


async def _write_foam_asset_notes(
    doc_id: str,
    *,
    asset_type: str | None,
    asset_id: str,
    wiki_root: str,
    output_dir: str,
    index_path: str,
    citation_key: str,
    update_index: bool,
    overwrite: bool,
    response_format: str,
) -> Any:
    if not wiki_root:
        return _missing_document_param("wiki_root")
    manifest = await document_service.get_manifest(doc_id)
    if manifest is None:
        return {"success": False, "doc_id": doc_id, "error": "Document not found"}
    root = Path(wiki_root).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    output_base = Path(output_dir or "assets")
    if output_base.is_absolute():
        output_base = output_base.resolve()
    else:
        output_base = (root / output_base).resolve()
    if output_base != root and root not in output_base.parents:
        return {
            "success": False,
            "doc_id": doc_id,
            "error": f"Foam asset output path escapes wiki_root: {output_base}",
        }
    selected = _selected_manifest_assets(manifest, asset_type, asset_id)
    if not selected:
        return {
            "success": False,
            "doc_id": doc_id,
            "error": "No matching table/figure assets found",
        }
    written: list[dict[str, Any]] = []
    for kind, asset in selected:
        note, meta = _format_foam_asset_note(
            manifest,
            kind,
            asset,
            citation_key=citation_key,
        )
        filename = f"{_foam_slug(citation_key or doc_id)}-{_foam_slug(asset.id)}.md"
        target = output_base / filename
        try:
            _write_foam_text(target, note, overwrite=overwrite)
        except FileExistsError as exc:
            return {"success": False, "doc_id": doc_id, "error": str(exc)}
        meta.update(
            {
                "path": str(target),
                "page": getattr(asset, "page", None),
            }
        )
        written.append(meta)
    resolved_index = (
        Path(index_path).expanduser() if index_path else Path("Evidence Index.md")
    )
    if not resolved_index.is_absolute():
        resolved_index = root / resolved_index
    resolved_index = resolved_index.resolve()
    if resolved_index != root and root not in resolved_index.parents:
        return {
            "success": False,
            "doc_id": doc_id,
            "error": f"Foam index path escapes wiki_root: {resolved_index}",
        }
    if update_index:
        _update_foam_asset_index(resolved_index, written)
    payload = {
        "success": True,
        "operation": "foam_asset_notes",
        "doc_id": doc_id,
        "wiki_root": str(root),
        "output_dir": str(output_base),
        "index_path": str(resolved_index) if update_index else "",
        "index_updated": update_index,
        "written": written,
        "written_count": len(written),
    }
    if response_format == "json":
        return payload
    lines = [
        f"✅ Wrote {len(written)} Foam asset notes",
        f"- **doc_id:** `{doc_id}`",
        f"- **output_dir:** `{output_base}`",
    ]
    if update_index:
        lines.append(f"- **index_path:** `{resolved_index}`")
    for item in written:
        lines.append(f"- {item['wikilink']} -> `{item['path']}`")
    return "\n".join(lines)


def _extract_json_fences(text: str) -> list[dict[str, Any]]:
    objects: list[dict[str, Any]] = []
    for match in re.finditer(r"```json\s*(.*?)```", text, re.DOTALL | re.IGNORECASE):
        try:
            data = json.loads(match.group(1).strip())
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict):
            objects.append(data)
    return objects


def _foam_note_index(wiki_root: Path) -> dict[str, Path]:
    notes: dict[str, Path] = {}
    for path in wiki_root.rglob("*.md"):
        notes[path.stem] = path
        rel_no_suffix = path.relative_to(wiki_root).with_suffix("").as_posix()
        notes[rel_no_suffix] = path
    return notes


def _verify_asset_ref_payload(ref: dict[str, Any]) -> dict[str, Any]:
    source_type = str(ref.get("source_type") or "")
    if source_type == "span":
        return _verify_span_ref_payload(ref)
    if source_type not in {"table", "figure"}:
        return {
            "valid": False,
            "status": "unsupported",
            "issues": ["Only span/table/figure AssetRef objects can be health-checked"],
        }
    doc_id = str(ref.get("doc_id") or "")
    asset_id = str(ref.get("asset_id") or "")
    if not doc_id or not asset_id:
        return {
            "valid": False,
            "status": "invalid",
            "issues": ["Asset ref must include doc_id and asset_id"],
        }
    manifest = repository.load_manifest(doc_id)
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
    if "source_revision_id" in ref and ref.get("source_revision_id") != getattr(
        manifest, "source_pdf_sha256", ""
    ):
        issues.append("source_revision_id mismatch")
    if (
        ref.get("locator_version")
        and ref.get("locator_version") != _ASSET_LOCATOR_VERSION
    ):
        issues.append("locator_version mismatch")
    expected_locator = _asset_locator_sha256(manifest, source_type, asset)
    if (
        "locator_source_sha256" in ref
        and ref.get("locator_source_sha256") != expected_locator
    ):
        issues.append("locator_source_sha256 mismatch")
    if "page" in ref and ref.get("page") != getattr(asset, "page", None):
        issues.append("page mismatch")
    if "block_id" in ref and ref.get("block_id") != getattr(
        asset, "source_block_id", ""
    ):
        issues.append("source_block_id mismatch")
    if "line_range" in ref and coerce_range(ref.get("line_range")) != [
        getattr(asset, "line_start", None),
        getattr(asset, "line_end", None),
    ]:
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


def _audit_foam_wiki_health(wiki_root: str, *, output_format: str) -> Any:
    if not wiki_root:
        return _missing_document_param("wiki_root")
    root = Path(wiki_root).expanduser().resolve()
    if not root.exists():
        return {
            "success": False,
            "error": f"wiki_root does not exist: {root}",
        }
    note_index = _foam_note_index(root)
    files = sorted(root.rglob("*.md"))
    asset_ref_results: list[dict[str, Any]] = []
    wikilink_issues: list[dict[str, str]] = []
    anchors_by_file: dict[Path, set[str]] = {}

    for path in files:
        text = path.read_text(encoding="utf-8")
        anchors_by_file[path] = set(
            re.findall(r"(?m)(\^[A-Za-z0-9][A-Za-z0-9-]*)\s*$", text)
        )

    for path in files:
        text = path.read_text(encoding="utf-8")
        for ref in _extract_json_fences(text):
            if ref.get("source_type") not in {"span", "table", "figure"}:
                continue
            verification = _verify_asset_ref_payload(ref)
            asset_ref_results.append(
                {
                    "file": str(path.relative_to(root)),
                    "span_id": ref.get("span_id", ""),
                    "asset_id": ref.get("asset_id", ""),
                    "source_type": ref.get("source_type", ""),
                    "doc_id": ref.get("doc_id", ""),
                    "status": verification.get("status", "unknown"),
                    "valid": bool(verification.get("valid")),
                    "issues": verification.get("issues") or [],
                }
            )

        for match in re.finditer(r"!?\[\[([^#\]|]+)#(\^[A-Za-z0-9][^\]|]+)", text):
            target_name = match.group(1).strip()
            anchor = match.group(2).strip()
            target_path = note_index.get(target_name)
            if target_path is None:
                wikilink_issues.append(
                    {
                        "file": str(path.relative_to(root)),
                        "wikilink": match.group(0),
                        "issue": "target note missing",
                    }
                )
            elif anchor not in anchors_by_file.get(target_path, set()):
                wikilink_issues.append(
                    {
                        "file": str(path.relative_to(root)),
                        "wikilink": match.group(0),
                        "issue": "target anchor missing",
                    }
                )

    invalid_refs = [item for item in asset_ref_results if not item["valid"]]
    payload = {
        "success": True,
        "operation": "foam_health",
        "wiki_root": str(root),
        "files_scanned": len(files),
        "asset_refs": len(asset_ref_results),
        "span_asset_refs": len(
            [item for item in asset_ref_results if item["source_type"] == "span"]
        ),
        "valid_refs": len(asset_ref_results) - len(invalid_refs),
        "invalid_refs": len(invalid_refs),
        "wikilink_issues": len(wikilink_issues),
        "asset_ref_results": asset_ref_results,
        "wikilink_issue_details": wikilink_issues,
    }
    if output_format == "json":
        return payload

    lines = [
        "# Foam Citation Health",
        "",
        f"- **files_scanned:** {payload['files_scanned']}",
        f"- **span_asset_refs:** {payload['span_asset_refs']}",
        f"- **valid_refs:** {payload['valid_refs']}",
        f"- **invalid_refs:** {payload['invalid_refs']}",
        f"- **wikilink_issues:** {payload['wikilink_issues']}",
    ]
    if invalid_refs:
        lines.extend(["", "## Invalid AssetRefs"])
        for item in invalid_refs:
            lines.append(
                f"- `{item['file']}` `{item['span_id']}`: "
                f"{', '.join(item['issues']) or item['status']}"
            )
    if wikilink_issues:
        lines.extend(["", "## Wikilink Issues"])
        for item in wikilink_issues:
            lines.append(f"- `{item['file']}` {item['wikilink']}: {item['issue']}")
    return "\n".join(lines)


def _should_force_background_ingest(
    file_paths: list[str],
    *,
    use_marker: bool,
    ocr_enabled: bool,
    page_ranges: list[str] | None,
) -> tuple[bool, str]:
    """Decide whether sync ingestion should become a background job.

    Cline/stdio MCP requests have a finite request timeout. Even small PyMuPDF
    ingests can hit document-level extractor timeouts on Windows when the MCP
    server is launched through stdio, so the presentation layer should return a
    job id immediately and let callers poll with get_job_status.
    """
    return True, (
        "PDF ingestion runs in the background worker to avoid MCP stdio "
        "request timeouts"
    )


def _ingest_job_parameters(
    *,
    use_marker: bool,
    ocr_enabled: bool,
    ocr_language: str,
    rotate_pages: bool,
    deskew: bool,
    marker_max_pages_per_chunk: int,
    extract_figures: bool,
    page_ranges: list[str] | None,
    operation: str = "ingest_documents",
    require_marker: bool = False,
) -> dict[str, Any]:
    from src.presentation import dependencies

    return {
        "operation": operation,
        "use_marker": use_marker,
        "require_marker": require_marker,
        "ocr_enabled": ocr_enabled,
        "ocr_language": ocr_language,
        "rotate_pages": rotate_pages,
        "deskew": deskew,
        "marker_max_pages_per_chunk": marker_max_pages_per_chunk,
        "extract_figures": extract_figures,
        "page_ranges": page_ranges or [],
        "etl_profile": dependencies.etl_profile.name,
    }


async def _create_ingest_job_response(
    file_paths: list[str],
    *,
    use_marker: bool,
    ocr_enabled: bool,
    ocr_language: str,
    rotate_pages: bool,
    deskew: bool,
    marker_max_pages_per_chunk: int,
    extract_figures: bool,
    page_ranges: list[str] | None,
    ctx: Context | None,
    forced_reason: str = "",
    title: str = "ETL Job Created",
    operation: str = "ingest_documents",
    require_marker: bool = False,
) -> str:
    await report_progress(ctx, 20, message="Creating background ETL job")
    try:
        job = await job_service.create_ingest_job(
            file_paths,
            parameters=_ingest_job_parameters(
                use_marker=use_marker,
                ocr_enabled=ocr_enabled,
                ocr_language=ocr_language,
                rotate_pages=rotate_pages,
                deskew=deskew,
                marker_max_pages_per_chunk=marker_max_pages_per_chunk,
                extract_figures=extract_figures,
                page_ranges=page_ranges,
                operation=operation,
                require_marker=require_marker,
            ),
        )
    except RuntimeError as e:
        await log_message(ctx, "error", f"ingest_documents job creation failed: {e}")
        return f"# ??Could Not Create ETL Job\n\n{e!s}"

    await report_progress(ctx, 100, message=f"Created job {job.job_id}")
    await log_message(ctx, "info", f"ingest_documents job created: {job.job_id}")

    backend_note = " (Marker)" if use_marker else ""
    lines = [
        f"# ?? {title}{backend_note}",
        "",
        f"**Job ID:** `{job.job_id}`",
        f"**Files:** {len(file_paths)}",
        f"**Backend:** {'Marker (structured)' if use_marker else 'PyMuPDF (fast)'}",
        f"**Estimated Time:** ~{job.estimated_duration_seconds or 10}s",
    ]
    if forced_reason:
        lines.append(f"**Background Reason:** {forced_reason}")
    lines.extend(
        [
            "",
            f'Use `get_job_status("{job.job_id}")` to check progress.',
            f'Use `cancel_job("{job.job_id}")` if the job is no longer needed.',
            "Or use `list_jobs()` to see all active jobs.",
        ]
    )
    return "\n".join(lines)


@mcp.tool()
async def parse_pdf_structure(
    pdf_path: str,
    output_dir: str | None = None,
    async_mode: bool = True,
    ocr_enabled: bool = False,
    ocr_language: str = "eng",
    rotate_pages: bool = False,
    deskew: bool = False,
    marker_max_pages_per_chunk: int = 0,
    extract_figures: bool = True,
    page_ranges: list[str] | None = None,
    ctx: Context | None = None,
) -> str:
    """Create a background Marker parse job for a PDF."""
    pdf_file = Path(pdf_path)

    await log_message(ctx, "info", f"parse_pdf_structure start: {pdf_path}")
    await report_progress(ctx, 5, message=f"Validating {pdf_file.name}")

    if not pdf_file.exists():
        return f"❌ File not found: {pdf_path}"

    try:
        if page_ranges:
            total_page_count = pdf_extractor.get_page_count(pdf_file)
            normalize_page_ranges(page_ranges, total_page_count)
    except Exception as e:
        await log_message(ctx, "error", f"parse_pdf_structure invalid input: {e}")
        return f"❌ Invalid PDF or page range: {e!s}"

    if not async_mode:
        await log_message(
            ctx,
            "warning",
            "parse_pdf_structure forcing background job despite async_mode=False",
        )

    response = await _create_ingest_job_response(
        [pdf_path],
        use_marker=True,
        ocr_enabled=ocr_enabled,
        ocr_language=ocr_language,
        rotate_pages=rotate_pages,
        deskew=deskew,
        marker_max_pages_per_chunk=marker_max_pages_per_chunk,
        extract_figures=extract_figures,
        page_ranges=page_ranges,
        ctx=ctx,
        forced_reason=(
            "parse_pdf_structure uses Marker and is always routed through the "
            "background job system to avoid MCP stdio request timeouts"
        ),
        title="PDF Structure Parse Job Created",
        operation="parse_pdf_structure",
        require_marker=True,
    )
    if output_dir:
        response += (
            "\n\n**Note:** `output_dir` is ignored for background parses; artifacts "
            "are written under the configured data directory."
        )
    return response


@mcp.tool()
async def search_source_location(
    doc_id: str,
    query: str,
    block_types: list[str] | None = None,
) -> str:
    """
    搜尋文件中的來源位置（頁碼 + bbox）。

    用於驗證答案來源時，精確定位內容在原始 PDF 的位置。

    Args:
        doc_id: 文件 ID
        query: 搜尋關鍵字
        block_types: 限制搜尋的區塊類型（Text, Table, Figure, SectionHeader）

    Returns:
        匹配的區塊列表，包含頁碼和位置
    """
    try:
        blocks_data = repository.load_blocks(doc_id)
    except ValueError as e:
        return f"❌ Invalid doc_id: {e!s}"

    if blocks_data is None:
        return (
            f"❌ Blocks not found for doc_id: {doc_id}. "
            "Run `ingest_documents` with `use_marker=True` first."
        )

    try:
        if block_types:
            blocks_data = [b for b in blocks_data if b.get("block_type") in block_types]

        query_lower = query.lower()
        matches = []
        for block in blocks_data:
            text = block.get("text", "").lower()
            if query_lower in text:
                matches.append(
                    {
                        "block_id": block.get("block_id"),
                        "block_type": block.get("block_type"),
                        "page": block.get("page"),
                        "bbox": block.get("bbox"),
                        "section": block.get("section_hierarchy"),
                        "snippet": block.get("text", "")[:150] + "...",
                    }
                )

        if not matches:
            return f"No matches found for '{query}' in doc_id: {doc_id}"

        lines = [
            f"# 🔍 Source Locations for '{query}'",
            "",
            f"**Found:** {len(matches)} matches",
            "",
        ]

        for i, m in enumerate(matches[:10], 1):
            lines.append(f"## Match {i}")
            lines.append(f"- **Block:** `{m['block_id']}` ({m['block_type']})")
            lines.append(f"- **Page:** {m['page']}")
            if m.get("bbox"):
                lines.append(f"- **BBox:** {m['bbox']}")
            if m.get("section"):
                lines.append(f"- **Section:** {m['section']}")
            lines.append(f"- **Snippet:** _{m['snippet']}_")
            lines.append("")

        if len(matches) > 10:
            lines.append(f"_...and {len(matches) - 10} more matches_")

        return "\n".join(lines)

    except Exception as e:
        return f"❌ Search failed: {e!s}"


@mcp.tool()
async def find_evidence_spans(
    doc_id: str,
    query: str = "",
    span_id: str = "",
    span_kinds: list[str] | None = None,
    limit: int = 10,
) -> str:
    """
    Search citation-ready evidence spans with exact locator metadata.

    Returns span-level AssetRef JSON that can be passed to table_cite.
    """
    spans = load_or_build_evidence_spans(repository, doc_id)
    if not spans:
        status = load_citation_status(repository, doc_id) or {}
        reason = str(status.get("reason") or "").strip()
        if reason:
            return (
                f"No citation-ready evidence spans found for doc_id: {doc_id}. {reason}"
            )
        return (
            f"Citation index not found for doc_id: {doc_id}. "
            "Run ingest_documents again or ensure blocks.json/full markdown exist."
        )

    spans = _filter_evidence_spans(
        spans,
        query=query,
        span_id=span_id,
        span_kinds=span_kinds,
    )

    if not spans:
        target = span_id or query
        return f"No evidence spans found for `{target}` in doc_id: {doc_id}"

    lines = [
        f"# Evidence Spans: {doc_id}",
        "",
        f"**Found:** {len(spans)}",
        "",
    ]
    for index, span in enumerate(spans[: max(1, min(limit, 50))], 1):
        line_range = format_line_range(span.line_start, span.line_end)
        char_range = (
            f"{span.char_start}-{span.char_end}"
            if span.char_start is not None and span.char_end is not None
            else "?"
        )
        quote = span.text[:500] + ("..." if len(span.text) > 500 else "")
        lines.extend(
            [
                f"## Span {index}: `{span.span_id}`",
                f"- **Kind:** {span.span_kind}",
                f"- **Block:** `{span.block_id}`",
                f"- **Page:** {span.page or '?'}",
                f"- **Lines:** {line_range or '?'}",
                f"- **Chars:** {char_range}",
                f"- **SHA256:** `{span.text_sha256}`",
                (
                    "- **CRAAP:** "
                    f"currency={span.craap.currency.status}, "
                    f"relevance={span.craap.relevance.status}, "
                    f"authority={span.craap.authority.status}, "
                    f"accuracy={span.craap.accuracy.status}, "
                    f"purpose={span.craap.purpose.status}"
                ),
                "",
                f"> {quote}",
                "",
                "AssetRef:",
                "```json",
                json.dumps(asset_ref_from_span(span), ensure_ascii=False, indent=2),
                "```",
                "",
            ]
        )

    if len(spans) > limit:
        lines.append(f"_...and {len(spans) - limit} more spans_")

    return "\n".join(lines)


@mcp.tool()
async def verify_citation_ref(ref: dict[str, Any]) -> str:
    """Verify a span-level AssetRef against the persisted citation index."""
    payload = _verify_span_ref_payload(ref)
    issues = payload.get("issues") or []
    doc_id = str(payload.get("doc_id") or ref.get("doc_id") or "")
    span_id = str(payload.get("span_id") or ref.get("span_id") or "")
    if payload.get("status") == "unsupported":
        return "❌ Only span-level AssetRef objects can be verified by this tool."
    if payload.get("status") == "invalid":
        return "❌ Citation ref must include doc_id and span_id."
    if payload.get("status") == "missing":
        return f"❌ Citation span not found: {span_id}"

    status = (
        "✅ Citation ref verified"
        if payload.get("valid")
        else "⚠️ Citation ref mismatch"
    )
    lines = [
        status,
        f"- **doc_id:** `{doc_id}`",
        f"- **span_id:** `{span_id}`",
        f"- **page:** {payload.get('page') or '?'}",
        f"- **lines:** {payload.get('line_display') or '?'}",
        f"- **char_range:** {payload.get('char_range', ['?', '?'])[0]}-{payload.get('char_range', ['?', '?'])[1]}",
        f"- **text_sha256:** `{payload.get('text_sha256', '')}`",
    ]
    if issues:
        lines.append(f"- **issues:** {', '.join(issues)}")
    return "\n".join(lines)


@mcp.tool()
async def citation_bundle(
    doc_id: str,
    query: str = "",
    span_id: str = "",
    span_kinds: list[str] | None = None,
    limit: int = 10,
    include_verification: bool = True,
    output_format: str = "markdown",
    citation_key: str = "",
    wiki_root: str = "",
    output_path: str = "",
    index_path: str = "",
    update_index: bool = True,
    overwrite: bool = False,
) -> Any:
    """
    Export citation-ready evidence spans as a verified bundle.

    Each entry carries AssetRef, exact quote/hash, locator metadata, context,
    conservative CRAAP scaffold, optional verification status, and Foam anchor
    metadata. Use output_format="foam" for a Foam-compatible evidence pack.
    Pass wiki_root to write the pack and optionally update an index note.
    """
    spans = load_or_build_evidence_spans(repository, doc_id)
    if not spans:
        status = load_citation_status(repository, doc_id) or {}
        reason = str(status.get("reason") or "").strip()
        error = (
            f"No citation-ready evidence spans found for doc_id: {doc_id}. {reason}"
            if reason
            else (
                f"Citation index not found for doc_id: {doc_id}. "
                "Run ingest_documents again or ensure blocks.json/full markdown exist."
            )
        )
        payload = {
            "success": False,
            "doc_id": doc_id,
            "bundle_version": "citation-bundle-v1",
            "error": error,
        }
        if output_format == "json":
            return payload
        return error

    filtered = _filter_evidence_spans(
        spans,
        query=query,
        span_id=span_id,
        span_kinds=span_kinds,
    )
    if not filtered:
        target = span_id or query
        payload = {
            "success": False,
            "doc_id": doc_id,
            "bundle_version": "citation-bundle-v1",
            "error": f"No evidence spans found for `{target}` in doc_id: {doc_id}",
        }
        if output_format == "json":
            return payload
        return str(payload["error"])

    bounded_limit = max(1, min(limit, 50))
    entries = [
        _citation_bundle_entry(
            span,
            include_verification=include_verification,
            citation_key=citation_key,
        )
        for span in filtered[:bounded_limit]
    ]
    payload = {
        "success": True,
        "bundle_version": "citation-bundle-v1",
        "doc_id": doc_id,
        "query": query,
        "span_id": span_id,
        "span_kinds": span_kinds or [],
        "citation_key": citation_key,
        "matched_count": len(filtered),
        "returned": len(entries),
        "entries": entries,
    }
    if wiki_root or output_path:
        if output_format != "foam":
            return {
                "success": False,
                "doc_id": doc_id,
                "error": "Foam file writes require output_format='foam'",
            }
        try:
            return _write_foam_evidence_pack(
                payload,
                wiki_root=wiki_root,
                output_path=output_path,
                index_path=index_path,
                citation_key=citation_key,
                update_index=update_index,
                overwrite=overwrite,
            )
        except (FileExistsError, ValueError) as exc:
            return {"success": False, "doc_id": doc_id, "error": str(exc)}
    if output_format == "json":
        return payload
    if output_format == "foam":
        return _format_foam_evidence_pack(payload)
    return _format_citation_bundle(payload)


@mcp.tool()
async def ingest_documents(
    file_paths: list[str],
    async_mode: bool = True,
    use_marker: bool = False,
    ocr_enabled: bool = False,
    ocr_language: str = "eng",
    rotate_pages: bool = False,
    deskew: bool = False,
    marker_max_pages_per_chunk: int = 0,
    extract_figures: bool = True,
    page_ranges: list[str] | None = None,
    ctx: Context | None = None,
) -> str:
    """
    Process PDF files and create Document Manifests.

    ETL Pipeline:
    1. Extract text (to markdown) and images
    2. Generate structured Document Manifest
    3. Index in LightRAG (if enabled)

    Args:
        file_paths: List of absolute paths to PDF files
        async_mode: Kept for backwards compatibility. PDF ingestion is routed
                   to a background job from the MCP tool layer to keep stdio
                   clients responsive.
        use_marker: If True, use Marker for structured parsing (slower but more accurate).
                   Produces blocks.json with bbox/coordinates for precise source tracking.
                   Default False uses PyMuPDF (faster but less structured).
        marker_max_pages_per_chunk: When using Marker, split PDFs into fixed-size page chunks.
                                    Set 0 to use the safe automatic strategy.
        extract_figures: When using Marker, control whether image crops are extracted and saved.
                         Disable this first for image-heavy textbooks to reduce memory pressure.
        page_ranges: 1-indexed inclusive page ranges applied to every input file, e.g. ["1-50", "120-160"].

    Returns:
        Job ID for tracking progress with `get_job_status`.

    Example:
        # Async (recommended for large files):
        ingest_documents(["/papers/study1.pdf"])
        # Then check status:
        get_job_status("job_xxx")

        # With Marker for precise source tracking:
        ingest_documents(["/papers/textbook.pdf"], use_marker=True)
    """
    await log_message(
        ctx,
        "info",
        f"ingest_documents start: files={len(file_paths)} use_marker={use_marker} async_mode={async_mode}",
    )
    await report_progress(ctx, 5, message="Validating ingest request")

    if async_mode:
        return await _create_ingest_job_response(
            file_paths,
            use_marker=use_marker,
            ocr_enabled=ocr_enabled,
            ocr_language=ocr_language,
            rotate_pages=rotate_pages,
            deskew=deskew,
            marker_max_pages_per_chunk=marker_max_pages_per_chunk,
            extract_figures=extract_figures,
            page_ranges=page_ranges,
            ctx=ctx,
        )
    else:
        should_force, reason = _should_force_background_ingest(
            file_paths,
            use_marker=use_marker,
            ocr_enabled=ocr_enabled,
            page_ranges=page_ranges,
        )
        if should_force:
            await log_message(
                ctx,
                "warning",
                f"ingest_documents forcing background job: {reason}",
            )
            return await _create_ingest_job_response(
                file_paths,
                use_marker=use_marker,
                ocr_enabled=ocr_enabled,
                ocr_language=ocr_language,
                rotate_pages=rotate_pages,
                deskew=deskew,
                marker_max_pages_per_chunk=marker_max_pages_per_chunk,
                extract_figures=extract_figures,
                page_ranges=page_ranges,
                ctx=ctx,
                forced_reason=reason,
            )

        # Lazy-load Marker only for explicitly allowed synchronous Marker work.
        if use_marker and document_service.marker_extractor is None:
            try:
                document_service.marker_extractor = get_marker_extractor()
            except RuntimeError as e:
                return (
                    "# ❌ Marker Backend Not Available\n\n"
                    f"{e!s}\n\n"
                    "Use default PyMuPDF mode, or install the optional Marker dependency first."
                )

        await report_progress(ctx, 15, message="Starting synchronous ingestion")
        results = await document_service.ingest(
            file_paths,
            use_marker=use_marker,
            progress_callback=create_subrange_progress_callback(ctx, 15, 95),
            ocr_enabled=ocr_enabled,
            ocr_language=ocr_language,
            rotate_pages=rotate_pages,
            deskew=deskew,
            marker_max_pages_per_chunk=marker_max_pages_per_chunk,
            extract_figures=extract_figures,
            page_ranges=page_ranges,
        )
        await report_progress(ctx, 100, message="Synchronous ingestion finished")
        await log_message(ctx, "info", "ingest_documents sync completed")

        backend_label = "Marker" if use_marker else "PyMuPDF"
        output_lines = [f"# Ingestion Results ({backend_label})\n"]
        success_count = sum(1 for r in results if r.success)
        output_lines.append(f"**Processed:** {success_count}/{len(results)} files\n")
        if ocr_enabled:
            output_lines.append(
                f"**OCR:** enabled ({ocr_language}, rotate_pages={rotate_pages}, deskew={deskew})\n"
            )
        if use_marker:
            output_lines.append(
                f"**Marker chunk size:** {marker_max_pages_per_chunk or 'auto'}\n"
            )
            output_lines.append(
                f"**Extract figures:** {'yes' if extract_figures else 'no'}\n"
            )
        if page_ranges:
            output_lines.append(f"**Page ranges:** {', '.join(page_ranges)}\n")

        for result in results:
            if result.success:
                output_lines.append(f"\n## ✅ {result.filename}")
                output_lines.append(f"- **doc_id:** `{result.doc_id}`")
                output_lines.append(f"- **title:** {result.title or 'N/A'}")
                output_lines.append(f"- **backend:** {result.backend}")
                output_lines.append(f"- **pages:** {result.pages_processed}")
                output_lines.append(f"- **tables:** {result.tables_found}")
                output_lines.append(f"- **figures:** {result.figures_found}")
                output_lines.append(f"- **sections:** {result.sections_found}")
                output_lines.append(
                    f"- **time:** {result.processing_time_seconds:.2f}s"
                )
                if result.backend == "marker":
                    output_lines.append("- **blocks.json:** ✅ Created")
                for warning in result.warnings:
                    output_lines.append(f"- **warning:** {warning}")
            else:
                output_lines.append(f"\n## ❌ {result.filename}")
                output_lines.append(f"- **error:** {result.error}")

        return "\n".join(output_lines)


@mcp.tool()
async def list_documents() -> str:
    """
    List all processed documents with summaries.

    Returns:
        List of documents with doc_id, title, and asset counts
    """
    documents = await document_service.list_documents()

    if not documents:
        return "No documents found. Use `ingest_documents` to process PDF files."

    output_lines = [f"# Documents ({len(documents)} total)\n"]

    for doc in documents:
        output_lines.append(f"## {doc.title or doc.filename}")
        output_lines.append(f"- **doc_id:** `{doc.doc_id}`")
        output_lines.append(f"- **filename:** {doc.filename}")
        output_lines.append(f"- **tables:** {doc.table_count}")
        output_lines.append(f"- **figures:** {doc.figure_count}")
        output_lines.append(f"- **sections:** {doc.section_count}")
        output_lines.append(f"- **text_quality:** {doc.text_quality_status}")
        if doc.ocr_recommended:
            output_lines.append("- **ocr_recommended:** yes")
        output_lines.append(f"- **ingested:** {doc.ingested_at}")
        output_lines.append("")

    return "\n".join(output_lines)


@mcp.tool()
async def delete_document(doc_id: str) -> str:
    """
    刪除已攝入的 PDF 文件及其本地 artifacts。

    會移除 data/{doc_id}/ 下的 manifest、markdown、images、blocks.json 等檔案。
    若啟用了 LightRAG，會一併嘗試刪除對應的知識圖譜文件索引。
    """
    result = await document_service.delete_document(doc_id)
    if not result.get("success"):
        return f"❌ 刪除失敗：{result.get('error', '未知錯誤')}"

    lines = [
        "✅ PDF 文件已刪除",
        f"- **doc_id**: `{result.get('doc_id', '')}`",
        f"- **filename**: {result.get('filename', '')}",
    ]
    if "knowledge_graph_status" in result:
        lines.append(
            f"- **knowledge_graph**: {result.get('knowledge_graph_status', 'unknown')}"
        )
    for warning in result.get("warnings", []):
        lines.append(f"- **warning**: {warning}")
    return "\n".join(lines)


@mcp.tool()
async def convert_pdf_to_docx(
    doc_id: str,
    output_path: str | None = None,
    mode: str = "content",
    async_mode: bool = True,
    ctx: Context | None = None,
) -> str:
    """
    將已攝入的 PDF 文件轉為 DOCX。

    轉換範圍：
    - `content`：內容層重建。根據 PDF ETL 的 Markdown/表格/圖片生成可讀 DOCX。
    - `fidelity`：目前不支援，因為 PDF ETL 並非版面可逆。
    - `async_mode`：預設建立背景 conversion job；設為 False 可沿用同步回傳。
    """
    await log_message(ctx, "info", f"convert_pdf_to_docx start: {doc_id}")
    if async_mode:
        parameters = {
            "operation": "pdf_to_docx",
            "source": doc_id,
            "target_format": "docx",
            "output_path": output_path,
            "mode": mode,
        }

        async def handler(progress: Any) -> dict[str, Any]:
            await progress.report(
                step=2,
                phase="Converting",
                message=f"Converting {doc_id} to DOCX",
            )
            result = await document_service.convert_pdf_to_docx(
                doc_id,
                output_path,
                mode=mode,
            )
            await progress.report(
                step=3,
                phase="Packaging",
                message=f"Finalizing DOCX conversion for {doc_id}",
            )
            return conversion_result_payload(
                result,
                operation="pdf_to_docx",
                source=doc_id,
                target_format="docx",
            )

        return await create_conversion_job_response(
            job_service,
            operation="pdf_to_docx",
            source=doc_id,
            target_format="docx",
            parameters=parameters,
            handler=handler,
            ctx=ctx,
        )

    await report_progress(ctx, 10, message=f"Converting {doc_id} to DOCX")
    result = await document_service.convert_pdf_to_docx(
        doc_id,
        output_path,
        mode=mode,
    )
    if not result.get("success"):
        await log_message(ctx, "error", f"convert_pdf_to_docx failed: {doc_id}")
        return f"❌ 轉換失敗：{result.get('error', '未知錯誤')}"

    await report_progress(ctx, 100, message=f"Finished DOCX conversion for {doc_id}")
    await log_message(ctx, "info", f"convert_pdf_to_docx complete: {doc_id}")

    return "\n".join(
        [
            "✅ PDF → DOCX 轉換成功",
            f"- **doc_id**: `{result.get('doc_id', '')}`",
            f"- **mode**: {result.get('mode', mode)}",
            f"- **output_path**: `{result.get('output_path', '')}`",
            f"- **figures_embedded**: {result.get('figures_embedded', 0)}",
            f"- **tables_found**: {result.get('tables_found', 0)}",
        ]
    )


@mcp.tool()
async def convert_pdf_to_pptx(
    doc_id: str,
    output_path: str | None = None,
    mode: str = "content",
    async_mode: bool = True,
    ctx: Context | None = None,
) -> str:
    """
    將已攝入的 PDF 文件轉為 PPTX。

    轉換範圍：
    - `content`：依據 PDF ETL 的 Markdown/圖像生成可編輯投影片。
    - `async_mode`：預設建立背景 conversion job；設為 False 可沿用同步回傳。
    """
    await log_message(ctx, "info", f"convert_pdf_to_pptx start: {doc_id}")
    if async_mode:
        parameters = {
            "operation": "pdf_to_pptx",
            "source": doc_id,
            "target_format": "pptx",
            "output_path": output_path,
            "mode": mode,
        }

        async def handler(progress: Any) -> dict[str, Any]:
            await progress.report(
                step=2,
                phase="Converting",
                message=f"Converting {doc_id} to PPTX",
            )
            result = await document_service.convert_pdf_to_pptx(
                doc_id,
                output_path,
                mode=mode,
            )
            await progress.report(
                step=3,
                phase="Packaging",
                message=f"Finalizing PPTX conversion for {doc_id}",
            )
            return conversion_result_payload(
                result,
                operation="pdf_to_pptx",
                source=doc_id,
                target_format="pptx",
            )

        return await create_conversion_job_response(
            job_service,
            operation="pdf_to_pptx",
            source=doc_id,
            target_format="pptx",
            parameters=parameters,
            handler=handler,
            ctx=ctx,
        )

    await report_progress(ctx, 10, message=f"Converting {doc_id} to PPTX")
    result = await document_service.convert_pdf_to_pptx(
        doc_id,
        output_path,
        mode=mode,
    )
    if not result.get("success"):
        await log_message(ctx, "error", f"convert_pdf_to_pptx failed: {doc_id}")
        return f"❌ 轉換失敗：{result.get('error', '未知錯誤')}"

    await report_progress(ctx, 100, message=f"Finished PPTX conversion for {doc_id}")
    await log_message(ctx, "info", f"convert_pdf_to_pptx complete: {doc_id}")

    return "\n".join(
        [
            "✅ PDF → PPTX 轉換成功",
            f"- **doc_id**: `{result.get('doc_id', '')}`",
            f"- **mode**: {result.get('mode', mode)}",
            f"- **output_path**: `{result.get('output_path', '')}`",
            f"- **slides_created**: {result.get('slides_created', 0)}",
            f"- **figure_slides**: {result.get('figure_slides', 0)}",
        ]
    )


@mcp.tool()
async def inspect_document_manifest(doc_id: str) -> str:
    """
    Get detailed Document Manifest for precise asset retrieval.

    The manifest contains:
    - Document metadata (title, pages, etc.)
    - Tables list with IDs and descriptions
    - Figures list with IDs, page numbers, and dimensions
    - Sections list with IDs and titles
    - LightRAG entities (if indexed)

    Use this to discover available assets before fetching.

    Args:
        doc_id: Document identifier from ingest_documents or list_documents

    Returns:
        Structured manifest in markdown format
    """
    manifest = await document_service.get_manifest(doc_id)

    if not manifest:
        return f"Document not found: `{doc_id}`"

    output_lines = [f"# Document Manifest: {manifest.title or manifest.filename}\n"]
    output_lines.append(f"**doc_id:** `{manifest.doc_id}`")
    output_lines.append(f"**pages:** {manifest.page_count}")
    output_lines.append(f"**text_quality:** {manifest.text_quality_status}")
    output_lines.append(f"**visible_text_chars:** {manifest.visible_text_chars}")
    output_lines.append(f"**visible_text_lines:** {manifest.visible_text_lines}")
    output_lines.append(f"**repeated_line_ratio:** {manifest.repeated_line_ratio:.2f}")
    output_lines.append(
        f"**ocr_recommended:** {'yes' if manifest.ocr_recommended else 'no'}"
    )
    if manifest.text_quality_reason:
        output_lines.append(f"**text_quality_reason:** {manifest.text_quality_reason}")
    output_lines.append(f"**ingested:** {manifest.ingested_at}")

    # Tables section
    output_lines.append(f"\n## Tables ({len(manifest.assets.tables)})")
    if manifest.assets.tables:
        for table in manifest.assets.tables:
            output_lines.append(f"\n### `{table.id}` (page {table.page})")
            output_lines.append(f"_{table.caption}_")
            output_lines.append(f"Rows: {table.row_count}, Cols: {table.col_count}")
    else:
        output_lines.append("_No tables found_")

    # Figures section
    output_lines.append(f"\n## Figures ({len(manifest.assets.figures)})")
    if manifest.assets.figures:
        for fig in manifest.assets.figures:
            output_lines.append(f"\n### `{fig.id}` (page {fig.page})")
            if fig.caption:
                output_lines.append(f"_{fig.caption}_")
            output_lines.append(f"Size: {fig.width}×{fig.height} ({fig.ext})")
    else:
        output_lines.append("_No figures found_")

    # Sections section
    output_lines.append(f"\n## Sections ({len(manifest.assets.sections)})")
    if manifest.assets.sections:
        for sec in manifest.assets.sections:
            indent = "  " * (sec.level - 1) if sec.level > 1 else ""
            output_lines.append(
                f"{indent}- `{sec.id}`: {sec.title} ({display_line_range(sec.start_line, sec.end_line)})"
            )
    else:
        output_lines.append("_No sections found_")

    # LightRAG entities
    if manifest.lightrag_entities:
        output_lines.append(
            f"\n## Knowledge Graph Entities ({len(manifest.lightrag_entities)})"
        )
        output_lines.append(", ".join(manifest.lightrag_entities[:20]))
        if len(manifest.lightrag_entities) > 20:
            output_lines.append(f"... and {len(manifest.lightrag_entities) - 20} more")

    return "\n".join(output_lines)


@mcp.tool()
async def export_document_segmentation(
    doc_id: str,
    page: int | None = None,
    limit: int | None = None,
    output_path: str | None = None,
    ctx: Context | None = None,
) -> str:
    """匯出整合 manifest、blocks、assets、reading order 的 segmentation schema。"""
    await log_message(ctx, "info", f"export_document_segmentation start: {doc_id}")
    await report_progress(ctx, 10, message=f"Loading manifest for {doc_id}")

    target = await segmentation_service.save_document_segmentation(
        doc_id,
        output_path=output_path,
        page=page,
        limit=limit,
    )
    segmentation = await segmentation_service.export_document_segmentation(
        doc_id,
        page=page,
        limit=limit,
    )

    await report_progress(ctx, 100, message=f"Segmentation exported for {doc_id}")
    await log_message(ctx, "info", f"export_document_segmentation complete: {doc_id}")

    summary_lines = [
        "# Unified Segmentation Export",
        "",
        f"**doc_id:** `{segmentation.doc_id}`",
        f"**backend:** {segmentation.source_backend}",
        f"**reading_order_policy:** {segmentation.reading_order_policy}",
        f"**segments:** {len(segmentation.segments)}",
        f"**pages:** {segmentation.page_count}",
        f"**output:** `{target}`",
        "",
        "## Segment Counts by Page",
    ]
    for page_number, count in segmentation.page_count_summary().items():
        summary_lines.append(f"- Page {page_number}: {count}")

    preview_segments = segmentation.segments[:5]
    if preview_segments:
        summary_lines.extend(["", "## Preview"])
        for segment in preview_segments:
            summary_lines.append(
                f"- #{segment.reading_order} P{segment.page_number} {segment.segment_type}"
                f" [{segment.segment_id}]"
            )

    return "\n".join(summary_lines)


@mcp.tool()
async def visualize_document_layout(
    doc_id: str,
    page: int = 1,
    show_labels: bool = True,
    include_reading_order: bool = True,
    output_path: str | None = None,
    ctx: Context | None = None,
) -> list[TextContent | ImageContent]:
    """產生 PDF page overlay，直接檢查 block bbox、類型與 reading order。"""
    await log_message(
        ctx, "info", f"visualize_document_layout start: {doc_id} page={page}"
    )
    await report_progress(
        ctx, 10, message=f"Loading segmentation for {doc_id} page {page}"
    )

    segmentation = await segmentation_service.export_document_segmentation(
        doc_id, page=page
    )
    await report_progress(
        ctx, 55, message=f"Rendering layout overlay for {doc_id} page {page}"
    )
    doc_dir = repository.get_doc_dir(doc_id)
    safe_output_path = None
    if output_path:
        try:
            safe_output_path = str(
                resolve_document_output_path(
                    doc_dir,
                    output_path,
                    default_name=f"layout_page_{page}.png",
                    allowed_suffixes={".png"},
                )
            )
        except ValueError as e:
            return [TextContent(type="text", text=f"❌ {e!s}")]
    overlay = layout_visualizer.render_page_overlay(
        doc_dir,
        segmentation,
        page,
        show_labels=show_labels,
        include_reading_order=include_reading_order,
        output_path=safe_output_path,
    )

    await report_progress(
        ctx, 100, message=f"Layout overlay ready for {doc_id} page {page}"
    )
    await log_message(
        ctx, "info", f"visualize_document_layout complete: {doc_id} page={page}"
    )

    summary = [
        f"## Layout Overlay: {doc_id}",
        f"**Page:** {page}",
        f"**Segments:** {len(segmentation.segments)}",
        f"**Image Size:** {overlay.width}×{overlay.height}",
    ]
    if overlay.output_path:
        summary.append(f"**Saved To:** {overlay.output_path}")

    return [
        TextContent(type="text", text="\n".join(summary)),
        ImageContent(type="image", data=overlay.image_base64, mimeType="image/png"),
    ]


@mcp.tool()
async def ocr_pdf_document(
    pdf_path: str,
    output_path: str | None = None,
    language: str = "eng",
    rotate_pages: bool = False,
    deskew: bool = False,
    ctx: Context | None = None,
) -> str:
    """Create a background OCR ingest job instead of blocking the MCP request."""
    pdf_file = Path(pdf_path)
    await log_message(ctx, "info", f"ocr_pdf_document start: {pdf_path}")
    await report_progress(ctx, 10, message=f"Creating OCR job for {pdf_file.name}")

    if not pdf_file.exists():
        return f"❌ File not found: {pdf_path}"

    response = await _create_ingest_job_response(
        [pdf_path],
        use_marker=False,
        ocr_enabled=True,
        ocr_language=language,
        rotate_pages=rotate_pages,
        deskew=deskew,
        marker_max_pages_per_chunk=0,
        extract_figures=True,
        page_ranges=None,
        ctx=ctx,
        forced_reason=(
            "OCR preprocessing can spawn long-running OCR engines, so it is "
            "always routed through the background job system"
        ),
        title="OCR Job Created",
        operation="ocr_pdf_document",
    )
    if output_path:
        response += (
            "\n\n**Note:** `output_path` is ignored for background OCR; the OCR "
            "artifact is saved as `ocr_processed.pdf` inside the created document "
            "artifact directory."
        )
    return response


@mcp.tool()
async def fetch_document_asset(
    doc_id: str,
    asset_type: str,
    asset_id: str = "full",
    max_size: int | None = None,
    ctx: Context | None = None,
) -> list[TextContent | ImageContent]:
    """
    Fetch specific content from a document with precision.

    Asset Types:
    - "table": Returns table as markdown (with page number)
    - "figure": Returns image as base64 with page number for verification
    - "section": Returns section text content
    - "full_text": Returns entire document as markdown

    Args:
        doc_id: Document identifier
        asset_type: One of "table", "figure", "section", "full_text"
        asset_id: Asset ID from manifest (e.g., "tab_1", "fig_1_1", "sec_methods")
                  Use "full" for full_text type
        max_size: Maximum image dimension (longest edge) for figures.
                  - None (default): Use default 1024px
                  - 0: Return original size (no resize)
                  - N: Resize to Npx longest edge (e.g., 512, 768, 2048)

    Returns:
        For figures: ImageContent that vision AI can directly analyze
        For others: TextContent in markdown format

    Example:
        # Get Table 1 from document
        fetch_document_asset("abc123", "table", "tab_1")

        # Get figure with default resize (1024px)
        fetch_document_asset("abc123", "figure", "fig_2_1")

        # Get figure at specific size (512px for smaller context)
        fetch_document_asset("abc123", "figure", "fig_2_1", max_size=512)

        # Get original image (no resize)
        fetch_document_asset("abc123", "figure", "fig_2_1", max_size=0)
    """
    await log_message(
        ctx, "info", f"fetch_document_asset start: {doc_id} {asset_type}:{asset_id}"
    )
    await report_progress(
        ctx, 10, message=f"Fetching {asset_type} {asset_id} from {doc_id}"
    )
    result = await asset_service.fetch_asset(
        doc_id, asset_type, asset_id, max_size=max_size
    )

    if not result.success:
        await log_message(ctx, "error", f"fetch_document_asset failed: {result.error}")
        return [TextContent(type="text", text=f"Error: {result.error}")]

    if result.image_base64:
        await report_progress(
            ctx, 100, message=f"Fetched {asset_type} {asset_id} from {doc_id}"
        )
        metadata_lines = [
            f"## Figure: {result.asset_id}",
            f"**Page:** {result.page or 'Unknown'}",
            f"**Size:** {result.width}×{result.height}",
            f"**Format:** {result.image_media_type}",
        ]
        line_range = format_line_range(result.line_start, result.line_end)
        if line_range:
            metadata_lines.append(f"**Line Range:** {line_range}")
        if result.section_title:
            metadata_lines.append(f"**Section:** {result.section_title}")
        if result.source_block_id:
            metadata_lines.append(f"**Source Block:** {result.source_block_id}")
        return [
            TextContent(type="text", text="\n".join(metadata_lines)),
            ImageContent(
                type="image",
                data=result.image_base64,
                mimeType=result.image_media_type or "image/png",
            ),
        ]
    else:
        await report_progress(
            ctx, 100, message=f"Fetched {asset_type} {asset_id} from {doc_id}"
        )
        lines = [f"## {asset_type.title()}: {result.asset_id}"]
        if result.page:
            lines.append(f"**Page:** {result.page}")
        line_range = format_line_range(result.line_start, result.line_end)
        if line_range:
            lines.append(f"**Line Range:** {line_range}")
        if result.section_title:
            lines.append(f"**Section:** {result.section_title}")
        if result.source_block_id:
            lines.append(f"**Source Block:** {result.source_block_id}")
        lines.append("")
        lines.append(result.text_content or "")
        return [TextContent(type="text", text="\n".join(lines))]


@mcp.tool()
async def document(
    op: str,
    file_paths: list[str] | None = None,
    pdf_path: str | None = None,
    doc_id: str | None = None,
    output_dir: str | None = None,
    async_mode: bool = True,
    use_marker: bool = False,
    ocr_enabled: bool = False,
    ocr_language: str = "eng",
    rotate_pages: bool = False,
    deskew: bool = False,
    marker_max_pages_per_chunk: int = 0,
    extract_figures: bool = True,
    page_ranges: list[str] | None = None,
    ctx: Context | None = None,
) -> Any:
    """
    Consolidated PDF document entrypoint.

    Existing document tools stay registered and keep their original contracts.
    """
    operation = _normalize_op(op)
    if operation in {"ingest", "import"}:
        if not file_paths:
            return _missing_document_param("file_paths")
        return await ingest_documents(
            file_paths,
            async_mode=async_mode,
            use_marker=use_marker,
            ocr_enabled=ocr_enabled,
            ocr_language=ocr_language,
            rotate_pages=rotate_pages,
            deskew=deskew,
            marker_max_pages_per_chunk=marker_max_pages_per_chunk,
            extract_figures=extract_figures,
            page_ranges=page_ranges,
            ctx=ctx,
        )
    if operation == "parse":
        source_pdf = pdf_path or (file_paths[0] if file_paths else None)
        if not source_pdf:
            return _missing_document_param("pdf_path")
        return await parse_pdf_structure(
            source_pdf,
            output_dir=output_dir,
            async_mode=async_mode,
            ocr_enabled=ocr_enabled,
            ocr_language=ocr_language,
            rotate_pages=rotate_pages,
            deskew=deskew,
            marker_max_pages_per_chunk=marker_max_pages_per_chunk,
            extract_figures=extract_figures,
            page_ranges=page_ranges,
            ctx=ctx,
        )
    if operation == "list":
        return await list_documents()
    if operation == "delete":
        if not doc_id:
            return _missing_document_param("doc_id")
        return await delete_document(doc_id)
    if operation == "inspect":
        if not doc_id:
            return _missing_document_param("doc_id")
        return await inspect_document_manifest(doc_id)

    return _unsupported_document_op(
        "document",
        op,
        {"delete", "ingest", "inspect", "list", "parse"},
    )


@mcp.tool()
async def document_asset(
    op: str,
    doc_id: str | None = None,
    asset_type: str | None = None,
    asset_id: str = "full",
    max_size: int | None = None,
    path: str | None = None,
    query: str | None = None,
    max_depth: int | None = None,
    response_format: str = "tree",
    include_children: bool = True,
    block_types: list[str] | None = None,
    limit: int | None = None,
    fuzzy: bool = True,
    wiki_root: str = "",
    output_dir: str = "assets",
    index_path: str = "",
    citation_key: str = "",
    update_index: bool = True,
    overwrite: bool = False,
    ctx: Context | None = None,
) -> Any:
    """Consolidated document asset and section entrypoint."""
    operation = _normalize_op(op)
    if not doc_id:
        return _missing_document_param("doc_id")

    if operation == "get":
        if not asset_type:
            return _missing_document_param("asset_type")
        return await fetch_document_asset(
            doc_id,
            asset_type,
            asset_id,
            max_size=max_size,
            ctx=ctx,
        )
    if operation in {"foam_notes", "asset_notes"}:
        return await _write_foam_asset_notes(
            doc_id,
            asset_type=asset_type,
            asset_id=asset_id,
            wiki_root=wiki_root,
            output_dir=output_dir,
            index_path=index_path,
            citation_key=citation_key,
            update_index=update_index,
            overwrite=overwrite,
            response_format=response_format,
        )

    from src.presentation.tools import section_tools

    if operation in {"tree", "list"}:
        return await section_tools.list_section_tree(
            doc_id,
            max_depth,
            response_format,
        )
    if operation == "detail":
        if not path:
            return _missing_document_param("path")
        return await section_tools.get_section_detail(doc_id, path)
    if operation in {"blocks", "list_blocks"}:
        if not path:
            return _missing_document_param("path")
        return await section_tools.get_section_blocks(
            doc_id,
            path,
            include_children,
            block_types,
            limit,
        )
    if operation == "search":
        if not query:
            return _missing_document_param("query")
        return await section_tools.search_sections(doc_id, query, fuzzy)

    return _unsupported_document_op(
        "document_asset",
        op,
        {
            "asset_notes",
            "blocks",
            "detail",
            "foam_notes",
            "get",
            "list",
            "search",
            "tree",
        },
    )


@mcp.tool()
async def evidence(
    op: str,
    doc_id: str | None = None,
    query: str = "",
    span_id: str = "",
    span_kinds: list[str] | None = None,
    limit: int = 10,
    ref: dict[str, Any] | None = None,
    block_types: list[str] | None = None,
    output_format: str = "markdown",
    citation_key: str = "",
    wiki_root: str = "",
    output_path: str = "",
    index_path: str = "",
    update_index: bool = True,
    overwrite: bool = False,
) -> Any:
    """Consolidated citation evidence entrypoint."""
    operation = _normalize_op(op)
    if operation == "find":
        if not doc_id:
            return _missing_document_param("doc_id")
        return await find_evidence_spans(
            doc_id,
            query=query,
            span_id=span_id,
            span_kinds=span_kinds,
            limit=limit,
        )
    if operation == "verify":
        if ref is None:
            return _missing_document_param("ref")
        return await verify_citation_ref(ref)
    if operation == "bundle":
        if not doc_id:
            return _missing_document_param("doc_id")
        return await citation_bundle(
            doc_id,
            query=query,
            span_id=span_id,
            span_kinds=span_kinds,
            limit=limit,
            include_verification=True,
            output_format=output_format,
            citation_key=citation_key,
            wiki_root=wiki_root,
            output_path=output_path,
            index_path=index_path,
            update_index=update_index,
            overwrite=overwrite,
        )
    if operation in {"claim_promotion", "claims", "promote_claims"}:
        if not doc_id:
            return _missing_document_param("doc_id")
        payload = _claim_promotion_payload(
            doc_id=doc_id,
            query=query,
            span_id=span_id,
            span_kinds=span_kinds,
            limit=limit,
            citation_key=citation_key,
        )
        if wiki_root or output_path:
            if output_format != "foam":
                return {
                    "success": False,
                    "doc_id": doc_id,
                    "error": "Foam claim writes require output_format='foam'",
                }
            if not payload.get("success"):
                return payload
            try:
                return _write_foam_claim_promotion_pack(
                    payload,
                    wiki_root=wiki_root,
                    output_path=output_path,
                    index_path=index_path,
                    citation_key=citation_key,
                    update_index=update_index,
                    overwrite=overwrite,
                )
            except (FileExistsError, ValueError) as exc:
                return {"success": False, "doc_id": doc_id, "error": str(exc)}
        if output_format == "json":
            return payload
        if output_format == "foam":
            return _format_foam_claim_promotion_pack(payload)
        return _format_claim_promotion_markdown(payload)
    if operation in {"health", "foam_health", "wiki_health"}:
        return _audit_foam_wiki_health(wiki_root, output_format=output_format)
    if operation in {"locate", "search_location"}:
        if not doc_id:
            return _missing_document_param("doc_id")
        if not query:
            return _missing_document_param("query")
        return await search_source_location(doc_id, query, block_types=block_types)

    return _unsupported_document_op(
        "evidence",
        op,
        {"bundle", "claim_promotion", "find", "health", "locate", "verify"},
    )


@mcp.tool()
async def convert_document(
    source: str,
    target_format: str,
    source_format: str = "auto",
    output_path: str | None = None,
    mode: str = "content",
    md_text: str | None = None,
    async_mode: bool = True,
    ctx: Context | None = None,
) -> Any:
    """
    Consolidated document conversion entrypoint.

    Dispatches to the existing conversion tools so each source family keeps its
    established output-path containment policy.
    """
    source_kind = source_format.strip().lower().replace("markdown", "md")
    target = target_format.strip().lower().lstrip(".")
    if source_kind == "auto":
        suffix = Path(source).suffix.lower()
        if suffix in {".md", ".markdown"}:
            source_kind = "md"
        elif suffix == ".pdf":
            source_kind = "pdf"
        elif suffix in {".doc", ".docx", ".odt", ".ods"} or target in {
            "doc",
            "odt",
            "pdf",
        }:
            source_kind = "docx"
        else:
            source_kind = "pdf"

    if source_kind == "pdf":
        if target == "docx":
            return await convert_pdf_to_docx(
                source,
                output_path=output_path,
                mode=mode,
                async_mode=async_mode,
                ctx=ctx,
            )
        if target == "pptx":
            return await convert_pdf_to_pptx(
                source,
                output_path=output_path,
                mode=mode,
                async_mode=async_mode,
                ctx=ctx,
            )
    elif source_kind == "docx":
        from src.presentation.tools import docx_tools

        if target == "doc":
            return await docx_tools.convert_docx_to_doc(
                source,
                output_path=output_path,
                mode=mode,
                async_mode=async_mode,
                ctx=ctx,
            )
        if target == "pdf":
            return await docx_tools.convert_docx_to_pdf(
                source,
                output_path=output_path,
                mode=mode,
                async_mode=async_mode,
                ctx=ctx,
            )
        if target == "odt":
            return await docx_tools.convert_docx_to_odt(
                source,
                output_path=output_path,
                mode=mode,
                async_mode=async_mode,
                ctx=ctx,
            )
    elif source_kind == "md":
        from src.presentation.tools import docx_tools

        if target in {"doc", "docx", "odt", "pdf"}:
            return await docx_tools.export_markdown(
                md_path=source if md_text is None else None,
                md_text=md_text,
                output_path=output_path,
                output_format=target,
                async_mode=async_mode,
                ctx=ctx,
            )

    return (
        f"Unsupported conversion: {source_kind} -> {target}. "
        "Supported conversions: pdf->docx/pptx, docx->doc/pdf/odt, "
        "markdown->doc/docx/odt/pdf."
    )
